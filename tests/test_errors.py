"""
Тесты обработки ошибок и граничных случаев
"""
import pytest
import json
import os
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient


class TestErrorHandling:
    """Тесты общей обработки ошибок"""
    
    def test_404_for_unknown_endpoint(self, client):
        """Тест 404 для несуществующих эндпоинтов"""
        response = client.get("/nonexistent")
        assert response.status_code == 404
    
    def test_405_for_wrong_method(self, client, auth_headers):
        """Тест 405 для неправильного HTTP метода"""
        # GET на POST эндпоинт
        response = client.get("/login", headers=auth_headers)
        assert response.status_code == 405
        
        # POST на GET эндпоинт
        response = client.post("/dialogs", headers=auth_headers)
        assert response.status_code == 405
    
    def test_malformed_json(self, client, auth_headers):
        """Тест обработки некорректного JSON"""
        response = client.post(
            "/login", 
            data="invalid json{", 
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_content_type_validation(self, client, auth_headers):
        """Тест валидации Content-Type"""
        # Отправляем данные без правильного Content-Type
        response = client.post(
            "/login",
            data="username=test&password=test",
            headers=auth_headers
        )
        # FastAPI должен обработать это корректно
        assert response.status_code in [422, 400]


class TestInstagramAPIErrors:
    """Тесты ошибок Instagram API"""
    
    @patch('main.cl')
    def test_instagram_rate_limit_error(self, mock_client, client, auth_headers, sample_login_data):
        """Тест обработки rate limit от Instagram"""
        mock_client.login.side_effect = Exception("Rate limit exceeded")
        
        response = client.post("/login", json=sample_login_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "Rate limit exceeded" in response.json()["detail"]
    
    @patch('main.cl')
    def test_instagram_network_error(self, mock_client, client, auth_headers, sample_login_data):
        """Тест обработки сетевых ошибок"""
        mock_client.login.side_effect = Exception("Connection timeout")
        
        response = client.post("/login", json=sample_login_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "Connection timeout" in response.json()["detail"]
    
    @patch('main.get_client')
    def test_instagram_banned_account_error(self, mock_get_client, client, auth_headers, sample_message_data):
        """Тест обработки заблокированного аккаунта"""
        mock_client = Mock()
        mock_client.user_id_from_username.side_effect = Exception("Account is banned")
        mock_get_client.return_value = mock_client
        
        response = client.post("/send_message", json=sample_message_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "Account is banned" in response.json()["detail"]


class TestSessionErrors:
    """Тесты ошибок сессии"""
    
    @patch('main.os.path.exists')
    def test_session_file_not_found(self, mock_exists, client, auth_headers):
        """Тест отсутствующего файла сессии"""
        mock_exists.return_value = False
        
        response = client.get("/dialogs", headers=auth_headers)
        
        assert response.status_code == 401
        assert "Not logged in" in response.json()["detail"]
    
    @patch('main.os.path.exists')
    @patch('main.cl')
    def test_corrupted_session_file(self, mock_cl, mock_exists, client, auth_headers):
        """Тест поврежденного файла сессии"""
        mock_exists.return_value = True
        mock_cl.load_settings.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        response = client.get("/dialogs", headers=auth_headers)
        
        assert response.status_code == 401
        assert "Invalid session" in response.json()["detail"]
    
    @patch('main.os.path.exists')
    @patch('main.cl')
    def test_permission_denied_session_file(self, mock_cl, mock_exists, client, auth_headers):
        """Тест отсутствия прав доступа к файлу сессии"""
        mock_exists.return_value = True
        mock_cl.load_settings.side_effect = PermissionError("Permission denied")
        
        response = client.get("/dialogs", headers=auth_headers)
        
        assert response.status_code == 401
        assert "Invalid session" in response.json()["detail"]


class TestDataValidationErrors:
    """Тесты ошибок валидации данных"""
    
    @pytest.mark.parametrize("invalid_data", [
        {},  # Пустые данные
        {"username": ""},  # Пустой username
        {"password": "test"},  # Отсутствует username
        {"username": "test"},  # Отсутствует password
        {"username": None, "password": "test"},  # None в username
        {"username": "test", "password": None},  # None в password
    ])
    def test_login_data_validation(self, client, auth_headers, invalid_data):
        """Тест валидации данных логина"""
        response = client.post("/login", json=invalid_data, headers=auth_headers)
        assert response.status_code == 422
    
    @pytest.mark.parametrize("invalid_message", [
        {},  # Пустые данные
        {"username": ""},  # Пустой username
        {"text": "test"},  # Отсутствует username
        {"username": "test"},  # Отсутствует text
        {"username": None, "text": "test"},  # None в username
        {"username": "test", "text": None},  # None в text
    ])
    def test_message_data_validation(self, client, auth_headers, invalid_message):
        """Тест валидации данных сообщения"""
        response = client.post("/send_message", json=invalid_message, headers=auth_headers)
        assert response.status_code == 422
    
    def test_extremely_long_username(self, client, auth_headers):
        """Тест очень длинного username"""
        long_data = {
            "username": "a" * 1000,  # Очень длинный username
            "password": "test"
        }
        response = client.post("/login", json=long_data, headers=auth_headers)
        # Не должно вызывать server error
        assert response.status_code != 500
    
    def test_sql_injection_attempt(self, client, auth_headers):
        """Тест попытки SQL инъекции"""
        malicious_data = {
            "username": "'; DROP TABLE users; --",
            "password": "test"
        }
        response = client.post("/login", json=malicious_data, headers=auth_headers)
        # Не должно вызывать server error
        assert response.status_code != 500


class TestConcurrencyErrors:
    """Тесты ошибок конкурентности"""
    
    @patch('main.cl')
    def test_concurrent_login_attempts(self, mock_client, client, auth_headers, sample_login_data):
        """Тест одновременных попыток логина"""
        import threading
        import time
        
        results = []
        
        def login_attempt():
            try:
                response = client.post("/login", json=sample_login_data, headers=auth_headers)
                results.append(response.status_code)
            except Exception as e:
                results.append(str(e))
        
        # Запускаем несколько потоков одновременно
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=login_attempt)
            threads.append(thread)
            thread.start()
        
        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()
        
        # Проверяем что не было критических ошибок
        assert len(results) == 5
        for result in results:
            if isinstance(result, int):
                assert result != 500  # Не должно быть server errors


class TestMemoryAndResourceErrors:
    """Тесты ошибок ресурсов и памяти"""
    
    def test_large_payload(self, client, auth_headers):
        """Тест обработки очень большого payload"""
        large_data = {
            "username": "test",
            "password": "x" * (1024 * 1024)  # 1MB пароль
        }
        
        response = client.post("/login", json=large_data, headers=auth_headers)
        # Не должно вызывать server error
        assert response.status_code != 500
    
    @patch('main.get_client')
    def test_memory_leak_simulation(self, mock_get_client, client, auth_headers):
        """Тест на потенциальные утечки памяти"""
        mock_client = Mock()
        mock_client.direct_threads.return_value = []
        mock_get_client.return_value = mock_client
        
        # Делаем много запросов подряд
        for _ in range(100):
            response = client.get("/dialogs", headers=auth_headers)
            assert response.status_code == 200
        
        # Если дошли до сюда без ошибок - хорошо


class TestSecurityErrors:
    """Тесты безопасности и потенциальных уязвимостей"""
    
    def test_path_traversal_attempt(self, client):
        """Тест попытки path traversal"""
        malicious_paths = [
            "/../../../etc/passwd",
            "/..\\..\\..\\windows\\system32",
            "/%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        for path in malicious_paths:
            response = client.get(path)
            # Должен быть 404, не server error
            assert response.status_code == 404
    
    def test_header_injection(self, client, valid_api_key):
        """Тест попытки инъекции в заголовки"""
        malicious_headers = {
            "x-api-key": f"{valid_api_key}\r\nX-Injected-Header: malicious",
            "X-Forwarded-For": "127.0.0.1, 127.0.0.1",
            "User-Agent": "Mozilla/5.0\r\nX-Injected: malicious"
        }
        
        response = client.get("/dialogs", headers=malicious_headers)
        # Не должно быть server error
        assert response.status_code != 500
    
    def test_dos_via_regex(self, client, auth_headers):
        """Тест защиты от DoS через regex"""
        # Потенциально опасный паттерн для regex
        evil_string = "a" * 10000 + "!"
        
        data = {
            "username": evil_string,
            "password": "test"
        }
        
        response = client.post("/login", json=data, headers=auth_headers)
        # Не должно висеть или вызывать server error
        assert response.status_code != 500