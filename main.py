from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import requests
from fastapi_mcp import FastApiMCP

app = FastAPI()
registry: dict[str, str] = {}  # name → callback URL

class Registration(BaseModel):
    name: str
    url: str

class RelayMessage(BaseModel):
    session_id: str
    message: str

@app.get("/", include_in_schema=False)
async def root():
    return PlainTextResponse("🌟 Agent Relay is live!")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return PlainTextResponse("", status_code=204)

@app.post("/register", operation_id="registerAgent")
async def register_agent(body: Registration, req: Request):
    registry[body.name] = body.url
    return {"status": "registered"}

@app.post("/relay", operation_id="relayMessage")
async def relay_message(body: RelayMessage):
    _, target = body.session_id.split(":", 1)
    url = registry.get(target)
    if not url:
        raise HTTPException(404, f"{target} not registered")
    resp = requests.post(url, json=body.dict(), timeout=10)
    return {"reply": resp.json().get("reply", "")}

mcp = FastApiMCP(app, name="Agent Relay MCP")
mcp.mount()
