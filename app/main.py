
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
import instagrapi
import os
import json

API_KEY = "neuro123"
API_KEY_NAME = "x-api-key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

SESSION_FILE = "session.json"

cl = instagrapi.Client()

def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

class LoginCredentials(BaseModel):
    username: str
    password: str

class Message(BaseModel):
    username: str
    text: str

def get_client():
    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid session, please login again: {e}")
    else:
        raise HTTPException(status_code=401, detail="Not logged in")
    return cl

@app.post("/login")
def login(credentials: LoginCredentials, api_key: str = Depends(get_api_key)):
    try:
        cl.login(credentials.username, credentials.password)
        cl.dump_settings(SESSION_FILE)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/send_message")
def send_message(message: Message, api_key: str = Depends(get_api_key)):
    client = get_client()
    try:
        user_id = client.user_id_from_username(message.username)
        client.direct_send(message.text, user_ids=[user_id])
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/inbox")
def get_inbox(api_key: str = Depends(get_api_key)):
    client = get_client()
    try:
        threads = client.direct_threads(amount=20)
        return [thread.dict() for thread in threads]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/dialogs")
def get_dialogs(api_key: str = Depends(get_api_key)):
    client = get_client()
    try:
        threads = client.direct_threads()
        return [{"id": t.id, "users": [u.username for u in t.users]} for t in threads]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
