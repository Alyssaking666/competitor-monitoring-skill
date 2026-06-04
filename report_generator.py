"""
报告生成器
整合各板块数据，生成结构化的竞品监测报告
输出格式: Markdown (可直接导入飞书文档)
"""

import json
import os
from datetime import datetime
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportGenerator:
    """竞品监测报告生成器"""
    
    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_report(self, 
                       brand_name: str,
                       period: str,
                       data: Dict) -> str:
        """
        生成完整报告
        
        Args:
            brand_name: 品牌名称
            period: 报告周期 (YYYY-MM)
            data: 各板块数据
            
        Returns:
            报告文件路径
        """
        report_lines = []
        
        # 1. 报告标题
        report_lines.extend(self._generate_header(brand_name, period))
        
        # 2. 执行摘要
        report_lines.extend(self._generate_executive_summary(data))
        
        # 3. 板块概览 Dashboard
        report_lines.extend(self._generate_dashboard(data))
        
        # 4. 各板块详细报告
        report_lines.extend(self._generate_brand_products_section(data.get('brand_products', {})))
        report_lines.extend(self._generate_social_media_section(data.get('social_media', {})))
        report_lines.extend(self._generate_influencer_section(data.get('influencers', {})))
        report_lines.extend(self._generate_ugc_section(data.get('ugc_sentiment', {})))
        report_lines.extend(self._generate_pr_section(data.get('pr_articles', {})))
        report_lines.extend(self._generate_meta_ads_section(data.get('meta_ads', {})))
        
        # 5. 附录
        report_lines.extend(self._generate_appendix())
        
        # 保存报告
        report_content = '\n'.join(report_lines)
        filename = f"{brand_name}_竞品监测报告_{period}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"报告已生成: {filepath}")
        return filepath
    
    def _generate_header(self, brand_name: str, period: str) -> List[str]:
        """生成报告标题"""
        year, month = period.split('-')
        return [
            f"# 📊 竞品监测报告 - {brand_name} - {year}年{month}月",
            "",
            f"> **监测周期**: {year}-{month}-01 至 {year}-{month}-31",
            f"> **报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "> **数据来源**: Meta Ad Library, Instagram, Reddit, Google News",
            "",
            "---",
            "",
        ]
    
    def _generate_executive_summary(self, data: Dict) -> List[str]:
        """生成执行摘要"""
        lines = [
            "## 📋 执行摘要",
            "",
            "> **核心发现**:",
        ]
        
        # 从各板块提取关键信息
        key_findings = []
        
        # 品牌新品
        brand_products = data.get('brand_products', {})
        if brand_products.get('new_products'):
            key_findings.append(f"- 本月品牌上线 {len(brand_products['new_products'])} 款新品")
        
        # 社媒数据
        social = data.get('social_media', {})
        if social.get('total_posts'):
            key_findings.append(f"- 全平台共发布 {social['total_posts']} 条内容")
        
        # 红人
        influencers = data.get('influencers', {})
        if influencers.get('total_influencers'):
            key_findings.append(f"- 合作红人 {influencers['total_influencers']} 位")
        
        # PR
        pr = data.get('pr_articles', {})
        if pr.get('total_articles'):
            key_findings.append(f"- PR稿件 {pr['total_articles']} 篇")
        
        # Meta广告
        ads = data.get('meta_ads', {})
        if ads.get('total_ads'):
            key_findings.append(f"- Meta广告 {ads['total_ads']} 条")
        
        if not key_findings:
            key_findings.append("- 本月数据采集中，暂无核心发现")
        
        lines.extend(key_findings)
        lines.extend(["", "---", ""])
        
        return lines
    
    def _generate_dashboard(self, data: Dict) -> List[str]:
        """生成板块概览 Dashboard"""
        lines = [
            "## 📱 板块概览 Dashboard",
            "",
            "| 板块 | 核心指标 | 数值 |",
            "|------|---------|------|",
        ]
        
        # 品牌新品
        brand_products = data.get('brand_products', {})
        new_products_count = len(brand_products.get('new_products', []))
        lines.append(f"| 📦 品牌新品动向 | 新品数量 | {new_products_count} |")
        
        # 社媒
        social = data.get('social_media', {})
        total_posts = social.get('total_posts', 0)
        lines.append(f"| 📊 社媒数据表现 | 总Post数 | {total_posts} |")
        
        # 红人
        influencers = data.get('influencers', {})
        total_influencers = influencers.get('total_influencers', 0)
        lines.append(f"| 👥 红人合作数据 | 合作红人 | {total_influencers} |")
        
        # UGC
        ugc = data.get('ugc_sentiment', {})
        total_mentions = ugc.get('total_posts', 0)
        lines.append(f"| 💬 UGC舆情监测 | 提及数量 | {total_mentions} |")
        
        # PR
        pr = data.get('pr_articles', {})
        total_articles = pr.get('total_articles', 0)
        lines.append(f"| 📰 PR稿件监测 | PR篇数 | {total_articles} |")
        
        # Meta广告
        ads = data.get('meta_ads', {})
        total_ads = ads.get('total_ads', 0)
        lines.append(f"| 🎯 Meta广告监测 | 广告条数 | {total_ads} |")
        
        lines.extend(["", "---", ""])
        
        return lines
    
    def _generate_brand_products_section(self, data: Dict) -> List[str]:
        """生成品牌新品动向板块"""
        lines = [
            "## 📦 1. 品牌新品动向",
            "",
            "> **板块总结**: ",
        ]
        
        new_products = data.get('new_products', [])
        main_products = data.get('main_products', [])
        
        if new_products:
            lines.append(f"> - 本月上线 {len(new_products)} 款新品")
            lines.append(f"> - 主推产品: {', '.join(main_products[:3]) if main_products else '暂无数据'}")
        else:
            lines.append("> - 本月未发现新品上线")
            lines.append(f"> - 近期主推产品: {', '.join(main_products[:3]) if main_products else '暂无数据'}")
        
        lines.append("")
        
        # 新品列表
        if new_products:
            lines.append("### 新品上线列表")
            lines.append("")
            lines.append("| 产品名称 | 上线时间 | 主推卖点 | 价格 |")
            lines.append("|---------|---------|---------|------|")
            
            for product in new_products[:10]:
                name = product.get('name', 'N/A')
                launch_date = product.get('launch_date', 'N/A')
                selling_point = product.get('main_selling_point', 'N/A')[:30]
                price = product.get('price', 'N/A')
                lines.append(f"| {name} | {launch_date} | {selling_point} | {price} |")
            
            lines.append("")
        
        # 主推产品
        if main_products:
            lines.append("### 近期主推产品")
            lines.append("")
            for i, product in enumerate(main_products[:5], 1):
                lines.append(f"{i}. **{product}**")
            lines.append("")
        
        lines.extend(["---", ""])
        
        return lines
    
    def _generate_social_media_section(self, data: Dict) -> List[str]:
        """生成社媒数据板块"""
        lines = [
            "## 📊 2. 社媒数据表现",
            "",
            "> **板块总结**:",
        ]
        
        total_posts = data.get('total_posts', 0)
        avg_engagement = data.get('avg_engagement', 0)
        posting_frequency = data.get('posting_frequency', 0)
        
        lines.append(f"> - 全平台共发布 {total_posts} 条内容")
        lines.append(f"> - 平均互动量: {avg_engagement}")
        lines.append(f"> - 发布频次: 约 {posting_frequency} 条/天")
        lines.append("")
        
        # 核心数据 Dashboard
        lines.append("### 核心数据 Dashboard")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 总Post数 | {total_posts} |")
        lines.append(f"| 视频Post | {data.get('video_posts', 0)} |")
        lines.append(f"| 图片Post | {data.get('image_posts', 0)} |")
        lines.append(f"| 平均点赞 | {data.get('avg_likes', 0)} |")
        lines.append(f"| 平均评论 | {data.get('avg_comments', 0)} |")
        lines.append(f"| 平均互动 | {avg_engagement} |")
        lines.append("")
        
        # 高互动帖文
        top_posts = data.get('top_posts', [])
        if top_posts:
            lines.append("### 高互动帖文 Top 10")
            lines.append("")
            lines.append("| 排名 | 平台 | 互动量 | 内容摘要 |")
            lines.append("|------|------|--------|---------|")
            
            for i, post in enumerate(top_posts[:10], 1):
                platform = post.get('platform', 'N/A')
                engagement = post.get('engagement', 0)
                caption = post.get('caption', '')[:50] + '...' if len(post.get('caption', '')) > 50 else post.get('caption', '')
                lines.append(f"| {i} | {platform} | {engagement} | {caption} |")
            
            lines.append("")
        
        lines.extend(["---", ""])
        
        return lines
    
    def _generate_influencer_section(self, data: Dict) -> List[str]:
        """生成红人合作板块"""
        lines = [
            "## 👥 3. 红人合作数据",
            "",
            "> **板块总结**:",
        ]
        
        total_influencers = data.get('total_influencers', 0)
        total_exposure = data.get('total_exposure', 0)
        
        lines.append(f"> - 合作红人 {total_influencers} 位")
        lines.append(f"> - 总曝光量: {total_exposure:,}" if total_exposure else "> - 总曝光量: 暂无数据")
        lines.append("")
        
        # 核心数据 Dashboard
        lines.append("### 核心数据 Dashboard")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 红人总数 | {total_influencers} |")
        lines.append(f"| 总曝光 | {total_exposure:,} |" if total_exposure else "| 总曝光 | N/A |")
        
        # 平台分布
        platform_dist = data.get('platform_distribution', {})
        if platform_dist:
            lines.append("| 平台分布 | " + ", ".join([f"{k}: {v}" for k, v in platform_dist.items()]) + " |")
        
        # 量级分布
        tier_dist = data.get('tier_distribution', {})
        if tier_dist:
            lines.append("| 量级分布 | " + ", ".join([f"{k}: {v}" for k, v in tier_dist.items()]) + " |")
        
        lines.append("")
        
        # 红人明细
        influencer_list = data.get('influencer_list', [])
        if influencer_list:
            lines.append("### 红人明细列表")
            lines.append("")
            lines.append("| 红人账号 | 平台 | 粉丝数 | 量级 | 类型 | 推广产品 |")
            lines.append("|---------|------|--------|------|------|---------|")
            
            for inf in influencer_list[:20]:
                username = inf.get('username', 'N/A')
                platform = inf.get('platform', 'N/A')
                followers = inf.get('followers', 0)
                tier = inf.get('tier', 'N/A')
                type_ = inf.get('type', 'N/A')
                product = inf.get('product', 'N/A')[:20]
                lines.append(f"| @{username} | {platform} | {followers:,} | {tier} | {type_} | {product} |")
            
            lines.append("")
        
        # 高互动视频
        top_videos = data.get('top_videos', [])
        if top_videos:
            lines.append("### 高互动视频")
            lines.append("")
            for i, video in enumerate(top_videos[:5], 1):
                lines.append(f"**{i}. {video.get('title', 'N/A')}**")
                lines.append(f"- 平台: {video.get('platform', 'N/A')}")
                lines.append(f"- 互动量: {video.get('engagement', 0):,}")
                lines.append(f"- 链接: {video.get('url', 'N/A')}")
                lines.append("")
        
        lines.extend(["---", ""])
        
        return lines
    
    def _generate_ugc_section(self, data: Dict) -> List[str]:
        """生成UGC舆情板块"""
        lines = [
            "## 💬 4. UGC舆情监测",
            "",
            "> **板块总结**:",
        ]
        
        sentiment = data.get('sentiment_analysis', {})
        total_posts = sentiment.get('total_posts', 0)
        positive_rate = sentiment.get('positive_rate', 0)
        negative_rate = sentiment.get('negative_rate', 0)
        
        lines.append(f"> - Reddit提及 {total_posts} 次")
        lines.append(f"> - 正面评价: {positive_rate}%")
        lines.append(f"> - 负面评价: {negative_rate}%")
        lines.append("")
        
        # 情感分析
        lines.append("### 情感分析")
        lines.append("")
        lines.append("| 情感 | 数量 | 占比 |")
        lines.append("|------|------|------|")
        lines.append(f"| 😊 正面 | {sentiment.get('positive', 0)} | {positive_rate}% |")
        lines.append(f"| 😐 中性 | {sentiment.get('neutral', 0)} | {sentiment.get('neutral_rate', 0)}% |")
        lines.append(f"| 😞 负面 | {sentiment.get('negative', 0)} | {negative_rate}% |")
        lines.append("")
        
        # 热门话题
        key_topics = sentiment.get('key_topics', [])
        if key_topics:
            lines.append("### 热门讨论话题")
            lines.append("")
            lines.append("| 话题 | 提及次数 |")
            lines.append("|------|---------|")
            for topic in key_topics[:10]:
                lines.append(f"| {topic.get('word', 'N/A')} | {topic.get('count', 0)} |")
            lines.append("")
        
        # 热门帖子
        top_posts = data.get('top_posts', [])
        if top_posts:
            lines.append("### 热门讨论帖子")
            lines.append("")
            for i, post in enumerate(top_posts[:5], 1):
                lines.append(f"**{i}. {post.get('title', 'N/A')}**")
                lines.append(f"- Subreddit: r/{post.get('subreddit', 'N/A')}")
                lines.append(f"- 点赞: {post.get('score', 0)}")
                lines.append(f"- 评论: {post.get('num_comments', 0)}")
                lines.append(f"- 链接: {post.get('permalink', 'N/A')}")
                lines.append("")
        
        lines.extend(["---", ""])
        
        return lines
    
    def _generate_pr_section(self, data: Dict) -> List[str]:
        """生成PR稿件板块"""
        lines = [
            "## 📰 5. PR稿件监测",
            "",
            "> **板块总结**:",
        ]
        
        total_articles = data.get('total_articles', 0)
        lines.append(f"> - 本月PR稿件 {total_articles} 篇")
        
        # 推广重点
        focus_analysis = data.get('focus_analysis', [])
        if focus_analysis:
            top_focus = focus_analysis[0]
            lines.append(f"> - 主要推广方向: {top_focus.get('focus', 'N/A')}")
        
        lines.append("")
        
        # 核心数据 Dashboard
        lines.append("### 核心数据 Dashboard")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| PR篇数 | {total_articles} |")
        
        # 媒体层级分布
        tier_dist = data.get('tier_distribution', {})
        if tier_dist:
            for tier, count in tier_dist.items():
                lines.append(f"| {tier}媒体 | {count}篇 |")
        
        # 媒体类型分布
        type_dist = data.get('type_distribution', {})
        if type_dist:
            for type_, count in type_dist.items():
                lines.append(f"| {type_} | {count}篇 |")
        
        lines.append("")
        
        # 推广重点分析
        if focus_analysis:
            lines.append("### 推广重点分析")
            lines.append("")
            lines.append("| 推广方向 | 提及次数 | 占比 |")
            lines.append("|---------|---------|------|")
            for focus in focus_analysis[:5]:
                lines.append(f"| {focus.get('focus', 'N/A')} | {focus.get('mentions', 0)} | {focus.get('percentage', 0)}% |")
            lines.append("")
        
        # PR稿件列表
        articles = data.get('articles', [])
        if articles:
            lines.append("### PR稿件列表")
            lines.append("")
            lines.append("| 标题 | 媒体 | 层级 | 类型 | 日期 |")
            lines.append("|------|------|------|------|------|")
            
            for article in articles[:15]:
                title = article.get('title', 'N/A')[:40] + '...' if len(article.get('title', '')) > 40 else article.get('title', 'N/A')
                media = article.get('source', 'N/A')
                tier = article.get('media_tier', 'N/A')
                type_ = article.get('media_type', 'N/A')
                date = article.get('published_date', 'N/A')[:10]
                lines.append(f"| {title} | {media} | {tier} | {type_} | {date} |")
            
            lines.append("")
        
        lines.extend(["---", ""])
        
        return lines
    
    def _generate_meta_ads_section(self, data: Dict) -> List[str]:
        """生成Meta广告板块"""
        lines = [
            "## 🎯 6. Meta广告监测",
            "",
            "> **板块总结**:",
        ]
        
        total_ads = data.get('total_ads', 0)
        new_ads = data.get('new_ads', 0)
        main_products = data.get('main_products', [])
        
        lines.append(f"> - 广告总条数: {total_ads}")
        lines.append(f"> - 新上线广告: {new_ads}")
        lines.append(f"> - 主推产品: {', '.join(main_products[:3]) if main_products else '暂无数据'}")
        lines.append("")
        
        # 核心数据 Dashboard
        lines.append("### 核心数据 Dashboard")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 广告总条数 | {total_ads} |")
        lines.append(f"| 新广告数量 | {new_ads} |")
        
        # 平台分布
        platform_dist = data.get('platform_distribution', {})
        if platform_dist:
            for platform, count in platform_dist.items():
                lines.append(f"| {platform} | {count} |")
        
        lines.append("")
        
        # 主推产品
        if main_products:
            lines.append("### 主推产品")
            lines.append("")
            for i, product in enumerate(main_products[:5], 1):
                lines.append(f"{i}. **{product}**")
            lines.append("")
        
        # 广告详情
        ads_details = data.get('ads_details', [])
        if ads_details:
            lines.append("### 广告素材分析")
            lines.append("")
            
            for i, ad in enumerate(ads_details[:10], 1):
                lines.append(f"**广告 {i}**")
                lines.append(f"- 创建时间: {ad.get('creation_time', 'N/A')}")
                lines.append(f"- 投放平台: {', '.join(ad.get('platforms', []))}")
                lines.append(f"- 文案: {ad.get('body', 'N/A')[:100]}...")
                lines.append("")
        
        lines.extend(["---", ""])
        
        return lines
    
    def _generate_appendix(self) -> List[str]:
        """生成附录"""
        return [
            "## 📌 附录",
            "",
            "### 数据来源说明",
            "",
            "| 板块 | 数据来源 | 采集方式 |",
            "|------|---------|---------|",
            "| 品牌新品动向 | 品牌官网、官方社媒 | 网页抓取 |",
            "| 社媒数据 | Instagram公开页面 | 网页抓取 |",
            "| 红人合作 | Instagram tagged区域 | 网页抓取 |",
            "| UGC舆情 | Reddit API | API调用 |",
            "| PR稿件 | Google Custom Search API | API调用 |",
            "| Meta广告 | Meta Ad Library API | API调用 |",
            "",
            "### 数据限制声明",
            "",
            "> - 本报告数据基于公开渠道采集，可能存在延迟或遗漏",
            "> - Instagram数据受反爬机制影响，采集频率受限",
            "> - Reddit API有调用频率限制（60次/分钟）",
            "> - Google Custom Search API免费额度为100次/天",
            "> - Meta Ad Library部分字段可能需要开发者账号才能访问",
            "",
            "### 方法论",
            "",
            "> - 情感分析基于关键词匹配，仅供参考",
            "> - 红人量级划分: Nano(<1K), Micro(1K-100K), Macro(100K-1M), Mega(>1M)",
            "> - 媒体层级划分基于行业通用标准",
            "",
            "---",
            "",
            f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
        ]


