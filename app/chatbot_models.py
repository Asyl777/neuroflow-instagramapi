"""
Модели для чат-бота конструктора
Система триггеров, событий и сценариев
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON, BigInteger, Index, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum
from datetime import datetime
from typing import Optional, List, Dict, Any


class TriggerType(str, enum.Enum):
    """Типы триггеров"""
    EXACT_MATCH = "exact_match"          # Точное совпадение текста
    CONTAINS = "contains"                # Содержит текст
    STARTS_WITH = "starts_with"          # Начинается с
    ENDS_WITH = "ends_with"              # Заканчивается на
    REGEX = "regex"                      # Регулярное выражение
    NUMBER_RANGE = "number_range"        # Диапазон чисел
    BUTTON_CLICK = "button_click"        # Нажатие кнопки
    USER_JOIN = "user_join"              # Новый пользователь
    TIME_BASED = "time_based"            # По времени
    USER_STATE = "user_state"            # По состоянию пользователя


class ActionType(str, enum.Enum):
    """Типы действий"""
    SEND_MESSAGE = "send_message"        # Отправить сообщение
    SEND_TEMPLATE = "send_template"      # Отправить шаблон
    SET_USER_STATE = "set_user_state"    # Установить состояние
    WEBHOOK_CALL = "webhook_call"        # Вызвать webhook
    AI_AGENT_CALL = "ai_agent_call"      # Вызвать AI агента
    DELAY = "delay"                      # Задержка
    GO_TO_STEP = "go_to_step"           # Перейти к шагу
    COLLECT_DATA = "collect_data"        # Собрать данные
    TAG_USER = "tag_user"               # Добавить тег пользователю


class UserState(str, enum.Enum):
    """Состояния пользователя"""
    NEW = "new"                         # Новый пользователь
    ACTIVE = "active"                   # Активный
    WAITING_INPUT = "waiting_input"     # Ждет ввода
    IN_SCENARIO = "in_scenario"         # В сценарии
    BLOCKED = "blocked"                 # Заблокирован
    VIP = "vip"                        # VIP клиент


class ChatbotScenario(Base):
    """Сценарии чат-бота (последовательности шагов)"""
    __tablename__ = "chatbot_scenarios"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(200), nullable=False, comment="Название сценария")
    description = Column(Text, nullable=True, comment="Описание сценария")
    
    # Настройки
    is_active = Column(Boolean, default=True, index=True, comment="Активен ли сценарий")
    priority = Column(Integer, default=100, comment="Приоритет (меньше = выше)")
    
    # Условия запуска сценария
    start_triggers = Column(JSONB, default=[], comment="Триггеры для запуска сценария")
    start_conditions = Column(JSONB, default={}, comment="Дополнительные условия")
    
    # Метаданные
    total_steps = Column(Integer, default=0, comment="Общее количество шагов")
    success_rate = Column(Float, default=0.0, comment="Процент успешных прохождений")
    avg_completion_time = Column(Integer, default=0, comment="Среднее время прохождения (сек)")
    
    # Статистика
    total_starts = Column(Integer, default=0, comment="Всего запусков")
    total_completions = Column(Integer, default=0, comment="Всего завершений")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    steps = relationship("ChatbotStep", back_populates="scenario", order_by="ChatbotStep.step_order")
    user_sessions = relationship("UserScenarioSession", back_populates="scenario")
    
    __table_args__ = (
        Index('ix_chatbot_scenarios_active_priority', is_active, priority),
    )
    
    def __repr__(self):
        return f"<ChatbotScenario(id={self.id}, name={self.name})>"


class ChatbotStep(Base):
    """Шаги сценария чат-бота"""
    __tablename__ = "chatbot_steps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_scenarios.id"), nullable=False)
    
    # Основная информация
    name = Column(String(200), nullable=False, comment="Название шага")
    step_order = Column(Integer, nullable=False, comment="Порядок шага в сценарии")
    description = Column(Text, nullable=True, comment="Описание шага")
    
    # Настройки шага
    is_active = Column(Boolean, default=True, comment="Активен ли шаг")
    is_required = Column(Boolean, default=False, comment="Обязательный ли шаг")
    timeout_seconds = Column(Integer, default=300, comment="Таймаут ожидания (сек)")
    
    # Триггеры для перехода к следующему шагу
    triggers = Column(JSONB, default=[], comment="Триггеры для активации шага")
    conditions = Column(JSONB, default={}, comment="Условия выполнения")
    
    # Действия на этом шаге
    actions = Column(JSONB, default=[], comment="Действия которые выполняются")
    
    # Данные которые собираем на этом шаге
    collect_data = Column(JSONB, default={}, comment="Какие данные собираем")
    validation_rules = Column(JSONB, default={}, comment="Правила валидации ввода")
    
    # Переходы
    success_next_step = Column(Integer, nullable=True, comment="Следующий шаг при успехе")
    failure_next_step = Column(Integer, nullable=True, comment="Следующий шаг при неудаче")
    fallback_actions = Column(JSONB, default=[], comment="Действия при неудаче")
    
    # Статистика
    total_visits = Column(Integer, default=0, comment="Количество посещений")
    success_count = Column(Integer, default=0, comment="Успешных прохождений")
    avg_time_spent = Column(Integer, default=0, comment="Среднее время на шаге")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    scenario = relationship("ChatbotScenario", back_populates="steps")
    
    __table_args__ = (
        Index('ix_chatbot_steps_scenario_order', scenario_id, step_order),
    )
    
    def __repr__(self):
        return f"<ChatbotStep(id={self.id}, name={self.name}, order={self.step_order})>"


class ChatbotTrigger(Base):
    """Триггеры чат-бота (глобальные правила)"""
    __tablename__ = "chatbot_triggers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(200), nullable=False, comment="Название триггера")
    description = Column(Text, nullable=True, comment="Описание триггера")
    
    # Тип и настройки триггера
    trigger_type = Column(Enum(TriggerType), nullable=False, comment="Тип триггера")
    trigger_value = Column(Text, nullable=False, comment="Значение триггера")
    trigger_conditions = Column(JSONB, default={}, comment="Дополнительные условия")
    
    # Настройки
    is_active = Column(Boolean, default=True, index=True, comment="Активен ли триггер")
    priority = Column(Integer, default=100, comment="Приоритет выполнения")
    is_global = Column(Boolean, default=False, comment="Глобальный триггер (работает везде)")
    
    # Ограничения
    max_triggers_per_user = Column(Integer, default=None, comment="Максимум срабатываний на пользователя")
    cooldown_seconds = Column(Integer, default=0, comment="Задержка между срабатываниями")
    active_hours = Column(JSONB, default={}, comment="Часы активности")
    
    # Действия при срабатывании
    actions = Column(JSONB, nullable=False, default=[], comment="Действия при срабатывании")
    
    # Статистика
    total_triggers = Column(Integer, default=0, comment="Всего срабатываний")
    success_rate = Column(Float, default=0.0, comment="Процент успешных срабатываний")
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index('ix_chatbot_triggers_type_active', trigger_type, is_active),
        Index('ix_chatbot_triggers_active_priority', is_active, priority),
    )
    
    def __repr__(self):
        return f"<ChatbotTrigger(id={self.id}, name={self.name}, type={self.trigger_type})>"


class ChatbotUser(Base):
    """Пользователи чат-бота с состоянием"""
    __tablename__ = "chatbot_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    instagram_user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=False, index=True)
    
    # Состояние пользователя
    current_state = Column(Enum(UserState), default=UserState.NEW, index=True)
    previous_state = Column(Enum(UserState), nullable=True)
    state_data = Column(JSONB, default={}, comment="Данные состояния")
    
    # Текущий сценарий
    current_scenario_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_scenarios.id"), nullable=True)
    current_step = Column(Integer, default=0, comment="Текущий шаг в сценарии")
    scenario_started_at = Column(DateTime(timezone=True), nullable=True)
    
    # Собранные данные
    collected_data = Column(JSONB, default={}, comment="Данные собранные от пользователя")
    user_preferences = Column(JSONB, default={}, comment="Предпочтения пользователя")
    
    # Теги и сегменты
    tags = Column(JSONB, default=[], comment="Теги пользователя")
    segment = Column(String(50), nullable=True, comment="Сегмент пользователя")
    
    # Статистика
    total_messages = Column(Integer, default=0)
    total_scenarios_started = Column(Integer, default=0)
    total_scenarios_completed = Column(Integer, default=0)
    avg_response_time = Column(Integer, default=0, comment="Среднее время ответа (сек)")
    
    # Метаданные
    first_seen_at = Column(DateTime(timezone=True), default=func.now())
    last_activity_at = Column(DateTime(timezone=True), default=func.now())
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    sessions = relationship("UserScenarioSession", back_populates="user")
    messages = relationship("ChatbotMessage", back_populates="user")
    
    __table_args__ = (
        Index('ix_chatbot_users_state', current_state),
        Index('ix_chatbot_users_scenario', current_scenario_id, current_step),
        Index('ix_chatbot_users_activity', last_activity_at.desc()),
    )
    
    def __repr__(self):
        return f"<ChatbotUser(id={self.id}, username={self.username}, state={self.current_state})>"


class UserScenarioSession(Base):
    """Сессии прохождения сценариев пользователями"""
    __tablename__ = "user_scenario_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_users.id"), nullable=False)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_scenarios.id"), nullable=False)
    
    # Статус сессии
    status = Column(String(20), default="active", index=True, comment="active, completed, abandoned, failed")
    current_step = Column(Integer, default=1, comment="Текущий шаг")
    
    # Данные сессии
    session_data = Column(JSONB, default={}, comment="Данные собранные в сессии")
    step_history = Column(JSONB, default=[], comment="История прохождения шагов")
    
    # Время
    started_at = Column(DateTime(timezone=True), default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), default=func.now())
    
    # Результаты
    completion_rate = Column(Float, default=0.0, comment="Процент завершения")
    total_steps_completed = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    user = relationship("ChatbotUser", back_populates="sessions")
    scenario = relationship("ChatbotScenario", back_populates="user_sessions")
    
    __table_args__ = (
        Index('ix_user_scenario_sessions_user_status', user_id, status),
        Index('ix_user_scenario_sessions_scenario_status', scenario_id, status),
    )
    
    def __repr__(self):
        return f"<UserScenarioSession(id={self.id}, status={self.status}, step={self.current_step})>"


class ChatbotMessage(Base):
    """Сообщения чат-бота с контекстом"""
    __tablename__ = "chatbot_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_users.id"), nullable=False)
    
    # Содержимое
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text", comment="text, image, button, template")
    sender_type = Column(String(10), nullable=False, comment="user или bot")
    
    # Контекст
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_scenarios.id"), nullable=True)
    step_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_steps.id"), nullable=True)
    trigger_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_triggers.id"), nullable=True)
    
    # Instagram данные
    instagram_message_id = Column(String(100), unique=True, nullable=True)
    instagram_thread_id = Column(String(100), nullable=True)
    
    # Обработка
    processed = Column(Boolean, default=False, index=True)
    triggered_actions = Column(JSONB, default=[], comment="Сработавшие действия")
    processing_time_ms = Column(Integer, nullable=True)
    
    # AI данные (если использовался внешний AI)
    ai_processed = Column(Boolean, default=False, comment="Обработано внешним AI")
    ai_agent_response = Column(JSONB, default={}, comment="Ответ от AI агента")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Связи
    user = relationship("ChatbotUser", back_populates="messages")
    
    __table_args__ = (
        Index('ix_chatbot_messages_user_created', user_id, created_at.desc()),
        Index('ix_chatbot_messages_processed', processed),
        Index('ix_chatbot_messages_sender', sender_type),
        Index('ix_chatbot_messages_scenario_step', scenario_id, step_id),
    )
    
    def __repr__(self):
        return f"<ChatbotMessage(id={self.id}, sender={self.sender_type}, processed={self.processed})>"


class ChatbotTemplate(Base):
    """Шаблоны сообщений для чат-бота"""
    __tablename__ = "chatbot_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(200), nullable=False, comment="Название шаблона")
    category = Column(String(50), default="general", index=True, comment="Категория шаблона")
    
    # Содержимое шаблона
    template_text = Column(Text, nullable=False, comment="Текст шаблона с переменными")
    template_variables = Column(JSONB, default=[], comment="Список переменных в шаблоне")
    template_type = Column(String(20), default="text", comment="text, button, carousel, etc")
    
    # Настройки
    is_active = Column(Boolean, default=True, index=True)
    language = Column(String(10), default="ru", comment="Язык шаблона")
    
    # Кнопки и интерактивность (если есть)
    buttons = Column(JSONB, default=[], comment="Кнопки для шаблона")
    quick_replies = Column(JSONB, default=[], comment="Быстрые ответы")
    
    # Статистика использования
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0, comment="Процент успешных отправок")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index('ix_chatbot_templates_category_active', category, is_active),
    )
    
    def __repr__(self):
        return f"<ChatbotTemplate(id={self.id}, name={self.name}, category={self.category})>"


class ChatbotEvent(Base):
    """События в системе чат-бота"""
    __tablename__ = "chatbot_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Основная информация
    event_type = Column(String(50), nullable=False, index=True, comment="Тип события")
    event_name = Column(String(200), nullable=False, comment="Название события")
    
    # Участники события
    user_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_users.id"), nullable=True)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_scenarios.id"), nullable=True)
    trigger_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_triggers.id"), nullable=True)
    
    # Данные события
    event_data = Column(JSONB, default={}, comment="Данные события")
    context = Column(JSONB, default={}, comment="Контекст события")
    
    # Результат
    success = Column(Boolean, default=True, index=True)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('ix_chatbot_events_type_created', event_type, created_at.desc()),
        Index('ix_chatbot_events_user_created', user_id, created_at.desc()),
        Index('ix_chatbot_events_success', success),
    )
    
    def __repr__(self):
        return f"<ChatbotEvent(id={self.id}, type={self.event_type}, success={self.success})>"