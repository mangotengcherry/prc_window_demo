from fastapi import APIRouter

from app.services.mock_data_service import metadata, reset_mock_data

router = APIRouter()


@router.get("/api/metadata")
def get_metadata():
    return metadata()


@router.post("/api/mock-data/reset")
def reset_data():
    return reset_mock_data()
