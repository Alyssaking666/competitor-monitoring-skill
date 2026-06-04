"""
Meta Ad Library 爬虫
无需API Key，直接调用公开接口
API文档: https://www.facebook.com/ads/library/api
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetaAdScraper:
    """Meta广告库爬虫"""
    
    BASE_URL = "https://graph.facebook.com/v18.0/ads_archive"
    
    def __init__(self, access_token: Optional[str] = None, country: str = "US"):
        self.access_token = access_token
        self.country = country
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_ads(self, 
                  search_terms: List[str],
                  start_date: str,
                  end_date: str,
                  limit: int = 100) -> List[Dict]:
        """
        获取广告数据
        
        Args:
            search_terms: 搜索关键词列表（品牌名、产品名）
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            limit: 每条关键词获取的广告数量
            
        Returns:
            广告数据列表
        """
        all_ads = []
        
        for term in search_terms:
            logger.info(f"正在搜索广告: {term}")
            ads = self._fetch_ads_by_term(term, start_date, end_date, limit)
            all_ads.extend(ads)
            time.sleep(2)  # 请求间隔
        
        # 去重
        seen_ids = set()
        unique_ads = []
        for ad in all_ads:
            ad_id = ad.get('id', '')
            if ad_id and ad_id not in seen_ids:
                seen_ids.add(ad_id)
                unique_ads.append(ad)
        
        logger.info(f"共获取 {len(unique_ads)} 条唯一广告")
        return unique_ads
    
    def _fetch_ads_by_term(self, 
                           term: str, 
                           start_date: str, 
                           end_date: str,
                           limit: int) -> List[Dict]:
        """根据关键词获取广告"""
        ads = []
        after = None
        
        while len(ads) < limit:
            params = {
                'search_terms': term,
                'ad_reached_countries': [self.country],
                'ad_delivery_date_min': start_date,
                'ad_delivery_date_max': end_date,
                'fields': 'id,ad_creation_time,ad_creative_bodies,ad_creative_link_captions,'
                          'ad_creative_link_descriptions,ad_creative_link_titles,'
                          'ad_delivery_start_time,ad_delivery_stop_time,'
                          'publisher_platforms,spend,impressions,'
                          'demographic_distribution,region_distribution',
                'limit': min(50, limit - len(ads))
            }
            
            if self.access_token:
                params['access_token'] = self.access_token
            
            if after:
                params['after'] = after
            
            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if 'error' in data:
                    logger.error(f"API错误: {data['error']}")
                    break
                
                batch_ads = data.get('data', [])
                if not batch_ads:
                    break
                
                ads.extend(batch_ads)
                
                # 分页
                paging = data.get('paging', {})
                cursors = paging.get('cursors', {})
                after = cursors.get('after')
                
                if not after:
                    break
                
                time.sleep(1)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"请求失败: {e}")
                break
        
        return ads[:limit]
    
    def analyze_ads(self, ads: List[Dict]) -> Dict:
        """
        分析广告数据
        
        Returns:
            分析结果
        """
        if not ads:
            return {
                'total_ads': 0,
                'new_ads': 0,
                'main_products': [],
                'creative_types': {},
                'platform_distribution': {},
                'ads_details': []
            }
        
        # 统计
        total_ads = len(ads)
        
        # 新广告（30天内创建）
        thirty_days_ago = datetime.now() - timedelta(days=30)
        new_ads = 0
        
        # 平台分布
        platform_distribution = {}
        
        # 创意类型
        creative_types = {'image': 0, 'video': 0, 'carousel': 0, 'other': 0}
        
        # 广告详情
        ads_details = []
        
        for ad in ads:
            # 检查是否新广告
            creation_time = ad.get('ad_creation_time', '')
            if creation_time:
                try:
                    ad_date = datetime.strptime(creation_time[:10], '%Y-%m-%d')
                    if ad_date >= thirty_days_ago:
                        new_ads += 1
                except:
                    pass
            
            # 平台分布
            platforms = ad.get('publisher_platforms', [])
            for platform in platforms:
                platform_distribution[platform] = platform_distribution.get(platform, 0) + 1
            
            # 提取广告文案
            bodies = ad.get('ad_creative_bodies', [])
            titles = ad.get('ad_creative_link_titles', [])
            descriptions = ad.get('ad_creative_link_descriptions', [])
            
            ad_detail = {
                'id': ad.get('id', ''),
                'creation_time': creation_time,
                'delivery_start': ad.get('ad_delivery_start_time', ''),
                'body': ' '.join(bodies) if bodies else '',
                'title': ' '.join(titles) if titles else '',
                'description': ' '.join(descriptions) if descriptions else '',
                'platforms': platforms,
                'spend': ad.get('spend', {}),
                'impressions': ad.get('impressions', {})
            }
            ads_details.append(ad_detail)
        
        # 提取主推产品（从文案中提取关键词）
        all_text = ' '.join([ad['body'] + ' ' + ad['title'] for ad in ads_details])
        main_products = self._extract_products(all_text)
        
        return {
            'total_ads': total_ads,
            'new_ads': new_ads,
            'main_products': main_products,
            'creative_types': creative_types,
            'platform_distribution': platform_distribution,
            'ads_details': ads_details
        }
    
    def _extract_products(self, text: str) -> List[str]:
        """从广告文案中提取产品关键词"""
        # 这里可以实现更复杂的NLP提取逻辑
        # 简单实现：提取大写的词组（通常是产品名）
        import re
        
        # 提取引号中的内容
        quoted = re.findall(r'"([^"]+)"', text)
        
        # 提取大写词组
        caps = re.findall(r'\b[A-Z][A-Z0-9\s]+\b', text)
        
        products = list(set(quoted + caps))[:10]  # 去重，最多10个
        return products


if __name__ == "__main__":
    # 测试
    scraper = MetaAdScraper()
    ads = scraper.fetch_ads(
        search_terms=["example brand"],
        start_date="2025-04-01",
        end_date="2025-05-31",
        limit=50
    )
    analysis = scraper.analyze_ads(ads)
    print(json.dumps(analysis, indent=2, ensure_ascii=False))