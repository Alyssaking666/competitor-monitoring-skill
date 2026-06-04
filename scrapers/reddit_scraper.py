"""
Reddit 舆情爬虫 v2.0
通过搜索引擎检索Reddit帖文（替代PRAW，沙箱无需Reddit API凭证）
"""
import logging
import requests
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedditScraper:
    """Reddit舆情采集 - 搜索引擎模式"""

    def __init__(self, search_tool=None, config: Dict = None):
        """
        Args:
            search_tool: Coze搜索工具实例（Skill执行时注入）
            config: 采集配置
        """
        self.search_tool = search_tool
        self.config = config or {}

    def search_brand_mentions(self, brand_name: str,
                              product_keywords: List[str],
                              subreddits: List[str] = None,
                              limit: int = 30) -> List[Dict]:
        """
        搜索Reddit品牌提及

        策略:
        1. site:reddit.com + 品牌名 搜索
        2. 垂类subreddit内搜索品牌/产品关键词
        3. 每条结果提取: 标题、链接、摘要、subreddit

        Args:
            brand_name: 品牌名称
            product_keywords: 产品关键词
            subreddits: 垂类subreddit列表(可选)
            limit: 最大结果数
        """
        all_posts = []
        seen_urls = set()

        # 1. 全站搜索品牌名
        queries = [f"site:reddit.com {brand_name}"]

        # 2. 添加产品关键词搜索
        for kw in product_keywords[:3]:
            queries.append(f"site:reddit.com {kw}")

        # 3. 垂类subreddit搜索
        if subreddits:
            for sub in subreddits[:3]:
                queries.append(f"site:reddit.com/r/{sub} {brand_name}")

        for query in queries:
            logger.info(f"[Reddit] 搜索: {query}")

            if self.search_tool:
                try:
                    results = self.search_tool.search(query)
                    for r in results[:limit]:
                        url = r.get('url', r.get('link', ''))
                        if url in seen_urls:
                            continue
                        if 'reddit.com' not in url:
                            continue
                        seen_urls.add(url)

                        # 提取subreddit
                        subreddit = ''
                        if '/r/' in url:
                            parts = url.split('/r/')
                            if len(parts) > 1:
                                subreddit = parts[1].split('/')[0]

                        all_posts.append({
                            'title': r.get('title', ''),
                            'url': url,
                            'snippet': r.get('snippet', r.get('text', '')),
                            'subreddit': subreddit,
                            'source': 'search'
                        })
                except Exception as e:
                    logger.error(f"[Reddit] 搜索失败: {e}")
            else:
                logger.warning("[Reddit] 无搜索工具，使用Reddit公开JSON API降级...")
                try:
                    reddit_url = "https://www.reddit.com/search.json"
                    reddit_params = {
                        'q': query.replace('site:reddit.com ', ''),
                        'sort': 'new',
                        't': 'month',
                        'limit': min(limit, 50)
                    }
                    reddit_headers = {'User-Agent': 'CompetitorMonitor/2.0'}
                    reddit_resp = requests.get(reddit_url, params=reddit_params,
                                               headers=reddit_headers, timeout=15)
                    reddit_resp.raise_for_status()
                    reddit_data = reddit_resp.json()

                    children = reddit_data.get('data', {}).get('children', [])
                    for child in children[:limit]:
                        post = child.get('data', {})
                        post_url = f"https://www.reddit.com{post.get('permalink', '')}"
                        if post_url in seen_urls:
                            continue
                        seen_urls.add(post_url)

                        all_posts.append({
                            'title': post.get('title', ''),
                            'url': post_url,
                            'snippet': (post.get('selftext', '') or '')[:300],
                            'subreddit': post.get('subreddit', ''),
                            'author': post.get('author', ''),
                            'score': post.get('score', 0),
                            'num_comments': post.get('num_comments', 0),
                            'source': 'reddit_json_api'
                        })
                except Exception as e:
                    logger.error(f"[Reddit] JSON API降级失败: {e}")

        # 去重 & 截断
        logger.info(f"[Reddit] ✅ {brand_name}: {len(all_posts)} 条提及")
        return all_posts[:limit]

    def analyze_sentiment(self, posts: List[Dict]) -> Dict:
        """
        情感分析（LLM增强版）

        注意: 实际LLM分析在Skill执行层完成
        这里做基础统计
        """
        if not posts:
            return {
                'total_posts': 0,
                'positive': 0,
                'neutral': 0,
                'negative': 0,
                'positive_rate': 0,
                'negative_rate': 0,
                'neutral_rate': 0,
                'key_topics': [],
                'sentiment_note': 'LLM情感分析将在报告生成阶段执行'
            }

        # 基于关键词的快速预分类（LLM会在后续覆盖）
        positive_words = ['good', 'great', 'love', 'best', 'recommend', 'amazing',
                         'excellent', 'works', 'helped', 'happy', 'satisfied']
        negative_words = ['bad', 'terrible', 'worst', 'hate', 'problem', 'issue',
                         'broken', 'disappointed', 'return', 'refund', 'waste',
                         'doesn\'t work', 'stopped', 'side effect']

        positive = 0
        negative = 0
        neutral = 0

        for post in posts:
            text = (post.get('title', '') + ' ' + post.get('snippet', '')).lower()
            pos_count = sum(1 for w in positive_words if w in text)
            neg_count = sum(1 for w in negative_words if w in text)

            if pos_count > neg_count:
                positive += 1
            elif neg_count > pos_count:
                negative += 1
            else:
                neutral += 1

        total = len(posts)

        return {
            'total_posts': total,
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'positive_rate': round(positive / total * 100, 1),
            'negative_rate': round(negative / total * 100, 1),
            'neutral_rate': round(neutral / total * 100, 1),
            'key_topics': [],  # LLM填充
            'sentiment_note': '⚠️ 基于关键词预分类，LLM深度分析将在报告阶段执行'
        }
