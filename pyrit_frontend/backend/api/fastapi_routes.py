"""
PyRIT Frontend FastAPI 路由
提供現代化的 REST API 接口
"""

import asyncio
import httpx
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
import os
sys.path.insert(0, '/workspace/pyrit')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from pyrit_frontend.core.orchestrator_wrapper import OrchestratorWrapper
from pyrit_frontend.core.preset_objectives import get_all_categories, get_all_objectives, get_strategy_info, get_available_models
from pyrit_frontend.core.simple_attack_engine import SimpleAttackEngine
from pyrit_frontend.config.settings import settings, ModelConfig


app = FastAPI(title="PyRIT 攻擊測試平台", version="1.0.0")

# 添加 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全域攻擊包裝器
orchestrator = OrchestratorWrapper()
simple_attacker = SimpleAttackEngine()


# Pydantic 模型
class ModelResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str
    type: str
    model_name: Optional[str] = None


class CustomModelRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str
    type: str
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class TestConnectionRequest(BaseModel):
    target_config: Dict[str, Any]


class TestChatRequest(BaseModel):
    target_config: Dict[str, Any]


class AttackRequest(BaseModel):
    attack_generator: str
    scoring_model: str
    target_config: Dict[str, Any]
    objectives: List[str]
    max_turns: int = 5
    attack_type: str = "crescendo"


@app.get("/")
async def read_index():
    """返回主頁面"""
    return FileResponse('/workspace/pyrit/pyrit_frontend/frontend/templates/index.html')


