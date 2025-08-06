"""
Конфигурация для тестов Instagram API
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient
import asyncio

# Добавляем путь к приложению
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from main import app, get_api_key


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для всех тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """Тестовый клиент FastAPI"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client():
    """Асинхронный тестовый клиент"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def valid_api_key():
    """Валидный API ключ для тестов"""
    return "neuro123"


@pytest.fixture
def invalid_api_key():
    """Невалидный API ключ для тестов"""
    return "invalid_key"


@pytest.fixture
def auth_headers(valid_api_key):
    """Заголовки с валидным API ключом"""
    return {"x-api-key": valid_api_key}


@pytest.fixture
def invalid_auth_headers(invalid_api_key):
    """Заголовки с невалидным API ключом"""
    return {"x-api-key": invalid_api_key}


@pytest.fixture
def temp_session_file():
    """Временный файл сессии для тестов"""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp_file:
        temp_file.write('{"test": "session"}')
        temp_file_path = temp_file.name
    
    yield temp_file_path
    
    # Удаляем временный файл после теста
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


@pytest.fixture
def mock_instagram_client():
    """Мок Instagram клиента"""
    mock_client = Mock()
    mock_client.login.return_value = True
    mock_client.dump_settings.return_value = None
    mock_client.load_settings.return_value = None
    mock_client.user_id_from_username.return_value = "123456789"
    mock_client.direct_send.return_value = True
    mock_client.direct_threads.return_value = []
    return mock_client


@pytest.fixture
def sample_login_data():
    """Тестовые данные для логина"""
    return {
        "username": "test_user",
        "password": "test_password"
    }


@pytest.fixture
def sample_message_data():
    """Тестовые данные для сообщения"""
    return {
        "username": "recipient_user",
        "text": "Тестовое сообщение"
    }


@pytest.fixture
def mock_direct_threads():
    """Мок данных для direct threads"""
    mock_thread = Mock()
    mock_thread.dict.return_value = {
        "id": "thread_123",
        "users": ["user1", "user2"],
        "messages": []
    }
    mock_thread.id = "thread_123"
    
    mock_user = Mock()
    mock_user.username = "test_user"
    mock_thread.users = [mock_user]
    
    return [mock_thread]


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Автоматическая настройка окружения для каждого теста"""
    # Устанавливаем тестовые переменные окружения
    os.environ['TESTING'] = 'true'
    yield
    # Очищаем после теста
    if 'TESTING' in os.environ:
        del os.environ['TESTING']