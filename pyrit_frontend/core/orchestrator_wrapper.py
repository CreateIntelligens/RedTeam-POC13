"""
PyRIT 編排器包裝類
真正集成PyRIT庫的攻擊編排功能
"""

import asyncio
import logging
import os
from typing import Dict, List, Any, Optional

# 真正的PyRIT imports
try:
    from pyrit.common import initialize_pyrit
    from pyrit.orchestrator import (
        CrescendoOrchestrator,
        PAIROrchestrator,
        TreeOfAttacksWithPruningOrchestrator,
        RedTeamingOrchestrator,
        ContextComplianceOrchestrator,
        FlipAttackOrchestrator,
        ManyShotJailbreakOrchestrator,
        PromptSendingOrchestrator,
        RolePlayOrchestrator,
        RolePlayPaths,
    )
    from pyrit.prompt_target import OpenAIChatTarget
    from pyrit.score import SelfAskRefusalScorer, Scorer, SelfAskTrueFalseScorer, TrueFalseQuestion
    from pyrit.memory import CentralMemory
    from pyrit.prompt_converter import Base64Converter, ROT13Converter
    PYRIT_AVAILABLE = True
    print("✅ PyRIT 庫載入成功")
except ImportError as e:
    print(f"⚠️ PyRIT 庫載入失敗: {e}")
    PYRIT_AVAILABLE = False

from ..config.settings import ModelConfig, AttackConfig

logger = logging.getLogger(__name__)

