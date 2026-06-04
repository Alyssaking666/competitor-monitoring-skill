"""
PR/新闻监测爬虫 v2.0
通过搜索引擎检索品牌PR新闻（替代Google CSE，无需额外API Key）
"""
import logging
import re
import requests
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PRScraper:
    """PR/新闻监测 - 搜索引擎模式"""

    def __init__(self, search_tool=None, config: Dict = None):
        self.search_tool = search_tool
        self.config = config or {}

    def search_news(self, brand_name: str,
                    product_keywords: List[str],
                    limit: int = 30) -> List[Dict]:
        """
        搜索品牌相关PR/新闻

        策略:
        1. "品牌名 press release"
        2. "品牌名 announces" / "品牌名 launches"
        3. "品牌名 news" / "品牌名 review"
        """
        all_news = []
        seen_urls = set()

        queries = [
            f"{brand_name} press release",
            f"{brand_name} announces OR launches",
            f"{brand_name} news OR review",
        ]

        # 添加产品关键词
        for kw in product_keywords[:2]:
            queries.append(f"{kw} press release OR news")

        for query in queries:
            logger.info(f"[PR] 搜索: {query}")

            if self.search_tool:
                try:
                    results = self.search_tool.search(query)
                    for r in results[:limit]:
                        url = r.get('url', r.get('link', ''))
                        if url in seen_urls:
                            continue
                        # 排除社媒平台
                        if any(d in url for d in ['instagram.com', 'tiktok.com',
                                                   'facebook.com', 'youtube.com',
                                                   'reddit.com', 'twitter.com',
                                                           'x.com']):
                            continue
                        seen_urls.add(url)

                        domain = ''
                        if '//' in url:
                            domain = url.split('//')[1].split('/')[0]

                        all_news.append({
                            'title': r.get('title', ''),
                            'url': url,
                            'snippet': r.get('snippet', r.get('text', '')),
                            'source': domain,
                            'media_tier': self._classify_media_tier(domain),
                            'media_type': self._classify_media_type(domain),
                            'publish_date': r.get('date', ''),
                            'source_type': 'search'
                        })
                except Exception as e:
                    logger.error(f"[PR] 搜索失败: {e}")
            else:
                logger.warning("[PR] 无搜索工具，使用DuckDuckGo HTML搜索降级...")
                try:
                    ddg_url = "https://html.duckduckgo.com/html/"
                    ddg_resp = requests.post(ddg_url, data={'q': query}, timeout=15)
                    ddg_resp.raise_for_status()

                    title_pattern = re.compile(r'class="result__a"[^>]*>(.*?)</a>', re.DOTALL)
                    url_pattern = re.compile(r'class="result__url"[^>]*>(.*?)</a>', re.DOTALL)
                    snippet_pattern = re.compile(r'class="result__snippet"[^>]*>(.*?)</[^>]+>', re.DOTALL)

                    titles = title_pattern.findall(ddg_resp.text)
                    urls = url_pattern.findall(ddg_resp.text)
                    snippets = snippet_pattern.findall(ddg_resp.text)

                    clean = lambda s: re.sub(r'<[^>]+>', '', s).strip()

                    for i in range(min(len(titles), limit)):
                        result_url = clean(urls[i]) if i < len(urls) else ''
                        if result_url and not result_url.startswith('http'):
                            result_url = f"https://duckduckgo.com{result_url}"
                        if result_url in seen_urls:
                            continue
                        if 'duckduckgo.com' in result_url:
                            continue
                        # 排除社媒平台
                        if any(d in result_url for d in ['instagram.com', 'tiktok.com',
                                                           'facebook.com', 'youtube.com',
                                                           'reddit.com', 'twitter.com',
                                                           'x.com']):
                            continue
                        seen_urls.add(result_url)

                        domain = ''
                        if '//' in result_url:
                            domain = result_url.split('//')[1].split('/')[0]

                        all_news.append({
                            'title': clean(titles[i]),
                            'url': result_url,
                            'snippet': clean(snippets[i]) if i < len(snippets) else '',
                            'source': domain,
                            'media_tier': self._classify_media_tier(domain),
                            'media_type': self._classify_media_type(domain),
                            'publish_date': '',
                            'source_type': 'duckduckgo_fallback'
                        })
                except Exception as e:
                    logger.error(f"[PR] DuckDuckGo降级失败: {e}")

        logger.info(f"[PR] ✅ {brand_name}: {len(all_news)} 条新闻")
        return all_news[:limit]

    def analyze_news(self, news: List[Dict]) -> Dict:
        """分析PR新闻数据"""
        if not news:
            return {
                'total_articles': 0,
                'media_distribution': {},
                'tier_distribution': {},
                'type_distribution': {},
                'focus_analysis': []
            }

        total = len(news)

        # 媒体分布
        media_distribution = {}
        tier_distribution = {'Tier 1': 0, 'Tier 2': 0, 'Tier 3': 0}
        type_distribution = {}

        for item in news:
            source = item.get('source', 'Unknown')
            media_distribution[source] = media_distribution.get(source, 0) + 1

            tier = item.get('media_tier', 'Tier 3')
            tier_distribution[tier] = tier_distribution.get(tier, 0) + 1

            mtype = item.get('media_type', '其他')
            type_distribution[mtype] = type_distribution.get(mtype, 0) + 1

        # 推广重点分析（基于关键词预分类，LLM可覆盖）
        all_text = ' '.join([n.get('title', '') + ' ' + n.get('snippet', '') for n in news]).lower()
        focus_keywords = {
            '新品发布': ['launch', 'new', 'announce', 'introduce', 'release'],
            '促销活动': ['sale', 'discount', 'deal', 'offer', 'coupon', 'promotion'],
            '产品评测': ['review', 'test', 'hands-on', 'rating', 'comparison'],
            '合作动态': ['partnership', 'collaborate', 'team up', 'joint'],
            '融资/扩张': ['funding', 'invest', 'raise', 'expand', 'growth'],
            '竞品横测': ['vs', 'versus', 'comparison', 'alternative', 'competitor']
        }

        focus_analysis = []
        for focus, keywords in focus_keywords.items():
            count = sum(1 for kw in keywords if kw in all_text)
            if count > 0:
                focus_analysis.append({
                    'focus': focus,
                    'mentions': count,
                    'percentage': round(count / total * 100, 1)
                })

        focus_analysis.sort(key=lambda x: x['mentions'], reverse=True)

        return {
            'total_articles': total,
            'media_distribution': dict(sorted(media_distribution.items(),
                                              key=lambda x: x[1], reverse=True)[:10]),
            'tier_distribution': tier_distribution,
            'type_distribution': type_distribution,
            'focus_analysis': focus_analysis[:5]
        }

    def _classify_media_tier(self, domain: str) -> str:
        """分类媒体层级"""
        if not domain:
            return 'Tier 3'

        tier1 = ['techcrunch.com', 'theverge.com', 'wired.com', 'engadget.com',
                 'cnn.com', 'bbc.com', 'reuters.com', 'forbes.com',
                 'bloomberg.com', 'wsj.com', 'nytimes.com', 'washingtonpost.com',
                 'businessinsider.com']

        tier2 = ['mashable.com', 'gizmodo.com', 'cnet.com', 'zdnet.com',
                 'venturebeat.com', 'fastcompany.com', 'inc.com',
                 'huffpost.com', 'usatoday.com', 'nbcnews.com']

        domain_lower = domain.lower()
        if any(t in domain_lower for t in tier1):
            return 'Tier 1'
        elif any(t in domain_lower for t in tier2):
            return 'Tier 2'
        else:
            return 'Tier 3'

    def _classify_media_type(self, domain: str) -> str:
        """分类媒体类型"""
        if not domain:
            return '垂直媒体'

        domain_lower = domain.lower()
        tech = ['techcrunch', 'theverge', 'wired', 'engadget', 'cnet', 'gizmodo', 'zdnet']
        business = ['forbes', 'bloomberg', 'wsj', 'businessinsider', 'fastcompany', 'venturebeat', 'inc']
        news = ['cnn', 'bbc', 'reuters', 'nytimes', 'washingtonpost', 'nbc', 'usa today', 'huffpost']
        lifestyle = ['well+good', 'mindbodygreen', 'healthline', 'webmd', 'prevention']

        if any(t in domain_lower for t in tech):
            return '科技媒体'
        elif any(t in domain_lower for t in business):
            return '商业媒体'
        elif any(t in domain_lower for t in news):
            return '综合新闻'
        elif any(t in domain_lower for t in lifestyle):
            return '生活/健康媒体'
        else:
            return '垂直媒体'
