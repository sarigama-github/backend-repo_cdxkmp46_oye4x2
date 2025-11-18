import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import JournalEntry, JournalEntryCreate, JournalEntryUpdate

app = FastAPI(title="Trader's Journal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------- Helpers ---------
class ObjectIdStr(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return v

def serialize_entry(doc: dict) -> dict:
    if not doc:
        return {}
    out = {**doc}
    out["id"] = str(out.pop("_id"))
    # Convert datetime to isoformat if present
    if "created_at" in out and hasattr(out["created_at"], "isoformat"):
        out["created_at"] = out["created_at"].isoformat()
    if "updated_at" in out and hasattr(out["updated_at"], "isoformat"):
        out["updated_at"] = out["updated_at"].isoformat()
    return out


@app.get("/")
def read_root():
    return {"message": "Trader's Journal API is running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, 'name', None) or "Unknown"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# --------- Journal Endpoints ---------

@app.post("/api/entries", response_model=dict)
def create_entry(payload: JournalEntryCreate):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    entry = JournalEntry(**payload.model_dump())
    inserted_id = create_document("journalentry", entry)
    doc = db["journalentry"].find_one({"_id": ObjectId(inserted_id)})
    return serialize_entry(doc)


@app.get("/api/entries", response_model=List[dict])
def list_entries(date: Optional[str] = None, tag: Optional[str] = None, q: Optional[str] = None, limit: Optional[int] = 200):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    filt = {}
    if date:
        filt["date"] = date
    if tag:
        filt["tags"] = {"$in": [tag]}
    if q:
        filt["$or"] = [
            {"notes": {"$regex": q, "$options": "i"}},
            {"instrument": {"$regex": q, "$options": "i"}},
            {"session": {"$regex": q, "$options": "i"}},
            {"outcome": {"$regex": q, "$options": "i"}}
        ]
    docs = get_documents("journalentry", filt, limit)
    return [serialize_entry(d) for d in docs]


@app.get("/api/entries/{entry_id}", response_model=dict)
def get_entry(entry_id: str):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    doc = db["journalentry"].find_one({"_id": ObjectId(entry_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_entry(doc)


@app.patch("/api/entries/{entry_id}", response_model=dict)
def update_entry(entry_id: str, payload: JournalEntryUpdate):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    update_data = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    res = db["journalentry"].update_one({"_id": ObjectId(entry_id)}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = db["journalentry"].find_one({"_id": ObjectId(entry_id)})
    return serialize_entry(doc)


@app.delete("/api/entries/{entry_id}", response_model=dict)
def delete_entry(entry_id: str):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    res = db["journalentry"].delete_one({"_id": ObjectId(entry_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "deleted", "id": entry_id}


@app.get("/api/tags", response_model=List[str])
def get_tags():
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    pipeline = [
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 100}
    ]
    results = list(db["journalentry"].aggregate(pipeline))
    return [r["_id"] for r in results]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
