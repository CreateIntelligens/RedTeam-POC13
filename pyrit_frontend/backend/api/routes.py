"""
PyRIT Frontend API 路由
提供 REST API 接口
"""

import asyncio
from typing import Dict, List, Any
from flask import Flask, request, jsonify
from flask_cors import CORS

from ..core.orchestrator_wrapper import OrchestratorWrapper
from ..config.settings import settings, ModelConfig, AttackConfig


app = Flask(__name__)
CORS(app)  # 允許跨域請求

# 全域攻擊包裝器
orchestrator = OrchestratorWrapper()


@app.route('/api/models', methods=['GET'])
def get_available_models():
    """獲取可用的模型列表"""
    try:
        models = []
        for model in settings.available_models:
            models.append({
                "name": model.name,
                "type": model.type,
                "model_name": model.model_name
            })
        
        return jsonify({
            "success": True,
            "models": models
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/models/add', methods=['POST'])
def add_custom_model():
    """添加自定義模型"""
    try:
        data = request.json
        
        config = ModelConfig(
            name=data['name'],
            type=data['type'],
            endpoint=data.get('endpoint'),
            api_key=data.get('api_key'),
            model_name=data.get('model_name'),
            headers=data.get('headers')
        )
        
        settings.add_custom_model(config)
        
        return jsonify({
            "success": True,
            "message": f"模型 {config.name} 已添加"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


@app.route('/api/test', methods=['POST'])
def test_connection():
    """測試連接"""
    try:
        data = request.json
        generator_name = data['generator_model']
        target_endpoint = data['target_endpoint']
        target_api_key = data['target_api_key']
        
        # 獲取生成器配置
        generator_config = settings.get_model_by_name(generator_name)
        if not generator_config:
            return jsonify({
                "success": False,
                "error": f"找不到模型: {generator_name}"
            }), 404
        
        # 執行異步測試
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            orchestrator.quick_test(generator_config, target_endpoint, target_api_key)
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/attack', methods=['POST'])
def run_attack():
    """執行攻擊"""
    try:
        data = request.json
        
        # 解析請求數據
        generator_name = data['attack_generator']
        scoring_name = data['scoring_model']
        target_endpoint = data['target_endpoint']
        target_api_key = data['target_api_key']
        target_model = data.get('target_model', 'gpt-3.5-turbo')
        objectives = data['objectives']
        
        # 攻擊配置
        attack_config = AttackConfig(
            max_turns=data.get('max_turns', 5),
            max_backtracks=data.get('max_backtracks', 2),
            attack_type=data.get('attack_type', 'crescendo')
        )
        
        # 獲取模型配置
        generator_config = settings.get_model_by_name(generator_name)
        scoring_config = settings.get_model_by_name(scoring_name)
        
        if not generator_config:
            return jsonify({
                "success": False,
                "error": f"找不到攻擊生成模型: {generator_name}"
            }), 404
            
        if not scoring_config:
            return jsonify({
                "success": False,
                "error": f"找不到評分模型: {scoring_name}"
            }), 404
        
        # 執行攻擊
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            orchestrator.run_attack(
                attack_generator_config=generator_config,
                scoring_config=scoring_config,
                target_endpoint=target_endpoint,
                target_api_key=target_api_key,
                target_model=target_model,
                objectives=objectives,
                attack_config=attack_config,
                target_headers=data.get('target_headers')
            )
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """獲取系統狀態"""
    return jsonify({
        "success": True,
        "status": "running",
        "available_models": len(settings.available_models),
        "pyrit_initialized": orchestrator.is_initialized
    })


@app.route('/', methods=['GET'])
def index():
    """主頁面"""
    with open('/home/human/PyRIT/pyrit_frontend/frontend/templates/index.html', 'r', encoding='utf-8') as f:
        return f.read()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)