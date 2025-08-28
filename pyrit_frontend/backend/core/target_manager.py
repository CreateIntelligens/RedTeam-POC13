"""
AI 目標管理器
負責創建和管理不同類型的 AI 目標
"""

import sys
import os
sys.path.insert(0, '/workspace/pyrit')

from typing import Optional
from pyrit.prompt_target import OpenAIChatTarget
from pyrit.prompt_target.google.gemini_target import GeminiTarget
from pyrit.prompt_target.common.prompt_chat_target import PromptChatTarget
from ..config.settings import ModelConfig


class TargetManager:
    """AI 目標管理器"""
    
    @staticmethod
    def create_target(config: ModelConfig):
        """根據配置創建 AI 目標
        
        Args:
            config: 模型配置
            
        Returns:
            AI 目標實例
        """
        if config.type == "openai":
            return TargetManager._create_openai_target(config)
        elif config.type == "gemini":
            return TargetManager._create_gemini_target(config)
        elif config.type == "custom":
            return TargetManager._create_custom_target(config)
        else:
            raise ValueError(f"不支援的模型類型: {config.type}")
    
    @staticmethod
    def _create_openai_target(config: ModelConfig):
        """創建 OpenAI 目標"""
        return OpenAIChatTarget(
            endpoint=config.endpoint,
            api_key=config.api_key,
            model_name=config.model_name
        )
    
    @staticmethod
    def _create_gemini_target(config: ModelConfig):
        """創建 Gemini 目標"""
        return GeminiTarget(
            api_key=config.api_key,
            model=config.model_name
        )
    
    @staticmethod
    def _create_custom_target(config: ModelConfig):
        """創建自定義目標"""
        # 這裡可以擴展支援更多自定義 API
        headers = config.headers or {}
        
        # 暫時使用 OpenAI 兼容格式作為自定義目標
        # 在實際使用中，你可能需要為特定 API 創建專門的適配器
        return OpenAIChatTarget(
            endpoint=config.endpoint,
            api_key=config.api_key,
            model_name=config.model_name or "default-model"
        )
    
    @staticmethod
    def create_external_target(endpoint: str, api_key: str, model: str = "gpt-3.5-turbo", custom_headers: dict = None):
        """創建外部 API 目標（被攻擊的目標）
        
        Args:
            endpoint: API 端點
            api_key: API 金鑰
            model: 模型名稱
            custom_headers: 自定義標頭
        """
        # 判斷是否為 OpenAI 兼容 API
        if "chat/completions" in endpoint:
            return OpenAIChatTarget(
                endpoint=endpoint,
                api_key=api_key,
                model_name=model
            )
        else:
            # 自定義 API
            config = ModelConfig(
                name="External API",
                type="custom",
                endpoint=endpoint,
                api_key=api_key,
                model_name=model,
                headers=custom_headers
            )
            return TargetManager.create_target(config)