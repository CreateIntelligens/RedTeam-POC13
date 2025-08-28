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
from pyrit_frontend.core.preset_objectives import get_all_categories, get_all_objectives, get_strategy_info
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
    generator_model: str
    target_endpoint: str


class AttackRequest(BaseModel):
    attack_generator: str
    scoring_model: str
    target_endpoint: str
    objectives: List[str]
    max_turns: int = 5
    attack_type: str = "crescendo"


@app.get("/")
async def read_index():
    """返回主頁面"""
    return FileResponse('/workspace/pyrit/pyrit_frontend/frontend/templates/index.html')


@app.get("/api/models", response_model=Dict[str, Any])
async def get_available_models():
    """獲取可用的模型列表"""
    try:
        models = []
        for model in settings.available_models:
            models.append(ModelResponse(
                name=model.name,
                type=model.type,
                model_name=model.model_name
            ))

        return {
            "success": True,
            "models": [model.dict() for model in models]
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
        
        # 準備測試訊息
        test_message = "Hello, this is a test message from PyRIT."
        
        start_time = time.time()
        
        # 發送簡單的POST請求到目標端點
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                request.target_endpoint,
                json={"message": test_message},
                headers={"Content-Type": "application/json"}
            )
        
        end_time = time.time()
        latency = round((end_time - start_time) * 1000)  # 毫秒
        
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


@app.post("/api/attack")
async def run_attack(request: AttackRequest):
    """執行攻擊"""
    try:
        # 檢查基本參數
        if not request.target_endpoint:
            raise HTTPException(status_code=400, detail="目標端點不能為空")
        
        if not request.objectives:
            raise HTTPException(status_code=400, detail="攻擊目標不能為空")

        # 使用簡單攻擊引擎執行攻擊
        result = await simple_attacker.run_simple_attack(
            target_endpoint=request.target_endpoint,
            objectives=request.objectives,
            attack_type=request.attack_type,
            max_turns=request.max_turns
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    """獲取系統狀態"""
    return {
        "success": True,
        "status": "running",
        "available_models": len(settings.available_models),
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
