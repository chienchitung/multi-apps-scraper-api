from typing import List, Optional, Tuple
from datetime import datetime
import re
import os
from google_play_scraper import reviews, Sort
import emoji
from langdetect import detect, LangDetectException
import requests
import json
import time
from tqdm import tqdm
import urllib.parse
import traceback

SERPAPI_KEY = os.getenv('SERPAPI_KEY')
SERPAPI_URL = 'https://serpapi.com/search.json'
MAX_PAGES = 10  # 最大抓取頁數，也作為 total_page_count 缺失時的預設值

def detect_language(text):
    if not text or not isinstance(text, str):
        return 'unknown'
    
    text = emoji.replace_emoji(text, replace='')
    
    # 檢查中文字符
    if re.search(r'[\u4e00-\u9fff]', text):
        return 'zh'
    
    # 新增：檢查文本是否只包含英文字母、數字和常見標點
    if re.match(r'^[a-zA-Z0-9\s\.,!?\'"-]+$', text):
        return 'en'
    
    # 如果上述條件都不符合，才使用 langdetect
    try:
        lang = detect(text)
        return 'en' if lang == 'en' else 'unknown'
    except LangDetectException:
        return 'unknown'

def parse_apple_url(url: str) -> Tuple[str, str]:
    """解析 Apple Store URL，取得國家代碼與 App ID"""
    try:
        # 解碼 URL
        decoded_url = urllib.parse.unquote(url, encoding='utf-8')

        pattern = r'apps\.apple\.com/(\w+)/app/[^/]+/id(\d+)'
        match = re.search(pattern, decoded_url)

        if not match:
            raise ValueError(f"Invalid Apple Store URL format: {url}")

        country_code = match.group(1)
        app_id = match.group(2)

        return country_code, app_id

    except Exception as e:
        print(f"Error parsing Apple Store URL: {str(e)}")
        raise

def fetch_apple_reviews_page(country: str, app_id: str, page_num: int) -> tuple:
    """透過 SerpApi Apple Reviews Engine 取得單頁 App Store 評論"""
    if not SERPAPI_KEY:
        print("未設定 SERPAPI_KEY 環境變數，無法抓取 App Store 評論")
        return [], 0

    params = {
        'engine': 'apple_reviews',
        'product_id': app_id,
        'country': country,
        'page': page_num,
        'api_key': SERPAPI_KEY
    }

    try:
        response = requests.get(SERPAPI_URL, params=params, timeout=30)

        if response.status_code != 200:
            print(f"第 {page_num} 頁請求失敗：狀態碼 {response.status_code}")
            return [], 0

        data = response.json()
        total_pages = data.get('search_information', {}).get('total_page_count', MAX_PAGES)
        return data.get('reviews', []), total_pages

    except Exception as e:
        print(f"抓取第 {page_num} 頁時發生錯誤：{e}")
        return [], 0

