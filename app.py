from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict
from dotenv import load_dotenv
from typing import List
from client import MCPClient


load_dotenv()
client = MCPClient()
app = FastAPI()

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

@app.on_event("startup")
async def startup_event():
    await client.connect_to_server('servers/weather.py')
    await client.connect_to_server('servers/calculator.py')

@app.on_event("shutdown")
async def shutdown_event():
    await client.cleanup() 

@app.get('/health')
async def health():
    return {"message": "OK"}

@app.post('/chat')
async def chat(request: ChatRequest = Body(...)):
    messages = request.messages
    response = await client.chat(messages)
    return {"response": response}