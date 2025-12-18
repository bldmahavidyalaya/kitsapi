from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.db.session import get_session
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate
from app.models.item import Item

router = APIRouter()


@router.post("/items", response_model=ItemRead)
def create_item(payload: ItemCreate, session: Session = Depends(get_session)):
    item = Item.from_orm(payload)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.get("/items", response_model=List[ItemRead])
def list_items(session: Session = Depends(get_session)):
    items = session.exec(select(Item)).all()
    return items


@router.get("/items/{item_id}", response_model=ItemRead)
def get_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.patch("/items/{item_id}", response_model=ItemRead)
def update_item(item_id: int, payload: ItemUpdate, session: Session = Depends(get_session)):
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item_data = payload.dict(exclude_unset=True)
    for k, v in item_data.items():
        setattr(item, k, v)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/items/{item_id}")
def delete_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    session.delete(item)
    session.commit()
    return {"ok": True}
