import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from fastapi_mcp import FastApiMCP
import os
from fastapi import Header
from fastapi.responses import JSONResponse

app = FastAPI()
registry: dict[str, str] = {}

class Registration(BaseModel):
    name: str
    url: str

class RelayMessage(BaseModel):
    session_id: str
    message: str

@app.get("/", include_in_schema=False)
async def root():
    return PlainTextResponse("🌟 Agent Relay is live!")

@app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
async def favicon():
    return PlainTextResponse("", status_code=204)

@app.post("/register")
def register_agent(body: Registration, x_api_key: str = Header(...)):
    if x_api_key != os.environ["MCP_SECRET"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    registry[body.name] = body.url
    return JSONResponse(content={"status": "registered"}, status_code=200)

@app.post("/relay", operation_id="relayMessage")
def relay_message(body: RelayMessage):
    print("→ [RELAY START] body:", body.json())

    parts = body.session_id.split(":", 1)
    if len(parts) != 2:
        print("⚠️ Invalid session_id format:", body.session_id)
        raise HTTPException(status_code=400, detail="session_id must be 'session:target'")

    _, target = parts
    url = registry.get(target)
    print("→ target:", target, "url:", url)
    if url is None:
        raise HTTPException(status_code=400, detail=f"Target '{target}' not registered")

    try:
        resp = requests.post(url, json=body.dict(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print("→ Forwarded OK, response JSON:", data)
    except Exception as e:
        print("‼️ Error in relay:", repr(e))
        raise HTTPException(status_code=502, detail=f"Forwarding failed: {e}")

    return {"reply": data.get("reply", "")}

mcp = FastApiMCP(app, name="Agent Relay MCP")
mcp.mount()
