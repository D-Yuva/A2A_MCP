import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from fastapi_mcp import FastApiMCP

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

@app.post("/register", operation_id="registerAgent")
def register_agent(body: Registration):
    registry[body.name] = body.url
    print(f"[REGISTER] {body.name} → {body.url}")
    return {"status": "registered"}

@app.post("/relay", operation_id="relayMessage")
def relay_message(body: RelayMessage):
    print("→ /relay called with:", body)
    _, target = body.session_id.split(":", 1)
    url = registry.get(target)
    print("→ target:", target, "url:", url)
    if not url:
        raise HTTPException(status_code=400, detail=f"{target} not registered")
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
