from fastapi import APIRouter

from app.models.schemas import PendingPredictionRequest
from app.services.prediction_service import compute_pending_prediction

router = APIRouter()


@router.post("/api/pending-prediction")
def post_pending_prediction(payload: PendingPredictionRequest):
    return compute_pending_prediction(payload)
