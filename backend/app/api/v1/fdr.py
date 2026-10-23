import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.entities import (
    User, UserRole, FDRCase, FDRVersion, Document,
    ExtractedField, ForensicFinding, DuplicateMatch, TrustEvent
)
from app.schemas.fdr import (
    FDRCaseResponse, FDRCaseListItem, ExtractedFieldUpdateRequest,
    ExtractedFieldResponse, ForensicFindingResponse, DuplicateMatchResponse
)
from app.api.deps import get_current_user, require_roles
from app.services.storage_service import store_encrypted_document, retrieve_and_decrypt_document
from app.services.pipeline_service import process_fdr_document
from app.forensics.preprocessor import pdf_bytes_to_images
from app.forensics.checks import compute_ela_heatmap
from PIL import Image

router = APIRouter(prefix="/fdr", tags=["FDR Operations"])


@router.post("/upload", response_model=FDRCaseResponse, status_code=status.HTTP_201_CREATED)
async def upload_fdr(
    file: UploadFile = File(...),
    institution_id: Optional[str] = Form(None),
    existing_case_id: Optional[str] = Form(None),
    change_reason: str = Form("INITIAL_SUBMISSION"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Intake endpoint for FDR submission:
    1. Validates magic bytes and max size limit
    2. Computes SHA-256 hash
    3. AES-256-GCM encrypts to MinIO / local storage
    4. Executes forensic inspection pipeline
    5. Evaluates Trust Ladder L1 -> L2 transition
    """
    # Enforce institution boundaries
    effective_inst_id = institution_id
    if current_user.role == UserRole.INSTITUTION:
        if not current_user.institution_id:
            raise HTTPException(status_code=400, detail="User has no associated institution")
        effective_inst_id = current_user.institution_id
    elif not effective_inst_id:
        effective_inst_id = "INST-001"

    contents = await file.read()
    try:
        storage_path, sha256_hash, file_size, mime_type = store_encrypted_document(
            filename=file.filename or "fdr_document.pdf",
            raw_data=contents
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Create Document record
    doc = Document(
        filename=file.filename or "fdr_document.pdf",
        original_name=file.filename or "fdr_document.pdf",
        mime_type=mime_type,
        file_size=file_size,
        storage_path=storage_path,
        sha256_hash=sha256_hash,
        is_encrypted=True
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Run intake & forensics pipeline
    res = process_fdr_document(
        db=db,
        document=doc,
        institution_id=effective_inst_id,
        user_id=current_user.id,
        existing_case_id=existing_case_id,
        change_reason=change_reason
    )

    case_obj = db.query(FDRCase).filter(FDRCase.id == res["case_id"]).first()
    return case_obj


@router.get("/cases", response_model=List[FDRCaseListItem])
def list_fdr_cases(
    trust_level: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List FDR cases with role-based scoping:
    Institutions only see their own cases. Officials and Admins see all cases across AICTE.
    """
    query = db.query(FDRCase)
    if current_user.role == UserRole.INSTITUTION:
        query = query.filter(FDRCase.institution_id == current_user.institution_id)

    if trust_level:
        query = query.filter(FDRCase.trust_level == trust_level)
    if status:
        query = query.filter(FDRCase.status == status)
    if search:
        query = query.filter(
            (FDRCase.fdr_number.ilike(f"%{search}%")) |
            (FDRCase.case_number.ilike(f"%{search}%")) |
            (FDRCase.bank_name.ilike(f"%{search}%"))
        )

    cases = query.order_by(desc(FDRCase.created_at)).offset(offset).limit(limit).all()

    items = []
    for c in cases:
        # Count unresolved flags on current version
        unresolved = 0
        current_v = next((v for v in c.versions if v.id == c.current_version_id), None)
        if current_v:
            unresolved = len([f for f in current_v.forensic_findings if f.status == "ANOMALY_FLAGGED" and not f.is_resolved])

        items.append(FDRCaseListItem(
            id=c.id,
            case_number=c.case_number,
            institution_id=c.institution_id,
            institution_name=c.institution.name if c.institution else None,
            bank_name=c.bank_name,
            fdr_number=c.fdr_number,
            principal_amount=c.principal_amount,
            maturity_amount=c.maturity_amount,
            interest_rate=c.interest_rate,
            issue_date=c.issue_date,
            maturity_date=c.maturity_date,
            trust_level=c.trust_level,
            status=c.status,
            unresolved_flags_count=unresolved,
            created_at=c.created_at
        ))
    return items


@router.get("/cases/{case_id}", response_model=FDRCaseResponse)
def get_fdr_case_detail(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    case = db.query(FDRCase).filter(FDRCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="FDR Case not found")

    if current_user.role == UserRole.INSTITUTION and case.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Access forbidden to cases from other institutions")

    return case


@router.get("/cases/{case_id}/duplicates", response_model=List[DuplicateMatchResponse])
def get_case_duplicate_matches(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    matches = db.query(DuplicateMatch).filter(
        (DuplicateMatch.primary_case_id == case_id) |
        (DuplicateMatch.matching_case_id == case_id)
    ).all()
    return matches


@router.put("/extracted-fields/{field_id}", response_model=ExtractedFieldResponse)
def update_extracted_field(
    field_id: str,
    req: ExtractedFieldUpdateRequest,
    current_user: User = Depends(require_roles([UserRole.OFFICIAL, UserRole.ADMIN, UserRole.INSTITUTION])),
    db: Session = Depends(get_db)
):
    """
    Allow manual correction of OCR-extracted fields that were flagged below confidence threshold
    """
    field = db.query(ExtractedField).filter(ExtractedField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Extracted field not found")

    field.manual_corrected_value = req.manual_corrected_value
    field.is_flagged_for_manual_review = False
    db.commit()
    db.refresh(field)
    return field


@router.get("/cases/{case_id}/ela-heatmap")
def get_ela_heatmap_image(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns PNG image bytes of Error Level Analysis (ELA) heatmap for the FDR document
    """
    case = db.query(FDRCase).filter(FDRCase.id == case_id).first()
    if not case or not case.versions:
        raise HTTPException(status_code=404, detail="FDR Case or document version not found")

    version = next((v for v in case.versions if v.id == case.current_version_id), case.versions[0])
    if not version.document:
        raise HTTPException(status_code=404, detail="No document associated with version")

    doc_bytes = retrieve_and_decrypt_document(version.document.storage_path, expected_sha256=version.document.sha256_hash)
    if version.document.mime_type == "application/pdf":
        imgs = pdf_bytes_to_images(doc_bytes, dpi=150)
        base_img = imgs[0] if imgs else Image.new("RGB", (600, 800), "white")
    else:
        base_img = Image.open(io.BytesIO(doc_bytes)).convert("RGB")

    heatmap, _ = compute_ela_heatmap(base_img)
    buf = io.BytesIO()
    heatmap.save(buf, format="PNG")
    buf.seek(0)

    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/cases/{case_id}/document")
def download_fdr_document(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns decrypted original document bytes (PDF/image) for viewing or download.
    """
    case = db.query(FDRCase).filter(FDRCase.id == case_id).first()
    if not case or not case.versions:
        raise HTTPException(status_code=404, detail="FDR Case not found")

    if current_user.role == UserRole.INSTITUTION and case.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    version = next((v for v in case.versions if v.id == case.current_version_id), case.versions[0])
    if not version.document:
        raise HTTPException(status_code=404, detail="No document found")

    doc_bytes = retrieve_and_decrypt_document(version.document.storage_path, expected_sha256=version.document.sha256_hash)
    return Response(
        content=doc_bytes,
        media_type=version.document.mime_type or "application/pdf",
        headers={"Content-Disposition": f"inline; filename={version.document.original_name or 'fdr_document.pdf'}"}
    )


@router.get("/cases/{case_id}/preview")
def get_fdr_preview_image(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns PNG image bytes of page 1 of the FDR document for inline preview.
    """
    case = db.query(FDRCase).filter(FDRCase.id == case_id).first()
    if not case or not case.versions:
        raise HTTPException(status_code=404, detail="FDR Case not found")

    if current_user.role == UserRole.INSTITUTION and case.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    version = next((v for v in case.versions if v.id == case.current_version_id), case.versions[0])
    if not version.document:
        raise HTTPException(status_code=404, detail="No document found")

    doc_bytes = retrieve_and_decrypt_document(version.document.storage_path, expected_sha256=version.document.sha256_hash)
    if version.document.mime_type == "application/pdf":
        imgs = pdf_bytes_to_images(doc_bytes, dpi=150)
        base_img = imgs[0] if imgs else Image.new("RGB", (600, 800), "white")
    else:
        base_img = Image.open(io.BytesIO(doc_bytes)).convert("RGB")

    buf = io.BytesIO()
    base_img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")

