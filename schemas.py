"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal

class JournalEntry(BaseModel):
    """
    Trading journal entries
    Collection name: "journalentry"
    """
    date: str = Field(..., description="ISO date string YYYY-MM-DD")
    instrument: str = Field(..., description="Instrument traded, e.g., ES, NQ, XAUUSD")
    session: Literal["NY", "London", "Asia", "Other"] = Field(..., description="Trading session")
    rr: Optional[float] = Field(None, description="Risk/Reward ratio")
    lot_size: Optional[float] = Field(None, description="Lot size or contracts")
    outcome: Literal["Win", "Loss", "Break-even"] = Field(..., description="Trade outcome")
    notes: Optional[str] = Field("", description="Free-form notes for the entry")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    screenshots: List[str] = Field(default_factory=list, description="Base64 data URLs of screenshots")

class JournalEntryCreate(BaseModel):
    date: str
    instrument: str
    session: Literal["NY", "London", "Asia", "Other"]
    rr: Optional[float] = None
    lot_size: Optional[float] = None
    outcome: Literal["Win", "Loss", "Break-even"]
    notes: Optional[str] = ""
    tags: List[str] = []
    screenshots: List[str] = []

class JournalEntryUpdate(BaseModel):
    date: Optional[str] = None
    instrument: Optional[str] = None
    session: Optional[Literal["NY", "London", "Asia", "Other"]] = None
    rr: Optional[float] = None
    lot_size: Optional[float] = None
    outcome: Optional[Literal["Win", "Loss", "Break-even"]] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    screenshots: Optional[List[str]] = None
