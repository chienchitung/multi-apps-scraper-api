from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from scraper import fetch_ios_reviews, fetch_android_reviews
import os
from typing import Optional
from datetime import datetime

app = FastAPI(
    title="Scraper API",
    description="API for scraping app reviews",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScrapeRequest(BaseModel):
    appleStore: list[str] = []
    googlePlay: list[str] = []

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/scrape")
async def scrape_reviews(request: ScrapeRequest):
    try:
        print(f"收到請求: {request}")
        all_reviews = {
            "ios": {},
            "android": {}
        }

        # 處理 iOS 評論
        for apple_url in request.appleStore:
            print(f"正在抓取 iOS 評論，來源: {apple_url}")
            ios_reviews = fetch_ios_reviews(apple_url)  # 已經按日期排序且限制為 50 筆
            all_reviews["ios"][apple_url] = ios_reviews
            print(f"找到 {len(ios_reviews)} 筆 iOS 評論")
        
        # 處理 Android 評論
        for android_url in request.googlePlay:
            print(f"正在抓取 Android 評論，來源: {android_url}")
            android_reviews = fetch_android_reviews(android_url)  # 已經按日期排序且限制為 50 筆
            all_reviews["android"][android_url] = android_reviews
            print(f"找到 {len(android_reviews)} 筆 Android 評論")

        result = {
            "success": True,
            "data": all_reviews
        }
        return result
    except Exception as e:
        print(f"評論抓取過程發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)