# MultiApps Reviews Scraper API

這是一個用於抓取 App Store 和 Google Play 應用程式評論的 API 服務。支援多個應用程式同時抓取，並提供統一的資料格式。

## 功能特點

- 支援同時抓取多個應用程式的評論
- 支援 App Store 和 Google Play 兩個平台
- 每個應用程式最多抓取 100 筆最新評論（iOS 和 Android 各 50 筆）
- 自動語言檢測（支援中文和英文）
- 評論依日期排序（從新到舊）
- 包含評分、開發者回覆等完整資訊

## 系統需求

- Python 3.9+
- Docker（選用）
- Docker Compose（選用）

## 安裝方式

### 使用 Python 虛擬環境

```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
```

### 使用 Docker

```bash
# 建立映像檔
docker build -t app-reviews-scraper .

# 執行容器
docker run -p 8000:8000 app-reviews-scraper
```

### 使用 Docker Compose（推薦）

```bash
# 啟動服務
docker-compose up -d

# 查看日誌
docker-compose logs -f

# 停止服務
docker-compose down

# 重新建立並啟動服務
docker-compose up -d --build
```

Docker Compose 配置特點：
- 自動重啟功能
- 健康檢查
- 資源限制
- 日誌輪替
- 容器命名
- 環境變數配置

## API 使用說明

### 評論抓取 API

**端點：** `/scrape`
**方法：** POST

**請求格式：**
```json
{
    "appleStore": [
        "https://apps.apple.com/tw/app/app-name/id1234567890",
        "https://apps.apple.com/tw/app/another-app/id0987654321"
    ],
    "googlePlay": [
        "https://play.google.com/store/apps/details?id=com.example.app",
        "https://play.google.com/store/apps/details?id=com.example.another"
    ]
}
```

**回應格式：**
```json
{
    "success": true,
    "data": {
        "ios": {
            "https://apps.apple.com/tw/app/app-name/id1234567890": [
                {
                    "date": "2024-03-20",
                    "username": "使用者名稱",
                    "review": "評論內容",
                    "rating": 5,
                    "platform": "iOS",
                    "developerResponse": "開發者回覆",
                    "language": "zh",
                    "app_id": "1234567890"
                }
            ]
        },
        "android": {
            "https://play.google.com/store/apps/details?id=com.example.app": [
                {
                    "date": "2024-03-20",
                    "username": "使用者名稱",
                    "review": "評論內容",
                    "rating": 5,
                    "platform": "Android",
                    "developerResponse": "開發者回覆",
                    "language": "zh",
                    "app_id": "com.example.app"
                }
            ]
        }
    }
}
```

## 本地開發

1. 啟動開發伺服器：
```bash
uvicorn main:app --reload
```

2. 訪問 API 文件：
```
http://localhost:8000/docs
```

## 部署說明

### Railway 部署

1. 確保專案根目錄包含以下檔案：
   - `railway.toml`
   - `requirements.txt`
   - `runtime.txt`
   - `Dockerfile`

2. 設定環境變數：
   - `PORT`: 應用程式埠號（預設：8000）

### 其他部署方式

支援任何可以執行 Docker 容器或 Python 應用程式的平台，如：
- Heroku
- Google Cloud Run
- AWS Elastic Beanstalk

## 注意事項

1. 評論抓取限制：
   - 每個應用程式最多抓取 100 筆評論
   - iOS 和 Android 各 50 筆
   - 評論按日期排序，只返回最新的評論

2. 錯誤處理：
   - API 會自動重試失敗的請求
   - 提供詳細的錯誤訊息
   - 單一應用程式失敗不影響其他應用程式的抓取

3. 速率限制：
   - 包含適當的請求延遲
   - 自動處理 429 (Too Many Requests) 錯誤

## 貢獻指南

1. Fork 專案
2. 建立功能分支
3. 提交變更
4. 發送 Pull Request

## 授權

MIT License 