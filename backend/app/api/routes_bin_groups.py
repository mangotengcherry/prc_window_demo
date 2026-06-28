from fastapi import APIRouter

from app.models.schemas import BinGroupCreate
from app.services.bin_group_service import create_bin_group, list_bin_groups

router = APIRouter()


@router.post("/api/bin-groups")
def post_bin_group(payload: BinGroupCreate):
    return create_bin_group(payload)


@router.get("/api/bin-groups")
def get_bin_groups():
    return list_bin_groups()
