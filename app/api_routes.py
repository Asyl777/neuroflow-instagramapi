"""
API эндпоинты для внешнего AI агента и управления чат-ботом
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid

from app.database import get_db_session
from app.config import settings
from app.chatbot_models import *
from app.chatbot_service import chatbot_service

# Роутеры
api_router = APIRouter(prefix="/api/v1", tags=["API"])
ai_router = APIRouter(prefix="/api/v1/ai", tags=["AI Agent"])
chatbot_router = APIRouter(prefix="/api/v1/chatbot", tags=["Chatbot"])

# ============================================================================
# МОДЕЛИ ДАННЫХ ДЛЯ API
# ============================================================================

class MessageRequest(BaseModel):
    instagram_user_id: int
    username: str
    message: str
    instagram_message_id: Optional[str] = None
    instagram_thread_id: Optional[str] = None

class MessageResponse(BaseModel):
    success: bool
    user_id: str
    responses: List[Dict[str, Any]]
    actions_executed: int
    processing_time_ms: int
    user_state: str

class AIAgentRequest(BaseModel):
    user_id: str
    message: str
    context: Optional[Dict[str, Any]] = None
    agent_type: str = Field(default="general", description="Тип AI агента")
    
class AIAgentResponse(BaseModel):
    response: str
    confidence: float
    actions: List[Dict[str, Any]] = []
    user_state: Optional[str] = None
    next_step: Optional[str] = None

class TriggerCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_value: str
    actions: List[Dict[str, Any]]
    is_active: bool = True
    priority: int = 100
    is_global: bool = False

class ScenarioCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    start_triggers: List[Dict[str, Any]]
    steps: List[Dict[str, Any]]
    is_active: bool = True

class TemplateCreateRequest(BaseModel):
    name: str
    category: str = "general"
    template_text: str
    template_type: str = "text"
    buttons: List[Dict[str, Any]] = []
    language: str = "ru"

# ============================================================================
# API ДЛЯ ВНЕШНЕГО AI АГЕНТА
# ============================================================================

@ai_router.post("/process-message")
async def ai_process_message(
    request: MessageRequest,
    db: AsyncSession = Depends(get_db_session)
) -> MessageResponse:
    """
    Обработка сообщения через чат-бот
    Основной эндпоинт для получения сообщений из Instagram
    """
    
    result = await chatbot_service.process_message(
        db=db,
        instagram_user_id=request.instagram_user_id,
        username=request.username,
        message_text=request.message,
        instagram_message_id=request.instagram_message_id,
        instagram_thread_id=request.instagram_thread_id
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
    
    await db.commit()
    
    return MessageResponse(**result)

@ai_router.post("/agent-response")
async def receive_ai_agent_response(
    user_id: str,
    response: AIAgentResponse,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение ответа от внешнего AI агента
    Этот эндпоинт вызывает внешний AI агент когда у него готов ответ
    """
    
    try:
        # Находим пользователя
        user_query = select(ChatbotUser).where(ChatbotUser.id == user_id)
        result = await db.execute(user_query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Сохраняем ответ AI агента как сообщение бота
        ai_message = ChatbotMessage(
            user_id=user_id,
            content=response.response,
            sender_type="bot",
            ai_processed=True,
            ai_agent_response=response.dict()
        )
        
        db.add(ai_message)
        
        # Обновляем состояние пользователя если нужно
        if response.user_state:
            if response.user_state in [state.value for state in UserState]:
                user.current_state = UserState(response.user_state)
        
        # Выполняем дополнительные действия если есть
        if response.actions:
            await chatbot_service._execute_actions(db, user, response.actions, ai_message)
        
        await db.commit()
        
        return {
            "success": True,
            "message_id": str(ai_message.id),
            "actions_executed": len(response.actions)
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@ai_router.get("/user/{user_id}/context")
async def get_user_context(
    user_id: str,
    include_messages: bool = True,
    messages_limit: int = 20,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение контекста пользователя для AI агента
    """
    
    # Получаем пользователя
    user_query = select(ChatbotUser).where(ChatbotUser.id == user_id)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    context = {
        "user_id": str(user.id),
        "instagram_user_id": user.instagram_user_id,
        "username": user.username,
        "current_state": user.current_state.value,
        "collected_data": user.collected_data,
        "user_preferences": user.user_preferences,
        "tags": user.tags,
        "segment": user.segment,
        "total_messages": user.total_messages,
        "first_seen_at": user.first_seen_at.isoformat(),
        "last_activity_at": user.last_activity_at.isoformat()
    }
    
    # Добавляем сценарий если активен
    if user.current_scenario_id:
        scenario_query = select(ChatbotScenario).where(ChatbotScenario.id == user.current_scenario_id)
        scenario_result = await db.execute(scenario_query)
        scenario = scenario_result.scalar_one_or_none()
        
        if scenario:
            context["current_scenario"] = {
                "id": str(scenario.id),
                "name": scenario.name,
                "current_step": user.current_step
            }
    
    # Добавляем историю сообщений если нужно
    if include_messages:
        context["message_history"] = await chatbot_service._get_recent_messages(
            db, user_id, messages_limit
        )
    
    return context

@ai_router.get("/users/active")
async def get_active_users(
    limit: int = 100,
    state_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение списка активных пользователей
    """
    
    query = select(ChatbotUser).where(
        ChatbotUser.last_activity_at >= datetime.utcnow() - timedelta(hours=24)
    )
    
    if state_filter:
        query = query.where(ChatbotUser.current_state == state_filter)
    
    query = query.order_by(desc(ChatbotUser.last_activity_at)).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [
        {
            "user_id": str(user.id),
            "instagram_user_id": user.instagram_user_id,
            "username": user.username,
            "current_state": user.current_state.value,
            "last_activity_at": user.last_activity_at.isoformat(),
            "total_messages": user.total_messages
        }
        for user in users
    ]

# ============================================================================
# УПРАВЛЕНИЕ ЧАТ-БОТОМ
# ============================================================================

@chatbot_router.post("/triggers", response_model=dict)
async def create_trigger(
    request: TriggerCreateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Создание нового триггера"""
    
    trigger = ChatbotTrigger(
        name=request.name,
        description=request.description,
        trigger_type=TriggerType(request.trigger_type),
        trigger_value=request.trigger_value,
        actions=request.actions,
        is_active=request.is_active,
        priority=request.priority,
        is_global=request.is_global
    )
    
    db.add(trigger)
    await db.commit()
    await db.refresh(trigger)
    
    return {
        "success": True,
        "trigger_id": str(trigger.id),
        "message": f"Триггер '{request.name}' создан успешно"
    }

@chatbot_router.get("/triggers")
async def get_triggers(
    active_only: bool = True,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session)
):
    """Получение списка триггеров"""
    
    query = select(ChatbotTrigger)
    
    if active_only:
        query = query.where(ChatbotTrigger.is_active == True)
    
    query = query.order_by(ChatbotTrigger.priority, ChatbotTrigger.created_at).limit(limit)
    
    result = await db.execute(query)
    triggers = result.scalars().all()
    
    return [
        {
            "id": str(trigger.id),
            "name": trigger.name,
            "trigger_type": trigger.trigger_type.value,
            "trigger_value": trigger.trigger_value,
            "is_active": trigger.is_active,
            "priority": trigger.priority,
            "total_triggers": trigger.total_triggers,
            "success_rate": trigger.success_rate
        }
        for trigger in triggers
    ]

@chatbot_router.put("/triggers/{trigger_id}")
async def update_trigger(
    trigger_id: str,
    is_active: Optional[bool] = None,
    priority: Optional[int] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Обновление триггера"""
    
    query = select(ChatbotTrigger).where(ChatbotTrigger.id == trigger_id)
    result = await db.execute(query)
    trigger = result.scalar_one_or_none()
    
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    if is_active is not None:
        trigger.is_active = is_active
    if priority is not None:
        trigger.priority = priority
    if actions is not None:
        trigger.actions = actions
    
    await db.commit()
    
    return {"success": True, "message": "Триггер обновлен"}

@chatbot_router.post("/scenarios")
async def create_scenario(
    request: ScenarioCreateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Создание нового сценария"""
    
    scenario = ChatbotScenario(
        name=request.name,
        description=request.description,
        start_triggers=request.start_triggers,
        is_active=request.is_active,
        total_steps=len(request.steps)
    )
    
    db.add(scenario)
    await db.flush()  # Получаем ID
    
    # Создаем шаги сценария
    for i, step_data in enumerate(request.steps, 1):
        step = ChatbotStep(
            scenario_id=scenario.id,
            name=step_data.get("name", f"Шаг {i}"),
            step_order=i,
            description=step_data.get("description"),
            triggers=step_data.get("triggers", []),
            actions=step_data.get("actions", []),
            conditions=step_data.get("conditions", {}),
            success_next_step=i + 1 if i < len(request.steps) else None
        )
        db.add(step)
    
    await db.commit()
    
    return {
        "success": True,
        "scenario_id": str(scenario.id),
        "message": f"Сценарий '{request.name}' создан с {len(request.steps)} шагами"
    }

@chatbot_router.get("/scenarios")
async def get_scenarios(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db_session)
):
    """Получение списка сценариев"""
    
    query = select(ChatbotScenario)
    
    if active_only:
        query = query.where(ChatbotScenario.is_active == True)
    
    result = await db.execute(query)
    scenarios = result.scalars().all()
    
    return [
        {
            "id": str(scenario.id),
            "name": scenario.name,
            "description": scenario.description,
            "is_active": scenario.is_active,
            "total_steps": scenario.total_steps,
            "total_starts": scenario.total_starts,
            "total_completions": scenario.total_completions,
            "success_rate": scenario.success_rate
        }
        for scenario in scenarios
    ]

@chatbot_router.post("/templates")
async def create_template(
    request: TemplateCreateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Создание шаблона сообщения"""
    
    template = ChatbotTemplate(
        name=request.name,
        category=request.category,
        template_text=request.template_text,
        template_type=request.template_type,
        buttons=request.buttons,
        language=request.language
    )
    
    db.add(template)
    await db.commit()
    
    return {
        "success": True,
        "template_id": str(template.id),
        "message": f"Шаблон '{request.name}' создан"
    }

@chatbot_router.get("/templates")
async def get_templates(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Получение списка шаблонов"""
    
    query = select(ChatbotTemplate).where(ChatbotTemplate.is_active == True)
    
    if category:
        query = query.where(ChatbotTemplate.category == category)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return [
        {
            "id": str(template.id),
            "name": template.name,
            "category": template.category,
            "template_text": template.template_text,
            "template_type": template.template_type,
            "buttons": template.buttons,
            "usage_count": template.usage_count
        }
        for template in templates
    ]

# ============================================================================
# АНАЛИТИКА И МОНИТОРИНГ
# ============================================================================

@chatbot_router.get("/analytics/overview")
async def get_analytics_overview(
    days: int = 7,
    db: AsyncSession = Depends(get_db_session)
):
    """Общая аналитика чат-бота"""
    
    since_date = datetime.utcnow() - timedelta(days=days)
    
    # Общие метрики
    total_users_query = select(func.count(ChatbotUser.id))
    total_users_result = await db.execute(total_users_query)
    total_users = total_users_result.scalar()
    
    active_users_query = select(func.count(ChatbotUser.id)).where(
        ChatbotUser.last_activity_at >= since_date
    )
    active_users_result = await db.execute(active_users_query)
    active_users = active_users_result.scalar()
    
    total_messages_query = select(func.count(ChatbotMessage.id)).where(
        ChatbotMessage.created_at >= since_date
    )
    total_messages_result = await db.execute(total_messages_query)
    total_messages = total_messages_result.scalar()
    
    # Статистика по состояниям пользователей
    states_query = select(
        ChatbotUser.current_state,
        func.count(ChatbotUser.id)
    ).group_by(ChatbotUser.current_state)
    
    states_result = await db.execute(states_query)
    user_states = {state.value: count for state, count in states_result.fetchall()}
    
    return {
        "period_days": days,
        "total_users": total_users,
        "active_users": active_users,
        "total_messages": total_messages,
        "user_states": user_states,
        "engagement_rate": round(active_users / total_users * 100, 2) if total_users > 0 else 0
    }

@chatbot_router.get("/events")
async def get_events(
    event_type: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
):
    """Получение событий системы"""
    
    query = select(ChatbotEvent)
    
    if event_type:
        query = query.where(ChatbotEvent.event_type == event_type)
    
    query = query.order_by(desc(ChatbotEvent.created_at)).limit(limit)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return [
        {
            "id": str(event.id),
            "event_type": event.event_type,
            "event_name": event.event_name,
            "success": event.success,
            "event_data": event.event_data,
            "created_at": event.created_at.isoformat(),
            "processing_time_ms": event.processing_time_ms
        }
        for event in events
    ]