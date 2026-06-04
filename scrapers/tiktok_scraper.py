"""
TikTok 爬虫 v2.0
通过Apify Actor抓取TK账号信息+帖子
"""
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TikTokScraper:
    """TikTok数据采集 - 基于Apify Actor"""

    def __init__(self, apify_client, config: Dict = None):
        self.client = apify_client
        self.config = config or {}
        self.max_posts = self.config.get('max_posts_per_profile', 60)

    def get_profile(self, username: str) -> Optional[Dict]:
        """
        获取TikTok账号信息+帖子

        使用Actor: apify/tiktok-profile-scraper
        输入: usernames列表
        输出: profile信息 + 最近帖子
        """
        logger.info(f"[TK Profile] 采集: @{username}")

        # 移除@前缀
        clean_username = username.lstrip('@')

        run_input = {
            "usernames": [clean_username],
            "resultsPerPage": self.max_posts,
        }

        results = self.client.run_actor(
            actor_id="apify/tiktok-profile-scraper",
            run_input=run_input,
            timeout=300
        )

        if not results:
            logger.warning(f"[TK Profile] 无结果: @{username}")
            return None

        profile = results[0] if results else None
        if profile:
            followers = profile.get('fans', profile.get('followersCount', 'N/A'))
            logger.info(f"[TK Profile] ✅ @{username}: {followers} 粉丝")

        return profile

    def get_posts(self, username: str, max_posts: int = None) -> List[Dict]:
        """获取TK帖子（通常包含在profile结果中）"""
        profile = self.get_profile(username)
        if not profile:
            return []

        # TK profile scraper通常返回的帖子在profile中
        posts = profile.get('latestPosts', profile.get('posts', []))
        max_posts = max_posts or self.max_posts
        return posts[:max_posts]

    def analyze_posts(self, posts: List[Dict], period_start: str, period_end: str) -> Dict:
        """分析TK帖子数据"""
        if not posts:
            return {
                'total_posts': 0,
                'period_posts_count': 0,
                'avg_likes': 0,
                'avg_comments': 0,
                'top_posts': [],
                'posting_frequency': 0
            }

        # 筛选周期内帖子
        period_posts = []
        for post in posts:
            create_time = post.get('createTime', post.get('createdAt', ''))
            if not create_time:
                continue
            try:
                if isinstance(create_time, (int, float)):
                    from datetime import datetime
                    post_date = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d')
                else:
                    post_date = str(create_time)[:10]

                if period_start <= post_date <= period_end:
                    period_posts.append(post)
            except:
                period_posts.append(post)

        total = len(period_posts)
        total_likes = sum(p.get('diggCount', p.get('likesCount', 0)) for p in period_posts)
        total_comments = sum(p.get('commentCount', p.get('commentsCount', 0)) for p in period_posts)
        total_views = sum(p.get('playCount', p.get('videoViewCount', 0)) for p in period_posts)

        sorted_posts = sorted(period_posts,
                             key=lambda x: x.get('diggCount', x.get('likesCount', 0)),
                             reverse=True)

        return {
            'total_posts': len(posts),
            'period_posts_count': total,
            'avg_likes': total_likes // max(total, 1),
            'avg_comments': total_comments // max(total, 1),
            'total_views': total_views,
            'top_posts': sorted_posts[:10],
            'posting_frequency': round(total / 30, 2)
        }
