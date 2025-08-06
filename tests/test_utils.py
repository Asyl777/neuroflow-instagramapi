"""
Утилиты для тестирования Instagram API
"""
import os
import json
import tempfile
from typing import Dict, Any, Optional
from unittest.mock import Mock


class MockInstagramClient:
    """Расширенный мок Instagram клиента с реалистичным поведением"""
    
    def __init__(self):
        self.logged_in = False
        self.session_data = {}
        self.users = {
            "test_user": "123456789",
            "recipient_user": "987654321",
            "blocked_user": "555555555"
        }
        self.threads = []
        self.sent_messages = []
    
    def login(self, username: str, password: str):
        """Мок логина с различными сценариями"""
        if username == "invalid_user":
            raise Exception("User does not exist")
        elif username == "banned_user":
            raise Exception("Account is banned")
        elif password == "wrong_password":
            raise Exception("Incorrect password")
        elif username == "rate_limited":
            raise Exception("Rate limit exceeded")
        else:
            self.logged_in = True
            self.session_data = {
                "username": username,
                "user_id": self.users.get(username, "123456789")
            }
            return True
    
    def dump_settings(self, path: str):
        """Мок сохранения настроек"""
        if not self.logged_in:
            raise Exception("Not logged in")
        
        with open(path, 'w') as f:
            json.dump(self.session_data, f)
    
    def load_settings(self, path: str):
        """Мок загрузки настроек"""
        if not os.path.exists(path):
            raise Exception("Session file not found")
        
        try:
            with open(path, 'r') as f:
                self.session_data = json.load(f)
                self.logged_in = True
        except json.JSONDecodeError:
            raise Exception("Corrupted session file")
    
    def user_id_from_username(self, username: str) -> str:
        """Мок получения ID пользователя"""
        if not self.logged_in:
            raise Exception("Not logged in")
        
        if username == "nonexistent_user":
            raise Exception("User not found")
        elif username == "private_user":
            raise Exception("User is private")
        
        return self.users.get(username, "123456789")
    
    def direct_send(self, text: str, user_ids: list):
        """Мок отправки сообщения"""
        if not self.logged_in:
            raise Exception("Not logged in")
        
        if "blocked_user" in str(user_ids):
            raise Exception("Cannot send message to blocked user")
        elif len(text) > 1000:
            raise Exception("Message too long")
        
        message = {
            "text": text,
            "user_ids": user_ids,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        self.sent_messages.append(message)
        return True
    
    def direct_threads(self, amount: int = 20):
        """Мок получения диалогов"""
        if not self.logged_in:
            raise Exception("Not logged in")
        
        # Возвращаем мок данные
        threads = []
        for i in range(min(amount, len(self.threads) or 3)):
            thread = Mock()
            thread.id = f"thread_{i}"
            thread.dict.return_value = {
                "id": f"thread_{i}",
                "users": [f"user_{i}"],
                "messages": []
            }
            
            # Создаем мок пользователей
            user = Mock()
            user.username = f"user_{i}"
            thread.users = [user]
            
            threads.append(thread)
        
        return threads


class TestDataGenerator:
    """Генератор тестовых данных"""
    
    @staticmethod
    def create_login_data(username: str = "test_user", password: str = "test_password") -> Dict[str, str]:
        """Создает данные для логина"""
        return {
            "username": username,
            "password": password
        }
    
    @staticmethod
    def create_message_data(username: str = "recipient", text: str = "Test message") -> Dict[str, str]:
        """Создает данные для сообщения"""
        return {
            "username": username,
            "text": text
        }
    
    @staticmethod
    def create_api_headers(api_key: str = "neuro123") -> Dict[str, str]:
        """Создает заголовки с API ключом"""
        return {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
    
    @staticmethod
    def create_invalid_data_variants() -> list:
        """Создает варианты невалидных данных для тестирования"""
        return [
            {},  # Пустые данные
            {"username": ""},  # Пустое поле
            {"username": None},  # None значение
            {"username": " " * 100},  # Очень длинное значение
            {"username": "test", "extra_field": "value"},  # Лишние поля
        ]


class SessionFileManager:
    """Менеджер для работы с файлами сессии в тестах"""
    
    def __init__(self):
        self.temp_files = []
    
    def create_temp_session_file(self, data: Optional[Dict[str, Any]] = None) -> str:
        """Создает временный файл сессии"""
        if data is None:
            data = {"test": "session", "user_id": "123456789"}
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(data, temp_file)
        temp_file.close()
        
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def create_corrupted_session_file(self) -> str:
        """Создает поврежденный файл сессии"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_file.write("invalid json{")
        temp_file.close()
        
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def cleanup(self):
        """Очищает все временные файлы"""
        for file_path in self.temp_files:
            try:
                os.unlink(file_path)
            except OSError:
                pass  # Файл уже удален
        self.temp_files.clear()


class AssertionHelpers:
    """Помощники для утверждений в тестах"""
    
    @staticmethod
    def assert_api_response_structure(response_data: dict, expected_keys: list):
        """Проверяет структуру ответа API"""
        assert isinstance(response_data, dict), "Response should be a dictionary"
        for key in expected_keys:
            assert key in response_data, f"Expected key '{key}' not found in response"
    
    @staticmethod
    def assert_error_response(response, expected_status: int, expected_message_part: str = None):
        """Проверяет структуру ошибочного ответа"""
        assert response.status_code == expected_status
        
        if expected_message_part:
            response_data = response.json()
            assert "detail" in response_data
            assert expected_message_part.lower() in response_data["detail"].lower()
    
    @staticmethod
    def assert_success_response(response, expected_data: dict = None):
        """Проверяет успешный ответ"""
        assert response.status_code == 200
        
        if expected_data:
            response_data = response.json()
            for key, value in expected_data.items():
                assert response_data.get(key) == value


class PerformanceProfiler:
    """Профайлер для измерения производительности в тестах"""
    
    def __init__(self):
        self.measurements = {}
    
    def measure_time(self, operation_name: str):
        """Контекстный менеджер для измерения времени"""
        import time
        
        class TimeContext:
            def __init__(self, profiler, name):
                self.profiler = profiler
                self.name = name
                self.start_time = None
            
            def __enter__(self):
                self.start_time = time.time()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                end_time = time.time()
                duration = end_time - self.start_time
                self.profiler.measurements[self.name] = duration
        
        return TimeContext(self, operation_name)
    
    def get_measurement(self, operation_name: str) -> float:
        """Получает измерение времени"""
        return self.measurements.get(operation_name, 0.0)
    
    def assert_performance_threshold(self, operation_name: str, max_seconds: float):
        """Проверяет что операция выполнилась быстрее порога"""
        actual_time = self.get_measurement(operation_name)
        assert actual_time <= max_seconds, \
            f"Operation '{operation_name}' took {actual_time:.3f}s, expected <= {max_seconds}s"


# Глобальные утилиты для использования в тестах
def create_mock_client_with_scenario(scenario: str) -> MockInstagramClient:
    """Создает мок клиента с предустановленным сценарием"""
    client = MockInstagramClient()
    
    if scenario == "logged_in":
        client.logged_in = True
        client.session_data = {"username": "test_user", "user_id": "123456789"}
    elif scenario == "rate_limited":
        # Настройка для rate limit тестов
        pass
    elif scenario == "network_error":
        # Настройка для тестов сетевых ошибок
        pass
    
    return client