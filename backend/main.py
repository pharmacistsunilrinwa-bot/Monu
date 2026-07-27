from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db, init_db
from models import ChatHistory
from services.gemini_service import gemini_service
from services.voice_service import voice_service
from services.search_service import search_service
from services.google_workspace_service import google_workspace_service
from services.analysis_service import analysis_service
from services.sentiment_service import sentiment_service
from services.gemini_logic_service import gemini_logic_service
from services.file_manager_service import file_manager_service
from schemas import ChatRequest, ChatResponse, SearchRequest, TaskPlanRequest, ProjectPlan
import os
import shutil
import asyncio
import socket

app = FastAPI(title="Personal AI Assistant API")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "invalid value")
        errors.append(f"Field '{field}': {msg}")
    user_friendly_msg = "Invalid or missing request parameters. " + "; ".join(errors)
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Bad Request: Missing or invalid parameters.",
            "detail": user_friendly_msg
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "detail": str(exc.detail)
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    status_code = 500
    error_message = "An unexpected server error occurred."
    exc_name = type(exc).__name__
    
    if "Timeout" in exc_name or isinstance(exc, (asyncio.TimeoutError, socket.timeout)):
        status_code = 504
        error_message = "The request timed out. Please try again later."
    elif "Connection" in exc_name or isinstance(exc, ConnectionError):
        status_code = 503
        error_message = "Unable to connect to downstream services. Please check your network connection."
        
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": error_message,
            "detail": str(exc)
        }
    )

@app.on_event("startup")
async def on_startup():
    await init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    # 1. Retrieve history context
    context = await gemini_logic_service.get_context(db, request.user_id)
    
    # 2. Analyze sentiment (non-blocking)
    asyncio.create_task(asyncio.to_thread(sentiment_service.analyze_text, request.message))
    
    # 3. Get reasoned response with context
    response_text = await gemini_logic_service.reasoned_chat(request.message, context)
    
    # 4. Save to history
    new_entry = ChatHistory(
        user_id=request.user_id,
        message=request.message,
        response=response_text
    )
    db.add(new_entry)
    
    return ChatResponse(response=response_text)

@app.get("/chat/history")
async def get_chat_history(user_id: str = "default", db: AsyncSession = Depends(get_db)):
    from sqlalchemy.future import select
    result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.timestamp.asc())
    )
    history = result.scalars().all()
    return [{"role": "user", "content": h.message} if i % 2 == 0 else {"role": "assistant", "content": h.response} 
            for h in history for i in range(2)]

@app.delete("/chat/history")
async def clear_chat_history(user_id: str = "default", db: AsyncSession = Depends(get_db)):
    from sqlalchemy import delete
    await db.execute(delete(ChatHistory).where(ChatHistory.user_id == user_id))
    return {"success": True, "message": "History cleared"}

@app.post("/voice-to-text")
async def voice_to_text(file: UploadFile = File(...)):
    temp_path = f"voice_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        text = await voice_service.speech_to_text(temp_path)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech to text failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- Power Feature: Google Workspace ---
@app.get("/auth/url")
async def get_auth_url():
    return {"url": google_workspace_service.get_auth_url()}

@app.get("/google/gmail")
async def list_gmail(creds: str):
    return await google_workspace_service.list_gmail_messages(creds)

# --- Power Feature: Data Analysis ---
@app.post("/analysis/csv")
async def analyze_csv(file: UploadFile = File(...)):
    temp_path = f"data_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        report = analysis_service.analyze_csv(temp_path)
        return report
    finally:
        os.remove(temp_path)

# --- Power Feature: File System ---
@app.get("/files/list")
async def list_files(path: str = ""):
    return {"files": file_manager_service.list_files(path)}

@app.post("/files/mkdir")
async def make_dir(name: str):
    return {"message": file_manager_service.create_directory(name)}

@app.post("/tasks/plan", response_model=ProjectPlan)
async def plan_tasks(request: TaskPlanRequest):
    prompt = f"Create a detailed project plan for the following goal: {request.goal}. Return the response in JSON format with 'title' and a list of 'steps' (each step having 'step' and 'description')."
    response_text = await gemini_service.generate_content(prompt)
    return ProjectPlan(title=request.goal, steps=[{"step": "Initial Step", "description": response_text}])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
