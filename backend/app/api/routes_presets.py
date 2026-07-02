from fastapi import APIRouter, Header

from app.models.schemas import (
    CustomEdsItemCreate,
    PresetCreate,
    PresetDuplicate,
    PresetFolderCreate,
    PresetFolderUpdate,
    PresetPatch,
    PresetRevisionCreate,
)
from app.services import preset_service

router = APIRouter()


def _user(x_user: str | None) -> str:
    return x_user or "me"


@router.get("/api/preset-tree")
def get_preset_tree():
    return preset_service.get_preset_tree()


@router.post("/api/preset-folders")
def post_preset_folder(payload: PresetFolderCreate):
    return preset_service.create_folder(payload.name)


@router.patch("/api/preset-folders/{folder_id}")
def patch_preset_folder(folder_id: str, payload: PresetFolderUpdate):
    return preset_service.rename_folder(folder_id, payload.name)


@router.delete("/api/preset-folders/{folder_id}")
def delete_preset_folder(folder_id: str):
    return preset_service.delete_folder(folder_id)


@router.post("/api/presets")
def post_preset(payload: PresetCreate, x_user: str | None = Header(default=None, alias="X-User")):
    return preset_service.create_preset(payload, _user(x_user))


@router.post("/api/presets/{preset_id}/revisions")
def post_preset_revision(
    preset_id: str, payload: PresetRevisionCreate, x_user: str | None = Header(default=None, alias="X-User")
):
    return preset_service.add_revision(preset_id, payload, _user(x_user))


@router.get("/api/presets/{preset_id}/revisions/{rev}")
def get_preset_revision(preset_id: str, rev: int):
    return preset_service.get_revision(preset_id, rev)


@router.patch("/api/presets/{preset_id}")
def patch_preset(preset_id: str, payload: PresetPatch, x_user: str | None = Header(default=None, alias="X-User")):
    return preset_service.patch_preset(preset_id, payload, _user(x_user))


@router.post("/api/presets/{preset_id}/duplicate")
def post_preset_duplicate(
    preset_id: str, payload: PresetDuplicate, x_user: str | None = Header(default=None, alias="X-User")
):
    return preset_service.duplicate_preset(preset_id, payload, _user(x_user))


@router.delete("/api/presets/{preset_id}")
def delete_preset(preset_id: str, x_user: str | None = Header(default=None, alias="X-User")):
    return preset_service.delete_preset(preset_id, _user(x_user))


@router.get("/api/custom-eds-items")
def get_custom_eds_items():
    return preset_service.list_custom_eds_items()


@router.post("/api/custom-eds-items")
def post_custom_eds_item(payload: CustomEdsItemCreate, x_user: str | None = Header(default=None, alias="X-User")):
    return preset_service.create_custom_eds_item(payload, _user(x_user))


@router.delete("/api/custom-eds-items/{name}")
def delete_custom_eds_item(name: str, x_user: str | None = Header(default=None, alias="X-User")):
    return preset_service.delete_custom_eds_item(name, _user(x_user))
