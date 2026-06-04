"""
Apify API 共享客户端
封装Actor调用、结果轮询、降级逻辑
"""
import os
import time
import json
import logging
import requests
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ApifyClient:
    """Apify API 客户端，封装常用操作"""

    API_BASE = "https://api.apify.com/v2"

    def __init__(self, api_token: str = None):
        self.api_token = api_token or os.getenv("APIFY_API_TOKEN", "")
        if not self.api_token:
            logger.warning("⚠️ APIFY_API_TOKEN 未设置，将使用搜索降级模式")
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
        # 本次运行消耗追踪
        self.cost_tracker = {
            'actors_run': [],
            'total_results': 0,
            'estimated_cost_usd': 0.0
        }

    def run_actor(self, actor_id: str, run_input: Dict,
                  timeout: int = 300, poll_interval: int = 10,
                  max_results: int = None) -> List[Dict]:
        """
        运行Apify Actor并等待结果

        Args:
            actor_id: Actor ID，如 "apify/instagram-profile-scraper"
            run_input: Actor输入参数
            timeout: 最大等待时间(秒)
            poll_interval: 轮询间隔(秒)
            max_results: 最多返回结果数

        Returns:
            结果列表
        """
        if not self.api_token:
            logger.error(f"❌ 无APIFY_TOKEN，无法运行 {actor_id}")
            return []

        # 用~替换/用于API URL
        actor_path = actor_id.replace("/", "~")

        # 1. 启动Actor
        start_url = f"{self.API_BASE}/acts/{actor_path}/runs?token={self.api_token}"
        logger.info(f"🚀 启动Actor: {actor_id}")

        try:
            start_resp = self.session.post(start_url, json=run_input, timeout=30)
            start_resp.raise_for_status()
            run_data = start_resp.json().get('data', {})
            run_id = run_data.get('id')
            default_dataset_id = run_data.get('defaultDatasetId', '')

            if not run_id:
                logger.error(f"❌ Actor启动失败: 无run_id")
                return []

            logger.info(f"   Run ID: {run_id}, Dataset: {default_dataset_id}")

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Actor启动失败: {e}")
            return []

        # 2. 轮询等待完成
        status_url = f"{self.API_BASE}/acts/{actor_path}/runs/{run_id}?token={self.api_token}"
        elapsed = 0

        while elapsed < timeout:
            try:
                status_resp = self.session.get(status_url, timeout=30)
                status_data = status_resp.json().get('data', {})
                status = status_data.get('status', 'UNKNOWN')

                if status in ('SUCCEEDED', 'FINISHED'):
                    logger.info(f"✅ Actor完成: {actor_id}")
                    break
                elif status in ('FAILED', 'ABORTED', 'TIMED-OUT'):
                    logger.error(f"❌ Actor异常结束: {status}")
                    self.cost_tracker['actors_run'].append({
                        'actor': actor_id, 'status': status, 'run_id': run_id
                    })
                    return []
                else:
                    logger.info(f"   等待中... 状态: {status} ({elapsed}s/{timeout}s)")
                    time.sleep(poll_interval)
                    elapsed += poll_interval

            except requests.exceptions.RequestException as e:
                logger.error(f"❌ 轮询失败: {e}")
                time.sleep(poll_interval)
                elapsed += poll_interval

        if elapsed >= timeout:
            logger.error(f"❌ Actor超时: {actor_id}")
            return []

        # 3. 获取结果
        if not default_dataset_id:
            logger.error(f"❌ 无dataset ID")
            return []

        results_url = f"{self.API_BASE}/datasets/{default_dataset_id}/items?token={self.api_token}&clean=true"
        if max_results:
            results_url += f"&limit={max_results}"

        try:
            results_resp = self.session.get(results_url, timeout=60)
            results_resp.raise_for_status()
            items = results_resp.json()

            # 记录消耗
            self.cost_tracker['actors_run'].append({
                'actor': actor_id,
                'status': 'SUCCEEDED',
                'run_id': run_id,
                'results_count': len(items)
            })
            self.cost_tracker['total_results'] += len(items)

            logger.info(f"   获取到 {len(items)} 条结果")
            return items

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 获取结果失败: {e}")
            return []

    def get_cost_summary(self) -> Dict:
        """获取本次运行成本摘要"""
        return self.cost_tracker

    def verify_token(self) -> bool:
        """验证API Token是否有效"""
        if not self.api_token:
            return False
        try:
            url = f"{self.API_BASE}/users/me?token={self.api_token}"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                user_data = resp.json().get('data', {})
                logger.info(f"✅ Apify Token验证通过: {user_data.get('username', 'unknown')}")
                return True
            else:
                logger.error(f"❌ Apify Token验证失败: {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Token验证异常: {e}")
            return False


