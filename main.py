"""
竞品监测主程序
整合各板块爬虫，生成完整监测报告
"""

import yaml
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List
import logging

# 添加scrapers目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'scrapers'))

from scrapers.meta_ad_scraper import MetaAdScraper
from scrapers.instagram_scraper import InstagramScraper
from scrapers.reddit_scraper import RedditScraper
from scrapers.pr_scraper import PRScraper
from report_generator import ReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompetitorMonitor:
    """竞品监测主类"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化监测器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.data_dir = self.config['monitoring']['data_dir']
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 初始化各板块爬虫
        self.meta_scraper = MetaAdScraper(
            access_token=self.config['meta_ad_library'].get('access_token'),
            country=self.config['meta_ad_library'].get('country', 'US')
        )
        
        self.instagram_scraper = InstagramScraper(
            delay=self.config['request'].get('delay_between_requests', 3)
        )
        
        self.reddit_scraper = RedditScraper(
            client_id=self.config['reddit']['client_id'],
            client_secret=self.config['reddit']['client_secret'],
            user_agent=self.config['reddit']['user_agent']
        )
        
        self.pr_scraper = PRScraper(
            api_key=self.config['google']['api_key'],
            cx=self.config['google']['cx']
        )
        
        self.report_generator = ReportGenerator(
            output_dir=self.config['monitoring']['output_dir']
        )
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def run(self):
        """执行完整监测流程"""
        period = self.config['monitoring']['report_period']
        brands = self.config['brands']
        
        logger.info(f"开始执行竞品监测 - 周期: {period}")
        logger.info(f"监测品牌数: {len(brands)}")
        
        # 计算日期范围
        year, month = period.split('-')
        start_date = f"{year}-{month}-01"
        # 计算月末日期
        if month == '12':
            end_date = f"{int(year)+1}-01-01"
        else:
            end_date = f"{year}-{int(month)+1:02d}-01"
        
        for brand in brands:
            brand_name = brand['name']
            logger.info(f"\n{'='*50}")
            logger.info(f"正在监测品牌: {brand_name}")
            logger.info(f"{'='*50}\n")
            
            # 采集各板块数据
            data = self._collect_brand_data(brand, start_date, end_date)
            
            # 保存原始数据
            self._save_raw_data(brand_name, period, data)
            
            # 生成报告
            report_path = self.report_generator.generate_report(
                brand_name=brand_name,
                period=period,
                data=data
            )
            
            logger.info(f"品牌 {brand_name} 监测完成，报告: {report_path}")
        
        logger.info("\n所有品牌监测完成!")
    
    def _collect_brand_data(self, brand: Dict, start_date: str, end_date: str) -> Dict:
        """
        采集单个品牌的所有数据
        
        Args:
            brand: 品牌配置
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            品牌数据字典
        """
        data = {
            'brand_products': {},
            'social_media': {},
            'influencers': {},
            'ugc_sentiment': {},
            'pr_articles': {},
            'meta_ads': {}
        }
        
        brand_name = brand['name']
        product_keywords = brand.get('product_keywords', [])
        social_accounts = brand.get('social_accounts', {})
        
        # 1. 采集Meta广告数据
        try:
            logger.info("[1/6] 采集Meta广告数据...")
            search_terms = [brand_name] + product_keywords[:3]
            ads = self.meta_scraper.fetch_ads(
                search_terms=search_terms,
                start_date=start_date,
                end_date=end_date,
                limit=100
            )
            data['meta_ads'] = self.meta_scraper.analyze_ads(ads)
            logger.info(f"✓ Meta广告: {data['meta_ads']['total_ads']} 条")
        except Exception as e:
            logger.error(f"✗ Meta广告采集失败: {e}")
            data['meta_ads'] = {'total_ads': 0, 'error': str(e)}
        
        # 2. 采集Instagram数据
        try:
            logger.info("[2/6] 采集Instagram数据...")
            instagram_username = social_accounts.get('instagram', '')
            
            if instagram_username:
                # 获取账号信息
                profile = self.instagram_scraper.get_profile_info(instagram_username)
                
                # 获取最近帖子
                posts = self.instagram_scraper.get_recent_posts(instagram_username, count=30)
                
                # 分析帖子
                analysis = self.instagram_scraper.analyze_posts(posts)
                
                data['social_media'] = {
                    'profile': profile,
                    'total_posts': analysis.get('total_posts', 0),
                    'video_posts': analysis.get('video_posts', 0),
                    'image_posts': analysis.get('image_posts', 0),
                    'avg_likes': analysis.get('avg_likes', 0),
                    'avg_comments': analysis.get('avg_comments', 0),
                    'avg_engagement': analysis.get('avg_engagement', 0),
                    'posting_frequency': analysis.get('posting_frequency', 0),
                    'top_posts': analysis.get('top_posts', [])
                }
                
                # 获取合作红人（从tagged区域）
                tagged_users = self.instagram_scraper.get_tagged_users(instagram_username, count=30)
                
                # 分析红人
                data['influencers'] = self._analyze_influencers(tagged_users)
                
                logger.info(f"✓ Instagram: {data['social_media']['total_posts']} 条帖子, {data['influencers']['total_influencers']} 位红人")
            else:
                logger.warning("未配置Instagram账号，跳过")
                
        except Exception as e:
            logger.error(f"✗ Instagram采集失败: {e}")
            data['social_media'] = {'total_posts': 0, 'error': str(e)}
            data['influencers'] = {'total_influencers': 0, 'error': str(e)}
        
        # 3. 采集Reddit数据
        try:
            logger.info("[3/6] 采集Reddit舆情数据...")
            
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            posts = self.reddit_scraper.search_brand_mentions(
                brand_name=brand_name,
                product_keywords=product_keywords[:3],
                start_date=start_dt,
                end_date=end_dt,
                limit=100
            )
            
            sentiment = self.reddit_scraper.analyze_sentiment(posts)
            
            # 获取高互动帖子
            top_posts = sorted(posts, key=lambda x: x.get('score', 0), reverse=True)[:10]
            
            data['ugc_sentiment'] = {
                'total_posts': len(posts),
                'sentiment_analysis': sentiment,
                'top_posts': top_posts
            }
            
            logger.info(f"✓ Reddit: {len(posts)} 条提及, 正面{sentiment.get('positive_rate', 0)}%")
            
        except Exception as e:
            logger.error(f"✗ Reddit采集失败: {e}")
            data['ugc_sentiment'] = {'total_posts': 0, 'error': str(e)}
        
        # 4. 采集PR数据
        try:
            logger.info("[4/6] 采集PR稿件数据...")
            
            news = self.pr_scraper.search_news(
                brand_name=brand_name,
                product_keywords=product_keywords[:2],
                start_date=start_date,
                end_date=end_date,
                limit=50
            )
            
            analysis = self.pr_scraper.analyze_news(news)
            analysis['articles'] = news
            
            data['pr_articles'] = analysis
            
            logger.info(f"✓ PR稿件: {analysis.get('total_articles', 0)} 篇")
            
        except Exception as e:
            logger.error(f"✗ PR采集失败: {e}")
            data['pr_articles'] = {'total_articles': 0, 'error': str(e)}
        
        # 5. 品牌新品动向（从Meta广告和社媒数据推断）
        try:
            logger.info("[5/6] 分析品牌新品动向...")
            
            # 从Meta广告主推产品推断
            main_products = data['meta_ads'].get('main_products', [])
            
            # 从Instagram bio推断
            profile = data['social_media'].get('profile', {})
            bio = profile.get('biography', '')
            
            data['brand_products'] = {
                'new_products': [],  # 需要人工确认或从官网抓取
                'main_products': main_products[:5],
                'bio': bio
            }
            
            logger.info(f"✓ 主推产品: {', '.join(main_products[:3]) if main_products else '暂无'}")
            
        except Exception as e:
            logger.error(f"✗ 品牌产品分析失败: {e}")
            data['brand_products'] = {'new_products': [], 'error': str(e)}
        
        logger.info("[6/6] 数据采集完成!")
        
        return data
    
    def _analyze_influencers(self, tagged_users: List[Dict]) -> Dict:
        """分析红人数据"""
        if not tagged_users:
            return {
                'total_influencers': 0,
                'total_exposure': 0,
                'platform_distribution': {},
                'tier_distribution': {},
                'influencer_list': []
            }
        
        # 量级划分
        def get_tier(followers):
            if followers < 1000:
                return 'Nano'
            elif followers < 100000:
                return 'Micro'
            elif followers < 1000000:
                return 'Macro'
            else:
                return 'Mega'
        
        # 统计
        tier_distribution = {}
        total_exposure = 0
        influencer_list = []
        
        for user in tagged_users:
            followers = user.get('followers', 0)
            tier = get_tier(followers)
            
            tier_distribution[tier] = tier_distribution.get(tier, 0) + 1
            total_exposure += followers
            
            influencer_list.append({
                'username': user.get('username', ''),
                'platform': 'Instagram',
                'followers': followers,
                'tier': tier,
                'type': 'Lifestyle',  # 需要进一步分析
                'product': ''  # 需要关联帖子分析
            })
        
        return {
            'total_influencers': len(tagged_users),
            'total_exposure': total_exposure,
            'platform_distribution': {'Instagram': len(tagged_users)},
            'tier_distribution': tier_distribution,
            'influencer_list': influencer_list
        }
    
    def _save_raw_data(self, brand_name: str, period: str, data: Dict):
        """保存原始数据"""
        filename = f"{brand_name}_{period}_raw_data.json"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"原始数据已保存: {filepath}")


def main():
    """主函数"""
    print("="*60)
    print("竞品监测工具 v1.0")
    print("="*60)
    print()
    
    # 检查配置文件
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        print(f"错误: 配置文件 {config_path} 不存在")
        print("请复制 config.example.yaml 为 config.yaml 并填写配置")
        return
    
    # 运行监测
    monitor = CompetitorMonitor(config_path)
    monitor.run()
    
    print()
    print("="*60)
    print("监测完成! 请查看 reports 目录获取报告")
    print("="*60)


if __name__ == "__main__":
    main()