if __name__ == "__main__":
    # 测试
    generator = ReportGenerator()
    
    # 模拟数据
    test_data = {
        'brand_products': {
            'new_products': [
                {'name': 'Product X', 'launch_date': '2025-05-15', 'main_selling_point': '超长续航', 'price': '$299'}
            ],
            'main_products': ['Product X', 'Product Y', 'Product Z']
        },
        'social_media': {
            'total_posts': 45,
            'video_posts': 20,
            'image_posts': 25,
            'avg_likes': 1200,
            'avg_comments': 80,
            'avg_engagement': 1280,
            'posting_frequency': 1.5,
            'top_posts': [
                {'platform': 'Instagram', 'engagement': 5000, 'caption': 'New launch! Check out our latest product'}
            ]
        },
        'influencers': {
            'total_influencers': 15,
            'total_exposure': 500000,
            'platform_distribution': {'Instagram': 10, 'TikTok': 5},
            'tier_distribution': {'Micro': 10, 'Macro': 5},
            'influencer_list': [
                {'username': 'influencer1', 'platform': 'Instagram', 'followers': 50000, 'tier': 'Micro', 'type': 'Lifestyle', 'product': 'Product X'}
            ]
        },
        'ugc_sentiment': {
            'total_posts': 120,
            'sentiment_analysis': {
                'positive': 72,
                'neutral': 36,
                'negative': 12,
                'positive_rate': 60,
                'neutral_rate': 30,
                'negative_rate': 10,
                'key_topics': [{'word': 'battery', 'count': 25}, {'word': 'design', 'count': 20}]
            },
            'top_posts': [
                {'title': 'Great product review', 'subreddit': 'gadgets', 'score': 150, 'num_comments': 30, 'permalink': 'https://reddit.com/r/gadgets/abc'}
            ]
        },
        'pr_articles': {
            'total_articles': 8,
            'tier_distribution': {'Tier 1': 2, 'Tier 2': 3, 'Tier 3': 3},
            'type_distribution': {'科技媒体': 4, '商业媒体': 3, '新闻媒体': 1},
            'focus_analysis': [{'focus': '新品发布', 'mentions': 5, 'percentage': 62.5}],
            'articles': [
                {'title': 'BrandA Launches New Product', 'source': 'techcrunch.com', 'media_tier': 'Tier 1', 'media_type': '科技媒体', 'published_date': '2025-05-15T10:00:00Z'}
            ]
        },
        'meta_ads': {
            'total_ads': 25,
            'new_ads': 10,
            'main_products': ['Product X', 'Product Y'],
            'platform_distribution': {'Facebook': 15, 'Instagram': 10},
            'ads_details': [
                {'creation_time': '2025-05-01', 'platforms': ['Facebook', 'Instagram'], 'body': 'Check out our new Product X! Limited time offer.'}
            ]
        }
    }
    
    filepath = generator.generate_report("BrandA", "2025-05", test_data)
    print(f"测试报告已生成: {filepath}")