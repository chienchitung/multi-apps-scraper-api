from typing import List, Optional, Tuple
from datetime import datetime
import re
from google_play_scraper import reviews, Sort
import emoji
from langdetect import detect, LangDetectException
import requests
import json
import random
import time
from tqdm import tqdm
import urllib.parse
import traceback

# 定義 User-Agents
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
]

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

def fetch_apple_reviews_page(country: str, app_id: str, page: int) -> list:
    """透過 iTunes RSS Feed 取得單頁 App Store 評論"""
    url = (f"https://itunes.apple.com/{country}/rss/customerreviews/"
           f"page={page}/id={app_id}/sortBy=mostRecent/json")

    retry_count = 0
    MAX_RETRIES = 3
    BASE_DELAY_SECS = 5

    while retry_count < MAX_RETRIES:
        try:
            response = requests.get(
                url,
                headers={'User-Agent': random.choice(user_agents)},
                timeout=30
            )

            response.encoding = 'utf-8'  # 強制設定編碼為 UTF-8

            if response.status_code == 200:
                data = response.json()
                entries = data.get('feed', {}).get('entry', [])
                # RSS Feed 內若無評分欄位代表非評論項目，需濾除
                return [entry for entry in entries if 'im:rating' in entry]

            elif response.status_code == 429:
                retry_count += 1
                backoff_time = BASE_DELAY_SECS * retry_count
                print(f"達到請求限制! 重試 ({retry_count}/{MAX_RETRIES}) 等待 {backoff_time} 秒...")
                time.sleep(backoff_time)
                continue

            else:
                print(f"無法從第 {page} 頁抓取資料：狀態碼 {response.status_code}")
                print(f"回應內容: {response.text[:200]}")  # 只印出前 200 個字元
                return []

        except requests.exceptions.RequestException as e:
            retry_count += 1
            print(f"請求異常: {str(e)}, 重試 {retry_count}/{MAX_RETRIES}")
            if retry_count == MAX_RETRIES:
                return []
            time.sleep(BASE_DELAY_SECS)
            continue

    return []

def fetch_ios_reviews(url: str) -> List[dict]:
    try:
        print(f"開始抓取 iOS 評論，URL: {url}")
        country_code, app_id = parse_apple_url(url)

        all_reviews = []
        REVIEWS_FETCH_COUNT = 150  # 抓取 150 筆評論
        REVIEWS_RETURN_COUNT = 50  # 但只返回 50 筆
        MAX_PAGES = 10  # App Store RSS Feed 最多提供約 10 頁評論

        for page in range(1, MAX_PAGES + 1):
            if len(all_reviews) >= REVIEWS_FETCH_COUNT:
                break

            print(f"正在抓取第 {page} 頁評論")
            entries = fetch_apple_reviews_page(country_code, app_id, page)

            if not entries:
                print(f"第 {page} 頁已無評論，停止抓取")
                break

            for entry in entries:
                updated_label = entry.get('updated', {}).get('label')
                if not updated_label:
                    continue
                try:
                    review_date = datetime.strptime(
                        updated_label, '%Y-%m-%dT%H:%M:%S%z'
                    ).strftime('%Y-%m-%d')
                except ValueError:
                    continue

                review_text = entry.get('content', {}).get('label', '')
                all_reviews.append({
                    'date': review_date,
                    'username': entry.get('author', {}).get('name', {}).get('label', ''),
                    'review': review_text,
                    'rating': int(entry.get('im:rating', {}).get('label', 0) or 0),
                    'platform': 'iOS',
                    'developerResponse': '',
                    'language': detect_language(review_text),
                    'app_id': app_id
                })

                if len(all_reviews) >= REVIEWS_FETCH_COUNT:
                    break

            print(f"已處理累計 {len(all_reviews)} 筆評論")

            if len(all_reviews) >= REVIEWS_FETCH_COUNT:
                break

            time.sleep(0.5)

        # 按日期排序（從新到舊）
        all_reviews.sort(key=lambda x: x['date'], reverse=True)

        # 只返回前 50 筆最新評論
        final_reviews = all_reviews[:REVIEWS_RETURN_COUNT]

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
        REVIEWS_FETCH_COUNT = 150  # 抓取 150 筆評論
        REVIEWS_RETURN_COUNT = 50  # 但只返回 50 筆
        reviews_per_language = REVIEWS_FETCH_COUNT // 2  # 中英文各取一半
        
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
                    'app_id': app_id
                }
                all_reviews.append(review_data)
            
            # 按日期排序（從新到舊）
            all_reviews.sort(key=lambda x: x['date'], reverse=True)
            
            # 只返回前 50 筆最新評論
            final_reviews = all_reviews[:REVIEWS_RETURN_COUNT]
            
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