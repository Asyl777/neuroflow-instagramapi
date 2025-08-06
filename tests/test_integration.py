"""
Интеграционные тесты Instagram API
Тесты полного цикла работы приложения
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient


class TestFullWorkflow:
    """Тесты полного рабочего процесса"""
    
    @patch('main.cl')
    @patch('main.os.path.exists')
    def test_complete_login_and_message_flow(self, mock_exists, mock_client, client, auth_headers):
        """Тест полного цикла: логин → отправка сообщения"""
        # Настройка моков для логина
        mock_client.login.return_value = True
        mock_client.dump_settings.return_value = None
        
        # Шаг 1: Логин
        login_data = {"username": "test_user", "password": "test_password"}
        login_response = client.post("/login", json=login_data, headers=auth_headers)
        assert login_response.status_code == 200
        
        # Настройка моков для отправки сообщения
        mock_exists.return_value = True
        mock_client.load_settings.return_value = None
        mock_client.user_id_from_username.return_value = "123456789"
        mock_client.direct_send.return_value = True
        
        # Шаг 2: Отправка сообщения
        message_data = {"username": "recipient", "text": "Тестовое сообщение"}
        with patch('main.get_client', return_value=mock_client):
            message_response = client.post("/send_message", json=message_data, headers=auth_headers)
        
        assert message_response.status_code == 200
        assert message_response.json() == {"status": "ok"}
    
    @patch('main.cl')
    @patch('main.os.path.exists')
    def test_login_inbox_dialogs_flow(self, mock_exists, mock_client, client, auth_headers):
        """Тест цикла: логин → получение inbox → получение диалогов"""
        # Логин
        mock_client.login.return_value = True
        mock_client.dump_settings.return_value = None
        
        login_data = {"username": "test_user", "password": "test_password"}
        login_response = client.post("/login", json=login_data, headers=auth_headers)
        assert login_response.status_code == 200
        
        # Настройка для inbox и dialogs
        mock_exists.return_value = True
        mock_client.load_settings.return_value = None
        
        # Мок данных threads
        mock_thread = Mock()
        mock_thread.dict.return_value = {"id": "thread1", "users": ["user1"]}
        mock_thread.id = "thread1"
        mock_user = Mock()
        mock_user.username = "user1"
        mock_thread.users = [mock_user]
        
        mock_client.direct_threads.return_value = [mock_thread]
        
        with patch('main.get_client', return_value=mock_client):
            # Получение inbox
            inbox_response = client.get("/inbox", headers=auth_headers)
            assert inbox_response.status_code == 200
            
            # Получение dialogs
            dialogs_response = client.get("/dialogs", headers=auth_headers)
            assert dialogs_response.status_code == 200
    
    @patch('main.cl')
    def test_failed_login_blocks_other_operations(self, mock_client, client, auth_headers):
        """Тест что неудачный логин блокирует другие операции"""
        # Неудачный логин
        mock_client.login.side_effect = Exception("Login failed")
        
        login_data = {"username": "invalid", "password": "invalid"}
        login_response = client.post("/login", json=login_data, headers=auth_headers)
        assert login_response.status_code == 400
        
        # Попытка отправить сообщение без успешного логина
        message_data = {"username": "test", "text": "test"}
        message_response = client.post("/send_message", json=message_data, headers=auth_headers)
        assert message_response.status_code == 401  # Не авторизован


class TestSessionPersistence:
    """Тесты персистентности сессии"""
    
    @patch('main.cl')
    def test_session_persistence_after_login(self, mock_client, client, auth_headers, temp_session_file):
        """Тест сохранения сессии после логина"""
        mock_client.login.return_value = True
        
        # Настраиваем мок для сохранения в конкретный файл
        def mock_dump_settings(path):
            with open(temp_session_file, 'w') as f:
                f.write('{"session": "data"}')
        
        mock_client.dump_settings.side_effect = mock_dump_settings
        
        login_data = {"username": "test", "password": "test"}
        response = client.post("/login", json=login_data, headers=auth_headers)
        
        assert response.status_code == 200
        assert os.path.exists(temp_session_file)
    
    @patch('main.cl')
    @patch('main.SESSION_FILE')
    def test_session_loading_on_request(self, mock_session_file, mock_client, client, auth_headers, temp_session_file):
        """Тест загрузки сессии при запросе"""
        mock_session_file.__str__ = lambda: temp_session_file
        
        # Создаем файл сессии
        with open(temp_session_file, 'w') as f:
            f.write('{"session": "data"}')
        
        mock_client.load_settings.return_value = None
        mock_client.direct_threads.return_value = []
        
        with patch('main.os.path.exists', return_value=True), \
             patch('main.get_client', return_value=mock_client):
            response = client.get("/dialogs", headers=auth_headers)
        
        assert response.status_code == 200
        mock_client.load_settings.assert_called()


class TestCORSAndSecurity:
    """Интеграционные тесты CORS и безопасности"""
    
    def test_cors_headers_present(self, client, auth_headers):
        """Тест наличия CORS заголовков"""
        response = client.get("/dialogs", headers=auth_headers)
        
        # Проверяем наличие CORS заголовков
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"
    
    def test_options_request_handled(self, client):
        """Тест обработки OPTIONS запросов"""
        response = client.options("/dialogs")
        
        # OPTIONS должен обрабатываться корректно
        assert response.status_code in [200, 204]
    
    def test_multiple_origins_handling(self, client, auth_headers):
        """Тест обработки запросов с разными Origin"""
        origins = [
            "http://localhost:3000",
            "https://example.com",
            "https://malicious-site.com"
        ]
        
        for origin in origins:
            headers = {**auth_headers, "Origin": origin}
            response = client.get("/dialogs", headers=headers)
            
            # Все origin должны быть разрешены (текущая конфигурация)
            assert response.status_code != 403


class TestPerformanceAndLimits:
    """Тесты производительности и ограничений"""
    
    @patch('main.get_client')
    def test_concurrent_requests_handling(self, mock_get_client, client, auth_headers):
        """Тест обработки одновременных запросов"""
        import threading
        import time
        
        mock_client = Mock()
        mock_client.direct_threads.return_value = []
        mock_get_client.return_value = mock_client
        
        results = []
        
        def make_request():
            try:
                response = client.get("/dialogs", headers=auth_headers)
                results.append(response.status_code)
            except Exception as e:
                results.append(str(e))
        
        # Запускаем 10 одновременных запросов
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Все запросы должны быть обработаны успешно
        assert len(results) == 10
        successful_requests = [r for r in results if r == 200]
        assert len(successful_requests) >= 8  # Минимум 80% успешных
    
    def test_request_timeout_handling(self, client, auth_headers):
        """Тест обработки таймаутов запросов"""
        # Симуляция медленного запроса
        with patch('main.get_client') as mock_get_client:
            mock_client = Mock()
            
            def slow_operation(*args, **kwargs):
                import time
                time.sleep(0.1)  # Небольшая задержка
                return []
            
            mock_client.direct_threads.side_effect = slow_operation
            mock_get_client.return_value = mock_client
            
            response = client.get("/dialogs", headers=auth_headers)
            
            # Запрос должен завершиться, несмотря на задержку
            assert response.status_code == 200


class TestDataFlow:
    """Тесты потока данных"""
    
    @patch('main.get_client')
    def test_data_consistency_across_endpoints(self, mock_get_client, client, auth_headers):
        """Тест консистентности данных между эндпоинтами"""
        # Настраиваем одинаковые данные для inbox и dialogs
        mock_client = Mock()
        
        mock_thread = Mock()
        mock_thread.dict.return_value = {
            "id": "thread123",
            "users": ["user1", "user2"]
        }
        mock_thread.id = "thread123"
        
        mock_user = Mock()
        mock_user.username = "user1"
        mock_thread.users = [mock_user]
        
        mock_client.direct_threads.return_value = [mock_thread]
        mock_get_client.return_value = mock_client
        
        # Получаем данные из inbox
        inbox_response = client.get("/inbox", headers=auth_headers)
        inbox_data = inbox_response.json()
        
        # Получаем данные из dialogs
        dialogs_response = client.get("/dialogs", headers=auth_headers)
        dialogs_data = dialogs_response.json()
        
        # Проверяем что оба эндпоинта возвращают связанные данные
        assert inbox_response.status_code == 200
        assert dialogs_response.status_code == 200
        
        if dialogs_data:
            assert "id" in dialogs_data[0]
            assert dialogs_data[0]["id"] == "thread123"


class TestApplicationLifecycle:
    """Тесты жизненного цикла приложения"""
    
    def test_application_startup(self, client):
        """Тест запуска приложения"""
        # Проверяем что приложение отвечает на базовые запросы
        response = client.get("/docs")  # OpenAPI документация
        # Может быть 404 если не настроена, но не 500
        assert response.status_code != 500
    
    def test_health_check_simulation(self, client, auth_headers):
        """Симуляция health check"""
        # Используем простой эндпоинт как health check
        response = client.get("/dialogs", headers=auth_headers)
        
        # Приложение должно отвечать (даже с ошибкой, но не падать)
        assert response.status_code != 500
    
    @patch('main.cl')
    def test_graceful_error_recovery(self, mock_client, client, auth_headers):
        """Тест восстановления после ошибок"""
        # Первый запрос падает
        mock_client.login.side_effect = Exception("Temporary error")
        
        login_data = {"username": "test", "password": "test"}
        response1 = client.post("/login", json=login_data, headers=auth_headers)
        assert response1.status_code == 400
        
        # Второй запрос должен работать
        mock_client.login.side_effect = None
        mock_client.login.return_value = True
        mock_client.dump_settings.return_value = None
        
        response2 = client.post("/login", json=login_data, headers=auth_headers)
        assert response2.status_code == 200