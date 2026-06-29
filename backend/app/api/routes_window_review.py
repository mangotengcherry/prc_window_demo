from fastapi import APIRouter

from app.models.schemas import WindowReviewRequest
from app.services.window_analysis_service import compute_window_review

router = APIRouter()


@router.post("/api/window-review")
def post_window_review(payload: WindowReviewRequest):
    return compute_window_review(payload)
