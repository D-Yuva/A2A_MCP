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
    print("→ [RELAY START] body:", body.json())
    try:
        _, target = body.session_id.split(":", 1)
        print("→ parsed target:", target)
        url = registry.get(target)
        print("→ looked up URL:", url)

        if url is None:
            print("⚠️ Unknown target, raising 400")
            raise HTTPException(status_code=400, detail="Target not registered")

        resp = requests.post(url, json=body.dict(), timeout=10)
        print("→ HTTP POST status:", resp.status_code, "| body:", resp.text[:200])

        data = resp.json()
        print("→ JSON parsed:", data)

        reply = data.get("reply", "<no reply field>")
        print("→ Reply:", reply)

        return {"reply": reply}

    except HTTPException:
        raise
    except Exception as e:
        print("‼️ [RELAY ERROR]", type(e).__name__, str(e))
        raise HTTPException(status_code=500, detail=f"Relay error: {e}")


mcp = FastApiMCP(app, name="Agent Relay MCP")
mcp.mount()
