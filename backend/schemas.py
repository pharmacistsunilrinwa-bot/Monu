from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    user_id: Optional[str] = "default"
    message: str
    attachment: Optional[str] = None  # Base64 encoded string of attachment
    attachment_mime: Optional[str] = None  # MIME type of attachment, e.g. "image/jpeg"

class ChatResponse(BaseModel):
    response: str

class SearchRequest(BaseModel):
    query: str

class TaskPlanRequest(BaseModel):
    goal: str

class TaskStep(BaseModel):
    step: str
    description: str

class ProjectPlan(BaseModel):
    title: str
    steps: List[TaskStep]

class AuthRequest(BaseModel):
    code: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
