"""
Тесты API эндпоинтов Instagram API
"""
import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


class TestLoginEndpoint:
    """Тесты эндпоинта /login"""
    
    @patch('main.cl')
    def test_login_success(self, mock_client, client, auth_headers, sample_login_data):
        """Тест успешного логина"""
        # Настраиваем мок
        mock_client.login.return_value = True
        mock_client.dump_settings.return_value = None
        
        response = client.post("/login", json=sample_login_data, headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_client.login.assert_called_once_with(
            sample_login_data["username"], 
            sample_login_data["password"]
        )
        mock_client.dump_settings.assert_called_once()
    
    @patch('main.cl')
    def test_login_failure(self, mock_client, client, auth_headers, sample_login_data):
        """Тест неуспешного логина"""
        # Настраиваем мок для эмуляции ошибки
        mock_client.login.side_effect = Exception("Invalid credentials")
        
        response = client.post("/login", json=sample_login_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "Invalid credentials" in response.json()["detail"]
    
    def test_login_invalid_data(self, client, auth_headers):
        """Тест логина с невалидными данными"""
        invalid_data = {"username": "", "password": ""}
        response = client.post("/login", json=invalid_data, headers=auth_headers)
        
        # Должна быть ошибка валидации или 400
        assert response.status_code in [400, 422]
    
    def test_login_missing_fields(self, client, auth_headers):
        """Тест логина с отсутствующими полями"""
        incomplete_data = {"username": "test"}  # Отсутствует password
        response = client.post("/login", json=incomplete_data, headers=auth_headers)
        
        assert response.status_code == 422  # Ошибка валидации Pydantic
    
    @patch('main.cl')
    def test_login_dump_settings_error(self, mock_client, client, auth_headers, sample_login_data):
        """Тест ошибки сохранения настроек"""
        mock_client.login.return_value = True
        mock_client.dump_settings.side_effect = Exception("Cannot save settings")
        
        response = client.post("/login", json=sample_login_data, headers=auth_headers)
        
        assert response.status_code == 400


class TestSendMessageEndpoint:
    """Тесты эндпоинта /send_message"""
    
    @patch('main.get_client')
    def test_send_message_success(self, mock_get_client, client, auth_headers, sample_message_data):
        """Тест успешной отправки сообщения"""
        # Настраиваем мок клиента
        mock_client = Mock()
        mock_client.user_id_from_username.return_value = "123456789"
        mock_client.direct_send.return_value = True
        mock_get_client.return_value = mock_client
        
        response = client.post("/send_message", json=sample_message_data, headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_client.user_id_from_username.assert_called_once_with(sample_message_data["username"])
        mock_client.direct_send.assert_called_once_with(
            sample_message_data["text"], 
            user_ids=["123456789"]
        )
    
    @patch('main.get_client')
    def test_send_message_user_not_found(self, mock_get_client, client, auth_headers, sample_message_data):
        """Тест отправки сообщения несуществующему пользователю"""
        mock_client = Mock()
        mock_client.user_id_from_username.side_effect = Exception("User not found")
        mock_get_client.return_value = mock_client
        
        response = client.post("/send_message", json=sample_message_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "User not found" in response.json()["detail"]
    
    @patch('main.get_client')
    def test_send_message_api_error(self, mock_get_client, client, auth_headers, sample_message_data):
        """Тест ошибки Instagram API при отправке"""
        mock_client = Mock()
        mock_client.user_id_from_username.return_value = "123456789"
        mock_client.direct_send.side_effect = Exception("Instagram API error")
        mock_get_client.return_value = mock_client
        
        response = client.post("/send_message", json=sample_message_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "Instagram API error" in response.json()["detail"]
    
    def test_send_message_empty_text(self, client, auth_headers):
        """Тест отправки пустого сообщения"""
        empty_message = {"username": "test_user", "text": ""}
        response = client.post("/send_message", json=empty_message, headers=auth_headers)
        
        # Может быть успешным (зависит от Instagram API) или ошибкой валидации
        assert response.status_code in [200, 400, 422]
    
    def test_send_message_invalid_username(self, client, auth_headers):
        """Тест отправки сообщения с невалидным username"""
        invalid_data = {"username": "", "text": "Test message"}
        response = client.post("/send_message", json=invalid_data, headers=auth_headers)
        
        assert response.status_code in [400, 422]


class TestInboxEndpoint:
    """Тесты эндпоинта /inbox"""
    
    @patch('main.get_client')
    def test_get_inbox_success(self, mock_get_client, client, auth_headers, mock_direct_threads):
        """Тест успешного получения входящих"""
        mock_client = Mock()
        mock_client.direct_threads.return_value = mock_direct_threads
        mock_get_client.return_value = mock_client
        
        response = client.get("/inbox", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        mock_client.direct_threads.assert_called_once_with(amount=20)
    
    @patch('main.get_client')
    def test_get_inbox_empty(self, mock_get_client, client, auth_headers):
        """Тест получения пустого inbox"""
        mock_client = Mock()
        mock_client.direct_threads.return_value = []
        mock_get_client.return_value = mock_client
        
        response = client.get("/inbox", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json() == []
    
    @patch('main.get_client')
    def test_get_inbox_api_error(self, mock_get_client, client, auth_headers):
        """Тест ошибки API при получении inbox"""
        mock_client = Mock()
        mock_client.direct_threads.side_effect = Exception("Instagram API error")
        mock_get_client.return_value = mock_client
        
        response = client.get("/inbox", headers=auth_headers)
        
        assert response.status_code == 400
        assert "Instagram API error" in response.json()["detail"]


class TestDialogsEndpoint:
    """Тесты эндпоинта /dialogs"""
    
    @patch('main.get_client')
    def test_get_dialogs_success(self, mock_get_client, client, auth_headers, mock_direct_threads):
        """Тест успешного получения диалогов"""
        mock_client = Mock()
        mock_client.direct_threads.return_value = mock_direct_threads
        mock_get_client.return_value = mock_client
        
        response = client.get("/dialogs", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:  # Если есть данные
            assert "id" in data[0]
            assert "users" in data[0]
        mock_client.direct_threads.assert_called_once()
    
    @patch('main.get_client')
    def test_get_dialogs_empty(self, mock_get_client, client, auth_headers):
        """Тест получения пустого списка диалогов"""
        mock_client = Mock()
        mock_client.direct_threads.return_value = []
        mock_get_client.return_value = mock_client
        
        response = client.get("/dialogs", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json() == []
    
    @patch('main.get_client')
    def test_get_dialogs_api_error(self, mock_get_client, client, auth_headers):
        """Тест ошибки API при получении диалогов"""
        mock_client = Mock()
        mock_client.direct_threads.side_effect = Exception("Instagram API error")
        mock_get_client.return_value = mock_client
        
        response = client.get("/dialogs", headers=auth_headers)
        
        assert response.status_code == 400
        assert "Instagram API error" in response.json()["detail"]


class TestSessionManagement:
    """Тесты управления сессией"""
    
    @patch('main.os.path.exists')
    @patch('main.cl')
    def test_get_client_with_existing_session(self, mock_cl, mock_exists, client, auth_headers):
        """Тест получения клиента с существующей сессией"""
        mock_exists.return_value = True
        mock_cl.load_settings.return_value = None
        
        # Используем любой эндпоинт который вызывает get_client()
        response = client.get("/dialogs", headers=auth_headers)
        
        # Не должно быть ошибки 401 (сессия должна загрузиться)
        assert response.status_code != 401
        mock_cl.load_settings.assert_called()
    
    @patch('main.os.path.exists')
    def test_get_client_without_session(self, mock_exists, client, auth_headers):
        """Тест получения клиента без существующей сессии"""
        mock_exists.return_value = False
        
        response = client.get("/dialogs", headers=auth_headers)
        
        assert response.status_code == 401
        assert "Not logged in" in response.json()["detail"]
    
    @patch('main.os.path.exists')
    @patch('main.cl')
    def test_invalid_session_file(self, mock_cl, mock_exists, client, auth_headers):
        """Тест обработки поврежденного файла сессии"""
        mock_exists.return_value = True
        mock_cl.load_settings.side_effect = Exception("Corrupted session")
        
        response = client.get("/dialogs", headers=auth_headers)
        
        assert response.status_code == 401
        assert "Invalid session, please login again" in response.json()["detail"]


class TestDataValidation:
    """Тесты валидации данных"""
    
    def test_login_with_special_characters(self, client, auth_headers):
        """Тест логина со специальными символами"""
        special_data = {
            "username": "test@user.com",
            "password": "пароль123!@#"
        }
        
        # Не должно быть ошибки валидации на уровне API
        response = client.post("/login", json=special_data, headers=auth_headers)
        assert response.status_code != 422
    
    def test_message_with_unicode(self, client, auth_headers):
        """Тест отправки сообщения с Unicode символами"""
        unicode_message = {
            "username": "test_user",
            "text": "Привет! 🎉 How are you? 中文"
        }
        
        response = client.post("/send_message", json=unicode_message, headers=auth_headers)
        # Не должно быть ошибки валидации
        assert response.status_code != 422
    
    def test_long_message_text(self, client, auth_headers):
        """Тест отправки очень длинного сообщения"""
        long_message = {
            "username": "test_user",
            "text": "a" * 10000  # Очень длинное сообщение
        }
        
        response = client.post("/send_message", json=long_message, headers=auth_headers)
        # Может быть ограничение Instagram API, но не ошибка валидации
        assert response.status_code != 422