class OrchestratorWrapper:
    """真正的PyRIT編排器包裝類"""
    
    def __init__(self):
        self.is_initialized = False
        self.orchestrators = {}
        
        if PYRIT_AVAILABLE:
            try:
                # 初始化PyRIT
                initialize_pyrit(memory_db_type="InMemory")
                self.memory = CentralMemory.get_memory_instance()
                self.is_initialized = True
                logger.info("✅ PyRIT 初始化成功")
            except Exception as e:
                logger.error(f"❌ PyRIT 初始化失敗: {e}")
                self.is_initialized = False
        else:
            logger.warning("❌ PyRIT 庫不可用，使用模擬模式")
    
    def _create_target_from_config(self, config: Dict[str, Any]) -> Any:
        """根據配置創建PyRIT目標"""
        if not PYRIT_AVAILABLE:
            return None
            
        api_type = config.get('api_type', 'openai')
        
        try:
            if api_type == 'openai':
                api_key = config.get('api_key')
                model = config.get('model', 'gpt-4o')
                
                if api_key:
                    os.environ['OPENAI_API_KEY'] = api_key
                
                return OpenAIChatTarget(model_name=model)
                
            elif api_type == 'custom':
                # 處理自定義API配置
                endpoint = config.get('endpoint')
                custom_template = config.get('customTemplate')
                headers = config.get('headers', {})
                
                if not endpoint:
                    logger.error("自定義API缺少endpoint配置")
                    return None
                
                print(f"🔧 創建自定義API目標:")
                print(f"   端點: {endpoint}")
                print(f"   模板: {custom_template}")
                print(f"   Headers: {headers}")
                
                # 使用PyRIT的HTTPXAPITarget
                return self._create_custom_api_target(endpoint, custom_template, headers)
                
            else:
                logger.warning(f"不支援的API類型: {api_type}，使用OpenAI作為備用")
                return OpenAIChatTarget()
                
        except Exception as e:
            logger.error(f"創建目標失敗: {e}")
            return None
    
    def _create_custom_api_target(self, endpoint: str, custom_template: str, headers: Dict[str, str]) -> Any:
        """創建自定義API目標"""
        try:
            from pyrit.prompt_target import HTTPXAPITarget
            import json
            
            # 解析自定義模板為JSON
            try:
                template_json = json.loads(custom_template)
                print(f"✅ 成功解析自定義模板: {template_json}")
                
                # 檢查是否已經是 {body: {...}, headers: {...}} 格式
                if 'body' in template_json and 'headers' in template_json:
                    print(f"🔧 檢測到分離格式，提取body部分")
                    actual_json_data = template_json['body']
                    actual_headers = template_json.get('headers', {})
                    # 合併headers
                    if headers:
                        actual_headers.update(headers)
                else:
                    # 直接的JSON格式
                    actual_json_data = template_json
                    actual_headers = headers if headers else {"Content-Type": "application/json"}
                    
            except json.JSONDecodeError as e:
                print(f"❌ 自定義模板JSON格式錯誤: {e}")
                # 使用備用模板
                actual_json_data = {"message": "{MESSAGE}"}
                actual_headers = headers if headers else {"Content-Type": "application/json"}
            
            # 創建HTTPXAPITarget - 使用處理過的json_data
            target = HTTPXAPITarget(
                http_url=endpoint,
                method="POST",
                json_data=actual_json_data,
                headers=actual_headers,
                max_requests_per_minute=10
            )
            
            print(f"✅ 成功創建HTTPXAPITarget")
            print(f"📝 最終JSON數據: {actual_json_data}")
            print(f"📝 最終Headers: {actual_headers}")
            return target
            
        except ImportError:
            print("❌ HTTPXAPITarget不可用，無法創建自定義API目標")
            raise Exception("PyRIT HTTPXAPITarget不可用")
            
        except Exception as e:
            print(f"❌ 自定義API目標創建失敗: {e}")
            raise Exception(f"自定義API目標創建失敗: {e}")
    
    def _create_model_target(self, model_name: str) -> Any:
        """根據模型名稱創建PyRIT目標"""
        if not PYRIT_AVAILABLE:
            return None
            
        try:
            # 根據模型名稱判斷類型
            if 'gpt' in model_name.lower() or 'openai' in model_name.lower():
                return OpenAIChatTarget(model_name=model_name)
            elif 'claude' in model_name.lower():
                # 需要實現Claude target，暫時使用OpenAI
                logger.warning("Claude目標尚未實現，使用OpenAI作為備用")
                return OpenAIChatTarget()
            elif 'gemini' in model_name.lower():
                # 需要實現Gemini target，暫時使用OpenAI
                logger.warning("Gemini目標尚未實現，使用OpenAI作為備用")
                return OpenAIChatTarget()
            else:
                # 默認使用OpenAI
                return OpenAIChatTarget(model_name=model_name)
                
        except Exception as e:
            logger.error(f"創建模型目標失敗: {e}")
            return OpenAIChatTarget()  # 備用

    def _create_orchestrator(self, attack_type: str, objective_target, adversarial_chat, scoring_target, scorer, max_turns) -> Any:
        """工廠函數，根據 attack_type 創建並返回對應的 orchestrator 實例"""
        
        # 注意：部分Orchestrator已被棄用，但根據要求仍在此處集成
        # 注意：部分Orchestrator的參數需求與Crescendo不同，這裡使用通用參數進行簡化適配
        
        if attack_type == "crescendo":
            return CrescendoOrchestrator(
                objective_target=objective_target,
                adversarial_chat=adversarial_chat,
                scoring_target=scoring_target,
                max_turns=max_turns,
                max_backtracks=2
            )
        elif attack_type == "pair":
            return PAIROrchestrator(
                objective_target=objective_target,
                adversarial_chat=adversarial_chat,
                scoring_target=scoring_target,
                depth=max_turns, # 使用 max_turns 作為 depth
            )
        elif attack_type == "tap":
            return TreeOfAttacksWithPruningOrchestrator(
                objective_target=objective_target,
                adversarial_chat=adversarial_chat,
                scoring_target=scoring_target,
                depth=max_turns, # 使用 max_turns 作為 depth
                width=2,
                branching_factor=2,
            )
        elif attack_type == "red_teaming":
            # RedTeamingOrchestrator 需要一個二元分類的 scorer
            binary_scorer = SelfAskTrueFalseScorer(
                chat_target=scoring_target,
                true_false_question=TrueFalseQuestion.from_yaml_file(os.path.join(os.path.dirname(__file__), '..', '..', 'pyrit', 'datasets', 'score', 'true_false_question', 'prompt_injection.yaml'))
            )
            return RedTeamingOrchestrator(
                objective_target=objective_target,
                adversarial_chat=adversarial_chat,
                objective_scorer=binary_scorer,
                max_turns=max_turns,
            )
        elif attack_type == "prompt_sending":
            return PromptSendingOrchestrator(
                objective_target=objective_target,
                objective_scorer=scorer,
            )
        elif attack_type == "many_shot_jailbreak":
            return ManyShotJailbreakOrchestrator(
                objective_target=objective_target,
                objective_scorer=scorer,
            )
        elif attack_type == "flip_attack":
            return FlipAttackOrchestrator(
                objective_target=objective_target,
                objective_scorer=scorer,
            )
        elif attack_type == "role_play":
            return RolePlayOrchestrator(
                objective_target=objective_target,
                adversarial_chat=adversarial_chat,
                role_play_definition_path=RolePlayPaths.VIDEO_GAME.value, # 硬編碼一個預設值
                objective_scorer=scorer,
            )
        elif attack_type == "context_compliance":
            return ContextComplianceOrchestrator(
                objective_target=objective_target,
                adversarial_chat=adversarial_chat,
                objective_scorer=scorer,
            )
        else:
            logger.warning(f"攻擊類型 {attack_type} 尚未實現或無法直接適配，使用 crescendo 作為備用")
            return CrescendoOrchestrator(
                objective_target=objective_target,
                adversarial_chat=adversarial_chat,
                scoring_target=scoring_target,
                max_turns=max_turns,
                max_backtracks=2
            )

    async def run_real_attack(
        self,
        attack_generator: str,
        scoring_model: str,
        target_config: Dict[str, Any],
        objectives: List[str],
        attack_type: str = "crescendo",
        max_turns: int = 5
    ) -> Dict[str, Any]:
        """執行真正的PyRIT攻擊"""
        
        if not PYRIT_AVAILABLE or not self.is_initialized:
            return await self._fallback_attack(objectives, attack_type, max_turns)
        
        try:
            print(f"\n🔧 PyRIT 攻擊引擎初始化")
            print(f"   • 攻擊類型: {attack_type}")
            print(f"   • PyRIT 初始化狀態: {self.is_initialized}")
            print(f"   • PyRIT 可用狀態: {PYRIT_AVAILABLE}")
            
            logger.info(f"🚀 開始真正的PyRIT攻擊: {attack_type}")
            
            # 創建目標
            print(f"🎯 創建攻擊目標...")
            objective_target = self._create_target_from_config(target_config)
            if not objective_target:
                raise Exception("無法創建目標AI")
            
            print(f"✅ 目標AI創建成功: {type(objective_target).__name__}")
            
            # 創建攻擊生成器
            print(f"🤖 創建攻擊生成器: {attack_generator}")
            adversarial_chat = self._create_model_target(attack_generator)
            if not adversarial_chat:
                raise Exception("無法創建攻擊生成器")
            print(f"✅ 攻擊生成器創建成功: {type(adversarial_chat).__name__}")
            
            # 創建評分器
            print(f"📊 創建評分模型: {scoring_model}")
            scoring_target = self._create_model_target(scoring_model)
            if not scoring_target:
                raise Exception("無法創建評分模型")
            print(f"✅ 評分模型創建成功: {type(scoring_target).__name__}")
            
            scorer = SelfAskRefusalScorer(chat_target=scoring_target)
            print(f"✅ 評分器創建成功: {type(scorer).__name__}")
            
            # 創建編排器
            print(f"🏗️ 創建 {attack_type} 編排器...")
            orchestrator = self._create_orchestrator(attack_type, objective_target, adversarial_chat, scoring_target, scorer, max_turns)
            print(f"✅ 編排器創建成功: {type(orchestrator).__name__}")
            
            # 執行攻擊
            memory_labels = {
                "attack_type": attack_type,
                "frontend_attack": "true",
                "timestamp": str(asyncio.get_event_loop().time())
            }
            
            print(f"⚡ 開始執行攻擊，目標數量: {len(objectives)}")
            print(f"📝 Memory labels: {memory_labels}")
            logger.info(f"執行攻擊，目標數量: {len(objectives)}")
            
            results = []
            if hasattr(orchestrator, 'run_attacks_async'):
                print(f"🔄 使用批處理模式執行攻擊...")
                # 如果Orchestrator支援批處理
                results = await orchestrator.run_attacks_async(
                    objectives=objectives,
                    memory_labels=memory_labels
                )
                print(f"✅ 批處理攻擊完成，結果數量: {len(results)}")
            else:
                print(f"🔄 使用逐一執行模式...")
                # 否則，遍歷objectives並逐一執行
                for i, objective in enumerate(objectives, 1):
                    print(f"⚡ 執行攻擊 {i}/{len(objectives)}: {objective[:50]}...")
                    result = await orchestrator.run_attack_async(objective=objective, memory_labels=memory_labels)
                    results.append(result)
                    print(f"✅ 攻擊 {i} 完成")

            # 轉換結果格式
            print(f"🔄 處理攻擊結果...")
            formatted_results = []
            successful_attacks = 0
            
            for i, result in enumerate(results):
                print(f"📋 處理結果 {i+1}/{len(results)}...")
                # 獲取對話和評分
                conversation = self.memory.get_conversation(conversation_id=result.conversation_id)
                
                # 提取最後的AI回應
                last_response = ""
                if conversation and len(conversation) > 0:
                    last_message = conversation[-1]
                    raw_response = getattr(last_message, 'converted_value', None) or getattr(last_message, 'text', None) or str(last_message)
                    
                    print(f"🔍 原始回應格式: {type(raw_response).__name__}")
                    print(f"🔍 原始回應內容: {str(raw_response)[:100]}...")
                    
                    # 處理HTTPXAPITarget的複雜回應格式
                    if isinstance(raw_response, str):
                        # 檢查是否包含 b'...' 格式的bytes
                        if "b'" in raw_response and "assistant:" in raw_response:
                            try:
                                # 從字符串中提取bytes部分
                                import re
                                bytes_match = re.search(r"b'([^']+)'", raw_response)
                                if bytes_match:
                                    hex_string = bytes_match.group(1)
                                    # 將轉義的hex字符串轉換為實際的bytes
                                    import codecs
                                    try:
                                        # 先嘗試作為轉義字符串處理
                                        bytes_data = codecs.decode(hex_string, 'unicode_escape').encode('latin1')
                                        decoded_text = bytes_data.decode('utf-8')
                                        print(f"🔍 解碼後的完整回應: {decoded_text}")
                                        
                                        # 嘗試解析JSON並提取回應內容
                                        import json
                                        try:
                                            json_response = json.loads(decoded_text)
                                            # 支持多種回應字段
                                            for field in ['response', 'message', 'text', 'content', 'answer']:
                                                if field in json_response:
                                                    last_response = json_response[field]
                                                    print(f"✅ 從 '{field}' 字段提取回應")
                                                    break
                                            else:
                                                # 如果沒有找到標準字段，使用整個JSON
                                                last_response = str(json_response)
                                        except json.JSONDecodeError:
                                            # JSON解析失敗，使用解碼後的文本
                                            last_response = decoded_text
                                    except Exception as decode_error:
                                        print(f"⚠️ 解碼失敗: {decode_error}")
                                        last_response = raw_response
                                else:
                                    last_response = raw_response
                            except Exception as e:
                                print(f"⚠️ 回應解析異常: {e}")
                                last_response = raw_response
                        else:
                            last_response = raw_response
                    else:
                        last_response = str(raw_response)
                    
                    print(f"📝 最終解析的回應: {last_response[:200]}...")
                
                # 簡化評分邏輯，先讓攻擊能執行
                success = hasattr(result, 'status') and str(result.status).lower() == 'success'
                score_value = 1.0 if success else 0.5  # 假設部分成功
                
                print(f"   結果狀態: {getattr(result, 'status', 'unknown')}")
                print(f"   成功判定: {success}")
                print(f"   回應長度: {len(last_response)}")
                
                if success:
                    successful_attacks += 1
                
                formatted_result = {
                    "turn": i + 1,
                    "objective": objectives[i] if i < len(objectives) else "未知目標",
                    "attack_message": "由PyRIT生成的攻擊訊息",
                    "success": success,
                    "response": last_response[:500] + "..." if len(last_response) > 500 else last_response,
                    "score": score_value,
                    "status_code": 200
                }
                formatted_results.append(formatted_result)
            
            success_rate = successful_attacks / len(objectives) if objectives else 0
            
            print(f"\n📊 攻擊完成統計:")
            print(f"   • 總攻擊次數: {len(objectives)}")
            print(f"   • 成功攻擊數: {successful_attacks}")
            print(f"   • 成功率: {success_rate:.1%}")
            print(f"✅ PyRIT攻擊完成！")
            
            return {
                "success": True,
                "attack_type": attack_type,
                "total_turns": len(objectives),
                "successful_attacks": successful_attacks,
                "success_rate": success_rate,
                "results": formatted_results,
                "summary": f"✅ PyRIT攻擊完成！在 {len(objectives)} 次攻擊中成功 {successful_attacks} 次 (成功率: {success_rate:.1%})"
            }
            
        except Exception as e:
            print(f"\n❌ PyRIT攻擊執行失敗:")
            print(f"   • 錯誤類型: {type(e).__name__}")
            print(f"   • 錯誤訊息: {str(e)}")
            import traceback
            print(f"   • 詳細追蹤:")
            traceback.print_exc()
            
            logger.error(f"❌ PyRIT攻擊執行失敗: {e}")
            return {
                "success": False,
                "error": f"PyRIT攻擊失敗: {str(e)}"
            }
    
    async def _fallback_attack(
        self,
        objectives: List[str],
        attack_type: str,
        max_turns: int
    ) -> Dict[str, Any]:
        """備用攻擊方法（當PyRIT不可用時）"""
        logger.warning("⚠️ 使用備用攻擊方法（PyRIT不可用）")
        
        # 簡單的模擬攻擊
        import random
        results = []
        
        for i, objective in enumerate(objectives):
            success = random.random() > 0.6  # 40%成功率
            
            result = {
                "turn": i + 1,
                "objective": objective,
                "attack_message": f"模擬攻擊訊息: {objective}",
                "success": success,
                "response": f"模擬回應: {'攻擊成功' if success else '攻擊被阻擋'}",
                "score": random.uniform(0.6, 0.9) if success else random.uniform(0.1, 0.4),
                "status_code": 200
            }
            results.append(result)
        
        successful_attacks = sum(1 for r in results if r["success"])
        success_rate = successful_attacks / len(results) if results else 0
        
        return {
            "success": True,
            "attack_type": attack_type,
            "total_turns": len(results),
            "successful_attacks": successful_attacks,
            "success_rate": success_rate,
            "results": results,
            "summary": f"⚠️ 備用模式攻擊完成！在 {len(results)} 次攻擊中成功 {successful_attacks} 次 (成功率: {success_rate:.1%})"
        }