@app.get("/api/models", response_model=Dict[str, Any])
async def get_models():
    """獲取可用的模型列表 (新版，提供預設列表)"""
    try:
        models = get_available_models()
        return {
            "success": True,
            "models": models
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models/add")
async def add_custom_model(model_request: CustomModelRequest):
    """添加自定義模型"""
    try:
        config = ModelConfig(
            name=model_request.name,
            type=model_request.type,
            endpoint=model_request.endpoint,
            api_key=model_request.api_key,
            model_name=model_request.model_name,
            headers=model_request.headers
        )

        settings.add_custom_model(config)

        return {
            "success": True,
            "message": f"模型 {config.name} 已添加"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/test")
async def test_connection(request: TestConnectionRequest):
    """測試連接"""
    try:
        import time
        
        print(f"\n🔍 開始測試連接")
        print(f"{'='*40}")
        
        start_time = time.time()
        
        # 從配置中提取信息
        config = request.target_config
        endpoint = config.get('endpoint')
        request_body = config.get('request_body')
        headers = config.get('headers', {})
        headers['Content-Type'] = 'application/json'
        
        print(f"🎯 測試目標:")
        print(f"   • 端點: {endpoint}")
        print(f"   • 請求體: {request_body}")
        print(f"   • Headers: {headers}")
        
        if not endpoint:
            print(f"❌ 缺少API端點配置")
            return {
                "success": False,
                "error": "缺少API端點配置"
            }
        
        # 發送POST請求到目標端點
        print(f"🌐 發送HTTP POST請求...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                endpoint,
                json=request_body,
                headers=headers
            )
        
        end_time = time.time()
        latency = round((end_time - start_time) * 1000)  # 毫秒
        
        print(f"📨 收到回應:")
        print(f"   • 狀態碼: {response.status_code}")
        print(f"   • 延遲: {latency}ms")
        print(f"   • 回應長度: {len(response.text)} 字符")
        
        # 檢查響應
        if response.status_code == 200:
            try:
                response_data = response.json()
                return {
                    "success": True,
                    "message": f"連接成功！端點回應正常",
                    "status_code": response.status_code,
                    "latency": f"{latency}ms",
                    "response_preview": str(response_data)[:200] + "..." if len(str(response_data)) > 200 else str(response_data)
                }
            except:
                return {
                    "success": True,
                    "message": f"連接成功！端點回應正常 (非JSON格式)",
                    "status_code": response.status_code,
                    "latency": f"{latency}ms",
                    "response_preview": response.text[:200] + "..." if len(response.text) > 200 else response.text
                }
        else:
            return {
                "success": False,
                "error": f"端點回應錯誤 (狀態碼: {response.status_code})",
                "latency": f"{latency}ms",
                "response_text": response.text[:200]
            }
        
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "連接超時，請檢查端點URL是否正確"
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "error": f"連接失敗: {str(e)}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def test_chat(request: TestChatRequest):
    """測試對話"""
    try:
        import time
        
        start_time = time.time()
        
        # 從配置中提取信息
        config = request.target_config
        endpoint = config.get('endpoint')
        request_body = config.get('request_body')
        headers = config.get('headers', {})
        headers['Content-Type'] = 'application/json'
        api_type = config.get('api_type', 'openai')
        
        if not endpoint:
            return {
                "success": False,
                "error": "缺少API端點配置"
            }
        
        # 發送POST請求到目標端點
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                endpoint,
                json=request_body,
                headers=headers
            )
        
        end_time = time.time()
        latency = round((end_time - start_time) * 1000)  # 毫秒
        
        # 檢查響應
        if response.status_code == 200:
            try:
                response_data = response.json()
                
                # 根據不同API類型提取回應文字
                response_text = ""
                if api_type == 'openai':
                    if 'choices' in response_data and len(response_data['choices']) > 0:
                        response_text = response_data['choices'][0].get('message', {}).get('content', '')
                elif api_type == 'gemini':
                    if 'candidates' in response_data and len(response_data['candidates']) > 0:
                        content = response_data['candidates'][0].get('content', {})
                        if 'parts' in content and len(content['parts']) > 0:
                            response_text = content['parts'][0].get('text', '')
                elif api_type == 'claude':
                    if 'content' in response_data and len(response_data['content']) > 0:
                        response_text = response_data['content'][0].get('text', '')
                else:
                    # 自定義API，嘗試常見的回應字段
                    response_text = (response_data.get('response') or 
                                   response_data.get('text') or 
                                   response_data.get('content') or 
                                   response_data.get('message') or 
                                   str(response_data))
                
                if not response_text:
                    response_text = "無法解析AI回應"
                
                return {
                    "success": True,
                    "response": response_text,
                    "latency": f"{latency}ms",
                    "raw_response": response_data
                }
            except Exception as parse_error:
                return {
                    "success": False,
                    "error": f"解析回應失敗: {str(parse_error)}",
                    "latency": f"{latency}ms",
                    "raw_text": response.text[:500]
                }
        else:
            return {
                "success": False,
                "error": f"API回應錯誤 (狀態碼: {response.status_code})",
                "latency": f"{latency}ms",
                "response_text": response.text[:200]
            }
        
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "請求超時，AI回應時間過長"
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "error": f"連接失敗: {str(e)}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/attack")
async def run_attack(request: AttackRequest):
    """執行攻擊 - 使用真正的PyRIT"""
    try:
        # 檢查基本參數
        if not request.target_config:
            raise HTTPException(status_code=400, detail="目標配置不能為空")
        
        if not request.objectives:
            raise HTTPException(status_code=400, detail="攻擊目標不能為空")
        
        if not request.attack_generator:
            raise HTTPException(status_code=400, detail="請選擇攻擊生成模型")
        
        if not request.scoring_model:
            raise HTTPException(status_code=400, detail="請選擇評分模型")

        # 提取配置信息
        target_config = request.target_config
        endpoint = target_config.get('endpoint')
        
        if not endpoint:
            raise HTTPException(status_code=400, detail="目標端點不能為空")
        
        print(f"\n{'='*60}")
        print(f"🚀 開始真正的PyRIT攻擊")
        print(f"{'='*60}")
        print(f"📊 攻擊配置:")
        print(f"   • 攻擊生成模型: {request.attack_generator}")
        print(f"   • 評分模型: {request.scoring_model}")
        print(f"   • 目標端點: {endpoint}")
        print(f"   • 攻擊類型: {request.attack_type}")
        print(f"   • 最大輪次: {request.max_turns}")
        print(f"   • 攻擊目標數量: {len(request.objectives)}")
        print(f"📋 攻擊目標列表:")
        for i, obj in enumerate(request.objectives, 1):
            print(f"   {i}. {obj}")
        print(f"🔧 目標配置:")
        print(f"   • API類型: {target_config.get('api_type', 'unknown')}")
        print(f"   • 端點: {endpoint}")
        if target_config.get('api_key'):
            print(f"   • API Key: {'*' * len(target_config.get('api_key', ''))}")
        print(f"{'='*60}\n")
        
        # 只使用真正的PyRIT攻擊，不允許備用機制
        attack_result = await orchestrator.run_real_attack(
            attack_generator=request.attack_generator,
            scoring_model=request.scoring_model,
            target_config=target_config,
            objectives=request.objectives,
            attack_type=request.attack_type,
            max_turns=request.max_turns
        )
        
        # 如果PyRIT失敗，直接報錯，不使用假的備用引擎
        if not attack_result.get("success"):
            error_msg = attack_result.get("error", "PyRIT攻擊執行失敗")
            print(f"❌ PyRIT攻擊失敗: {error_msg}")
            raise HTTPException(status_code=500, detail=f"PyRIT攻擊失敗: {error_msg}")
        
        return attack_result

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 攻擊執行錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    """獲取系統狀態"""
    return {
        "success": True,
        "status": "running",
        "pyrit_initialized": orchestrator.is_initialized
    }


@app.get("/api/objectives/categories")
async def get_objective_categories():
    """獲取攻擊目標分類"""
    try:
        categories = get_all_categories()
        return {
            "success": True,
            "categories": categories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/objectives/presets")
async def get_preset_objectives():
    """獲取預設攻擊目標"""
    try:
        objectives = get_all_objectives()
        return {
            "success": True,
            "objectives": [
                {
                    "id": obj.id,
                    "name": obj.name,
                    "description": obj.description,
                    "objectives": obj.objectives,
                    "category": obj.category
                }
                for obj in objectives
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategies")
async def get_attack_strategies():
    """獲取攻擊策略資訊"""
    try:
        strategies = get_strategy_info()
        return {
            "success": True,
            "strategies": strategies
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "message": "PyRIT API 運行正常"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
