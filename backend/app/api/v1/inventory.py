from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.profile import current_profile
from app.db.session import get_db
from app.models import InventoryItem
from app.schemas.inventory import InventoryCreate, InventoryResponse
from app.services.food_matching import normalize_food

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryResponse])
def list_inventory(db: Session = Depends(get_db)):
    profile = current_profile(db)
    return db.query(InventoryItem).filter_by(profile_id=profile.id).order_by(InventoryItem.created_at).all()


@router.post("", response_model=InventoryResponse, status_code=201)
def add_inventory(payload: InventoryCreate, db: Session = Depends(get_db)):
    profile = current_profile(db)
    name = " ".join(payload.name.strip().split())
    normalized = normalize_food(name)
    if not normalized:
        raise ApiError(422, "INVALID_INVENTORY_ITEM", "Food name cannot be empty.")
    existing = db.query(InventoryItem).filter_by(profile_id=profile.id, normalized_name=normalized).first()
    if existing:
        raise ApiError(409, "DUPLICATE_INVENTORY_ITEM", "That food is already in the inventory.")
    item = InventoryItem(profile_id=profile.id, name=name, normalized_name=normalized)
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "DUPLICATE_INVENTORY_ITEM", "That food is already in the inventory.") from exc
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_inventory(item_id: str, db: Session = Depends(get_db)):
    profile = current_profile(db)
    item = db.query(InventoryItem).filter_by(id=item_id, profile_id=profile.id).first()
    if not item:
        raise ApiError(404, "INVENTORY_ITEM_NOT_FOUND", "Inventory item not found.")
    db.delete(item)
    db.commit()

