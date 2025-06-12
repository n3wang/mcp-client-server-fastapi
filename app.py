from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import List, Optional, Literal
from dotenv import load_dotenv
from client import MCPClient
import json

load_dotenv()

client = MCPClient()
app = FastAPI()

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

def load_config_from_file(path: str = "config.json") -> dict:
    with open(path, "r") as f:
        return json.load(f)

@app.on_event("startup")
async def startup_event():
    config = load_config_from_file()  # loads 'config.json' by default
    await client.connect_from_config(config)

@app.on_event("shutdown")
async def shutdown_event():
    await client.cleanup() 

@app.get('/health')
async def health():
    return {"message": "OK"}

@app.post('/chat')
async def chat(request: ChatRequest = Body(...)):
    response = await client.chat(request.messages)
    return {"response": response}
