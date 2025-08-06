"""
ИИ сервис для обработки сообщений и генерации ответов
Интеграция с OpenAI GPT и другими LLM
"""
import openai
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import re
from app.config import settings
from app.models import InstagramMessage, InstagramConversation, InstagramUser

logger = logging.getLogger(__name__)

class AIService:
    """Сервис для работы с ИИ"""
    
    def __init__(self):
        if settings.openai_api_key:
            openai.api_key = settings.openai_api_key
            self.openai_available = True
            logger.info("✅ OpenAI API инициализирован")
        else:
            self.openai_available = False
            logger.warning("⚠️ OpenAI API ключ не настроен")
    
    async def generate_response(
        self,
        user_message: str,
        conversation_context: List[Dict[str, str]],
        user_profile: Optional[Dict] = None,
        ai_personality: str = "helpful"
    ) -> Dict[str, any]:
        """
        Генерация ответа с учетом контекста диалога
        
        Args:
            user_message: Сообщение пользователя
            conversation_context: История диалога
            user_profile: Профиль пользователя  
            ai_personality: Личность ИИ
            
        Returns:
            Dict с ответом, метриками и метаданными
        """
        if not self.openai_available:
            return {
                "response": "Извините, ИИ сервис временно недоступен.",
                "confidence": 0.0,
                "tokens_used": 0,
                "model": "fallback"
            }
        
        try:
            start_time = datetime.now()
            
            # Подготовка промпта с контекстом
            system_prompt = self._build_system_prompt(ai_personality, user_profile)
            messages = self._build_conversation_messages(system_prompt, conversation_context, user_message)
            
            # Запрос к OpenAI
            response = await self._call_openai(messages)
            
            end_time = datetime.now()
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                "response": response["content"],
                "confidence": self._calculate_confidence(response),
                "tokens_used": response.get("usage", {}).get("total_tokens", 0),
                "prompt_tokens": response.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": response.get("usage", {}).get("completion_tokens", 0),
                "model": settings.openai_model,
                "response_time_ms": response_time_ms,
                "metadata": {
                    "system_prompt_length": len(system_prompt),
                    "context_messages": len(conversation_context),
                    "ai_personality": ai_personality
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации ответа ИИ: {e}")
            return {
                "response": "Извините, произошла ошибка при генерации ответа.",
                "confidence": 0.0,
                "tokens_used": 0,
                "model": "error",
                "error": str(e)
            }
    
    def _build_system_prompt(self, ai_personality: str, user_profile: Optional[Dict] = None) -> str:
        """Построение системного промпта"""
        
        personality_prompts = {
            "helpful": "Ты дружелюбный и полезный ИИ-помощник. Отвечай вежливо и информативно.",
            "sales": "Ты опытный продавец. Твоя цель - помочь клиенту и направить его к покупке.",
            "support": "Ты специалист техподдержки. Решай проблемы клиентов быстро и эффективно.",
            "casual": "Ты общаешься в неформальном, дружеском стиле. Используй эмодзи и будь позитивным."
        }
        
        base_prompt = personality_prompts.get(ai_personality, personality_prompts["helpful"])
        
        additional_context = []
        
        if user_profile:
            if user_profile.get("language"):
                additional_context.append(f"Отвечай на языке: {user_profile['language']}")
            if user_profile.get("timezone"):
                additional_context.append(f"Часовой пояс пользователя: {user_profile['timezone']}")
        
        additional_context.extend([
            "Отвечай кратко и по существу.",
            "Если не знаешь ответ, так и скажи.",
            "Не придумывай факты.",
            "Будь вежливым и профессиональным.",
            "Используй эмодзи умеренно."
        ])
        
        return f"{base_prompt}\n\nДополнительные инструкции:\n" + "\n".join(f"- {ctx}" for ctx in additional_context)
    
    def _build_conversation_messages(
        self,
        system_prompt: str,
        conversation_context: List[Dict[str, str]],
        user_message: str
    ) -> List[Dict[str, str]]:
        """Построение массива сообщений для OpenAI"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавляем контекст диалога (последние N сообщений)
        context_limit = 10  # Ограничиваем контекст для экономии токенов
        recent_context = conversation_context[-context_limit:] if conversation_context else []
        
        for msg in recent_context:
            role = "user" if msg["sender_type"] == "user" else "assistant"
            messages.append({
                "role": role,
                "content": msg["content"]
            })
        
        # Добавляем текущее сообщение пользователя
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    async def _call_openai(self, messages: List[Dict[str, str]]) -> Dict:
        """Асинхронный вызов OpenAI API"""
        
        try:
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=settings.openai_model,
                messages=messages,
                max_tokens=settings.ai_max_tokens,
                temperature=settings.ai_temperature,
                top_p=1,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )
            
            return {
                "content": response.choices[0].message.content.strip(),
                "usage": response.usage._asdict() if response.usage else {},
                "finish_reason": response.choices[0].finish_reason
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка вызова OpenAI API: {e}")
            raise
    
    def _calculate_confidence(self, response: Dict) -> float:
        """Расчет уверенности ИИ в ответе"""
        
        # Базовая уверенность
        confidence = 0.8
        
        # Снижаем уверенность если ответ был обрезан
        if response.get("finish_reason") == "length":
            confidence -= 0.2
        
        # Снижаем уверенность для очень коротких ответов
        content_length = len(response.get("content", ""))
        if content_length < 10:
            confidence -= 0.3
        elif content_length < 30:
            confidence -= 0.1
        
        # Снижаем уверенность если в ответе есть слова неуверенности
        uncertainty_words = ["возможно", "может быть", "не уверен", "не знаю", "вероятно"]
        content_lower = response.get("content", "").lower()
        
        for word in uncertainty_words:
            if word in content_lower:
                confidence -= 0.15
                break
        
        return max(0.0, min(1.0, confidence))
    
    async def analyze_sentiment(self, text: str) -> Dict[str, any]:
        """
        Анализ эмоциональной окраски текста
        
        Args:
            text: Текст для анализа
            
        Returns:
            Dict с результатами анализа
        """
        
        if not self.openai_available:
            return self._fallback_sentiment_analysis(text)
        
        try:
            prompt = f"""
            Проанализируй эмоциональную окраску следующего текста:
            "{text}"
            
            Верни результат в JSON формате:
            {{
                "sentiment": "positive|neutral|negative",
                "score": число_от_-1_до_1,
                "confidence": число_от_0_до_1,
                "emotions": ["радость", "грусть", "гнев", "страх", "удивление"],
                "explanation": "краткое объяснение"
            }}
            """
            
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа sentiment: {e}")
            return self._fallback_sentiment_analysis(text)
    
    def _fallback_sentiment_analysis(self, text: str) -> Dict[str, any]:
        """Простой анализ sentiment без ИИ"""
        
        positive_words = ["хорошо", "отлично", "супер", "класс", "спасибо", "👍", "😊", "❤️"]
        negative_words = ["плохо", "ужасно", "не работает", "проблема", "ошибка", "👎", "😞", "😡"]
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
            score = 0.3 + min(positive_count * 0.2, 0.7)
        elif negative_count > positive_count:
            sentiment = "negative" 
            score = -0.3 - min(negative_count * 0.2, 0.7)
        else:
            sentiment = "neutral"
            score = 0.0
        
        return {
            "sentiment": sentiment,
            "score": score,
            "confidence": 0.6,
            "emotions": [],
            "explanation": "Базовый анализ по ключевым словам"
        }
    
    async def extract_intent(self, text: str) -> Dict[str, any]:
        """
        Извлечение намерения пользователя из текста
        
        Args:
            text: Текст для анализа
            
        Returns:
            Dict с намерением и уверенностью
        """
        
        # Простые правила для определения намерений
        intent_patterns = {
            "question": [r"\?", r"как", r"что", r"где", r"когда", r"почему", r"зачем"],
            "complaint": [r"не работает", r"проблема", r"ошибка", r"баг", r"сломалось"],
            "greeting": [r"привет", r"здравствуй", r"добро", r"hello", r"hi"],
            "thanks": [r"спасибо", r"благодар", r"thanks", r"thank you"],
            "request": [r"можно", r"помог", r"нужно", r"хочу", r"please"],
            "goodbye": [r"пока", r"до свидан", r"увидимся", r"bye", r"goodbye"],
            "order": [r"заказ", r"купить", r"оплат", r"стоимост", r"цена", r"price"]
        }
        
        text_lower = text.lower()
        intent_scores = {}
        
        for intent, patterns in intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches
            
            if score > 0:
                intent_scores[intent] = score
        
        if intent_scores:
            # Берем намерение с наивысшим счетом
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = min(intent_scores[best_intent] * 0.3, 1.0)
            
            return {
                "intent": best_intent,
                "confidence": confidence,
                "all_intents": intent_scores
            }
        else:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "all_intents": {}
            }


# Глобальный экземпляр сервиса
ai_service = AIService()