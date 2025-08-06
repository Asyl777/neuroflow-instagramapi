# 🧪 Тестирование Instagram API

Комплексный набор тестов для Instagram API приложения.

## 📁 Структура тестов

```
tests/
├── conftest.py           # Общие фикстуры и настройки
├── test_auth.py          # Тесты аутентификации
├── test_api.py           # Тесты API эндпоинтов
├── test_errors.py        # Тесты обработки ошибок
├── test_integration.py   # Интеграционные тесты
├── test_utils.py         # Утилиты для тестирования
└── README.md            # Этот файл
```

## 🚀 Запуск тестов

### Установка зависимостей
```bash
pip install -r requirements.txt
```

### Запуск всех тестов
```bash
pytest
```

### Запуск конкретной категории тестов
```bash
# Тесты аутентификации
pytest tests/test_auth.py

# Тесты API
pytest tests/test_api.py

# Интеграционные тесты
pytest tests/test_integration.py -v
```

### Запуск с покрытием кода
```bash
pytest --cov=app --cov-report=html
```

### Запуск с маркерами
```bash
# Только быстрые тесты
pytest -m "not slow"

# Только тесты безопасности
pytest -m security

# Тесты производительности
pytest -m performance
```

## 📊 Категории тестов

### 🔐 Тесты аутентификации (`test_auth.py`)
- Валидация API ключей
- Защита эндпоинтов
- Безопасность заголовков
- Rate limiting (если реализован)

**Примеры:**
```python
def test_valid_api_key_success()      # ✅ Валидный ключ
def test_invalid_api_key_fails()      # ❌ Невалидный ключ
def test_missing_api_key_fails()      # ❌ Отсутствует ключ
```

### 🌐 Тесты API (`test_api.py`)
- Эндпоинт `/login`
- Эндпоинт `/send_message`
- Эндпоинт `/inbox`
- Эндпоинт `/dialogs`
- Валидация данных

**Примеры:**
```python
def test_login_success()              # ✅ Успешный логин
def test_send_message_success()       # ✅ Отправка сообщения
def test_get_inbox_success()          # ✅ Получение inbox
```

### ⚠️ Тесты ошибок (`test_errors.py`)
- Обработка исключений
- Граничные случаи
- Безопасность
- Конкурентность

**Примеры:**
```python
def test_404_for_unknown_endpoint()   # 404 ошибки
def test_malformed_json()             # Некорректный JSON
def test_sql_injection_attempt()      # Защита от инъекций
```

### 🔄 Интеграционные тесты (`test_integration.py`)
- Полные рабочие циклы
- Персистентность сессий
- CORS и безопасность
- Производительность

**Примеры:**
```python
def test_complete_login_and_message_flow()  # Полный цикл
def test_session_persistence_after_login()  # Сохранение сессии
def test_concurrent_requests_handling()     # Конкурентность
```

## 🛠️ Моки и фикстуры

### Основные фикстуры (conftest.py)
- `client` - Тестовый клиент FastAPI
- `auth_headers` - Заголовки с валидным API ключом
- `mock_instagram_client` - Мок Instagram клиента
- `temp_session_file` - Временный файл сессии

### Утилиты тестирования (test_utils.py)
- `MockInstagramClient` - Расширенный мок с различными сценариями
- `TestDataGenerator` - Генератор тестовых данных
- `SessionFileManager` - Управление файлами сессий
- `AssertionHelpers` - Помощники для проверок

## 📈 Покрытие кода

Цель: **80%+ покрытие кода**

```bash
# Генерация отчета покрытия
pytest --cov=app --cov-report=html

# Просмотр отчета
open htmlcov/index.html
```

## 🎯 Маркеры тестов

```python
@pytest.mark.unit          # Юнит-тесты
@pytest.mark.integration   # Интеграционные тесты
@pytest.mark.api          # Тесты API
@pytest.mark.auth         # Тесты аутентификации
@pytest.mark.slow         # Медленные тесты
@pytest.mark.security     # Тесты безопасности
@pytest.mark.performance  # Тесты производительности
```

## 🚨 Важные сценарии

### Тестирование безопасности
```bash
# Все тесты безопасности
pytest -m security -v

# Проверка на инъекции
pytest tests/test_errors.py::TestSecurityErrors -v
```

### Тестирование производительности
```bash
# Тесты производительности
pytest -m performance -v

# Конкурентные запросы
pytest tests/test_integration.py::TestPerformanceAndLimits -v
```

### Тестирование ошибок
```bash
# Все тесты ошибок
pytest tests/test_errors.py -v

# Граничные случаи
pytest tests/test_errors.py::TestDataValidationErrors -v
```

## 🔧 Отладка тестов

### Подробный вывод
```bash
pytest -v -s tests/test_api.py::TestLoginEndpoint::test_login_success
```

### Остановка на первой ошибке
```bash
pytest -x
```

### Запуск упавших тестов
```bash
pytest --lf
```

### Профилирование
```bash
pytest --profile-svg
```

## 📝 Добавление новых тестов

### Шаблон теста
```python
def test_new_feature(client, auth_headers):
    """Описание теста"""
    # Arrange - подготовка
    data = {"key": "value"}
    
    # Act - действие
    response = client.post("/endpoint", json=data, headers=auth_headers)
    
    # Assert - проверка
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

### Использование моков
```python
@patch('main.get_client')
def test_with_mock(mock_get_client, client, auth_headers):
    # Настройка мока
    mock_client = Mock()
    mock_client.some_method.return_value = "expected_result"
    mock_get_client.return_value = mock_client
    
    # Тест
    response = client.get("/endpoint", headers=auth_headers)
    assert response.status_code == 200
```

## 📋 Чек-лист для новых тестов

- [ ] ✅ Успешный сценарий
- [ ] ❌ Сценарии ошибок
- [ ] 🔐 Проверка аутентификации
- [ ] 📝 Валидация входных данных
- [ ] 🧪 Использование моков для внешних зависимостей
- [ ] 📊 Проверка структуры ответа
- [ ] ⚡ Проверка производительности (при необходимости)
- [ ] 🛡️ Проверка безопасности (при необходимости)

## 🎉 Результаты тестов

После успешного запуска вы увидите:
```
======================== test session starts ========================
collected 45 items

tests/test_auth.py ........                              [ 17%]
tests/test_api.py ....................                   [ 62%]
tests/test_errors.py .............                       [ 91%]
tests/test_integration.py ....                           [100%]

======================== 45 passed in 2.34s ========================
```