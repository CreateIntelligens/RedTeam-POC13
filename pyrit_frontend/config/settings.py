"""
PyRIT Frontend 配置設定
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    type: str  # openai, gemini, custom
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


@dataclass 
class AttackConfig:
    """攻擊配置"""
    max_turns: int = 5
    max_backtracks: int = 2
    attack_type: str = "crescendo"


class Settings:
    """全域設定類"""
    
    def __init__(self):
        self.available_models: List[ModelConfig] = [
            ModelConfig(
                name="OpenAI GPT-4o",
                type="openai", 
                model_name="gpt-4o"
            ),
            ModelConfig(
                name="Google Gemini 1.5 Flash",
                type="gemini",
                model_name="gemini-1.5-flash" 
            ),
        ]
        self.custom_models: List[ModelConfig] = []
    
    def add_custom_model(self, config: ModelConfig):
        """添加自定義模型"""
        self.custom_models.append(config)
        self.available_models.append(config)
    
    def get_model_by_name(self, name: str) -> Optional[ModelConfig]:
        """根據名稱獲取模型配置"""
        for model in self.available_models:
            if model.name == name:
                return model
        return None
    
    def remove_model(self, name: str) -> bool:
        """移除模型"""
        for model in self.available_models:
            if model.name == name and model in self.custom_models:
                self.available_models.remove(model)
                self.custom_models.remove(model)
                return True
        return False


# 全域設定實例
settings = Settings()