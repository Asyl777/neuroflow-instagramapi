"""
Instagram API с чат-бот конструктором
Новая версия с полной системой триггеров, сценариев и AI интеграцией
"""
from fastapi import FastAPI, Depends, HTTPException, Security, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import logging
from datetime import datetime

# Импорты конфигурации и базы данных
from app.config import settings
from app.database import get_db_session, init_db, close_db, test_db_connection

# Импорты моделей
from app.models import *  # Старые модели для совместимости
from app.chatbot_models import *  # Новые модели чат-бота

# Импорты сервисов
from app.chatbot_service import chatbot_service
from app.api_routes import api_router, ai_router, chatbot_router

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Настройка API ключа
API_KEY_NAME = "x-api-key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    """Проверка API ключа"""
    if api_key_header == settings.api_key:
        return api_key_header
    else:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    
    logger.info("🚀 Запуск Instagram API с чат-бот конструктором...")
    
    try:
        # Инициализация базы данных
        await init_db()
        logger.info("✅ База данных инициализирована")
        
        # Проверка подключения
        db_connected = await test_db_connection()
        if not db_connected:
            logger.error("❌ Не удалось подключиться к базе данных")
            raise Exception("Database connection failed")
        
        logger.info("🎯 Сервис готов к работе!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска: {e}")
        raise
    
    yield
    
    # Завершение работы
    logger.info("🔄 Завершение работы сервиса...")
    await close_db()
    logger.info("👋 Сервис остановлен")

# Создание приложения
app = FastAPI(
    title="Instagram Chatbot API",
    description="API для Instagram чат-бота с конструктором сценариев и AI интеграцией",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(api_router)
app.include_router(ai_router)
app.include_router(chatbot_router)

# ============================================================================
# ОСНОВНЫЕ ЭНДПОИНТЫ
# ============================================================================

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": "Instagram Chatbot API",
        "version": "2.0.0",
        "features": [
            "Chatbot Constructor",
            "Trigger System", 
            "Scenario Management",
            "AI Agent Integration",
            "Template System",
            "User State Management",
            "Analytics & Events"
        ],
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Расширенный health check"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "services": {}
    }
    
    # Проверка базы данных
    try:
        db_status = await test_db_connection()
        health_status["services"]["database"] = "connected" if db_status else "disconnected"
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Проверка чат-бот сервиса
    try:
        health_status["services"]["chatbot"] = "ready"
    except Exception as e:
        health_status["services"]["chatbot"] = f"error: {str(e)}"
    
    return health_status

# ============================================================================
# WEBHOOK ЭНДПОИНТЫ
# ============================================================================

@app.post("/webhooks/instagram")
async def instagram_webhook(
    webhook_data: dict,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(get_api_key),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Webhook для получения сообщений из Instagram
    """
    
    try:
        logger.info(f"📨 Получен webhook от Instagram: {webhook_data}")
        
        # Извлекаем данные сообщения
        # Структура может отличаться в зависимости от настроек Instagram API
        message_data = webhook_data.get("entry", [{}])[0].get("messaging", [{}])[0]
        
        if not message_data:
            return {"status": "no_message_data"}
        
        # Извлекаем основную информацию
        sender_id = message_data.get("sender", {}).get("id")
        message_text = message_data.get("message", {}).get("text", "")
        message_id = message_data.get("message", {}).get("mid")
        
        if not sender_id or not message_text:
            return {"status": "incomplete_data"}
        
        # Получаем username (может потребоваться дополнительный запрос к Instagram API)
        username = f"user_{sender_id}"  # Временное решение
        
        # Обрабатываем сообщение через чат-бот в фоновом режиме
        background_tasks.add_task(
            process_instagram_message,
            db, sender_id, username, message_text, message_id
        )
        
        return {
            "status": "received",
            "message": "Сообщение принято в обработку",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки webhook: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

async def process_instagram_message(
    db: AsyncSession,
    sender_id: int,
    username: str,
    message_text: str,
    message_id: str
):
    """Фоновая обработка сообщения из Instagram"""
    
    try:
        result = await chatbot_service.process_message(
            db=db,
            instagram_user_id=int(sender_id),
            username=username,
            message_text=message_text,
            instagram_message_id=message_id
        )
        
        await db.commit()
        
        # Если есть ответы для отправки, отправляем их
        if result.get("responses"):
            await send_responses_to_instagram(result["responses"], sender_id)
        
        logger.info(f"✅ Сообщение от {username} обработано успешно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения от {username}: {e}")
        await db.rollback()

async def send_responses_to_instagram(responses: list, recipient_id: str):
    """Отправка ответов обратно в Instagram"""
    
    # TODO: Реализовать отправку через Instagram API
    # Пока просто логируем
    
    for response in responses:
        if response.get("type") == "send_message":
            logger.info(f"📤 Отправка сообщения пользователю {recipient_id}: {response.get('text')}")
            # Здесь будет код отправки через instagrapi
        
        elif response.get("type") == "ai_agent_call":
            logger.info(f"🤖 Вызов AI агента: {response.get('agent_url')}")
            # Здесь будет HTTP запрос к внешнему AI агенту
        
        elif response.get("type") == "delay":
            logger.info(f"⏱️ Задержка {response.get('delay_seconds')} секунд")
            # Здесь будет планирование отложенного действия через Celery

# ============================================================================
# СОВМЕСТИМОСТЬ СО СТАРЫМИ ЭНДПОИНТАМИ
# ============================================================================

@app.post("/login")
async def login_compatibility(
    credentials: dict,
    api_key: str = Depends(get_api_key)
):
    """Совместимость со старым эндпоинтом логина"""
    
    logger.warning("⚠️ Используется устаревший эндпоинт /login")
    
    # TODO: Реализовать логику логина через instagrapi
    # Пока возвращаем заглушку
    
    return {
        "status": "ok",
        "message": "Login endpoint moved to chatbot system",
        "redirect": "/api/v1/chatbot"
    }

@app.post("/send_message")
async def send_message_compatibility(
    message: dict,
    api_key: str = Depends(get_api_key)
):
    """Совместимость со старым эндпоинтом отправки сообщений"""
    
    logger.warning("⚠️ Используется устаревший эндпоинт /send_message")
    
    # TODO: Интеграция со старой логикой отправки
    # Пока возвращаем заглушку
    
    return {
        "status": "ok", 
        "message": "Message sending moved to chatbot system",
        "redirect": "/api/v1/ai/process-message"
    }

@app.get("/inbox")
async def inbox_compatibility(
    api_key: str = Depends(get_api_key)
):
    """Совместимость со старым эндпоинтом inbox"""
    
    logger.warning("⚠️ Используется устаревший эндпоинт /inbox")
    
    return {
        "message": "Inbox functionality moved to chatbot system",
        "redirect": "/api/v1/ai/users/active"
    }

@app.get("/dialogs")
async def dialogs_compatibility(
    api_key: str = Depends(get_api_key)
):
    """Совместимость со старым эндпоинтом dialogs"""
    
    logger.warning("⚠️ Используется устаревший эндпоинт /dialogs")
    
    return {
        "message": "Dialogs functionality moved to chatbot system", 
        "redirect": "/api/v1/chatbot/scenarios"
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main_new:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )