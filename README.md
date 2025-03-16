# Multi-Apps Reviews Scraper API

多平台應用程式評論抓取 API 服務，支援同時抓取 App Store 和 Google Play 的應用程式評論。

## 目錄

- [功能特點](#功能特點)
- [系統需求](#系統需求)
- [快速開始](#快速開始)
  - [使用 Docker Compose](#使用-docker-compose)
  - [使用 Docker](#使用-docker)
  - [使用 Python 虛擬環境](#使用-python-虛擬環境)
- [API 文件](#api-文件)
  - [抓取評論 API](#抓取評論-api)
- [部署指南](#部署指南)
- [開發指南](#開發指南)
- [注意事項](#注意事項)

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

## 快速開始

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

### 使用 Docker

```bash
# 建立映像檔
docker build -t app-reviews-scraper .

# 執行容器
docker run -p 8000:8000 app-reviews-scraper
```

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

# 啟動服務
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API 文件

### 抓取評論 API

**端點：** `/scrape`  
**方法：** POST  
**Content-Type：** application/json

**請求格式：**
```json
{
  "apple_store_urls": [
    "https://apps.apple.com/tw/app/id123456789",
    "https://apps.apple.com/tw/app/id987654321"
  ],
  "google_play_urls": [
    "https://play.google.com/store/apps/details?id=com.example.app1",
    "https://play.google.com/store/apps/details?id=com.example.app2"
  ]
}
```

**使用範例：**

使用 curl：
```bash
curl -X 'POST' \
  'http://localhost:8000/scrape' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "appleStore": [
        "https://apps.apple.com/tw/app/ikea%E5%8F%B0%E7%81%A3/id1631350301",
        "https://apps.apple.com/tw/app/%E7%89%B9%E5%8A%9B%E5%B1%8B-%E8%87%AA%E7%B5%84%E6%A8%82%E8%B6%A3-%E8%87%AA%E9%80%A0%E7%BE%8E%E5%A5%BD/id1403339648",
        "https://apps.apple.com/tw/app/nitori-%E5%AE%9C%E5%BE%97%E5%88%A9%E5%AE%B6%E5%B1%85-tw/id1595994449"
  ],
  "googlePlay": [
        "https://play.google.com/store/apps/details?id=tw.com.nitori.points&hl=zh_TW",
        "https://play.google.com/store/apps/details?id=tw.com.ikea.android&hl=zh_TW",
        "https://play.google.com/store/apps/details?id=com.testritegroup.crm.loyaltyapp&hl=zh_TW"
  ]
}'
```

使用 Python requests：
```python
import requests
import json

url = "http://localhost:8000/scrape"
data = {
    "appleStore": ["https://apps.apple.com/tw/app/id123456789"],
    "googlePlay": ["https://play.google.com/store/apps/details?id=com.example.app"]
}

response = requests.post(url, json=data)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
```

**回應格式：**
```json
{
  "results": [
    {
      "app_id": "123456789",
      "platform": "ios",
      "reviews": [
        {
          "review_id": "12345",
          "rating": 5,
          "title": "很棒的應用",
          "content": "使用體驗非常好",
          "author": "使用者名稱",
          "date": "2024-03-16",
          "developer_response": "感謝您的評論",
          "developer_response_date": "2024-03-17"
        }
      ]
    }
  ]
}
```

## 部署指南

### Railway 部署

1. Fork 此專案到您的 GitHub
2. 在 Railway 中連接您的 GitHub 帳號
3. 選擇此專案進行部署
4. 環境變數設定：
   - `PORT`: 設定服務埠口（預設 8000）

### 其他平台部署

支援任何可以運行 Docker 容器的平台，如：
- Heroku
- Google Cloud Run
- AWS ECS

## 開發指南

1. Clone 專案：
```bash
git clone https://github.com/yourusername/multi-apps-scraper-api.git
cd app-reviews-scraper
```

2. 安裝開發依賴：
```bash
pip install -r requirements.txt
```

3. 啟動開發伺服器：
```bash
uvicorn main:app --reload
```

## 注意事項

- 評論抓取限制：每個應用程式最多抓取 100 筆評論（iOS 和 Android 各 50 筆）
- 評論排序：依照日期從新到舊排序
- 錯誤處理：API 會回傳適當的錯誤訊息和 HTTP 狀態碼
- 建議使用：建議在正式環境中使用 Docker Compose 部署

## 授權

本專案採用 MIT 授權條款。 