from pydantic import BaseModel
from typing import Optional

# --- Auth Schemas ---
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

# --- Task Schemas ---
class TaskCreate(BaseModel):
    text: str

class TaskUpdate(BaseModel):
    text: Optional[str] = None
    completed: Optional[bool] = None

class TaskOut(BaseModel):
    id: int
    text: str
    completed: bool

    class Config:
        from_attributes = True