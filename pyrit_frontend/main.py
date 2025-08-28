#!/usr/bin/env python3
"""
PyRIT Frontend 主啟動文件
"""

import sys
import os
import uvicorn

# 添加路徑
sys.path.insert(0, '/workspace/pyrit')
sys.path.insert(0, os.path.dirname(__file__))

from backend.api.fastapi_routes import app

if __name__ == "__main__":
    print("🚀 啟動 PyRIT 攻擊測試平台...")
    print("📡 API 文檔: http://localhost:8889/docs")
    print("🎯 主界面: http://localhost:8889")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8889,
        reload=False,  # 生產環境關閉
        log_level="info"
    )