from fastapi import APIRouter

from app.models.schemas import SelectionPreviewRequest
from app.services import selection_service

router = APIRouter()


@router.post("/api/selection/preview")
def post_selection_preview(payload: SelectionPreviewRequest):
    return selection_service.preview(payload)
