"""
PyRIT Frontend 配置管理
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """AI 模型配置"""
    name: str
    type: str  # 'openai', 'gemini', 'custom'
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


@dataclass
class AttackConfig:
    """攻擊配置"""
    max_turns: int = 5
    max_backtracks: int = 2
    attack_type: str = "crescendo"  # crescendo, tree_of_attacks, etc.


class Settings:
    """設置管理類"""
    
    def __init__(self):
        self.available_models = self._load_available_models()
        self.attack_config = AttackConfig()
        
    def _load_available_models(self) -> List[ModelConfig]:
        """載入可用的模型配置"""
        models = []
        
        # OpenAI 模型
        if os.getenv("PLATFORM_OPENAI_CHAT_API_KEY"):
            models.append(ModelConfig(
                name="OpenAI GPT-4o",
                type="openai",
                endpoint=os.getenv("PLATFORM_OPENAI_CHAT_ENDPOINT"),
                api_key=os.getenv("PLATFORM_OPENAI_CHAT_API_KEY"),
                model_name="gpt-4o"
            ))
        
        # Gemini 模型
        if os.getenv("GOOGLE_GEMINI_API_KEY"):
            models.append(ModelConfig(
                name="Google Gemini 1.5 Flash",
                type="gemini",
                api_key=os.getenv("GOOGLE_GEMINI_API_KEY"),
                model_name="gemini-1.5-flash"
            ))
            
        # 可以繼續添加其他模型...
        
        return models
    
    def get_model_by_name(self, name: str) -> Optional[ModelConfig]:
        """根據名稱獲取模型配置"""
        for model in self.available_models:
            if model.name == name:
                return model
        return None
    
    def add_custom_model(self, config: ModelConfig):
        """添加自定義模型"""
        self.available_models.append(config)


# 全域設置實例
settings = Settings()