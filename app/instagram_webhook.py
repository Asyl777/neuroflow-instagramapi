"""
Официальный Instagram Webhook handler
Поддержка Meta Business API webhooks
"""
import hashlib
import hmac
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Официальные типы событий Instagram API
class InstagramWebhookEvent(BaseModel):
    """Структура официального Instagram webhook события"""
    object: str  # "instagram" 
    entry: List[Dict[str, Any]]

class InstagramEntry(BaseModel):
    """Запись в webhook"""
    id: str  # Instagram Business Account ID
    time: int  # Unix timestamp
    messaging: Optional[List[Dict[str, Any]]] = None
    changes: Optional[List[Dict[str, Any]]] = None

class InstagramMessage(BaseModel):
    """Структура сообщения Instagram"""
    mid: str  # Message ID
    text: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    timestamp: int
    
class InstagramSender(BaseModel):
    """Отправитель сообщения"""
    id: str  # Instagram-scoped ID (IGSID)

class InstagramRecipient(BaseModel):
    """Получатель сообщения"""
    id: str  # Instagram Business Account ID


class InstagramWebhookProcessor:
    """Процессор официальных Instagram webhooks"""
    
    def __init__(self, app_secret: str = None):
        self.app_secret = app_secret
        self.supported_events = {
            "messages",
            "messaging_postbacks", 
            "messaging_optins",
            "messaging_referrals",
            "message_reads",
            "message_deliveries",
            "messaging_handovers",
            "messaging_policy_enforcement"
        }
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Проверка подписи webhook от Facebook/Instagram
        """
        if not self.app_secret:
            logger.warning("⚠️ App secret не настроен, пропускаем проверку подписи")
            return True
            
        expected_signature = hmac.new(
            self.app_secret.encode('utf-8'),
            payload,
            hashlib.sha1
        ).hexdigest()
        
        # Убираем префикс "sha1=" если есть
        if signature.startswith('sha1='):
            signature = signature[5:]
            
        return hmac.compare_digest(expected_signature, signature)
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Обработка официального Instagram webhook
        
        Официальный формат:
        {
          "object": "instagram",
          "entry": [
            {
              "id": "instagram-business-account-id",
              "time": 1234567890,
              "messaging": [
                {
                  "sender": {"id": "instagram-scoped-id"},
                  "recipient": {"id": "instagram-business-account-id"},
                  "timestamp": 1234567890,
                  "message": {
                    "mid": "message-id",
                    "text": "Hello World",
                    "attachments": [...]
                  }
                }
              ]
            }
          ]
        }
        """
        
        messages_to_process = []
        
        try:
            # Проверяем что это Instagram webhook
            if webhook_data.get("object") != "instagram":
                logger.warning(f"Неподдерживаемый тип объекта: {webhook_data.get('object')}")
                return []
            
            entries = webhook_data.get("entry", [])
            logger.info(f"📨 Получено {len(entries)} записей в webhook")
            
            for entry in entries:
                instagram_account_id = entry.get("id")
                entry_time = entry.get("time")
                
                # Обрабатываем сообщения
                messaging_events = entry.get("messaging", [])
                
                for messaging_event in messaging_events:
                    processed_message = await self._process_messaging_event(
                        messaging_event, 
                        instagram_account_id,
                        entry_time
                    )
                    
                    if processed_message:
                        messages_to_process.append(processed_message)
                
                # Обрабатываем изменения (например, подписки/отписки)
                changes = entry.get("changes", [])
                for change in changes:
                    await self._process_change_event(change, instagram_account_id)
            
            return messages_to_process
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки webhook: {e}")
            raise HTTPException(status_code=500, detail=f"Webhook processing error: {str(e)}")
    
    async def _process_messaging_event(
        self, 
        messaging_event: Dict[str, Any], 
        instagram_account_id: str,
        entry_time: int
    ) -> Optional[Dict[str, Any]]:
        """Обработка события сообщения"""
        
        try:
            sender = messaging_event.get("sender", {})
            recipient = messaging_event.get("recipient", {}) 
            timestamp = messaging_event.get("timestamp", entry_time)
            
            sender_id = sender.get("id")
            if not sender_id:
                logger.warning("Отсутствует ID отправителя")
                return None
            
            # Обрабатываем обычное сообщение
            if "message" in messaging_event:
                message_data = messaging_event["message"]
                
                return {
                    "type": "message",
                    "sender_id": sender_id,
                    "recipient_id": recipient.get("id", instagram_account_id),
                    "message_id": message_data.get("mid"),
                    "text": message_data.get("text", ""),
                    "attachments": message_data.get("attachments", []),
                    "timestamp": timestamp,
                    "instagram_account_id": instagram_account_id,
                    "raw_event": messaging_event
                }
            
            # Обрабатываем postback (нажатие кнопки)
            elif "postback" in messaging_event:
                postback_data = messaging_event["postback"]
                
                return {
                    "type": "postback",
                    "sender_id": sender_id,
                    "recipient_id": recipient.get("id", instagram_account_id), 
                    "payload": postback_data.get("payload"),
                    "title": postback_data.get("title"),
                    "timestamp": timestamp,
                    "instagram_account_id": instagram_account_id,
                    "raw_event": messaging_event
                }
            
            # Обрабатываем подтверждения доставки
            elif "delivery" in messaging_event:
                delivery_data = messaging_event["delivery"]
                
                logger.info(f"📬 Доставка сообщений подтверждена: {delivery_data.get('mids', [])}")
                return {
                    "type": "delivery",
                    "sender_id": sender_id,
                    "message_ids": delivery_data.get("mids", []),
                    "timestamp": timestamp
                }
            
            # Обрабатываем подтверждения прочтения
            elif "read" in messaging_event:
                read_data = messaging_event["read"]
                
                logger.info(f"👀 Сообщения прочитаны до: {read_data.get('watermark')}")
                return {
                    "type": "read",
                    "sender_id": sender_id,
                    "watermark": read_data.get("watermark"),
                    "timestamp": timestamp
                }
            
            else:
                logger.info(f"🤷 Неизвестный тип события: {messaging_event.keys()}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки messaging события: {e}")
            return None
    
    async def _process_change_event(self, change: Dict[str, Any], instagram_account_id: str):
        """Обработка события изменения (подписки, комментарии и т.д.)"""
        
        field = change.get("field")
        value = change.get("value", {})
        
        logger.info(f"🔄 Изменение в поле '{field}': {value}")
        
        # Обработка комментариев  
        if field == "comments":
            comment_id = value.get("id")
            text = value.get("text")
            from_user = value.get("from", {})
            
            logger.info(f"💬 Новый комментарий от {from_user.get('username', 'unknown')}: {text}")
        
        # Обработка упоминаний
        elif field == "mentions":
            media_id = value.get("media_id") 
            comment_id = value.get("comment_id")
            
            logger.info(f"📢 Упоминание в медиа {media_id}")
        
        # Другие типы изменений
        else:
            logger.info(f"ℹ️ Обработка события '{field}' не реализована")
    
    def get_verification_response(self, verify_token: str, challenge: str, mode: str) -> str:
        """
        Верификация webhook для Facebook/Instagram
        
        Facebook отправляет GET запрос для верификации:
        GET /webhooks/instagram?hub.mode=subscribe&hub.challenge=123&hub.verify_token=your_token
        """
        
        if mode == "subscribe" and verify_token == self.get_verify_token():
            logger.info("✅ Webhook верификация успешна")
            return challenge
        else:
            logger.error("❌ Неверный verify_token при верификации webhook")
            raise HTTPException(status_code=403, detail="Verification failed")
    
    def get_verify_token(self) -> str:
        """Получение verify токена из конфигурации"""
        # TODO: Вынести в settings
        return "instagram_webhook_verify_token_2024"
    
    async def extract_user_info(self, sender_id: str) -> Dict[str, Any]:
        """
        Получение информации о пользователе через Instagram Basic Display API
        
        Примечание: Требует дополнительных разрешений и токенов
        """
        
        # Пока возвращаем базовую информацию
        return {
            "instagram_user_id": sender_id,
            "username": f"user_{sender_id}",  # Временное решение
            "full_name": None,
            "profile_pic_url": None
        }


# Глобальный экземпляр процессора
instagram_webhook_processor = InstagramWebhookProcessor(
    app_secret=None  # TODO: Добавить в settings
)