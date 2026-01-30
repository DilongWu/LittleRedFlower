"""
AI Chat Service for Market Analysis
Provides intelligent chat responses with market context awareness
"""

import os
import json
from typing import Optional, List, Dict
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential


def load_config():
    """Load Azure OpenAI configuration from multiple sources"""
    # Priority 1: Environment variables
    if os.getenv("AZURE_OPENAI_ENDPOINT"):
        return {
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "apiKey": os.getenv("AZURE_OPENAI_API_KEY"),
            "deploymentName": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini"),
            "managedIdentityClientId": os.getenv("AZURE_MANAGED_IDENTITY_CLIENT_ID"),
            "maxTokens": int(os.getenv("AZURE_OPENAI_MAX_TOKENS", "500")),
            "temperature": float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.7"))
        }

    # Priority 2: src/config.json (fallback)
    src_config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "src",
        "config.json"
    )
    if os.path.exists(src_config_path):
        try:
            with open(src_config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Default configuration
    return {
        "deploymentName": "gpt-4.1-mini",
        "maxTokens": 500,
        "temperature": 0.7
    }


AZURE_CONFIG = load_config()


def get_azure_client():
    """Initialize Azure OpenAI client with Managed Identity or API Key"""
    try:
        # Method 1: API Key authentication
        if "apiKey" in AZURE_CONFIG and AZURE_CONFIG.get("apiKey"):
            return AzureOpenAI(
                azure_endpoint=AZURE_CONFIG["endpoint"],
                api_key=AZURE_CONFIG["apiKey"],
                api_version="2024-05-01-preview"
            )

        # Method 2: Managed Identity authentication
        credential = DefaultAzureCredential(
            managed_identity_client_id=AZURE_CONFIG.get("managedIdentityClientId")
        )
        token_provider = lambda: credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token

        return AzureOpenAI(
            azure_endpoint=AZURE_CONFIG["endpoint"],
            azure_ad_token_provider=token_provider,
            api_version="2024-05-01-preview"
        )
    except Exception as e:
        print(f"Failed to initialize Azure OpenAI client: {e}")
        return None


class ChatService:
    """AI Chat Service with market context awareness"""

    def __init__(self):
        self.client = get_azure_client()

    def build_system_prompt(self, market_context: Optional[Dict] = None) -> str:
        """Build system prompt with market context"""
        base_prompt = """你是一名专业的中国股市分析师助手。

你的职责：
- 回答用户关于市场、股票、板块的问题
- 提供客观、专业的分析建议
- 基于提供的市场数据进行分析
- 使用清晰、专业的中文表达

回答要求：
- 简洁明了，控制在200字以内
- 客观中立，避免夸大
- 如果数据不足，坦诚说明
- 重要风险必须提示"""

        # Add market context if available
        if market_context:
            context_str = "\n\n当前市场情况："

            # Sentiment data
            if "sentiment" in market_context:
                sentiment = market_context["sentiment"]
                label = sentiment.get("label", "未知")
                score = sentiment.get("score", "N/A")
                context_str += f"\n- 市场情绪: {label} ({score}分)"

            # Index data
            if "indexes" in market_context and len(market_context["indexes"]) > 0:
                for idx in market_context["indexes"][:3]:  # Top 3 indexes
                    name = idx.get("name", "")
                    close = idx.get("close", "")
                    change = idx.get("change_percent", "")
                    if name and close:
                        context_str += f"\n- {name}: {close}"
                        if change:
                            context_str += f" ({change}%)"

            base_prompt += context_str

        return base_prompt

    def get_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        market_context: Optional[Dict] = None
    ) -> str:
        """
        Get AI response with conversation history and market context

        Args:
            user_message: User's current message
            conversation_history: List of previous messages [{role, content}, ...]
            market_context: Current market data (sentiment, indexes, etc.)

        Returns:
            AI response text
        """
        if not self.client:
            return "抱歉，AI服务暂时不可用，请稍后再试。"

        try:
            # Build messages array
            messages = []

            # System prompt with market context
            system_prompt = self.build_system_prompt(market_context)
            messages.append({"role": "system", "content": system_prompt})

            # Add conversation history (last 10 messages to stay within token limits)
            if conversation_history:
                for msg in conversation_history[-10:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

            # Add current user message
            messages.append({"role": "user", "content": user_message})

            # Call Azure OpenAI
            response = self.client.chat.completions.create(
                model=AZURE_CONFIG.get("deploymentName", "gpt-4.1-mini"),
                messages=messages,
                temperature=AZURE_CONFIG.get("temperature", 0.7),
                max_tokens=AZURE_CONFIG.get("maxTokens", 500)
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            error_msg = str(e)
            print(f"Chat service error: {error_msg}")

            # Return user-friendly error message in Chinese
            if "rate" in error_msg.lower() or "quota" in error_msg.lower():
                return "抱歉，当前请求过多，请稍后再试。"
            elif "timeout" in error_msg.lower():
                return "抱歉，请求超时，请重试。"
            else:
                return "抱歉，发生了错误，请稍后重试。"


# Global chat service instance
chat_service = ChatService()
