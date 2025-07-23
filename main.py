import os
import requests
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from supabase import create_client, Client
from fastapi_mcp import FastApiMCP

# Initialize Supabase
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# FastAPI App
app = FastAPI()

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

@app.get("/registry")
def get_registry():
    response = supabase.table("agent_registry").select("*").execute()
    agents = {item["name"]: item["url"] for item in response.data}
    return agents

@app.post("/register")
def register_agent(body: Registration, x_api_key: str = Header(...)):
    if x_api_key != os.environ["MCP_SECRET"]:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Upsert (insert or update)
    supabase.table("agent_registry").upsert({
        "name": body.name,
        "url": body.url
    }).execute()

    print(f"✅ Registered '{body.name}' with URL: {body.url}")
    return JSONResponse(
        content={"status": "registered", "name": body.name, "url": body.url},
        status_code=200
    )

@app.post("/relay", operation_id="relayMessage")
def relay_message(body: RelayMessage):
    print("→ [RELAY START] body:", body.json())

    parts = body.session_id.split(":", 1)
    if len(parts) != 2:
        print("⚠️ Invalid session_id format:", body.session_id)
        raise HTTPException(status_code=400, detail="session_id must be 'session:target'")

    _, target = parts
    response = supabase.table("agent_registry").select("url").eq("name", target).execute()
    if not response.data:
        raise HTTPException(status_code=400, detail=f"Target '{target}' not registered")

    url = response.data[0]["url"]
    print("→ target:", target, "url:", url)

    try:
        resp = requests.post(url, json=body.dict(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print("→ Forwarded OK, response JSON:", data)
    except Exception as e:
        print("‼️ Error in relay:", repr(e))
        raise HTTPException(status_code=502, detail=f"Forwarding failed: {e}")

    return {"reply": data.get("reply", "")}

# Mount to MCP
mcp = FastApiMCP(app, name="Agent Relay MCP")
mcp.mount()
