import asyncio
import io
import json
import os
import secrets
import socket
from typing import List, Set, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from fastapi.responses import HTMLResponse
import uvicorn
import qrcode

app = FastAPI(title="I Hate Interviews Teleprompter Server")


connected_clients: Set[WebSocket] = set()
server_loop: Optional[asyncio.AbstractEventLoop] = None
SERVER_AUTH_TOKEN = secrets.token_urlsafe(32)

def get_auth_token() -> str:
    global SERVER_AUTH_TOKEN
    return SERVER_AUTH_TOKEN

def reset_auth_token() -> str:
    global SERVER_AUTH_TOKEN
    SERVER_AUTH_TOKEN = secrets.token_urlsafe(32)
    return SERVER_AUTH_TOKEN

def get_local_ip() -> str:
    """Finds the primary local IPv4 address for presentation pairing."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def generate_pairing_url(host: str = None, port: int = 8000) -> str:
    ip = host or get_local_ip()
    token = get_auth_token()
    return f"http://{ip}:{port}/?token={token}"

def generate_qr_code_image_bytes(url: str) -> bytes:
    """Generates PNG image bytes of QR code for PyQt GUI."""
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

@app.get("/", response_class=HTMLResponse)
async def get_teleprompter(token: Optional[str] = Query(None)):
    # Verify ephemeral token
    if token != SERVER_AUTH_TOKEN:
        return HTMLResponse(
            content="<h2 style='color:#ff5252; font-family: sans-serif; text-align:center; margin-top:50px;'>"
                    "401 Unauthorized: Invalid or Expired Meeting Pairing Token</h2>",
            status_code=401
        )

    template_path = os.path.join(os.path.dirname(__file__), "templates", "teleprompter.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            # Inject token into the client javascript template
            html_content = html_content.replace("__SERVER_AUTH_TOKEN__", token)
            return html_content
    return "<h1>MeetingCopilot Teleprompter Template Not Found</h1>"

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    if token != SERVER_AUTH_TOKEN:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        print("[CompanionServer] Rejected unauthorized WebSocket connection attempt.")
        return

    await websocket.accept()
    connected_clients.add(websocket)
    print(f"[CompanionServer] Authenticated Client connected. Active clients: {len(connected_clients)}")

    # 15s Periodic keep-alive ping loop
    async def keep_alive():
        while websocket in connected_clients:
            try:
                await asyncio.sleep(15.0)
                await websocket.send_text(json.dumps({"type": "ping"}))
            except Exception:
                break

    keep_alive_task = asyncio.create_task(keep_alive())

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            action = msg.get("action")
            if action == "clear":
                await broadcast_json({"type": "clear"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[CompanionServer] WebSocket error: {e}")
    finally:
        connected_clients.discard(websocket)
        keep_alive_task.cancel()
        print(f"[CompanionServer] Client disconnected. Active clients: {len(connected_clients)}")

async def broadcast_json(data: dict):
    """Broadcasts JSON payload to all authenticated connected clients."""
    if not connected_clients:
        return
    msg_str = json.dumps(data)
    dead_clients = []
    for client in list(connected_clients):
        try:
            await client.send_text(msg_str)
        except Exception:
            dead_clients.append(client)
    for dc in dead_clients:
        connected_clients.discard(dc)

def threadsafe_broadcast(data: dict):
    """Threadsafe helper to broadcast data from any background worker thread."""
    global server_loop
    if server_loop and server_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_json(data), server_loop)

def start_server_in_thread(host: str = "0.0.0.0", port: int = 8000):
    """Starts FastAPI uvicorn server in a separate background thread."""
    import threading
    def run_uv():
        global server_loop
        server_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(server_loop)
        config = uvicorn.Config(app=app, host=host, port=port, log_level="warning", loop="asyncio")
        server = uvicorn.Server(config)
        server_loop.run_until_complete(server.serve())

    t = threading.Thread(target=run_uv, name="CompanionServerThread", daemon=True)
    t.start()
    return t