class SearchFallback:
    """搜索降级模式：当Apify不可用时使用免费公开API"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def search_reddit(self, brand_name: str, product_keywords: List[str],
                      limit: int = 20) -> List[Dict]:
        """搜索Reddit帖文（降级模式 - Reddit公开JSON API）"""
        results = []
        search_terms = [brand_name] + product_keywords[:3]

        for term in search_terms:
            try:
                url = "https://www.reddit.com/search.json"
                params = {
                    'q': term,
                    'sort': 'new',
                    't': 'month',
                    'limit': min(limit, 50)
                }
                headers = {'User-Agent': 'CompetitorMonitor/2.0'}
                resp = self.session.get(url, params=params, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                children = data.get('data', {}).get('children', [])
                for child in children[:limit]:
                    post = child.get('data', {})
                    results.append({
                        'source': 'reddit_json_api',
                        'title': post.get('title', ''),
                        'url': f"https://www.reddit.com{post.get('permalink', '')}",
                        'snippet': (post.get('selftext', '') or '')[:300],
                        'subreddit': post.get('subreddit', ''),
                        'author': post.get('author', ''),
                        'score': post.get('score', 0),
                        'num_comments': post.get('num_comments', 0),
                        'created_utc': post.get('created_utc', ''),
                        'term': term,
                        'note': 'Reddit公开JSON API降级模式'
                    })
            except Exception as e:
                logger.warning(f"[SearchFallback] Reddit搜索失败 ({term}): {e}")
                results.append({
                    'source': 'search_fallback',
                    'query': f"site:reddit.com {term}",
                    'term': term,
                    'error': str(e),
                    'note': '搜索降级模式，数据精度低于Apify'
                })

        return results

    def search_pr_news(self, brand_name: str, product_keywords: List[str],
                       limit: int = 20) -> List[Dict]:
        """搜索PR新闻（降级模式 - DuckDuckGo HTML搜索）"""
        results = []
        search_terms = [
            f"{brand_name} press release",
            f"{brand_name} announces",
            f"{brand_name} news"
        ]

        for term in search_terms:
            try:
                url = "https://html.duckduckgo.com/html/"
                params = {'q': term}
                resp = self.session.post(url, data=params, timeout=15)
                resp.raise_for_status()

                # 解析DuckDuckGo HTML结果
                import re
                title_pattern = re.compile(r'class="result__a"[^>]*>(.*?)</a>', re.DOTALL)
                url_pattern = re.compile(r'class="result__url"[^>]*>(.*?)</a>', re.DOTALL)
                snippet_pattern = re.compile(r'class="result__snippet"[^>]*>(.*?)</[^>]+>', re.DOTALL)

                titles = title_pattern.findall(resp.text)
                urls = url_pattern.findall(resp.text)
                snippets = snippet_pattern.findall(resp.text)

                # 清理HTML标签
                clean = lambda s: re.sub(r'<[^>]+>', '', s).strip()

                for i in range(min(len(titles), limit)):
                    result_url = clean(urls[i]) if i < len(urls) else ''
                    if result_url and not result_url.startswith('http'):
                        result_url = f"https://duckduckgo.com{result_url}"
                    if 'duckduckgo.com' in result_url:
                        continue

                    results.append({
                        'source': 'duckduckgo_fallback',
                        'title': clean(titles[i]),
                        'url': result_url,
                        'snippet': clean(snippets[i]) if i < len(snippets) else '',
                        'query': term,
                        'note': 'DuckDuckGo搜索降级模式'
                    })
            except Exception as e:
                logger.warning(f"[SearchFallback] PR新闻搜索失败 ({term}): {e}")
                results.append({
                    'source': 'search_fallback',
                    'query': term,
                    'error': str(e),
                    'note': '搜索降级模式'
                })

        return results

    def search_social_mentions(self, brand_name: str, platform: str,
                               limit: int = 20) -> List[Dict]:
        """搜索社媒提及（降级模式 - DuckDuckGo搜索）"""
        results = []
        query = f"{brand_name} site:{platform}.com"

        try:
            url = "https://html.duckduckgo.com/html/"
            params = {'q': query}
            resp = self.session.post(url, data=params, timeout=15)
            resp.raise_for_status()

            import re
            title_pattern = re.compile(r'class="result__a"[^>]*>(.*?)</a>', re.DOTALL)
            url_pattern = re.compile(r'class="result__url"[^>]*>(.*?)</a>', re.DOTALL)
            snippet_pattern = re.compile(r'class="result__snippet"[^>]*>(.*?)</[^>]+>', re.DOTALL)

            titles = title_pattern.findall(resp.text)
            urls = url_pattern.findall(resp.text)
            snippets = snippet_pattern.findall(resp.text)

            clean = lambda s: re.sub(r'<[^>]+>', '', s).strip()

            for i in range(min(len(titles), limit)):
                result_url = clean(urls[i]) if i < len(urls) else ''
                if result_url and not result_url.startswith('http'):
                    result_url = f"https://duckduckgo.com{result_url}"
                if 'duckduckgo.com' in result_url:
                    continue

                results.append({
                    'source': 'duckduckgo_fallback',
                    'title': clean(titles[i]),
                    'url': result_url,
                    'snippet': clean(snippets[i]) if i < len(snippets) else '',
                    'platform': platform,
                    'query': query,
                    'note': 'DuckDuckGo搜索降级模式，无法获取精确互动数据'
                })
        except Exception as e:
            logger.warning(f"[SearchFallback] 社媒搜索失败 ({platform}): {e}")
            results.append({
                'source': 'search_fallback',
                'query': query,
                'platform': platform,
                'error': str(e),
                'note': '搜索降级模式，无法获取精确互动数据'
            })

        return results
