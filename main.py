import os
import requests
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from supabase import create_client, Client

# Supabase init
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
MCP_SECRET = os.environ["MCP_SECRET"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

# Models
class Registration(BaseModel):
    name: str
    url: str

class RelayMessage(BaseModel):
    session_id: str
    message: str

@app.get("/")
def root():
    return PlainTextResponse("📡 MCP Server is live!")

@app.post("/register")
def register_agent(body: Registration, x_api_key: str = Header(...)):
    if x_api_key != MCP_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    supabase.table("agent_registry").upsert({
        "name": body.name,
        "url": body.url
    }).execute()
    return {"status": "registered", "agent": body.name}

@app.post("/relay")
def relay_message(body: RelayMessage):
    sender, recipient = body.session_id.split(":")
    supabase.table("message_queue").insert({
        "session_id": body.session_id,
        "sender": sender,
        "recipient": recipient,
        "message": body.message
    }).execute()

    try:
        reg = supabase.table("agent_registry") \
            .select("url") \
            .eq("name", recipient) \
            .execute()
        recipient_url = reg.data[0]["url"]
        requests.post(recipient_url, json={
            "session_id": body.session_id,
            "message": body.message
        })
    except Exception as e:
        print("‼️ Push failed:", e)

    return {"status": "stored_and_pushed", "to": recipient}

@app.get("/poll")
def poll_messages(agent: str = Query(..., description="agent name to poll for")):
    try:
        resp = supabase.table("message_queue") \
            .select("*") \
            .eq("recipient", agent) \
            .execute()
        messages = resp.data or []

        # Extract and remove messages
        texts = [msg["message"] for msg in messages]
        ids = [msg["id"] for msg in messages if "id" in msg]
        if ids:
            supabase.table("message_queue").delete().in_("id", ids).execute()

        return {"messages": texts}
    except Exception as e:
        print("‼️ Poll error:", e)
        raise HTTPException(status_code=500, detail=f"Polling failed: {e}")
