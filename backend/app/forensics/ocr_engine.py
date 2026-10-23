import io
from typing import Dict, Any, List, Optional
from PIL import Image
import pymupdf
import pytesseract


def extract_text_from_pdf_stream(pdf_bytes: bytes) -> Optional[str]:
    """Extract embedded text directly from digital PDF if available"""
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        full_text = []
        for page in doc:
            full_text.append(page.get_text("text"))
        doc.close()
        text = "\n".join(full_text).strip()
        if len(text) > 40:
            return text
        return None
    except Exception:
        return None


def run_ocr_on_image(pil_img: Image.Image) -> Dict[str, Any]:
    """
    Run OCR on image.
    Uses Tesseract data extraction for word-level bounding boxes and confidence.
    """
    try:
        ocr_data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
        words = []
        confidences = []
        boxes = []

        n_boxes = len(ocr_data['text'])
        for i in range(n_boxes):
            w = ocr_data['text'][i].strip()
            conf = float(ocr_data['conf'][i])
            if w and conf > 0:
                words.append(w)
                confidences.append(conf / 100.0) # Scale to 0.0 - 1.0
                boxes.append({
                    "text": w,
                    "x": ocr_data['left'][i],
                    "y": ocr_data['top'][i],
                    "width": ocr_data['width'][i],
                    "height": ocr_data['height'][i],
                    "conf": conf / 100.0
                })

        full_text = " ".join(words)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.85
        return {
            "text": full_text,
            "confidence": avg_conf,
            "boxes": boxes,
            "engine": "tesseract"
        }
    except Exception:
        # Fallback if tesseract binary is not installed in local test environment
        return {
            "text": "",
            "confidence": 0.0,
            "boxes": [],
            "engine": "fallback_none"
        }


def extract_document_text(
    doc_bytes: bytes,
    mime_type: str,
    preprocessed_image: Optional[Image.Image] = None
) -> Dict[str, Any]:
    """
    Unified extractor:
    1. For PDFs: extracts digital text stream (100% precision)
    2. For scanned documents or images: runs optical character recognition
    """
    if mime_type == "application/pdf":
        digital_text = extract_text_from_pdf_stream(doc_bytes)
        if digital_text:
            return {
                "text": digital_text,
                "confidence": 0.99,
                "boxes": [],
                "engine": "pymupdf_native_stream"
            }

    if preprocessed_image:
        return run_ocr_on_image(preprocessed_image)

    # Convert bytes to PIL Image
    pil_img = Image.open(io.BytesIO(doc_bytes)).convert("RGB")
    return run_ocr_on_image(pil_img)
