from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import uvicorn
import asyncio

from src.models import (
    ChatResponse,
    ChatRequest
)

from src.services.chat_rag import chat_obj


app = FastAPI()

# CORS (frontend fetch() requires this)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend folder
app.mount("/static", StaticFiles(directory="static"), name="static")


# Root route to serve index.html
@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")


async def run_in_thread(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    resp =  await run_in_thread(chat_obj.chat_query, req)

    return ChatResponse(
        response=resp["response"],
        citations=resp["citations"]
    )


# Run uvicorn automatically if executed directly
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=6789)