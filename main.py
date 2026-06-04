"""
竞品监测主程序 v2.0
基于Apify真实爬虫架构，整合6大板块采集+LLM分析
"""
import yaml
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List
import logging

sys.path.append(os.path.dirname(__file__))
from scrapers.apify_client import ApifyClient, SearchFallback
from scrapers.instagram_scraper import InstagramScraper
from scrapers.tiktok_scraper import TikTokScraper
from scrapers.youtube_scraper import YouTubeScraper
from scrapers.meta_ad_scraper import MetaAdScraper
from scrapers.reddit_scraper import RedditScraper
from scrapers.pr_scraper import PRScraper
from report_generator import ReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompetitorMonitor:
    """竞品监测主类 v2.0"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.data_dir = self.config['monitoring']['data_dir']
        os.makedirs(self.data_dir, exist_ok=True)

        # 初始化Apify客户端
        apify_token = self.config.get('apify', {}).get('api_token', '')
        if apify_token.startswith('${') and apify_token.endswith('}'):
            apify_token = os.getenv('APIFY_API_TOKEN', '')
        self.apify = ApifyClient(apify_token)

        # 验证Token
        self.apify_available = self.apify.verify_token() if apify_token else False

        # 降级模式
        self.fallback = SearchFallback()
        self.use_fallback = not self.apify_available
        if self.use_fallback:
            logger.warning("⚠️ Apify不可用，使用搜索降级模式")

        # 初始化各板块爬虫
        actor_config = self.config.get('apify', {})

        self.instagram_scraper = InstagramScraper(self.apify, actor_config)
        self.tiktok_scraper = TikTokScraper(self.apify, actor_config)
        self.youtube_scraper = YouTubeScraper(self.apify, actor_config)
        self.meta_scraper = MetaAdScraper(self.apify, actor_config)
        self.reddit_scraper = RedditScraper(search_tool=None, config=self.config)
        self.pr_scraper = PRScraper(search_tool=None, config=self.config)

        self.report_generator = ReportGenerator(
            output_dir=self.config['monitoring']['output_dir']
        )

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def run(self):
        """执行完整监测流程"""
        period = self.config['monitoring']['report_period']
        brands = self.config['brands']

        # 计算日期范围
        year, month = period.split('-')
        start_date = f"{year}-{month}-01"
        if month == '12':
            end_date = f"{int(year)+1}-01-01"
        else:
            end_date = f"{year}-{int(month)+1:02d}-01"
        # end_date是下月1号，实际月末是end_date前一天
        period_end = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

        logger.info(f"📊 开始竞品监测 - 周期: {period} ({start_date} ~ {period_end})")
        logger.info(f"   品牌数: {len(brands)}")
        logger.info(f"   Apify: {'✅ 可用' if self.apify_available else '❌ 降级模式'}")

        for brand in brands:
            brand_name = brand['name']
            logger.info(f"\n{'='*60}")
            logger.info(f"🔍 监测品牌: {brand_name}")
            logger.info(f"{'='*60}\n")

            data = self._collect_brand_data(brand, start_date, period_end)
            self._save_raw_data(brand_name, period, data)

            report_path = self.report_generator.generate_report(
                brand_name=brand_name,
                period=period,
                start_date=start_date,
                end_date=period_end,
                data=data
            )

            logger.info(f"✅ 品牌 {brand_name} 监测完成，报告: {report_path}")

        # 输出成本摘要
        cost = self.apify.get_cost_summary()
        logger.info(f"\n💰 本次运行消耗: {cost['total_results']} 条结果, "
                    f"{len(cost['actors_run'])} 个Actor运行")

        logger.info("\n✅ 所有品牌监测完成!")

    def _collect_brand_data(self, brand: Dict, start_date: str, end_date: str) -> Dict:
        """采集单个品牌的所有数据"""
        data = {
            'brand_products': {},
            'social_media': {'instagram': {}, 'tiktok': {}, 'youtube': {}},
            'influencers': {},
            'ugc_sentiment': {},
            'pr_articles': {},
            'meta_ads': {}
        }

        brand_name = brand['name']
        product_keywords = brand.get('product_keywords', [])
        social_accounts = brand.get('social_accounts', {})
        ig_username = social_accounts.get('instagram', '')
        tk_username = social_accounts.get('tiktok', '')
        yt_channel = social_accounts.get('youtube', '')
        fb_page_url = brand.get('facebook_page_url', '')

        # ====== 板块6: Meta广告（先跑，最稳定）======
        try:
            logger.info("[1/6] 采集Meta广告数据...")
            ads = self.meta_scraper.fetch_ads(
                brand_name=brand_name,
                product_keywords=product_keywords,
                facebook_page_url=fb_page_url,
                country=self.config.get('meta_ad_library', {}).get('country', 'US')
            )
            data['meta_ads'] = self.meta_scraper.analyze_ads(ads, start_date, end_date)
            logger.info(f"   ✅ Meta广告: {data['meta_ads']['total_ads']} 条")
        except Exception as e:
            logger.error(f"   ❌ Meta广告失败: {e}")
            data['meta_ads'] = {'total_ads': 0, 'error': str(e)}

        # ====== 板块2: 社媒数据 ======
        # Instagram
        try:
            logger.info("[2/6] 采集Instagram数据...")
            if ig_username:
                ig_profile = self.instagram_scraper.get_profile(ig_username)
                ig_posts = self.instagram_scraper.get_posts(ig_username)
                ig_analysis = self.instagram_scraper.analyze_posts(ig_posts, start_date, end_date)

                data['social_media']['instagram'] = {
                    'profile': ig_profile,
                    'analysis': ig_analysis
                }
                logger.info(f"   ✅ IG: {ig_analysis.get('period_posts_count', 0)} 条周期内帖子")
            else:
                logger.warning("   ⚠️ 未配置IG账号")
        except Exception as e:
            logger.error(f"   ❌ IG采集失败: {e}")
            data['social_media']['instagram'] = {'error': str(e)}

        # TikTok
        try:
            logger.info("[2/6] 采集TikTok数据...")
            if tk_username:
                tk_profile = self.tiktok_scraper.get_profile(tk_username)
                tk_posts = self.tiktok_scraper.get_posts(tk_username)
                tk_analysis = self.tiktok_scraper.analyze_posts(tk_posts, start_date, end_date)

                data['social_media']['tiktok'] = {
                    'profile': tk_profile,
                    'analysis': tk_analysis
                }
                logger.info(f"   ✅ TK: {tk_analysis.get('period_posts_count', 0)} 条周期内帖子")
            else:
                logger.warning("   ⚠️ 未配置TK账号")
        except Exception as e:
            logger.error(f"   ❌ TK采集失败: {e}")
            data['social_media']['tiktok'] = {'error': str(e)}

        # YouTube
        try:
            logger.info("[2/6] 采集YouTube数据...")
            if yt_channel:
                yt_videos = self.youtube_scraper.get_channel_videos(yt_channel)
                yt_analysis = self.youtube_scraper.analyze_videos(yt_videos, start_date, end_date)

                data['social_media']['youtube'] = {
                    'analysis': yt_analysis
                }
                logger.info(f"   ✅ YT: {yt_analysis.get('period_videos_count', 0)} 条周期内视频")
            else:
                logger.warning("   ⚠️ 未配置YT频道")
        except Exception as e:
            logger.error(f"   ❌ YT采集失败: {e}")
            data['social_media']['youtube'] = {'error': str(e)}

        # ====== 板块3: 红人合作（IG Tagged区）======
        try:
            logger.info("[3/6] 采集红人合作数据(IG Tagged区)...")
            if ig_username:
                tagged_posts = self.instagram_scraper.get_tagged_posts(ig_username)
                influencer_data = self.instagram_scraper.identify_influencers(
                    tagged_posts, ig_username
                )
                data['influencers'] = influencer_data
                logger.info(f"   ✅ 红人: {influencer_data['total_influencers']} 位")
            else:
                logger.warning("   ⚠️ 无IG账号，跳过红人识别")
        except Exception as e:
            logger.error(f"   ❌ 红人采集失败: {e}")
            data['influencers'] = {'total_influencers': 0, 'error': str(e)}

        # ====== 板块4: UGC舆情 ======
        try:
            logger.info("[4/6] 采集Reddit舆情...")
            reddit_posts = self.reddit_scraper.search_brand_mentions(
                brand_name=brand_name,
                product_keywords=product_keywords,
                subreddits=brand.get('reddit_subreddits', []),
                limit=30
            )
            sentiment = self.reddit_scraper.analyze_sentiment(reddit_posts)
            data['ugc_sentiment'] = {
                'posts': reddit_posts,
                'sentiment_analysis': sentiment
            }
            logger.info(f"   ✅ Reddit: {len(reddit_posts)} 条提及")
        except Exception as e:
            logger.error(f"   ❌ Reddit采集失败: {e}")
            data['ugc_sentiment'] = {'posts': [], 'sentiment_analysis': {}, 'error': str(e)}

        # ====== 板块5: PR稿件 ======
        try:
            logger.info("[5/6] 采集PR稿件...")
            pr_news = self.pr_scraper.search_news(
                brand_name=brand_name,
                product_keywords=product_keywords,
                limit=30
            )
            pr_analysis = self.pr_scraper.analyze_news(pr_news)
            pr_analysis['articles'] = pr_news
            data['pr_articles'] = pr_analysis
            logger.info(f"   ✅ PR: {pr_analysis.get('total_articles', 0)} 篇")
        except Exception as e:
            logger.error(f"   ❌ PR采集失败: {e}")
            data['pr_articles'] = {'total_articles': 0, 'error': str(e)}

        # ====== 板块1: 品牌新品动向（从已采集数据推断）======
        try:
            logger.info("[6/6] 分析品牌新品动向...")
            data['brand_products'] = self._analyze_brand_products(
                brand, data, start_date, end_date
            )
            new_count = len(data['brand_products'].get('new_products', []))
            logger.info(f"   ✅ 新品: {new_count} 款")
        except Exception as e:
            logger.error(f"   ❌ 品牌产品分析失败: {e}")
            data['brand_products'] = {'new_products': [], 'error': str(e)}

        return data

    def _analyze_brand_products(self, brand: Dict, data: Dict,
                                 start_date: str, end_date: str) -> Dict:
        """分析品牌新品动向（从社媒帖子+广告推断）"""
        new_products = []
        main_products = []

        # 从IG帖子中识别新品关键词
        ig_data = data.get('social_media', {}).get('instagram', {})
        ig_analysis = ig_data.get('analysis', {})
        period_posts = ig_analysis.get('period_posts', [])

        new_launch_keywords = ['new', 'launch', 'just dropped', 'introducing',
                              'announce', 'now available', 'new product',
                              '新品', '上市', '首发']

        for post in period_posts:
            caption = (post.get('caption', '') or '').lower()
            if any(kw in caption for kw in new_launch_keywords):
                new_products.append({
                    'source': 'instagram',
                    'caption': post.get('caption', '')[:200],
                    'url': post.get('url', ''),
                    'date': post.get('timestamp', '')[:10],
                    'selling_point': 'LLM提取'  # 后续LLM分析填充
                })

        # 从Meta广告提取主推产品
        ads_data = data.get('meta_ads', {})
        main_products = ads_data.get('main_products', [])

        # 从IG profile bio推断
        profile = ig_data.get('profile', {})
        bio = ''
        if profile:
            bio = profile.get('biography', profile.get('bio', ''))

        return {
            'new_products': new_products[:10],
            'main_products': main_products[:5],
            'bio': bio,
            'website': brand.get('website', '')
        }

    def _save_raw_data(self, brand_name: str, period: str, data: Dict):
        """保存原始数据"""
        filename = f"{brand_name}_{period}_raw_data.json"
        filepath = os.path.join(self.data_dir, filename)

        # 序列化处理：移除不可JSON化的字段
        clean_data = self._make_json_safe(data)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"📁 原始数据已保存: {filepath}")

    def _make_json_safe(self, obj):
        """递归处理，确保可JSON序列化"""
        if isinstance(obj, dict):
            return {k: self._make_json_safe(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_safe(v) for v in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)


def main():
    print("=" * 60)
    print("📊 竞品监测工具 v2.0 (Apify真实爬虫架构)")
    print("=" * 60)
    print()

    config_path = "config.yaml"
    if not os.path.exists(config_path):
        print(f"❌ 配置文件 {config_path} 不存在")
        print("请复制 config.yaml 并填写品牌配置")
        return

    monitor = CompetitorMonitor(config_path)
    monitor.run()

    print()
    print("=" * 60)
    print("✅ 监测完成! 请查看 reports 目录获取报告")
    print("=" * 60)


if __name__ == "__main__":
    main()
