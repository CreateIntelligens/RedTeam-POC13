# PyRIT Frontend - AI vs AI 攻擊測試平台

一個基於 PyRIT 框架的 Web 前端工具，讓你可以輕鬆配置和執行 AI 對抗測試。

## 🚀 特色功能

- **模型管理**: 支援 OpenAI、Gemini 和自定義 API
- **視覺化界面**: 直觀的 Web 界面，無需編程知識
- **靈活配置**: 可自由組合攻擊生成 AI 和評分 AI
- **多種攻擊策略**: 支援 Crescendo 等攻擊策略
- **結果分析**: 詳細的攻擊結果和對話記錄

## 📁 項目結構

```
pyrit_frontend/
├── backend/
│   ├── api/                 # FastAPI 路由
│   ├── core/               # 核心邏輯
│   │   ├── target_manager.py    # AI 目標管理
│   │   └── orchestrator_wrapper.py  # 攻擊編排器包裝
│   └── config/             # 配置管理
│       └── settings.py
├── frontend/
│   └── templates/          # HTML 界面
├── main.py                 # 啟動文件
├── requirements.txt        # 依賴列表
└── README.md
```

## 🛠️ 安裝和使用

### 1. 環境準備

確保你已經安裝了 PyRIT：
```bash
cd /workspace/pyrit
pip install -e .
```

### 2. 安裝前端依賴

```bash
cd pyrit_frontend
pip install -r requirements.txt
```

### 3. 配置環境變數

在 PyRIT 根目錄的 `.env` 文件中確保有以下配置：

```env
# OpenAI (用於攻擊生成和評分)
PLATFORM_OPENAI_CHAT_API_KEY="your-openai-api-key"
PLATFORM_OPENAI_CHAT_ENDPOINT="https://api.openai.com/v1/chat/completions"

# Gemini (可選)
GOOGLE_GEMINI_API_KEY="your-gemini-api-key"
```

### 4. 啟動服務

```bash
python main.py
```

### 5. 訪問界面

- **主界面**: http://localhost:8000
- **API 文檔**: http://localhost:8000/docs

## 🎯 使用方式

### 基本流程

1. **配置你的 AI**
   - 選擇攻擊生成模型（用於產生攻擊提示）
   - 選擇評分模型（用於評估攻擊成功率）

2. **設置攻擊目標**
   - 輸入外部 API 端點
   - 提供 API 金鑰
   - 指定目標模型名稱

3. **定義攻擊目標**
   - 添加你想測試的攻擊場景
   - 例如："讓 AI 洩露系統提示"

4. **執行攻擊**
   - 點擊開始攻擊
   - 系統會自動執行 AI vs AI 對抗

5. **分析結果**
   - 查看詳細的對話記錄
   - 檢查攻擊成功率評分

### 支援的 API 格式

- **OpenAI 兼容**: 支援 OpenAI ChatGPT API 格式
- **Google Gemini**: 原生支援 Gemini API
- **自定義 API**: 可擴展支援其他 API（需要適配）

## 🔧 高級配置

### 添加自定義模型

通過 API 或界面添加自定義模型：

```python
# API 調用範例
{
    "name": "My Custom AI",
    "type": "custom",
    "endpoint": "https://my-ai.com/v1/chat",
    "api_key": "my-api-key",
    "model_name": "my-model"
}
```

### 攻擊策略配置

- **max_turns**: 最大攻擊輪次 (1-10)
- **max_backtracks**: 最大回溯次數
- **attack_type**: 攻擊策略類型（目前支援 crescendo）

## 📊 實際應用場景

### 1. 競品分析
測試競爭對手的 AI 產品安全性

### 2. 安全評估
對自己部署的 AI 系統進行紅隊測試

### 3. 合規檢查
確保 AI 系統符合安全標準

### 4. 研究用途
學習和研究 AI 安全攻防技術

## 🚨 注意事項

1. **僅用於合法測試**: 只對你有權測試的 AI 系統使用
2. **API 成本**: 攻擊測試會消耗 API 調用次數
3. **速率限制**: 注意 API 的速率限制
4. **數據安全**: 測試過程中的對話會暫存在記憶體中

## 🔍 故障排除

### 常見問題

1. **連接測試失敗**
   - 檢查 API 端點和金鑰
   - 確認網路連接

2. **模型載入失敗**
   - 檢查環境變數設置
   - 確認 API 金鑰有效

3. **攻擊執行錯誤**
   - 查看詳細錯誤訊息
   - 檢查目標 API 是否正常

## 🤝 擴展開發

### 添加新的攻擊策略

在 `orchestrator_wrapper.py` 中擴展：

```python
elif config.attack_type == "new_strategy":
    # 實現新的攻擊策略
    pass
```

### 支援新的 API 格式

在 `target_manager.py` 中添加新的適配器。

## 📄 授權

本項目基於 PyRIT 框架，請遵循相關開源協議。