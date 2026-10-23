from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import User
from app.schemas.query import AskSentinelRequest, AskSentinelResponse
from app.api.deps import get_current_user, limiter
from app.services.query_service import execute_ask_sentinel_query

router = APIRouter(prefix="/ask-sentinel", tags=["Ask-Sentinel NL Query"])


@router.post("", response_model=AskSentinelResponse)
def ask_sentinel(
    req: AskSentinelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ask-Sentinel Natural Language Query:
    1. Interprets English questions into validated JSON filters
    2. Runs secure parameterized SQLAlchemy queries (never raw LLM SQL)
    3. Strictly enforces role-scoping for institution accounts
    4. Logs every query to the hash-chained audit log
    """
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    res = execute_ask_sentinel_query(
        db=db,
        user=current_user,
        question=req.question.strip(),
        limit=req.limit
    )
    return res
