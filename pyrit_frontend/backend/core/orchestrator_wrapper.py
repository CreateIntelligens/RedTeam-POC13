"""
攻擊編排器包裝類
統一處理不同的攻擊策略
"""

import sys
import asyncio
sys.path.insert(0, '/workspace/pyrit')

from typing import List, Dict, Any, Optional
from pyrit.common.initialization import initialize_pyrit
from pyrit.memory.central_memory import CentralMemory
from pyrit.orchestrator import CrescendoOrchestrator
from pyrit.models import PromptRequestPiece, PromptRequestResponse

from .target_manager import TargetManager
from ..config.settings import ModelConfig, AttackConfig


class OrchestratorWrapper:
    """攻擊編排器包裝類"""
    
    def __init__(self):
        self.memory = None
        self.is_initialized = False
    
    async def initialize(self):
        """初始化 PyRIT 環境"""
        if not self.is_initialized:
            initialize_pyrit(memory_db_type="InMemory")
            self.memory = CentralMemory.get_memory_instance()
            self.is_initialized = True
    
    async def run_attack(
        self,
        attack_generator_config: ModelConfig,  # 生成攻擊的 AI
        scoring_config: ModelConfig,           # 評分的 AI
        target_endpoint: str,                  # 被攻擊的目標 API
        target_api_key: str,
        target_model: str,
        objectives: List[str],                 # 攻擊目標
        attack_config: Optional[AttackConfig] = None,
        target_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """執行攻擊
        
        Args:
            attack_generator_config: 生成攻擊的 AI 配置
            scoring_config: 評分 AI 配置
            target_endpoint: 被攻擊的目標 API 端點
            target_api_key: 目標 API 金鑰
            target_model: 目標模型名稱
            objectives: 攻擊目標列表
            attack_config: 攻擊配置
            target_headers: 目標 API 自定義標頭
            
        Returns:
            攻擊結果
        """
        await self.initialize()
        
        try:
            # 創建 AI 目標
            attack_generator = TargetManager.create_target(attack_generator_config)
            scoring_target = TargetManager.create_target(scoring_config)
            external_target = TargetManager.create_external_target(
                target_endpoint, target_api_key, target_model, target_headers
            )
            
            # 使用預設攻擊配置
            config = attack_config or AttackConfig()
            
            # 創建攻擊編排器
            if config.attack_type == "crescendo":
                orchestrator = CrescendoOrchestrator(
                    adversarial_chat=attack_generator,    # 你的 AI（生成攻擊）
                    objective_target=external_target,     # 外部 API（被攻擊）
                    scoring_target=scoring_target,        # 你的 AI（評分）
                    max_turns=config.max_turns,
                    max_backtracks=config.max_backtracks
                )
            else:
                raise ValueError(f"不支援的攻擊類型: {config.attack_type}")
            
            # 執行攻擊
            memory_labels = {
                "attack_type": config.attack_type,
                "target": target_endpoint,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            results = await orchestrator.run_attacks_async(
                objectives=objectives,
                memory_labels=memory_labels
            )
            
            # 解析結果
            parsed_results = await self._parse_results(results)
            
            return {
                "success": True,
                "results": parsed_results,
                "total_attacks": len(results),
                "config": {
                    "attack_generator": attack_generator_config.name,
                    "scoring_model": scoring_config.name,
                    "target": target_endpoint,
                    "objectives": objectives
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "config": {
                    "attack_generator": attack_generator_config.name,
                    "scoring_model": scoring_config.name,
                    "target": target_endpoint,
                    "objectives": objectives
                }
            }
    
    async def _parse_results(self, results) -> List[Dict[str, Any]]:
        """解析攻擊結果"""
        parsed = []
        
        for i, result in enumerate(results):
            try:
                # 獲取對話記錄
                conversation = []
                if hasattr(result, 'request_pieces') and result.request_pieces:
                    for piece in result.request_pieces:
                        conversation.append({
                            "role": piece.role,
                            "content": piece.converted_value,
                            "timestamp": str(piece.timestamp) if hasattr(piece, 'timestamp') else None
                        })
                
                # 獲取評分資訊
                scores = []
                if hasattr(result, 'score_memory_data') and result.score_memory_data:
                    for score_data in result.score_memory_data:
                        scores.append({
                            "score": score_data.score_value if hasattr(score_data, 'score_value') else None,
                            "rationale": score_data.score_rationale if hasattr(score_data, 'score_rationale') else None
                        })
                
                parsed.append({
                    "attack_id": i + 1,
                    "conversation": conversation,
                    "scores": scores,
                    "success": len(scores) > 0 and any(s.get("score", 0) > 0.5 for s in scores)
                })
                
            except Exception as e:
                parsed.append({
                    "attack_id": i + 1,
                    "error": str(e),
                    "conversation": [],
                    "scores": [],
                    "success": False
                })
        
        return parsed
    
    async def quick_test(self, generator_config: ModelConfig, target_endpoint: str, target_api_key: str) -> Dict[str, Any]:
        """快速測試連接"""
        await self.initialize()
        
        try:
            # 測試生成器
            generator = TargetManager.create_target(generator_config)
            
            # 測試目標
            target = TargetManager.create_external_target(target_endpoint, target_api_key)
            
            # 簡單測試
            test_prompt = "Hello, please introduce yourself briefly."
            request = PromptRequestResponse(request_pieces=[
                PromptRequestPiece(role="user", original_value=test_prompt, converted_value=test_prompt)
            ])
            
            response = await target.send_prompt_async(prompt_request=request)
            
            return {
                "success": True,
                "generator_available": True,
                "target_available": True,
                "test_response": response.request_pieces[0].converted_value if response.request_pieces else "No response"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }