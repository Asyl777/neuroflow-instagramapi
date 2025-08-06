"""
Сервис чат-бота конструктора
Обработка триггеров, сценариев и правил
"""
import asyncio
import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from app.chatbot_models import (
    ChatbotScenario, ChatbotStep, ChatbotTrigger, ChatbotUser, 
    UserScenarioSession, ChatbotMessage, ChatbotTemplate, ChatbotEvent,
    TriggerType, ActionType, UserState
)
from app.config import settings

logger = logging.getLogger(__name__)


class ChatbotService:
    """Основной сервис чат-бота"""
    
    def __init__(self):
        self.webhook_urls = {}  # Хранение webhook URL'ов для внешних AI агентов
    
    async def process_message(
        self, 
        db: AsyncSession,
        instagram_user_id: int,
        username: str,
        message_text: str,
        instagram_message_id: str = None,
        instagram_thread_id: str = None
    ) -> Dict[str, Any]:
        """
        Основной метод обработки входящего сообщения
        
        Returns:
            Dict с действиями которые нужно выполнить
        """
        start_time = datetime.now()
        
        try:
            # 1. Получаем или создаем пользователя
            user = await self._get_or_create_user(db, instagram_user_id, username)
            
            # 2. Сохраняем сообщение
            message = await self._save_message(
                db, user.id, message_text, "user", 
                instagram_message_id, instagram_thread_id
            )
            
            # 3. Проверяем триггеры
            triggered_actions = await self._check_triggers(db, user, message_text)\n            
            # 4. Обрабатываем текущий сценарий если есть
            scenario_actions = await self._process_current_scenario(db, user, message_text)
            
            # 5. Объединяем все действия
            all_actions = triggered_actions + scenario_actions
            
            # 6. Выполняем действия
            responses = await self._execute_actions(db, user, all_actions, message)\n            
            # 7. Обновляем статистику
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            await self._update_statistics(db, user, message, processing_time)
            
            return {
                "success": True,
                "user_id": str(user.id),
                "responses": responses,
                "actions_executed": len(all_actions),
                "processing_time_ms": int(processing_time),
                "user_state": user.current_state.value
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            
            # Логируем событие ошибки
            await self._log_event(
                db, "message_processing_error",
                {"error": str(e), "message": message_text, "user_id": instagram_user_id}
            )
            
            return {
                "success": False,
                "error": str(e),
                "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000)
            }
    
    async def _get_or_create_user(self, db: AsyncSession, instagram_user_id: int, username: str) -> ChatbotUser:
        """Получение или создание пользователя"""
        
        # Ищем существующего пользователя
        query = select(ChatbotUser).where(ChatbotUser.instagram_user_id == instagram_user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            # Обновляем активность
            user.last_activity_at = datetime.utcnow()
            user.username = username  # Обновляем username на случай если изменился
            return user
        
        # Создаем нового пользователя
        user = ChatbotUser(
            instagram_user_id=instagram_user_id,
            username=username,
            current_state=UserState.NEW
        )
        
        db.add(user)
        await db.flush()  # Получаем ID
        
        # Логируем событие нового пользователя
        await self._log_event(db, "user_joined", {"user_id": str(user.id), "username": username})
        
        return user
    
    async def _save_message(
        self, 
        db: AsyncSession,
        user_id: str,
        content: str,
        sender_type: str,
        instagram_message_id: str = None,
        instagram_thread_id: str = None
    ) -> ChatbotMessage:
        """Сохранение сообщения в БД"""
        
        message = ChatbotMessage(
            user_id=user_id,
            content=content,
            sender_type=sender_type,
            instagram_message_id=instagram_message_id,
            instagram_thread_id=instagram_thread_id
        )
        
        db.add(message)
        await db.flush()
        
        return message
    
    async def _check_triggers(self, db: AsyncSession, user: ChatbotUser, message_text: str) -> List[Dict[str, Any]]:
        """Проверка и выполнение триггеров"""
        
        # Получаем активные триггеры
        query = select(ChatbotTrigger).where(
            and_(
                ChatbotTrigger.is_active == True,
                or_(
                    ChatbotTrigger.is_global == True,
                    ChatbotTrigger.is_global == False  # TODO: добавить условия для контекстных триггеров
                )
            )
        ).order_by(ChatbotTrigger.priority)
        
        result = await db.execute(query)
        triggers = result.scalars().all()
        
        actions = []
        
        for trigger in triggers:
            if await self._trigger_matches(trigger, message_text, user):
                # Проверяем ограничения (cooldown, max uses)
                if await self._check_trigger_limits(db, trigger, user):
                    
                    # Добавляем действия триггера
                    for action in trigger.actions:
                        actions.append({
                            **action,
                            "trigger_id": str(trigger.id),
                            "trigger_name": trigger.name
                        })
                    
                    # Обновляем статистику триггера
                    trigger.total_triggers += 1
                    trigger.last_triggered_at = datetime.utcnow()
                    
                    # Логируем событие
                    await self._log_event(
                        db, "trigger_activated",
                        {
                            "trigger_id": str(trigger.id),
                            "trigger_name": trigger.name,
                            "user_id": str(user.id),
                            "message": message_text
                        }
                    )
        
        return actions
    
    async def _trigger_matches(self, trigger: ChatbotTrigger, message_text: str, user: ChatbotUser) -> bool:
        """Проверка соответствия триггера сообщению"""
        
        message_lower = message_text.lower().strip()
        trigger_value = trigger.trigger_value.lower() if trigger.trigger_value else ""
        
        if trigger.trigger_type == TriggerType.EXACT_MATCH:
            return message_lower == trigger_value
        
        elif trigger.trigger_type == TriggerType.CONTAINS:
            return trigger_value in message_lower
        
        elif trigger.trigger_type == TriggerType.STARTS_WITH:
            return message_lower.startswith(trigger_value)
        
        elif trigger.trigger_type == TriggerType.ENDS_WITH:
            return message_lower.endswith(trigger_value)
        
        elif trigger.trigger_type == TriggerType.REGEX:
            try:
                return bool(re.search(trigger_value, message_text, re.IGNORECASE))
            except re.error:
                logger.error(f"Неверное регулярное выражение в триггере {trigger.id}: {trigger_value}")
                return False
        
        elif trigger.trigger_type == TriggerType.NUMBER_RANGE:
            try:
                number = float(message_text.strip())
                range_data = json.loads(trigger_value)
                return range_data.get("min", 0) <= number <= range_data.get("max", 100)
            except (ValueError, json.JSONDecodeError):
                return False
        
        elif trigger.trigger_type == TriggerType.USER_STATE:
            return user.current_state.value == trigger_value
        
        elif trigger.trigger_type == TriggerType.USER_JOIN:
            return user.current_state == UserState.NEW
        
        return False
    
    async def _check_trigger_limits(self, db: AsyncSession, trigger: ChatbotTrigger, user: ChatbotUser) -> bool:
        """Проверка ограничений триггера"""
        
        # TODO: Реализовать проверку cooldown и max_triggers_per_user
        # Пока возвращаем True
        return True
    
    async def _process_current_scenario(self, db: AsyncSession, user: ChatbotUser, message_text: str) -> List[Dict[str, Any]]:
        """Обработка текущего сценария пользователя"""
        
        if not user.current_scenario_id:
            return []
        
        # Получаем текущий сценарий и шаг
        scenario_query = select(ChatbotScenario).options(
            selectinload(ChatbotScenario.steps)
        ).where(ChatbotScenario.id == user.current_scenario_id)
        
        result = await db.execute(scenario_query)
        scenario = result.scalar_one_or_none()
        
        if not scenario:
            # Сценарий не найден, сбрасываем состояние
            user.current_scenario_id = None
            user.current_step = 0
            return []
        
        # Находим текущий шаг
        current_step = None
        for step in scenario.steps:
            if step.step_order == user.current_step:
                current_step = step
                break
        
        if not current_step:
            return []
        
        # Проверяем триггеры шага
        actions = []
        for trigger_data in current_step.triggers:
            if await self._step_trigger_matches(trigger_data, message_text, user):
                
                # Добавляем действия шага
                actions.extend(current_step.actions)
                
                # Переходим к следующему шагу
                if current_step.success_next_step:
                    user.current_step = current_step.success_next_step
                else:
                    # Сценарий завершен
                    await self._complete_scenario(db, user, scenario)
                
                # Логируем прохождение шага
                await self._log_event(
                    db, "scenario_step_completed",
                    {
                        "scenario_id": str(scenario.id),
                        "step_id": str(current_step.id),
                        "user_id": str(user.id),
                        "step_order": current_step.step_order
                    }
                )
                
                break
        
        return actions
    
    async def _step_trigger_matches(self, trigger_data: Dict[str, Any], message_text: str, user: ChatbotUser) -> bool:
        """Проверка соответствия триггера шага"""
        
        # Упрощенная логика, аналогична _trigger_matches
        trigger_type = trigger_data.get("type", "contains")
        trigger_value = trigger_data.get("value", "").lower()
        message_lower = message_text.lower().strip()
        
        if trigger_type == "exact_match":
            return message_lower == trigger_value
        elif trigger_type == "contains":
            return trigger_value in message_lower
        elif trigger_type == "starts_with":
            return message_lower.startswith(trigger_value)
        elif trigger_type == "regex":
            try:
                return bool(re.search(trigger_data.get("value", ""), message_text, re.IGNORECASE))
            except re.error:
                return False
        
        return False
    
    async def _execute_actions(
        self, 
        db: AsyncSession, 
        user: ChatbotUser, 
        actions: List[Dict[str, Any]], 
        original_message: ChatbotMessage
    ) -> List[Dict[str, Any]]:
        """Выполнение действий"""
        
        responses = []
        
        for action in actions:
            action_type = action.get("type")
            action_data = action.get("data", {})
            
            try:
                if action_type == ActionType.SEND_MESSAGE.value:
                    response = await self._action_send_message(db, user, action_data)
                    responses.append(response)
                
                elif action_type == ActionType.SEND_TEMPLATE.value:
                    response = await self._action_send_template(db, user, action_data)
                    responses.append(response)
                
                elif action_type == ActionType.SET_USER_STATE.value:
                    await self._action_set_user_state(db, user, action_data)
                
                elif action_type == ActionType.AI_AGENT_CALL.value:
                    response = await self._action_call_ai_agent(db, user, action_data, original_message)
                    if response:
                        responses.append(response)
                
                elif action_type == ActionType.WEBHOOK_CALL.value:
                    await self._action_call_webhook(db, user, action_data)
                
                elif action_type == ActionType.GO_TO_STEP.value:
                    await self._action_go_to_step(db, user, action_data)
                
                elif action_type == ActionType.TAG_USER.value:
                    await self._action_tag_user(db, user, action_data)
                
                elif action_type == ActionType.DELAY.value:
                    # Задержка будет обработана позже (через Celery)
                    responses.append({
                        "type": "delay",
                        "delay_seconds": action_data.get("seconds", 1)
                    })
                
            except Exception as e:
                logger.error(f"Ошибка выполнения действия {action_type}: {e}")
                await self._log_event(
                    db, "action_execution_error",
                    {"action_type": action_type, "error": str(e), "user_id": str(user.id)}
                )
        
        return responses
    
    async def _action_send_message(self, db: AsyncSession, user: ChatbotUser, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Действие: отправить сообщение"""
        
        message_text = action_data.get("text", "")
        
        # Заменяем переменные
        message_text = await self._replace_variables(message_text, user)
        
        # Сохраняем сообщение бота
        bot_message = await self._save_message(db, user.id, message_text, "bot")
        
        return {
            "type": "send_message",
            "text": message_text,
            "message_id": str(bot_message.id)
        }
    
    async def _action_send_template(self, db: AsyncSession, user: ChatbotUser, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Действие: отправить шаблон"""
        
        template_id = action_data.get("template_id")
        if not template_id:
            return {"type": "error", "message": "Template ID not specified"}
        
        # Получаем шаблон
        query = select(ChatbotTemplate).where(ChatbotTemplate.id == template_id)
        result = await db.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            return {"type": "error", "message": "Template not found"}
        
        # Заменяем переменные в шаблоне
        message_text = await self._replace_variables(template.template_text, user)
        
        # Сохраняем сообщение
        bot_message = await self._save_message(db, user.id, message_text, "bot")
        
        return {
            "type": "send_template",
            "text": message_text,
            "template_type": template.template_type,
            "buttons": template.buttons,
            "message_id": str(bot_message.id)
        }
    
    async def _action_set_user_state(self, db: AsyncSession, user: ChatbotUser, action_data: Dict[str, Any]):
        """Действие: установить состояние пользователя"""
        
        new_state = action_data.get("state")
        if new_state and new_state in [state.value for state in UserState]:
            user.previous_state = user.current_state
            user.current_state = UserState(new_state)
            
            await self._log_event(
                db, "user_state_changed",
                {"user_id": str(user.id), "old_state": user.previous_state.value if user.previous_state else None, "new_state": new_state}
            )
    
    async def _action_call_ai_agent(
        self, 
        db: AsyncSession, 
        user: ChatbotUser, 
        action_data: Dict[str, Any],
        original_message: ChatbotMessage
    ) -> Optional[Dict[str, Any]]:
        """Действие: вызвать внешний AI агент"""
        
        agent_url = action_data.get("agent_url")
        if not agent_url:
            return None
        
        # Подготавливаем данные для AI агента
        payload = {
            "user_id": str(user.id),
            "instagram_user_id": user.instagram_user_id,
            "username": user.username,
            "message": original_message.content,
            "user_state": user.current_state.value,
            "context": user.state_data,
            "conversation_history": await self._get_recent_messages(db, user.id, limit=10)
        }
        
        # Помечаем сообщение как требующее AI обработки
        original_message.ai_processed = False
        
        return {
            "type": "ai_agent_call",
            "agent_url": agent_url,
            "payload": payload,
            "message_id": str(original_message.id)
        }
    
    async def _action_call_webhook(self, db: AsyncSession, user: ChatbotUser, action_data: Dict[str, Any]):
        """Действие: вызвать webhook"""
        
        webhook_url = action_data.get("url")
        payload = action_data.get("payload", {})
        
        # Добавляем данные пользователя
        payload.update({
            "user_id": str(user.id),
            "instagram_user_id": user.instagram_user_id,
            "username": user.username,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # TODO: Здесь должен быть асинхронный HTTP запрос к webhook'у
        # Пока просто логируем
        await self._log_event(
            db, "webhook_called",
            {"webhook_url": webhook_url, "payload": payload}
        )
    
    async def _action_go_to_step(self, db: AsyncSession, user: ChatbotUser, action_data: Dict[str, Any]):
        """Действие: перейти к шагу сценария"""
        
        scenario_id = action_data.get("scenario_id")
        step_number = action_data.get("step_number", 1)
        
        if scenario_id:
            user.current_scenario_id = scenario_id
            user.current_step = step_number
            user.scenario_started_at = datetime.utcnow()
            user.current_state = UserState.IN_SCENARIO
            
            await self._log_event(
                db, "scenario_started",
                {"user_id": str(user.id), "scenario_id": scenario_id, "step": step_number}
            )
    
    async def _action_tag_user(self, db: AsyncSession, user: ChatbotUser, action_data: Dict[str, Any]):
        """Действие: добавить тег пользователю"""
        
        tag = action_data.get("tag")
        if tag:
            if not user.tags:
                user.tags = []
            
            if tag not in user.tags:
                user.tags.append(tag)
                
                await self._log_event(
                    db, "user_tagged",
                    {"user_id": str(user.id), "tag": tag}
                )
    
    async def _replace_variables(self, text: str, user: ChatbotUser) -> str:
        """Замена переменных в тексте"""
        
        variables = {
            "{username}": user.username,
            "{first_name}": user.collected_data.get("first_name", user.username),
            "{user_state}": user.current_state.value,
            "{current_time}": datetime.now().strftime("%H:%M"),
            "{current_date}": datetime.now().strftime("%d.%m.%Y")
        }
        
        for var, value in variables.items():
            text = text.replace(var, str(value))
        
        return text
    
    async def _get_recent_messages(self, db: AsyncSession, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение последних сообщений для контекста"""
        
        query = select(ChatbotMessage).where(
            ChatbotMessage.user_id == user_id
        ).order_by(desc(ChatbotMessage.created_at)).limit(limit)
        
        result = await db.execute(query)
        messages = result.scalars().all()
        
        return [
            {
                "content": msg.content,
                "sender_type": msg.sender_type,
                "created_at": msg.created_at.isoformat()
            }
            for msg in reversed(messages)  # Хронологический порядок
        ]
    
    async def _complete_scenario(self, db: AsyncSession, user: ChatbotUser, scenario: ChatbotScenario):
        """Завершение сценария"""
        
        user.current_scenario_id = None
        user.current_step = 0
        user.current_state = UserState.ACTIVE
        user.total_scenarios_completed += 1
        
        # Обновляем статистику сценария
        scenario.total_completions += 1
        
        await self._log_event(
            db, "scenario_completed",
            {"user_id": str(user.id), "scenario_id": str(scenario.id)}
        )
    
    async def _update_statistics(
        self, 
        db: AsyncSession, 
        user: ChatbotUser, 
        message: ChatbotMessage, 
        processing_time: float
    ):
        """Обновление статистики"""
        
        user.total_messages += 1
        user.last_message_at = datetime.utcnow()
        
        message.processed = True
        message.processing_time_ms = int(processing_time)
    
    async def _log_event(
        self, 
        db: AsyncSession, 
        event_type: str, 
        event_data: Dict[str, Any],
        user_id: str = None,
        success: bool = True,
        error_message: str = None
    ) -> ChatbotEvent:
        """Логирование события"""
        
        event = ChatbotEvent(
            event_type=event_type,
            event_name=event_type.replace("_", " ").title(),
            user_id=user_id,
            event_data=event_data,
            success=success,
            error_message=error_message
        )
        
        db.add(event)
        return event


# Глобальный экземпляр сервиса
chatbot_service = ChatbotService()