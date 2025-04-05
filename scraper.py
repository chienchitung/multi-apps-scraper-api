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

def parse_apple_url(url: str) -> Tuple[str, str, str]:
    """解析 Apple Store URL"""
    try:
        # 解碼 URL
        decoded_url = urllib.parse.unquote(url, encoding='utf-8')
        
        # 更新正則表達式，捕捉 app_name
        pattern = r'apps\.apple\.com/(\w+)/app/(.*?)/id(\d+)'
        match = re.search(pattern, decoded_url)
        
        if not match:
            raise ValueError(f"Invalid Apple Store URL format: {url}")
            
        country_code = match.group(1)
        app_name = match.group(2)  # 提取 app_name
        app_id = match.group(3)
        
        # 不進行額外的 URL 編碼，保持原始形式
        return country_code, app_name, app_id
        
    except Exception as e:
        print(f"Error parsing Apple Store URL: {str(e)}")
        raise

def get_token(country: str, app_name: str, app_id: str) -> Optional[str]:
    """獲取 Apple Store API 的 token"""
    try:
        response = requests.get(
            f'https://apps.apple.com/{country}/app/{app_name}/id{app_id}',
            headers={'User-Agent': random.choice(user_agents)}
        )

        if response.status_code != 200:
            print(f"GET request failed. Response: {response.status_code} {response.reason}")
            return None

        tags = response.text.splitlines()
        token = None
        for tag in tags:
            if re.match(r"<meta.+web-experience-app/config/environment", tag):
                token_match = re.search(r"token%22%3A%22(.+?)%22", tag)
                if token_match:
                    token = token_match.group(1)
                    break

        if not token:
            print("無法找到 token")
            return None

        return token
    except Exception as e:
        print(f"Error getting token: {str(e)}")
        return None

def fetch_apple_reviews(country: str, app_name: str, app_id: str, token: str, offset: str = '1') -> tuple[list, Optional[str], int]:
    """獲取 App Store 評論"""
    try:
        # URL 編碼處理
        encoded_app_name = urllib.parse.quote(app_name)
        landing_url = f'https://apps.apple.com/{country}/app/{encoded_app_name}/id{app_id}'
        request_url = f'https://amp-api.apps.apple.com/v1/catalog/{country}/apps/{app_id}/reviews'

        headers = {
            'Accept': 'application/json',
            'Authorization': f'bearer {token}',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json; charset=utf-8',
            'Origin': 'https://apps.apple.com',
            'Referer': landing_url,
            'User-Agent': random.choice(user_agents)
        }

        params = {
            'l': 'zh-TW',
            'offset': str(offset),
            'limit': '20',
            'platform': 'web',
            'additionalPlatforms': 'appletv,ipad,iphone,mac'
        }

        retry_count = 0
        MAX_RETRIES = 5
        BASE_DELAY_SECS = 10

        while retry_count < MAX_RETRIES:
            try:
                response = requests.get(
                    request_url,
                    headers=headers,
                    params=params,
                    timeout=30
                )
                
                response.encoding = 'utf-8'  # 強制設定編碼為 UTF-8
                
                if response.status_code == 200:
                    result = response.json()
                    reviews = result.get('data', [])
                    
                    next_offset = None
                    if 'next' in result and result['next']:
                        next_match = re.search(r"^.+offset=([0-9]+).*$", result['next'])
                        if next_match:
                            next_offset = next_match.group(1)
                    
                    return reviews, next_offset, response.status_code
                    
                elif response.status_code == 429:
                    retry_count += 1
                    backoff_time = BASE_DELAY_SECS * retry_count
                    print(f"達到請求限制! 重試 ({retry_count}/{MAX_RETRIES}) 等待 {backoff_time} 秒...")
                    time.sleep(backoff_time)
                    continue
                    
                else:
                    print(f"請求失敗. 回應: {response.status_code} {response.reason}")
                    print(f"回應內容: {response.text[:200]}")  # 只印出前 200 個字元
                    return [], None, response.status_code

            except requests.exceptions.RequestException as e:
                retry_count += 1
                print(f"請求異常: {str(e)}, 重試 {retry_count}/{MAX_RETRIES}")
                if retry_count == MAX_RETRIES:
                    return [], None, 500
                time.sleep(BASE_DELAY_SECS)
                continue

        return [], None, 429
        
    except Exception as e:
        print(f"抓取 Apple 評論時發生錯誤: {str(e)}")
        print(f"錯誤詳情:\n{traceback.format_exc()}")
        return [], None, 500

def fetch_ios_reviews(url: str) -> List[dict]:
    try:
        print(f"開始抓取 iOS 評論，URL: {url}")
        country_code, app_name, app_id = parse_apple_url(url)
        
        print(f"正在取得 token，參數: {country_code}/{app_name}/{app_id}")
        token = get_token(country_code, app_name, app_id)
        if not token:
            print("取得 token 失敗")
            return []
        
        print("成功取得 token")
        all_reviews = []
        offset = '1'
        REVIEWS_FETCH_COUNT = 150  # 抓取 150 筆評論
        REVIEWS_RETURN_COUNT = 50  # 但只返回 50 筆
        
        while offset and len(all_reviews) < REVIEWS_FETCH_COUNT:
            print(f"正在抓取評論，offset: {offset}")
            reviews, next_offset, status_code = fetch_apple_reviews(
                country_code, app_name, app_id, token, offset
            )
            
            if status_code != 200:
                print(f"收到非 200 狀態碼: {status_code}")
                break
                
            processed_reviews = [{
                'date': datetime.strptime(review.get('attributes', {}).get('date', ''), '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d'),
                'username': review.get('attributes', {}).get('userName', ''),
                'review': review.get('attributes', {}).get('review', ''),
                'rating': review.get('attributes', {}).get('rating', 0),
                'platform': 'iOS',
                'developerResponse': review.get('attributes', {}).get('developerResponse', {}).get('body', ''),
                'language': detect_language(review.get('attributes', {}).get('review', '')),
                'app_id': app_id
            } for review in reviews]
            
            remaining_slots = REVIEWS_FETCH_COUNT - len(all_reviews)
            processed_reviews = processed_reviews[:remaining_slots]
            
            print(f"已處理 {len(processed_reviews)} 筆評論")
            all_reviews.extend(processed_reviews)
            
            if len(all_reviews) >= REVIEWS_FETCH_COUNT:
                break
                
            offset = next_offset
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