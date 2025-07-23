from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse   
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

@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def root():
    return PlainTextResponse("🌟 Agent Relay is live!")

@app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
async def favicon():
    return PlainTextResponse("", status_code=204)

@app.post("/register", operation_id="registerAgent")
async def register_agent(body: Registration, req: Request):
    registry[body.name] = body.url
    print(f"[REGISTER] {body.name} → {body.url}")
    return {"status": "registered"}

@app.post("/relay", operation_id="relayMessage")
async def relay_message(body: RelayMessage):
    _, target = body.session_id.split(":", 1)
    url = registry.get(target)
    if not url:
        raise HTTPException(404, f"{target} not registered")
    print(f"[RELAY] session={body.session_id} → {target} @ {url}")
    resp = requests.post(url, json=body.dict(), timeout=10)
    return {"reply": resp.json().get("reply", "")}

# Mount MCP endpoints after defining routes
mcp = FastApiMCP(app, name="Agent Relay MCP")
mcp.mount()