def parse_apple_review_date(date_str: str) -> Optional[str]:
    """解析 SerpApi 回傳的評論日期（例如「2023年02月24日」），轉為 %Y-%m-%d"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y年%m月%d日').strftime('%Y-%m-%d')
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(date_str).strftime('%Y-%m-%d')
    except ValueError:
        return None

def fetch_ios_reviews(url: str) -> List[dict]:
    try:
        print(f"開始抓取 iOS 評論，URL: {url}")
        country_code, app_id = parse_apple_url(url)

        all_reviews = []
        REVIEWS_PER_PLATFORM = 150  # 每個平台抓取 150 則評論

        for page_num in range(1, MAX_PAGES + 1):
            if len(all_reviews) >= REVIEWS_PER_PLATFORM:
                break

            print(f"正在抓取第 {page_num} 頁評論")
            entries, total_pages = fetch_apple_reviews_page(country_code, app_id, page_num)

            if not entries:
                print(f"第 {page_num} 頁無評論，停止抓取")
                break

            for entry in entries:
                review_date = parse_apple_review_date(entry.get('review_date', ''))
                if not review_date:
                    continue

                review_text = entry.get('text', '')
                raw_version = entry.get('reviewed_version', '') or ''
                developer_response = entry.get('developer_response')

                all_reviews.append({
                    'date': review_date,
                    'username': entry.get('author', {}).get('name', ''),
                    'review': review_text,
                    'rating': int(entry.get('rating', 0) or 0),
                    'platform': 'iOS',
                    'developerResponse': developer_response.get('body', '') if developer_response else '',
                    'language': detect_language(review_text),
                    'appVersion': re.sub(r'^版本\s*', '', raw_version),
                    'app_id': app_id
                })

            print(f"已處理累計 {len(all_reviews)} 筆評論")

            if page_num >= total_pages:
                print("已抓取所有頁面")
                break

        # 按日期排序（從新到舊）
        all_reviews.sort(key=lambda x: x['date'], reverse=True)

        # 只返回前 150 筆最新評論
        final_reviews = all_reviews[:REVIEWS_PER_PLATFORM]

        print(f"iOS 評論收集完成，共抓取 {len(all_reviews)} 筆，返回 {len(final_reviews)} 筆最新評論")
        return final_reviews

    except Exception as e:
        print(f"抓取 iOS 評論時發生錯誤: {str(e)}")
        print(f"錯誤詳情:\n{traceback.format_exc()}")
        return []

def parse_android_url(url: str) -> str:
    """解析 Google Play URL"""
    try:
        pattern = r'id=([^&]+)'
        match = re.search(pattern, url)
        if not match:
            raise ValueError(f"Invalid Google Play URL format: {url}")
        return match.group(1)
    except Exception as e:
        print(f"Error parsing Google Play URL: {str(e)}")
        raise

def fetch_android_reviews(url: str) -> List[dict]:
    try:
        REVIEWS_PER_PLATFORM = 150  # 每個平台抓取 150 則評論
        reviews_per_language = REVIEWS_PER_PLATFORM

        app_id = parse_android_url(url)
        print(f"開始抓取 Android 評論，應用程式 ID: {app_id}")
        
        all_reviews = []
        
        # 取得中文評論
        print("正在抓取中文評論...")
        try:
            reviews_zh, continuation_token_zh = reviews(
                app_id,
                lang='zh_TW',
                country='tw',
                sort=Sort.NEWEST,
                count=reviews_per_language,
                filter_score_with=None
            )
            
            for review in reviews_zh:
                review_data = {
                    'date': review['at'].strftime('%Y-%m-%d'),
                    'username': review['userName'],
                    'review': review['content'],
                    'rating': review['score'],
                    'platform': 'Android',
                    'developerResponse': review.get('replyContent', ''),
                    'language': detect_language(review['content']),
                    'appVersion': review.get('appVersion', ''),
                    'app_id': app_id
                }
                all_reviews.append(review_data)
            
            # 取得英文評論
            print("正在抓取英文評論...")
            reviews_en, continuation_token_en = reviews(
                app_id,
                lang='en',
                country='tw',
                sort=Sort.NEWEST,
                count=reviews_per_language,
                filter_score_with=None
            )
            
            for review in reviews_en:
                review_data = {
                    'date': review['at'].strftime('%Y-%m-%d'),
                    'username': review['userName'],
                    'review': review['content'],
                    'rating': review['score'],
                    'platform': 'Android',
                    'developerResponse': review.get('replyContent', ''),
                    'language': detect_language(review['content']),
                    'appVersion': review.get('appVersion', ''),
                    'app_id': app_id
                }
                all_reviews.append(review_data)
            
            # 按日期排序（從新到舊）
            all_reviews.sort(key=lambda x: x['date'], reverse=True)

            # 只返回前 150 筆最新評論
            final_reviews = all_reviews[:REVIEWS_PER_PLATFORM]

            print(f"Android 評論收集完成，共抓取 {len(all_reviews)} 筆，返回 {len(final_reviews)} 筆最新評論")
            return final_reviews
            
        except Exception as e:
            print(f"抓取評論時發生錯誤: {str(e)}")
            print(f"錯誤詳情:\n{traceback.format_exc()}")
            return []
            
    except Exception as e:
        print(f"抓取 Android 評論時發生錯誤: {str(e)}")
        print(f"錯誤詳情:\n{traceback.format_exc()}")
        return []