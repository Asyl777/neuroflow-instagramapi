"""
Модели базы данных для Instagram API с ИИ функциональностью
Использует существующую базу neuroflow с префиксом таблиц instagram_
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON, BigInteger, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
from datetime import datetime
from typing import Optional


class InstagramUser(Base):
    """Пользователи Instagram"""
    __tablename__ = "instagram_users"
    
    id = Column(Integer, primary_key=True, index=True)
    instagram_user_id = Column(BigInteger, unique=True, index=True, nullable=False, comment="ID пользователя в Instagram")
    username = Column(String(100), nullable=False, index=True, comment="Username в Instagram")
    full_name = Column(String(200), nullable=True, comment="Полное имя пользователя")
    profile_pic_url = Column(Text, nullable=True, comment="URL аватара")
    is_verified = Column(Boolean, default=False, comment="Верифицированный аккаунт")
    is_private = Column(Boolean, default=False, comment="Приватный аккаунт")
    follower_count = Column(Integer, default=0, comment="Количество подписчиков")
    following_count = Column(Integer, default=0, comment="Количество подписок")
    
    # Настройки пользователя для ИИ
    ai_preferences = Column(JSONB, default={}, comment="Настройки ИИ для пользователя")
    language = Column(String(10), default="ru", comment="Предпочитаемый язык")
    timezone = Column(String(50), default="UTC", comment="Часовой пояс")
    
    # Метаданные
    first_interaction = Column(DateTime(timezone=True), default=func.now(), comment="Первое взаимодействие")
    last_activity = Column(DateTime(timezone=True), default=func.now(), comment="Последняя активность")
    total_messages = Column(Integer, default=0, comment="Общее количество сообщений")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    conversations = relationship("InstagramConversation", back_populates="user")
    
    # Индексы
    __table_args__ = (
        Index('ix_instagram_users_username_lower', func.lower(username)),
        Index('ix_instagram_users_last_activity', last_activity.desc()),
    )
    
    def __repr__(self):
        return f"<InstagramUser(id={self.id}, username={self.username})>"


class InstagramConversation(Base):
    """Диалоги в Instagram с ИИ контекстом"""
    __tablename__ = "instagram_conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    instagram_thread_id = Column(String(100), unique=True, index=True, nullable=False, comment="ID треда в Instagram")
    user_id = Column(Integer, ForeignKey("instagram_users.id"), nullable=False, comment="ID пользователя")
    
    # Статус диалога
    status = Column(String(20), default="active", index=True, comment="Статус: active, paused, completed, archived")
    conversation_type = Column(String(30), default="direct", comment="Тип: direct, support, sales, etc")
    
    # ИИ контекст и память
    context_summary = Column(Text, nullable=True, comment="Краткое изложение диалога для ИИ")
    ai_personality = Column(String(50), default="helpful", comment="Личность ИИ: helpful, sales, support")
    context_data = Column(JSONB, default={}, comment="Структурированный контекст для ИИ")
    
    # Аналитика диалога
    sentiment_overall = Column(String(20), nullable=True, comment="Общий sentiment: positive, neutral, negative")
    intent_category = Column(String(50), nullable=True, comment="Категория намерений пользователя")
    conversation_score = Column(Float, default=0.0, comment="Оценка качества диалога (0.0-1.0)")
    
    # Настройки ИИ для диалога
    ai_enabled = Column(Boolean, default=True, comment="Включен ли ИИ для этого диалога")
    auto_reply = Column(Boolean, default=False, comment="Автоматические ответы")
    response_delay = Column(Integer, default=0, comment="Задержка ответа в секундах")
    
    # Метаданные
    message_count = Column(Integer, default=0, comment="Количество сообщений в диалоге")
    last_message_at = Column(DateTime(timezone=True), nullable=True, comment="Время последнего сообщения")
    last_ai_response_at = Column(DateTime(timezone=True), nullable=True, comment="Время последнего ответа ИИ")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    user = relationship("InstagramUser", back_populates="conversations")
    messages = relationship("InstagramMessage", back_populates="conversation", order_by="InstagramMessage.created_at")
    
    # Индексы
    __table_args__ = (
        Index('ix_instagram_conversations_user_status', user_id, status),
        Index('ix_instagram_conversations_last_message', last_message_at.desc().nulls_last()),
        Index('ix_instagram_conversations_ai_enabled', ai_enabled),
    )
    
    def __repr__(self):
        return f"<InstagramConversation(id={self.id}, thread_id={self.instagram_thread_id})>"


class InstagramMessage(Base):
    """Сообщения в Instagram с ИИ аналитикой"""
    __tablename__ = "instagram_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("instagram_conversations.id"), nullable=False)
    instagram_message_id = Column(String(100), unique=True, nullable=True, comment="ID сообщения в Instagram")
    
    # Содержимое сообщения
    content = Column(Text, nullable=False, comment="Текст сообщения")
    message_type = Column(String(20), default="text", comment="Тип: text, image, voice, video, sticker")
    sender_type = Column(String(10), nullable=False, comment="user или bot")
    
    # Медиа файлы
    media_urls = Column(JSONB, default=[], comment="URL медиа файлов")
    media_metadata = Column(JSONB, default={}, comment="Метаданные медиа")
    
    # ИИ анализ
    ai_generated = Column(Boolean, default=False, comment="Сгенерировано ИИ")
    ai_model = Column(String(50), nullable=True, comment="Модель ИИ использованная для генерации")
    ai_prompt_tokens = Column(Integer, nullable=True, comment="Количество токенов в промпте")
    ai_completion_tokens = Column(Integer, nullable=True, comment="Количество токенов в ответе")
    ai_confidence = Column(Float, nullable=True, comment="Уверенность ИИ в ответе (0.0-1.0)")
    
    # Анализ сообщения
    sentiment = Column(String(20), nullable=True, comment="Sentiment: positive, neutral, negative")
    sentiment_score = Column(Float, nullable=True, comment="Оценка sentiment (-1.0 до 1.0)")
    intent = Column(String(50), nullable=True, comment="Намерение пользователя")
    entities = Column(JSONB, default=[], comment="Извлеченные сущности")
    topics = Column(JSONB, default=[], comment="Темы сообщения")
    
    # Обработка
    processed = Column(Boolean, default=False, comment="Обработано ИИ")
    requires_human = Column(Boolean, default=False, comment="Требует вмешательства человека")
    flagged = Column(Boolean, default=False, comment="Помечено как проблемное")
    flag_reason = Column(String(100), nullable=True, comment="Причина пометки")
    
    # Метаданные
    response_time_ms = Column(Integer, nullable=True, comment="Время ответа ИИ в мс")
    instagram_timestamp = Column(DateTime(timezone=True), nullable=True, comment="Время в Instagram")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Связи
    conversation = relationship("InstagramConversation", back_populates="messages")
    
    # Индексы
    __table_args__ = (
        Index('ix_instagram_messages_conversation_created', conversation_id, created_at.desc()),
        Index('ix_instagram_messages_sender_type', sender_type),
        Index('ix_instagram_messages_ai_generated', ai_generated),
        Index('ix_instagram_messages_processed', processed),
        Index('ix_instagram_messages_requires_human', requires_human),
        Index('ix_instagram_messages_sentiment', sentiment),
    )
    
    def __repr__(self):
        return f"<InstagramMessage(id={self.id}, sender={self.sender_type})>"


class InstagramAgentPlan(Base):
    """Планы и задачи ИИ агента"""
    __tablename__ = "instagram_agent_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(200), nullable=False, comment="Название плана")
    description = Column(Text, nullable=True, comment="Описание плана")
    
    # План
    goal = Column(Text, nullable=False, comment="Цель плана")
    steps = Column(JSONB, nullable=False, default=[], comment="Шаги выполнения")
    constraints = Column(JSONB, default=[], comment="Ограничения")
    
    # Выполнение
    status = Column(String(20), default="pending", index=True, comment="pending, running, completed, failed, paused")
    progress = Column(Float, default=0.0, comment="Прогресс выполнения (0.0-1.0)")
    current_step = Column(Integer, default=0, comment="Текущий шаг")
    
    # Результаты
    result_data = Column(JSONB, default={}, comment="Результаты выполнения")
    error_message = Column(Text, nullable=True, comment="Сообщение об ошибке")
    
    # Настройки
    priority = Column(String(10), default="normal", comment="low, normal, high, urgent")
    scheduled_at = Column(DateTime(timezone=True), nullable=True, comment="Время запланированного выполнения")
    retry_count = Column(Integer, default=0, comment="Количество повторов")
    max_retries = Column(Integer, default=3, comment="Максимальное количество повторов")
    
    # Связи
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("instagram_conversations.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("instagram_users.id"), nullable=True)
    
    # Метаданные
    estimated_duration = Column(Integer, nullable=True, comment="Оценка времени выполнения в секундах")
    actual_duration = Column(Integer, nullable=True, comment="Фактическое время выполнения")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Индексы
    __table_args__ = (
        Index('ix_instagram_agent_plans_status_priority', status, priority),
        Index('ix_instagram_agent_plans_scheduled', scheduled_at),
    )
    
    def __repr__(self):
        return f"<InstagramAgentPlan(id={self.id}, name={self.name}, status={self.status})>"


class InstagramAutoReplyRule(Base):
    """Правила автоматических ответов"""
    __tablename__ = "instagram_auto_reply_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(200), nullable=False, comment="Название правила")
    description = Column(Text, nullable=True, comment="Описание правила")
    
    # Триггеры
    trigger_type = Column(String(50), nullable=False, comment="keyword, intent, sentiment, time, etc")
    trigger_value = Column(Text, nullable=False, comment="Значение триггера")
    trigger_conditions = Column(JSONB, default={}, comment="Дополнительные условия")
    
    # Ответ
    response_type = Column(String(30), default="template", comment="template, ai_generated, function")
    response_template = Column(Text, nullable=True, comment="Шаблон ответа")
    response_data = Column(JSONB, default={}, comment="Данные для ответа")
    
    # Настройки
    is_active = Column(Boolean, default=True, index=True, comment="Активно ли правило")
    priority = Column(Integer, default=100, comment="Приоритет (меньше = выше)")
    delay_seconds = Column(Integer, default=0, comment="Задержка перед ответом")
    
    # Ограничения
    max_uses_per_user = Column(Integer, nullable=True, comment="Максимальное использование на пользователя")
    max_uses_per_day = Column(Integer, nullable=True, comment="Максимальное использование в день")
    time_conditions = Column(JSONB, default={}, comment="Временные ограничения")
    
    # Статистика
    total_uses = Column(Integer, default=0, comment="Общее количество использований")
    success_rate = Column(Float, default=0.0, comment="Процент успешных срабатываний")
    last_used_at = Column(DateTime(timezone=True), nullable=True, comment="Время последнего использования")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Индексы
    __table_args__ = (
        Index('ix_instagram_auto_reply_rules_active_priority', is_active, priority),
        Index('ix_instagram_auto_reply_rules_trigger_type', trigger_type),
    )
    
    def __repr__(self):
        return f"<InstagramAutoReplyRule(id={self.id}, name={self.name})>"