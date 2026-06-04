"""
报告生成器 v2.0
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
    """竞品监测报告生成器 v2.0"""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_report(self, brand_name: str, period: str,
                       start_date: str, end_date: str,
                       data: Dict) -> str:
        """生成完整报告"""
        lines = []

        # 1. 报告标题
        lines.extend(self._generate_header(brand_name, period, start_date, end_date))

        # 2. 执行摘要（LLM生成占位）
        lines.extend(self._generate_executive_summary(data, brand_name, period))

        # 3. 板块概览 Dashboard
        lines.extend(self._generate_dashboard(data))

        # 4. 各板块详细报告
        lines.extend(self._generate_brand_products_section(data.get('brand_products', {}), period))
        lines.extend(self._generate_social_media_section(data.get('social_media', {})))
        lines.extend(self._generate_influencer_section(data.get('influencers', {})))
        lines.extend(self._generate_ugc_section(data.get('ugc_sentiment', {})))
        lines.extend(self._generate_pr_section(data.get('pr_articles', {})))
        lines.extend(self._generate_meta_ads_section(data.get('meta_ads', {})))

        # 5. 附录
        lines.extend(self._generate_appendix(data))

        # 保存
        report_content = '\n'.join(lines)
        filename = f"{brand_name}_竞品监测报告_{period}.md"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"📄 报告已生成: {filepath}")
        return filepath

    def _generate_header(self, brand_name: str, period: str,
                         start_date: str, end_date: str) -> List[str]:
        year, month = period.split('-')
        return [
            f"# 📊 竞品监测报告 - {brand_name} - {year}年{month}月",
            "",
            f"> **监测周期**: {start_date} 至 {end_date}",
            f"> **报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"> **数据来源**: Apify (IG/TK/YT/Meta Ads) + 搜索引擎 (Reddit/PR)",
            f"> **架构版本**: v2.0 (Apify真实爬虫)",
            "",
            "---",
            "",
        ]

    def _generate_executive_summary(self, data: Dict, brand_name: str, period: str) -> List[str]:
        lines = [
            "## 📋 执行摘要",
            "",
            "> **[LLM将在此生成执行摘要]**",
            "> 根据以下各板块数据，生成2-3句话的高度概括：",
            "> - 核心推广动作",
            "> - 推广方向",
            "> - 主推产品",
            "> - 关键发现",
            "",
        ]

        # 数据概要供LLM参考
        key_findings = []

        # 品牌新品
        bp = data.get('brand_products', {})
        new_count = len(bp.get('new_products', []))
        if new_count:
            key_findings.append(f"- 📦 上线 **{new_count}** 款新品")

        # 社媒
        sm = data.get('social_media', {})
        ig = sm.get('instagram', {}).get('analysis', {})
        tk = sm.get('tiktok', {}).get('analysis', {})
        yt = sm.get('youtube', {}).get('analysis', {})
        total_posts = (ig.get('period_posts_count', 0) +
                      tk.get('period_posts_count', 0) +
                      yt.get('period_videos_count', 0))
        if total_posts:
            key_findings.append(f"- 📱 全平台发布 **{total_posts}** 条内容")

        # 红人
        inf = data.get('influencers', {})
        inf_count = inf.get('total_influencers', 0)
        if inf_count:
            key_findings.append(f"- 👥 合作红人 **{inf_count}** 位")

        # PR
        pr = data.get('pr_articles', {})
        pr_count = pr.get('total_articles', 0)
        if pr_count:
            key_findings.append(f"- 📰 PR稿件 **{pr_count}** 篇")

        # 广告
        ads = data.get('meta_ads', {})
        ads_count = ads.get('total_ads', 0)
        new_ads = ads.get('new_ads', 0)
        if ads_count:
            key_findings.append(f"- 🎯 Meta广告 **{ads_count}** 条（新上线 **{new_ads}** 条）")

        if not key_findings:
            key_findings.append("- 暂无核心发现")

        lines.extend(key_findings)
        lines.extend(["", "---", ""])
        return lines

    def _generate_dashboard(self, data: Dict) -> List[str]:
        lines = [
            "## 📱 板块概览 Dashboard",
            "",
            "| 板块 | 核心指标 | 数值 | 备注 |",
            "|------|---------|------|------|",
        ]

        bp = data.get('brand_products', {})
        lines.append(f"| 📦 品牌新品动向 | 新品数量 | {len(bp.get('new_products', []))} | |")

        sm = data.get('social_media', {})
        ig = sm.get('instagram', {}).get('analysis', {})
        tk = sm.get('tiktok', {}).get('analysis', {})
        yt = sm.get('youtube', {}).get('analysis', {})
        total_posts = (ig.get('period_posts_count', 0) +
                      tk.get('period_posts_count', 0) +
                      yt.get('period_videos_count', 0))
        lines.append(f"| 📊 社媒数据表现 | 总Post数 | {total_posts} | IG+TK+YT |")

        inf = data.get('influencers', {})
        lines.append(f"| 👥 红人合作数据 | 合作红人 | {inf.get('total_influencers', 0)} | IG Tag区 |")

        ugc = data.get('ugc_sentiment', {})
        reddit_count = len(ugc.get('posts', []))
        lines.append(f"| 💬 UGC舆情监测 | Reddit提及 | {reddit_count} | |")

        pr = data.get('pr_articles', {})
        lines.append(f"| 📰 PR稿件监测 | PR篇数 | {pr.get('total_articles', 0)} | |")

        ads = data.get('meta_ads', {})
        lines.append(f"| 🎯 Meta广告监测 | 广告条数 | {ads.get('total_ads', 0)} | 新增{ads.get('new_ads', 0)} |")

        lines.extend(["", "---", ""])
        return lines

    def _generate_brand_products_section(self, data: Dict, period: str) -> List[str]:
        lines = [
            "## 📦 1. 品牌新品动向",
            "",
            "> **板块总结**: [LLM生成]",
            "",
        ]

        new_products = data.get('new_products', [])
        main_products = data.get('main_products', [])

        if new_products:
            lines.append("### 新品上线列表")
            lines.append("")
            lines.append("| 来源 | 内容摘要 | 日期 | 链接 |")
            lines.append("|------|---------|------|------|")
            for p in new_products[:10]:
                lines.append(f"| {p.get('source', 'N/A')} | "
                           f"{(p.get('caption', '') or p.get('selling_point', ''))[:50]} | "
                           f"{p.get('date', 'N/A')} | "
                           f"[链接]({p.get('url', '#')}) |")
            lines.append("")
        else:
            lines.append("> 本月未发现新品上线")
            lines.append("")

        if main_products:
            lines.append("### 近期主推产品")
            lines.append("")
            for i, product in enumerate(main_products[:5], 1):
                lines.append(f"{i}. **{product}**")
            lines.append("")

        lines.extend(["---", ""])
        return lines

    def _generate_social_media_section(self, data: Dict) -> List[str]:
        lines = [
            "## 📊 2. 社媒数据表现",
            "",
            "> **板块总结**: [LLM生成]",
            "",
        ]

        # 核心数据 Dashboard
        lines.append("### 核心数据 Dashboard")
        lines.append("")
        lines.append("| 平台 | 粉丝数 | 周期内Post | 平均点赞 | 平均评论 | 发布频次 |")
        lines.append("|------|--------|-----------|---------|---------|---------|")

        sm = data
        for platform in ['instagram', 'tiktok', 'youtube']:
            platform_data = sm.get(platform, {})
            if 'error' in platform_data:
                lines.append(f"| {platform.upper()} | ❌ 采集失败 | - | - | - | - |")
                continue

            analysis = platform_data.get('analysis', {})
            profile = platform_data.get('profile', {})

            followers = 'N/A'
            if profile:
                followers = profile.get('followersCount',
                            profile.get('fans',
                            profile.get('followers', 'N/A')))
                if isinstance(followers, int):
                    followers = f"{followers:,}"

            posts_count = analysis.get('period_posts_count',
                         analysis.get('period_videos_count', 0))
            avg_likes = analysis.get('avg_likes', 0)
            avg_comments = analysis.get('avg_comments', 0)
            frequency = analysis.get('posting_frequency', 0)

            lines.append(f"| {platform.upper()} | {followers} | {posts_count} | "
                       f"{avg_likes:,} | {avg_comments:,} | {frequency}/天 |")

        lines.append("")

        # 高互动帖文
        for platform in ['instagram', 'tiktok', 'youtube']:
            platform_data = sm.get(platform, {})
            analysis = platform_data.get('analysis', {})
            top_key = 'top_posts' if platform != 'youtube' else 'top_videos'
            top_items = analysis.get(top_key, [])

            if top_items:
                lines.append(f"### {platform.upper()} 高互动内容 Top 5")
                lines.append("")
                lines.append("| # | 互动量 | 内容摘要 | 链接 |")
                lines.append("|---|--------|---------|------|")

                for i, item in enumerate(top_items[:5], 1):
                    likes = item.get('likesCount', item.get('likes', item.get('diggCount', 0)))
                    comments = item.get('commentsCount', item.get('comments', item.get('commentCount', 0)))
                    engagement = (likes if isinstance(likes, int) else 0) + (comments if isinstance(comments, int) else 0)
                    caption = (item.get('caption', '') or item.get('title', ''))[:50]
                    url = item.get('url', '#')

                    lines.append(f"| {i} | {engagement:,} | {caption}... | [链接]({url}) |")

                lines.append("")

        lines.extend(["---", ""])
        return lines

    def _generate_influencer_section(self, data: Dict) -> List[str]:
        lines = [
            "## 👥 3. 红人合作数据",
            "",
            "> **板块总结**: [LLM生成]",
            "> 数据来源: Instagram Tagged区（别人tag了品牌的帖子）",
            "",
        ]

        total = data.get('total_influencers', 0)
        exposure = data.get('total_exposure', 0)
        tier_dist = data.get('tier_distribution', {})

        lines.append("### 核心数据 Dashboard")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 红人总数 | {total} |")
        lines.append(f"| 总曝光(粉丝数之和) | {exposure:,} |")
        for tier, count in tier_dist.items():
            lines.append(f"| {tier} | {count} |")
        lines.append("")

        # 红人明细
        influencer_list = data.get('influencer_list', [])
        if influencer_list:
            lines.append("### 红人明细列表")
            lines.append("")
            lines.append("| # | 红人账号 | 粉丝数 | 量级 | 合作类型 | 帖子数 | 总互动 |")
            lines.append("|---|---------|--------|------|---------|--------|--------|")

            for i, inf in enumerate(influencer_list[:20], 1):
                username = inf.get('username', 'N/A')
                followers = inf.get('followers', 0)
                tier = inf.get('tier', 'N/A')
                collab = inf.get('collab_type', 'N/A')
                post_count = len(inf.get('posts', []))
                engagement = inf.get('total_engagement', 0)

                lines.append(f"| {i} | @{username} | {followers:,} | {tier} | {collab} | "
                           f"{post_count} | {engagement:,} |")

            lines.append("")

        # 高互动tagged帖子
        top_tagged = data.get('top_tagged_posts', [])
        if top_tagged:
            lines.append("### 高互动合作帖子")
            lines.append("")
            for i, post in enumerate(top_tagged[:5], 1):
                lines.append(f"**{i}. @{post.get('username', 'N/A')}** "
                           f"(互动: {post.get('engagement', 0):,})")
                lines.append(f"- 内容: {post.get('caption', '')[:80]}...")
                lines.append(f"- 付费合作: {'是' if post.get('is_paid_partnership') else '否'}")
                lines.append(f"- 链接: {post.get('url', 'N/A')}")
                lines.append("")

        # 脚本拆解占位
        lines.append("### 视频脚本拆解")
        lines.append("")
        lines.append("> **[LLM将在此生成高互动视频脚本拆解]**")
        lines.append("")

        lines.extend(["---", ""])
        return lines

    def _generate_ugc_section(self, data: Dict) -> List[str]:
        lines = [
            "## 💬 4. UGC舆情监测",
            "",
            "> **板块总结**: [LLM生成]",
            "",
        ]

        sentiment = data.get('sentiment_analysis', {})
        posts = data.get('posts', [])

        # 情感分析
        if sentiment:
            lines.append("### 情感分布")
            lines.append("")
            lines.append("| 情感 | 数量 | 占比 |")
            lines.append("|------|------|------|")
            lines.append(f"| 😊 正面 | {sentiment.get('positive', 0)} | {sentiment.get('positive_rate', 0)}% |")
            lines.append(f"| 😐 中性 | {sentiment.get('neutral', 0)} | {sentiment.get('neutral_rate', 0)}% |")
            lines.append(f"| 😞 负面 | {sentiment.get('negative', 0)} | {sentiment.get('negative_rate', 0)}% |")
            lines.append("")

        # Reddit帖子
        if posts:
            lines.append("### Reddit 讨论帖子")
            lines.append("")
            lines.append("| # | 标题 | Subreddit | 链接 |")
            lines.append("|---|------|-----------|------|")

            for i, post in enumerate(posts[:15], 1):
                title = post.get('title', '')[:60]
                sub = post.get('subreddit', '')
                url = post.get('url', '#')
                lines.append(f"| {i} | {title} | r/{sub} | [链接]({url}) |")

            lines.append("")

        lines.extend(["---", ""])
        return lines

    def _generate_pr_section(self, data: Dict) -> List[str]:
        lines = [
            "## 📰 5. PR稿件监测",
            "",
            "> **板块总结**: [LLM生成]",
            "",
        ]

        total = data.get('total_articles', 0)
        tier_dist = data.get('tier_distribution', {})
        type_dist = data.get('type_distribution', {})

        lines.append("### 核心数据 Dashboard")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| PR篇数 | {total} |")
        for tier, count in tier_dist.items():
            lines.append(f"| {tier}媒体 | {count}篇 |")
        for mtype, count in type_dist.items():
            lines.append(f"| {mtype} | {count}篇 |")
        lines.append("")

        # 推广重点
        focus = data.get('focus_analysis', [])
        if focus:
            lines.append("### 推广重点分析")
            lines.append("")
            lines.append("| 推广方向 | 提及次数 | 占比 |")
            lines.append("|---------|---------|------|")
            for f in focus[:5]:
                lines.append(f"| {f.get('focus', 'N/A')} | {f.get('mentions', 0)} | {f.get('percentage', 0)}% |")
            lines.append("")

        # 稿件列表
        articles = data.get('articles', [])
        if articles:
            lines.append("### PR稿件列表")
            lines.append("")
            lines.append("| 标题 | 媒体 | 层级 | 类型 | 链接 |")
            lines.append("|------|------|------|------|------|")
            for article in articles[:15]:
                title = article.get('title', '')[:40]
                source = article.get('source', 'N/A')
                tier = article.get('media_tier', 'N/A')
                mtype = article.get('media_type', 'N/A')
                url = article.get('url', '#')
                lines.append(f"| {title} | {source} | {tier} | {mtype} | [链接]({url}) |")
            lines.append("")

        lines.extend(["---", ""])
        return lines

    def _generate_meta_ads_section(self, data: Dict) -> List[str]:
        lines = [
            "## 🎯 6. Meta广告监测",
            "",
            "> **板块总结**: [LLM生成]",
            "",
        ]

        total = data.get('total_ads', 0)
        new_ads = data.get('new_ads', 0)
        active = data.get('active_ads', 0)
        main_products = data.get('main_products', [])

        lines.append("### 核心数据 Dashboard")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 广告总条数 | {total} |")
        lines.append(f"| 新上线广告 | {new_ads} |")
        lines.append(f"| 当前活跃广告 | {active} |")

        # 素材类型分布
        creative_dist = data.get('creative_type_dist', {})
        for ctype, count in creative_dist.items():
            lines.append(f"| 素材类型-{ctype} | {count} |")

        # 平台分布
        platform_dist = data.get('platform_dist', {})
        for platform, count in platform_dist.items():
            lines.append(f"| 投放平台-{platform} | {count} |")

        lines.append("")

        # CTA分析
        cta = data.get('cta_analysis', {})
        if cta:
            lines.append("### CTA分析")
            lines.append("")
            lines.append("| CTA类型 | 次数 |")
            lines.append("|---------|------|")
            for cta_type, count in sorted(cta.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"| {cta_type} | {count} |")
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
            lines.append("### 广告素材分析 (Top 10)")
            lines.append("")

            for i, ad in enumerate(ads_details[:10], 1):
                lines.append(f"**广告 {i}**")
                lines.append(f"- 投放开始: {ad.get('startDate', 'N/A')}")
                lines.append(f"- 活跃状态: {'✅ 活跃' if ad.get('isActive') else '⏸️ 不活跃'}")
                lines.append(f"- 平台: {', '.join(ad.get('platforms', []))}")
                lines.append(f"- 格式: {ad.get('displayFormat', 'N/A')}")
                lines.append(f"- 标题: {ad.get('title', 'N/A')}")
                lines.append(f"- 文案: {(ad.get('bodyText', '') or '')[:100]}...")
                lines.append(f"- CTA: {ad.get('ctaText', 'N/A')}")
                if ad.get('linkUrl'):
                    lines.append(f"- 落地页: [链接]({ad.get('linkUrl')})")
                if ad.get('imageUrls'):
                    lines.append(f"- 图片: {len(ad['imageUrls'])}张")
                if ad.get('videoUrls'):
                    lines.append(f"- 视频: {len(ad['videoUrls'])}个")
                lines.append(f"- [Ad Library链接]({ad.get('adLibraryUrl', '#')})")
                lines.append("")

        # 脚本拆解占位
        lines.append("### 视频广告脚本拆解")
        lines.append("")
        lines.append("> **[LLM将在此生成视频广告脚本结构拆解]**")
        lines.append("")

        lines.extend(["---", ""])
        return lines

    def _generate_appendix(self, data: Dict) -> List[str]:
        return [
            "## 📌 附录",
            "",
            "### 数据来源说明",
            "",
            "| 板块 | 数据来源 | 采集方式 | Actor/API |",
            "|------|---------|---------|-----------|",
            "| 品牌新品动向 | Instagram + 官网 | Apify Actor | `apify/instagram-post-scraper` + fetch |",
            "| 社媒数据(IG) | Instagram | Apify Actor | `apify/instagram-profile-scraper` + `apify/instagram-post-scraper` |",
            "| 社媒数据(TK) | TikTok | Apify Actor | `apify/tiktok-profile-scraper` |",
            "| 社媒数据(YT) | YouTube | Apify Actor | `streamers/youtube-scraper` |",
            "| 红人合作 | Instagram Tag区 | Apify Actor | `scrapio/instagram-tagged-mentions-posts-scraper` |",
            "| UGC舆情 | Reddit | 搜索引擎 | `site:reddit.com 搜索` |",
            "| PR稿件 | 新闻搜索 | 搜索引擎 | `品牌名 press release 搜索` |",
            "| Meta广告 | Facebook Ad Library | Apify Actor | `automation-lab/facebook-ads-library` |",
            "",
            "### 数据限制声明",
            "",
            "> - Instagram数据依赖Apify Actor，偶尔可能因平台反爬导致部分数据缺失",
            "> - TikTok Actor对频繁调用有限制",
            "> - Reddit舆情基于搜索引擎，可能遗漏部分讨论",
            "> - Meta Ad Library仅包含公开广告数据，不含投放预算精确数据",
            "> - 红人数据来自IG Tag区，不包含品牌@mention的内容",
            "> - 情感分析基于关键词预分类，LLM深度分析可提升准确度",
            "",
            "### 方法论",
            "",
            "> - 红人量级划分: Nano(<1K), Micro(1K-100K), Macro(100K-1M), Mega(>1M)",
            "> - 媒体层级: Tier1(Top主流媒体), Tier2(知名垂直), Tier3(小众/垂直)",
            "> - 内容分类将由LLM执行: product_review/sponsorship/campaign/giveaway/educational/other",
            "> - 脚本拆解将分析: Hook→痛点→方案→信任背书→CTA",
            "",
            "---",
            "",
            f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 架构版本: v2.0*",
            "",
        ]
