# 📖 Instagram Chatbot API Documentation

## 🎯 **Архитектура: Instagram → API → AI Agents**

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│    Instagram    │ ←→ │  Instagram API       │ ←→ │   AI Agents     │
│                 │    │  (Конструктор бота)  │    │  (Отдельный     │
│ - Сообщения     │    │  - Триггеры          │    │   проект)       │
│ - События       │    │  - Правила           │    │  - OpenAI       │
│ - Webhook'и     │    │  - Сценарии          │    │  - Claude       │
└─────────────────┘    │  - События           │    │  - Local LLM    │
                       │  - API для AI        │    └─────────────────┘
                       └──────────────────────┘
```

## 🚀 **Основные возможности**

### ✅ **Конструктор чат-бота:**
- **Триггеры**: "Если клиент написал '1' → отправить шаблон"
- **Сценарии**: Многошаговые диалоги с переходами
- **Состояния пользователей**: NEW, ACTIVE, IN_SCENARIO, VIP
- **Шаблоны**: Готовые ответы с переменными
- **События**: Логирование всех действий

### 🤖 **AI Agent интеграция:**
- **Внешние AI агенты**: OpenAI, Claude, локальные модели
- **Контекст диалогов**: История, состояние, предпочтения
- **Webhook callbacks**: Получение ответов от AI
- **Аналитика**: Метрики использования AI

## 📋 **API Эндпоинты**

### 🎯 **Для внешних AI Агентов**

#### POST `/api/v1/ai/process-message`
**Основной эндпоинт для обработки сообщений**

```json
{
  "instagram_user_id": 123456789,
  "username": "john_doe", 
  "message": "Привет, хочу узнать о ваших услугах",
  "instagram_message_id": "msg_123",
  "instagram_thread_id": "thread_456"
}
```

**Ответ:**
```json
{
  "success": true,
  "user_id": "uuid-user-id",
  "responses": [
    {
      "type": "send_message",
      "text": "Привет, John! Рад помочь с информацией об услугах."
    },
    {
      "type": "ai_agent_call",
      "agent_url": "https://your-ai-agent.com/chat",
      "payload": {
        "user_id": "uuid",
        "message": "Привет...",
        "context": {...}
      }
    }
  ],
  "user_state": "active",
  "processing_time_ms": 150
}
```

#### POST `/api/v1/ai/agent-response`
**Получение ответа от внешнего AI агента**

```json
{
  "response": "Конечно! Наши основные услуги включают...",
  "confidence": 0.95,
  "actions": [
    {
      "type": "send_template",
      "data": {"template_id": "services_overview"}
    }
  ],
  "user_state": "interested",
  "next_step": "show_pricing"
}
```

#### GET `/api/v1/ai/user/{user_id}/context`
**Получение контекста пользователя для AI**

**Ответ:**
```json
{
  "user_id": "uuid",
  "instagram_user_id": 123456789,
  "username": "john_doe",
  "current_state": "active",
  "collected_data": {
    "name": "John",
    "interests": ["web-design", "marketing"]
  },
  "message_history": [
    {
      "content": "Привет",
      "sender_type": "user",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### 🛠️ **Управление чат-ботом**

#### POST `/api/v1/chatbot/triggers`
**Создание триггера**

```json
{
  "name": "Приветствие новых пользователей",
  "trigger_type": "exact_match",
  "trigger_value": "привет",
  "actions": [
    {
      "type": "send_message",
      "data": {
        "text": "Привет, {username}! Добро пожаловать! 👋"
      }
    },
    {
      "type": "set_user_state", 
      "data": {"state": "active"}
    }
  ],
  "is_active": true,
  "priority": 10
}
```

#### POST `/api/v1/chatbot/scenarios`
**Создание сценария**

```json
{
  "name": "Процесс продажи",
  "description": "Сценарий для продажи услуг",
  "start_triggers": [
    {"type": "contains", "value": "купить"},
    {"type": "contains", "value": "заказать"}
  ],
  "steps": [
    {
      "name": "Уточнение потребностей",
      "triggers": [{"type": "contains", "value": "*"}],
      "actions": [
        {
          "type": "send_message",
          "data": {"text": "Какие услуги вас интересуют?"}
        }
      ]
    },
    {
      "name": "Презентация услуг",
      "triggers": [{"type": "contains", "value": "*"}],
      "actions": [
        {
          "type": "send_template",
          "data": {"template_id": "services_catalog"}
        }
      ]
    }
  ]
}
```

#### POST `/api/v1/chatbot/templates`
**Создание шаблона**

```json
{
  "name": "Каталог услуг",
  "category": "sales",
  "template_text": "🎯 Наши услуги для {username}:\n\n1️⃣ Веб-дизайн - от 50,000₽\n2️⃣ Маркетинг - от 30,000₽\n3️⃣ SEO - от 25,000₽\n\nВыберите интересующую услугу:",
  "template_type": "text",
  "buttons": [
    {"text": "1", "value": "web_design"},
    {"text": "2", "value": "marketing"},
    {"text": "3", "value": "seo"}
  ]
}
```

### 📊 **Аналитика и мониторинг**

#### GET `/api/v1/chatbot/analytics/overview`
**Общая аналитика**

```json
{
  "period_days": 7,
  "total_users": 1250,
  "active_users": 347,
  "total_messages": 5240,
  "user_states": {
    "new": 125,
    "active": 892,
    "in_scenario": 233
  },
  "engagement_rate": 27.76
}
```

#### GET `/api/v1/ai/users/active`
**Активные пользователи**

```json
[
  {
    "user_id": "uuid1",
    "instagram_user_id": 123456789,
    "username": "john_doe",
    "current_state": "in_scenario",
    "last_activity_at": "2024-01-15T15:30:00Z",
    "total_messages": 15
  }
]
```

## 🔧 **Примеры использования**

### **Пример 1: Простой триггер на ключевое слово**

```python
# Создание триггера "цена"
trigger_data = {
    "name": "Запрос цены",
    "trigger_type": "contains",
    "trigger_value": "цена",
    "actions": [
        {
            "type": "send_template",
            "data": {"template_id": "price_list"}
        }
    ]
}

response = requests.post(
    "http://localhost:8001/api/v1/chatbot/triggers",
    json=trigger_data,
    headers={"x-api-key": "neuro123"}
)
```

### **Пример 2: Сценарий сбора контактов**

```python
scenario_data = {
    "name": "Сбор контактов",
    "start_triggers": [
        {"type": "contains", "value": "контакт"},
        {"type": "contains", "value": "связаться"}
    ],
    "steps": [
        {
            "name": "Запрос имени",
            "actions": [{"type": "send_message", "data": {"text": "Как вас зовут?"}}],
            "collect_data": {"field": "name", "type": "text"}
        },
        {
            "name": "Запрос телефона", 
            "actions": [{"type": "send_message", "data": {"text": "Ваш номер телефона?"}}],
            "collect_data": {"field": "phone", "type": "phone"}
        }
    ]
}
```

### **Пример 3: AI Agent интеграция**

```python
# В вашем AI Agent проекте
@app.post("/chat")
async def ai_chat(request: dict):
    user_message = request["message"]
    context = request["context"]
    
    # Генерация ответа через OpenAI/Claude
    ai_response = await generate_ai_response(user_message, context)
    
    # Отправка ответа обратно в Instagram API
    response_data = {
        "response": ai_response,
        "confidence": 0.95,
        "actions": [
            {
                "type": "tag_user",
                "data": {"tag": "ai_assisted"}
            }
        ]
    }
    
    # Отправляем callback в Instagram API
    await send_callback(request["user_id"], response_data)
    
    return {"status": "processed"}
```

### **Пример 4: Webhook обработка**

```python
# Instagram webhook обработка
@app.post("/webhooks/instagram")  
async def instagram_webhook(data: dict):
    # Данные автоматически обрабатываются чат-ботом
    # Триггеры проверяются, сценарии запускаются
    # AI агенты вызываются при необходимости
    
    return {"status": "processed"}
```

## 🎯 **Типы триггеров**

| Тип | Описание | Пример |
|-----|----------|---------|
| `exact_match` | Точное совпадение | "привет" → срабатывает на "привет" |
| `contains` | Содержит текст | "цена" → срабатывает на "какая цена?" |
| `starts_with` | Начинается с | "заказ" → срабатывает на "заказать услугу" |
| `regex` | Регулярное выражение | `\d+` → срабатывает на любое число |
| `number_range` | Диапазон чисел | 1-10 → срабатывает на "5" |
| `user_state` | Состояние пользователя | "new" → только для новых |

## 🔄 **Типы действий**

| Тип | Описание | Пример использования |
|-----|----------|---------------------|
| `send_message` | Отправить сообщение | Простой текстовый ответ |
| `send_template` | Отправить шаблон | Каталог, прайс-лист |
| `set_user_state` | Установить состояние | Перевести в VIP |
| `ai_agent_call` | Вызвать AI агента | Сложный вопрос → AI |
| `go_to_step` | Перейти к сценарию | Запуск продаж |
| `tag_user` | Добавить тег | Сегментация |
| `webhook_call` | Вызвать webhook | Внешняя интеграция |

## 🚀 **Быстрый старт**

### 1. Запуск системы

```bash
# Запуск с Docker Compose
docker-compose up -d --build

# Проверка здоровья
curl http://localhost:8001/health
```

### 2. Создание первого триггера

```bash
curl -X POST http://localhost:8001/api/v1/chatbot/triggers \
  -H "x-api-key: neuro123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Приветствие",
    "trigger_type": "contains", 
    "trigger_value": "привет",
    "actions": [
      {
        "type": "send_message",
        "data": {"text": "Привет! Чем могу помочь?"}
      }
    ]
  }'
```

### 3. Тест сообщения

```bash
curl -X POST http://localhost:8001/api/v1/ai/process-message \
  -H "x-api-key: neuro123" \
  -H "Content-Type: application/json" \
  -d '{
    "instagram_user_id": 123456789,
    "username": "test_user",
    "message": "Привет!"
  }'
```

## 🔐 **Безопасность**

- Все эндпоинты требуют API ключ в заголовке `x-api-key`
- Валидация входных данных через Pydantic
- Логирование всех действий и событий
- Ограничения на частоту запросов (планируется)

## 📈 **Мониторинг**

- **Health Check**: `/health` - статус всех сервисов
- **События**: `/api/v1/chatbot/events` - лог всех событий  
- **Аналитика**: `/api/v1/chatbot/analytics/overview` - метрики
- **Пользователи**: `/api/v1/ai/users/active` - активность

Теперь у вас есть полноценный **конструктор чат-бота** для Instagram с возможностью интеграции внешних AI агентов! 🎉