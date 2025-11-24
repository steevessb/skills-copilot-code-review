
from fastapi import APIRouter, Depends, HTTPException
from pymongo.collection import Collection
from src.backend.database import announcements_collection
from datetime import datetime
from typing import List, Optional
from src.backend.routers.auth import get_current_user
from pydantic import BaseModel, Field
from bson import ObjectId


class Announcement(BaseModel):
    id: str = Field(default_factory=str, alias="_id")
    message: str
    expires_at: datetime
    starts_at: Optional[datetime] = None
    created_by: Optional[str] = None

router = APIRouter()

@router.get("/announcements", response_model=List[Announcement])
def get_announcements():
    now = datetime.utcnow()
    announcements = list(announcements_collection.find({
        "$or": [
            {"starts_at": {"$lte": now}},
            {"starts_at": {"$exists": False}}
        ],
        "expires_at": {"$gte": now}
    }))
    for a in announcements:
        a["_id"] = str(a["_id"])
        if "starts_at" in a and isinstance(a["starts_at"], datetime):
            a["starts_at"] = a["starts_at"].isoformat()
        if "expires_at" in a and isinstance(a["expires_at"], datetime):
            a["expires_at"] = a["expires_at"].isoformat()
    return announcements

@router.post("/announcements", response_model=Announcement)
def create_announcement(data: Announcement, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authorized")
    doc = data.dict(by_alias=True)
    doc["created_by"] = user["username"]
    if "starts_at" not in doc or not doc["starts_at"]:
        doc["starts_at"] = datetime.utcnow()
    result = announcements_collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    if "starts_at" in doc and isinstance(doc["starts_at"], datetime):
        doc["starts_at"] = doc["starts_at"].isoformat()
    if "expires_at" in doc and isinstance(doc["expires_at"], datetime):
        doc["expires_at"] = doc["expires_at"].isoformat()
    return doc

@router.put("/announcements/{announcement_id}", response_model=Announcement)
def update_announcement(announcement_id: str, data: Announcement, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        oid = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    result = announcements_collection.update_one({"_id": oid}, {"$set": data.dict(exclude_unset=True, by_alias=True)})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    updated = announcements_collection.find_one({"_id": oid})
    updated["_id"] = str(updated["_id"])
    if "starts_at" in updated and isinstance(updated["starts_at"], datetime):
        updated["starts_at"] = updated["starts_at"].isoformat()
    if "expires_at" in updated and isinstance(updated["expires_at"], datetime):
        updated["expires_at"] = updated["expires_at"].isoformat()
    return updated

@router.delete("/announcements/{announcement_id}")
def delete_announcement(announcement_id: str, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        oid = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    result = announcements_collection.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return {"success": True}
