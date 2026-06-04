"""
PR/新闻监测爬虫
使用Google Custom Search API (免费额度100次/天)
注册地址: https://developers.google.com/custom-search/v1/overview
"""

import requests
import time
from datetime import datetime
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PRScraper:
    """PR/新闻监测爬虫"""
    
    BASE_URL = "https://www.googleapis.com/customsearch/v1"
    
    def __init__(self, api_key: str, cx: str):
        """
        初始化
        
        Args:
            api_key: Google API Key
            cx: Custom Search Engine ID
        """
        self.api_key = api_key
        self.cx = cx
        self.session = requests.Session()
    
    def search_news(self, 
                    brand_name: str,
                    product_keywords: List[str],
                    start_date: str,
                    end_date: str,
                    limit: int = 50) -> List[Dict]:
        """
        搜索品牌相关新闻/PR
        
        Args:
            brand_name: 品牌名称
            product_keywords: 产品关键词
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            limit: 获取数量
            
        Returns:
            新闻列表
        """
        all_news = []
        search_terms = [brand_name] + product_keywords[:3]  # 限制关键词数量
        
        for term in search_terms:
            logger.info(f"搜索新闻: {term}")
            news = self._search_by_term(term, start_date, end_date, limit // len(search_terms))
            all_news.extend(news)
            time.sleep(1)  # 请求间隔
        
        # 去重
        seen_urls = set()
        unique_news = []
        for item in all_news:
            url = item.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_news.append(item)
        
        logger.info(f"共获取 {len(unique_news)} 条唯一新闻")
        return unique_news[:limit]
    
    def _search_by_term(self, 
                        term: str, 
                        start_date: str, 
                        end_date: str,
                        limit: int) -> List[Dict]:
        """根据关键词搜索新闻"""
        news = []
        start_index = 1
        
        while len(news) < limit and start_index <= 100:  # Google CSE限制
            params = {
                'key': self.api_key,
                'cx': self.cx,
                'q': term,
                'sort': 'date',  # 按日期排序
                'dateRestrict': f"{start_date}:{end_date}",
                'start': start_index,
                'num': min(10, limit - len(news))
            }
            
            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if 'error' in data:
                    logger.error(f"API错误: {data['error']}")
                    break
                
                items = data.get('items', [])
                if not items:
                    break
                
                for item in items:
                    news_item = {
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'source': item.get('displayLink', ''),
                        'published_date': item.get('pagemap', {}).get('metatags', [{}])[0].get('article:published_time', ''),
                        'media_tier': self._classify_media_tier(item.get('displayLink', '')),
                        'media_type': self._classify_media_type(item.get('displayLink', ''))
                    }
                    news.append(news_item)
                
                # 分页
                start_index += len(items)
                
                # 检查是否有更多结果
                if len(items) < 10:
                    break
                
                time.sleep(0.5)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"请求失败: {e}")
                break
        
        return news[:limit]
    
    def _classify_media_tier(self, domain: str) -> str:
        """分类媒体层级"""
        tier1_domains = [
            'techcrunch.com', 'theverge.com', 'wired.com', 'engadget.com',
            'cnn.com', 'bbc.com', 'reuters.com', 'forbes.com',
            'bloomberg.com', 'wsj.com', 'nytimes.com', 'washingtonpost.com'
        ]
        
        tier2_domains = [
            'mashable.com', 'gizmodo.com', 'cnet.com', 'zdnet.com',
            'venturebeat.com', 'businessinsider.com', 'fastcompany.com'
        ]
        
        domain_lower = domain.lower()
        
        if any(tier1 in domain_lower for tier1 in tier1_domains):
            return 'Tier 1'
        elif any(tier2 in domain_lower for tier2 in tier2_domains):
            return 'Tier 2'
        else:
            return 'Tier 3'
    
    def _classify_media_type(self, domain: str) -> str:
        """分类媒体类型"""
        domain_lower = domain.lower()
        
        tech_sites = ['techcrunch', 'theverge', 'wired', 'engadget', 'cnet', 'gizmodo', 'zdnet']
        business_sites = ['forbes', 'bloomberg', 'wsj', 'businessinsider', 'fastcompany', 'venturebeat']
        news_sites = ['cnn', 'bbc', 'reuters', 'nytimes', 'washingtonpost']
        
        if any(site in domain_lower for site in tech_sites):
            return '科技媒体'
        elif any(site in domain_lower for site in business_sites):
            return '商业媒体'
        elif any(site in domain_lower for site in news_sites):
            return '新闻媒体'
        else:
            return '垂直媒体'
    
    def analyze_news(self, news: List[Dict]) -> Dict:
        """
        分析新闻数据
        
        Returns:
            分析结果
        """
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
        
        all_text = ''
        
        for item in news:
            # 媒体分布
            source = item.get('source', 'Unknown')
            media_distribution[source] = media_distribution.get(source, 0) + 1
            
            # 层级分布
            tier = item.get('media_tier', 'Tier 3')
            tier_distribution[tier] = tier_distribution.get(tier, 0) + 1
            
            # 类型分布
            media_type = item.get('media_type', '其他')
            type_distribution[media_type] = type_distribution.get(media_type, 0) + 1
            
            # 收集文本用于分析
            all_text += item.get('title', '') + ' ' + item.get('snippet', '') + ' '
        
        # 推广重点分析（基于关键词）
        focus_keywords = {
            '新品发布': ['launch', 'new', 'announce', 'introduce', 'release', '新品', '发布'],
            '融资动态': ['funding', 'invest', 'raise', 'million', '融资', '投资'],
            '产品评测': ['review', 'test', 'hands-on', '评测', '测评'],
            '合作动态': ['partnership', 'collaborate', 'team up', '合作'],
            '获奖荣誉': ['award', 'win', 'prize', '荣誉', '获奖'],
            '市场扩张': ['expand', 'market', 'growth', '扩张', '市场']
        }
        
        focus_analysis = []
        all_text_lower = all_text.lower()
        
        for focus, keywords in focus_keywords.items():
            count = sum(1 for kw in keywords if kw in all_text_lower)
            if count > 0:
                focus_analysis.append({
                    'focus': focus,
                    'mentions': count,
                    'percentage': round(count / total * 100, 2)
                })
        
        # 按提及次数排序
        focus_analysis.sort(key=lambda x: x['mentions'], reverse=True)
        
        return {
            'total_articles': total,
            'media_distribution': dict(sorted(media_distribution.items(), 
                                               key=lambda x: x[1], reverse=True)[:10]),
            'tier_distribution': tier_distribution,
            'type_distribution': type_distribution,
            'focus_analysis': focus_analysis[:5]
        }


if __name__ == "__main__":
    # 测试
    import json
    
    scraper = PRScraper(
        api_key="YOUR_GOOGLE_API_KEY",
        cx="YOUR_CUSTOM_SEARCH_ENGINE_ID"
    )
    
    news = scraper.search_news(
        brand_name="Apple",
        product_keywords=["iPhone", "MacBook"],
        start_date="2025-04-01",
        end_date="2025-05-31",
        limit=30
    )
    
    analysis = scraper.analyze_news(news)
    print(json.dumps(analysis, indent=2, ensure_ascii=False))