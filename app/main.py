from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy.orm import Session
import instagrapi
import json

from .database import get_db, create_tables, InstagramSession

API_KEY = "neuro123"
API_KEY_NAME = "x-api-key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

app = FastAPI()

# Создаем таблицы при старте
@app.on_event("startup")
def on_startup():
    create_tables()

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

class ClientRequest(BaseModel):
    username: str

def get_client(request: ClientRequest, db: Session = Depends(get_db)):
    session_data = db.query(InstagramSession).filter(InstagramSession.username == request.username).first()
    if not session_data:
        raise HTTPException(status_code=401, detail=f"Session for user {request.username} not found. Please login first.")

    cl = instagrapi.Client()
    try:
        cl.load_settings(json.loads(session_data.session_data))
        cl.get_timeline_feed() # Проверка, что сессия валидна
    except Exception as e:
        # Если сессия невалидна, можно ее удалить, чтобы заставить пользователя перелогиниться
        # db.delete(session_data)
        # db.commit()
        raise HTTPException(status_code=401, detail=f"Session for {request.username} is invalid, please login again. Error: {e}")
    return cl

@app.post("/login")
def login(credentials: LoginCredentials, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    cl = instagrapi.Client()
    try:
        cl.login(credentials.username, credentials.password)
        session_json = json.dumps(cl.get_settings())

        # Ищем существующую сессию и обновляем ее, или создаем новую
        db_session = db.query(InstagramSession).filter(InstagramSession.username == credentials.username).first()
        if db_session:
            db_session.session_data = session_json
        else:
            db_session = InstagramSession(username=credentials.username, session_data=session_json)
            db.add(db_session)
        
        db.commit()
        return {"status": "ok", "username": credentials.username}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/send_message")
def send_message(message: Message, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    client_request = ClientRequest(username=message.username) # Используем username получателя для поиска сессии отправителя
    # ВАЖНО: Логика должна быть изменена, чтобы знать, от чьего имени отправлять.
    # Пока предполагаем, что имя пользователя для отправки передается в теле.
    # Правильнее было бы иметь отдельный параметр для отправителя.
    # Для простоты, пока будем использовать username получателя как ключ для поиска сессии.
    # Это НЕПРАВИЛЬНО, но демонстрирует механику.
    # Правильная реализация требует указания "отправителя"
    raise HTTPException(status_code=501, detail="Logic needs clarification: which user is sending the message?")

@app.post("/inbox")
def get_inbox(request: ClientRequest, client: instagrapi.Client = Depends(get_client), api_key: str = Depends(get_api_key)):
    try:
        threads = client.direct_threads(amount=20)
        return [thread.dict() for thread in threads]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/dialogs")
def get_dialogs(request: ClientRequest, client: instagrapi.Client = Depends(get_client), api_key: str = Depends(get_api_key)):
    try:
        threads = client.direct_threads()
        return [{"id": t.id, "users": [u.username for u in t.users]} for t in threads]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))