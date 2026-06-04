"""
Meta Ad Library 爬虫 v2.0
通过Apify Actor抓取Facebook/Instagram广告
修复v1.0直接调用API需access_token的问题
"""
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetaAdScraper:
    """Meta广告库爬虫 - 基于Apify Actor（无需Meta API Token）"""

    def __init__(self, apify_client, config: Dict = None):
        """
        Args:
            apify_client: ApifyClient实例
            config: 采集配置
        """
        self.client = apify_client
        self.config = config or {}
        self.max_ads = self.config.get('max_ads_per_search', 100)
        self.country = self.config.get('country', 'US')

    def fetch_ads(self, brand_name: str, product_keywords: List[str],
                  facebook_page_url: str = None,
                  country: str = None) -> List[Dict]:
        """
        抓取Meta广告数据

        使用Actor: automation-lab/facebook-ads-library
        ★ 无需Meta API Token，无需app review ★
        通过Playwright浏览器直接抓取公开Ad Library

        Args:
            brand_name: 品牌名
            product_keywords: 产品关键词
            facebook_page_url: 品牌FB页面URL（按Page精确抓取）
            country: 搜索国家代码
        """
        country = country or self.country
        logger.info(f"[Meta Ads] 采集广告: {brand_name}, 国家: {country}")

        # 构建输入 - 支持关键词搜索和Page URL两种模式
        run_input = {
            "country": country,
            "activeStatus": "all",       # 包含活跃+不活跃广告
            "maxAds": self.max_ads,
        }

        # 优先用Page URL精确抓取
        if facebook_page_url:
            run_input["pageUrls"] = [facebook_page_url]
            # 同时用品牌名搜索补充
            run_input["searchQueries"] = [brand_name] + product_keywords[:2]
        else:
            run_input["searchQueries"] = [brand_name] + product_keywords[:3]

        results = self.client.run_actor(
            actor_id="automation-lab/facebook-ads-library",
            run_input=run_input,
            timeout=300
        )

        if not results:
            logger.warning(f"[Meta Ads] Apify无结果，尝试Meta Ad Library公开API降级...")
            results = self._fetch_ads_fallback(brand_name, product_keywords,
                                                facebook_page_url, country)

        if not results:
            logger.warning(f"[Meta Ads] 无结果: {brand_name}")
            return []

        logger.info(f"[Meta Ads] ✅ {brand_name}: {len(results)} 条广告")
        return results

    def _fetch_ads_fallback(self, brand_name: str, product_keywords: List[str],
                              facebook_page_url: str = None,
                              country: str = 'US') -> List[Dict]:
        """
        Meta Ad Library公开API降级方案

        使用Meta Graph API的ads_archive端点（无需access_token也可部分调用）
        注意：部分字段在无token时可能不可用
        """
        results = []
        search_terms = [brand_name] + product_keywords[:3]

        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'CompetitorMonitor/2.0'
            })

            for term in search_terms:
                params = {
                    'search_terms': term,
                    'ad_reached_countries': '["US"]',
                    'ad_delivery_date_min': '2025-01-01',
                    'ad_delivery_date_max': '2026-06-30',
                    'fields': 'ad_archive_id,ad_creator,name,currency,start_date,end_date,'
                              'ad_delivery_start_time,ad_delivery_stop_time,'
                              'byline,description,display_format,title,body,link_url,'
                              'image_url,video_url,cta_type,cta_text,'
                              'impressions,spend,demographics,platforms,page_name,page_id',
                    'limit': 200,
                    'access_token': ''
                }

                url = "https://graph.facebook.com/v19.0/ads_archive"
                resp = session.get(url, params=params, timeout=15)

                if resp.status_code == 200:
                    data = resp.json()
                    ads_data = data.get('data', [])
                    for ad in ads_data:
                        results.append({
                            'adArchiveId': ad.get('ad_archive_id', ''),
                            'adLibraryUrl': f"https://www.facebook.com/ads/library/?id={ad.get('ad_archive_id', '')}",
                            'pageName': ad.get('page_name', ad.get('byline', '')),
                            'isActive': ad.get('ad_delivery_stop_time') is None,
                            'startDate': ad.get('ad_delivery_start_time', ''),
                            'endDate': ad.get('ad_delivery_stop_time', ''),
                            'platforms': ad.get('platforms', []),
                            'displayFormat': ad.get('display_format', ''),
                            'bodyText': ad.get('description', ad.get('body', '')),
                            'title': ad.get('title', ''),
                            'ctaText': ad.get('cta_text', ad.get('cta_type', '')),
                            'linkUrl': ad.get('link_url', ''),
                            'imageUrls': [ad.get('image_url', '')] if ad.get('image_url') else [],
                            'videoUrls': [ad.get('video_url', '')] if ad.get('video_url') else [],
                            'spend': ad.get('spend', {}),
                            'impressions': ad.get('impressions', ''),
                            'source': 'meta_ad_library_fallback'
                        })
                    logger.info(f"[Meta Ads Fallback] {term}: {len(ads_data)} 条广告")
                else:
                    logger.warning(f"[Meta Ads Fallback] API返回 {resp.status_code}: {term}")

        except Exception as e:
            logger.error(f"[Meta Ads Fallback] 降级方案失败: {e}")

        return results

    def analyze_ads(self, ads: List[Dict], period_start: str, period_end: str) -> Dict:
        """
        分析广告数据

        Args:
            ads: 广告列表
            period_start: 周期开始 YYYY-MM-DD
            period_end: 周期结束 YYYY-MM-DD
        """
        if not ads:
            return {
                'total_ads': 0,
                'new_ads': 0,
                'active_ads': 0,
                'main_products': [],
                'creative_type_dist': {},
                'platform_dist': {},
                'ads_details': [],
                'cta_analysis': {}
            }

        # 统计
        new_ads = 0
        active_ads = 0
        creative_types = {}
        platform_dist = {}
        cta_types = {}
        ads_details = []

        for ad in ads:
            # 是否活跃
            if ad.get('isActive', False):
                active_ads += 1

            # 是否新广告（周期内开始投放）
            start_date = ad.get('startDate', '')
            if start_date:
                try:
                    if period_start <= start_date[:10] <= period_end:
                        new_ads += 1
                except:
                    pass

            # 素材类型
            display_format = ad.get('displayFormat', 'unknown')
            creative_types[display_format] = creative_types.get(display_format, 0) + 1

            # 投放平台
            platforms = ad.get('platforms', [])
            for p in platforms:
                platform_dist[p] = platform_dist.get(p, 0) + 1

            # CTA分析
            cta = ad.get('ctaText', ad.get('ctaType', 'unknown'))
            cta_types[cta] = cta_types.get(cta, 0) + 1

            # 广告详情
            ad_detail = {
                'adArchiveId': ad.get('adArchiveId', ''),
                'adLibraryUrl': ad.get('adLibraryUrl', ''),
                'pageName': ad.get('pageName', ''),
                'isActive': ad.get('isActive', False),
                'startDate': start_date,
                'endDate': ad.get('endDate', ''),
                'platforms': platforms,
                'displayFormat': display_format,
                'bodyText': ad.get('bodyText', ''),
                'title': ad.get('title', ''),
                'ctaText': cta,
                'linkUrl': ad.get('linkUrl', ''),
                'imageUrls': ad.get('imageUrls', []),
                'videoUrls': ad.get('videoUrls', []),
                'spend': ad.get('spend', {}),
                'impressions': ad.get('impressions', ''),
            }
            ads_details.append(ad_detail)

        # 提取主推产品（从文案中）
        all_text = ' '.join([
            (ad.get('bodyText', '') or '') + ' ' + (ad.get('title', '') or '')
            for ad in ads
        ])
        main_products = self._extract_products(all_text)

        return {
            'total_ads': len(ads),
            'new_ads': new_ads,
            'active_ads': active_ads,
            'main_products': main_products,
            'creative_type_dist': creative_types,
            'platform_dist': platform_dist,
            'ads_details': ads_details,
            'cta_analysis': cta_types
        }

    def _extract_products(self, text: str) -> List[str]:
        """从广告文案中提取产品关键词"""
        import re

        products = []
        # 提取引号中的内容
        quoted = re.findall(r'"([^"]+)"', text)
        # 提取品牌名+产品名的常见模式
        caps_words = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', text)

        candidates = list(set(quoted + caps_words))
        # 过滤常见非产品词
        stopwords = {'The', 'This', 'Get', 'Shop', 'Now', 'Learn', 'Free',
                    'Your', 'Our', 'New', 'And', 'For', 'With', 'From'}
        products = [p for p in candidates if p not in stopwords and len(p) > 3]

        return products[:10]
