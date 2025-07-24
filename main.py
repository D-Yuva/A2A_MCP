import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header, Query
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

# Models
class Registration(BaseModel):
    name: str
    url: str

class RelayMessage(BaseModel):
    session_id: str  # format: session42:target
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
    supabase.table("agent_registry").upsert({
        "name": body.name,
        "url": body.url
    }).execute()
    return {"status": "registered", "name": body.name, "url": body.url}

@app.post("/relay")
def relay_message(body: RelayMessage):
    parts = body.session_id.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="session_id must be 'session:target'")

    sender, recipient = parts[0].strip(), parts[1].strip()
    print("✅ Relaying from", sender, "to", recipient)
    print("📦 Message:", body.message)

    try:
        response = supabase.table("message_queue").insert({
            "session_id": body.session_id,
            "sender": sender,
            "recipient": recipient,
            "message": body.message,
            "timestamp": datetime.utcnow()
        }).execute()
        print("✅ Supabase insert response:", response)
    except Exception as e:
        print("‼️ Supabase insert failed:", repr(e))
        raise HTTPException(status_code=500, detail=f"Supabase insert error: {str(e)}")

    return {"status": "stored", "target": recipient}



@app.get("/poll")
def poll_messages(agent: str = Query(...)):
    response = supabase.table("message_queue").select("*").eq("recipient", agent).order("timestamp").execute()
    messages = response.data

    if messages:
        ids_to_delete = [msg["id"] for msg in messages]
        supabase.table("message_queue").delete().in_("id", ids_to_delete).execute()

    return {"messages": [msg["message"] for msg in messages]}

# Mount to MCP
mcp = FastApiMCP(app, name="Agent Relay MCP")
mcp.mount()
