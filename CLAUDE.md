# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

This is a FastAPI-based Instagram API wrapper that provides endpoints for Instagram messaging functionality. The application uses the `instagrapi` library to interact with Instagram's private API.

### Key Components

- **main.py**: Core FastAPI application with Instagram messaging endpoints
- **Session Management**: Persistent Instagram login sessions stored in `session.json`
- **API Key Authentication**: Simple API key authentication using `neuro123` as the key
- **Docker containerization**: Application runs in Docker container exposed on port 8001

### API Endpoints

- `POST /login`: Authenticate with Instagram credentials
- `POST /send_message`: Send direct messages to users
- `GET /inbox`: Retrieve recent direct message threads
- `GET /dialogs`: Get list of conversation threads

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application locally
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Docker Development
```bash
# Build and run with docker-compose
docker-compose up --build

# Build Docker image manually
docker build -f build/Dockerfile -t insta-bot .

# Run container
docker run -p 8001:8001 insta-bot
```

## Important Notes

- The application requires the `neuroflow` Docker network to be created externally
- Instagram session data is persisted in `session.json` files for maintaining login state
- API authentication uses a hardcoded key (`neuro123`) via `x-api-key` header
- CORS is configured to allow all origins for development
- The app directory is mounted as a volume in Docker for live code updates

## Testing

Проект включает комплексный набор тестов с покрытием 80%+.

### Запуск тестов
```bash
# Все тесты
pytest

# С покрытием кода
pytest --cov=app --cov-report=html

# Конкретная категория
pytest tests/test_auth.py -v
pytest tests/test_api.py -v
pytest tests/test_errors.py -v
pytest tests/test_integration.py -v

# По маркерам
pytest -m security      # Тесты безопасности
pytest -m performance   # Тесты производительности
pytest -m "not slow"    # Исключить медленные тесты
```

### Структура тестов
- `test_auth.py` - Тесты аутентификации и безопасности API ключей
- `test_api.py` - Тесты всех эндпоинтов с моками Instagram API
- `test_errors.py` - Тесты обработки ошибок и граничных случаев
- `test_integration.py` - Интеграционные тесты полных рабочих циклов
- `test_utils.py` - Утилиты и моки для тестирования
- `conftest.py` - Общие фикстуры и настройки pytest

## File Structure
```
├── app/
│   ├── main.py          # FastAPI application
│   └── session.json     # Instagram session data
├── build/
│   └── Dockerfile       # Container configuration  
├── compose.yml          # Docker Compose setup
├── requirements.txt     # Python dependencies
├── tests/               # Comprehensive test suite
│   ├── conftest.py      # Test configuration and fixtures
│   ├── test_auth.py     # Authentication tests
│   ├── test_api.py      # API endpoint tests
│   ├── test_errors.py   # Error handling tests
│   ├── test_integration.py # Integration tests
│   ├── test_utils.py    # Testing utilities
│   └── README.md        # Testing documentation
└── pytest.ini          # Pytest configuration
```