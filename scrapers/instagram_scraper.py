"""
Instagram 爬虫 v2.0
通过Apify Actor抓取：Profile + Posts + Tagged区
修复v1.0 _sharedData失效问题
"""
import time
import re
import requests
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InstagramScraper:
    """Instagram数据采集 - 基于Apify Actor"""

    def __init__(self, apify_client, config: Dict = None):
        """
        Args:
            apify_client: ApifyClient实例
            config: 采集配置
        """
        self.client = apify_client
        self.config = config or {}
        self.max_posts = self.config.get('max_posts_per_profile', 60)
        self.max_tagged = self.config.get('max_tagged_posts', 100)

    def get_profile(self, username: str) -> Optional[Dict]:
        """
        获取Instagram账号信息

        使用Actor: apify/instagram-profile-scraper
        输入: usernames列表
        输出: profile信息 + 最近12条帖子概要
        """
        logger.info(f"[IG Profile] 采集: @{username}")

        run_input = {
            "usernames": [username],
        }

        results = self.client.run_actor(
            actor_id="apify/instagram-profile-scraper",
            run_input=run_input,
            timeout=120
        )

        if not results:
            logger.warning(f"[IG Profile] Apify无结果，尝试网页抓取降级...")
            profile = self._get_profile_fallback(username)
            if profile:
                return profile
            logger.error(f"[IG Profile] 采集失败: @{username}")
            return None

        profile = results[0] if results else None
        if profile:
            logger.info(f"[IG Profile] ✅ @{username}: {profile.get('followersCount', 'N/A')} 粉丝, {profile.get('postsCount', 'N/A')} 帖子")

        return profile

    def get_posts(self, username: str, max_posts: int = None) -> List[Dict]:
        """
        获取Instagram帖子详情

        使用Actor: apify/instagram-post-scraper
        输入: usernames + maxPosts
        输出: 帖子详情列表(含caption, likes, comments, mentions, tagged users等)
        """
        max_posts = max_posts or self.max_posts
        logger.info(f"[IG Posts] 采集: @{username}, 最多{max_posts}条")

        run_input = {
            "usernames": [username],
            "maxPosts": max_posts,
        }

        results = self.client.run_actor(
            actor_id="apify/instagram-post-scraper",
            run_input=run_input,
            timeout=300
        )

        if not results:
            logger.warning(f"[IG Posts] Apify无结果，尝试网页抓取降级...")
            results = self._get_posts_fallback(username, max_posts)

        if not results:
            logger.warning(f"[IG Posts] 无结果: @{username}")
            return []

        logger.info(f"[IG Posts] ✅ @{username}: {len(results)} 条帖子")
        return results

    def get_tagged_posts(self, username: str, max_posts: int = None) -> List[Dict]:
        """
        获取Tagged区帖子（别人tag了该品牌的帖子）
        ★ 这是红人识别的核心数据源 ★

        使用Actor: scrapio/instagram-tagged-mentions-posts-scraper
        输入: urlsOrKeywords=[username]
        输出: tagged帖子列表，含owner信息、is_paid_partnership、is_ad等
        """
        max_posts = max_posts or self.max_tagged
        logger.info(f"[IG Tagged] 采集: @{username} 的tag区, 最多{max_posts}条")

        run_input = {
            "urlsOrKeywords": [username],
            "proxyConfiguration": {
                "useApifyProxy": True
            }
        }

        results = self.client.run_actor(
            actor_id="scrapio/instagram-tagged-mentions-posts-scraper",
            run_input=run_input,
            timeout=300
        )

        if not results:
            logger.warning(f"[IG Tagged] 无结果: @{username}")
            return []

        # 结果可能是嵌套结构（metadata + posts）
        tagged_posts = []
        for item in results:
            if 'posts' in item:
                tagged_posts.extend(item['posts'])
            else:
                tagged_posts.append(item)

        logger.info(f"[IG Tagged] ✅ @{username}: {len(tagged_posts)} 条tagged帖子")
        return tagged_posts[:max_posts]

    def _get_profile_fallback(self, username: str) -> Optional[Dict]:
        """
        Instagram Profile网页抓取降级方案

        尝试从Instagram页面HTML中提取sharedData
        注意：Instagram可能要求登录，此方法可能不稳定
        """
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            })

            url = f"https://www.instagram.com/{username}/"
            resp = session.get(url, timeout=15, allow_redirects=True)

            if resp.status_code != 200:
                logger.warning(f"[IG Profile Fallback] HTTP {resp.status_code}")
                return None

            html = resp.text

            # 尝试提取 window._sharedData
            shared_data_match = re.search(
                r'window\._sharedData\s*=\s*({.+?})\s*;</script>',
                html, re.DOTALL
            )

            if shared_data_match:
                try:
                    shared_data = json.loads(shared_data_match.group(1))
                    user_data = (shared_data
                                 .get('entry_data', {})
                                 .get('ProfilePage', [{}])[0]
                                 .get('graphql', {})
                                 .get('user', {}))

                    if user_data:
                        profile = {
                            'username': user_data.get('username', username),
                            'fullName': user_data.get('full_name', ''),
                            'biography': user_data.get('biography', ''),
                            'followersCount': user_data.get('edge_followed_by', {}).get('count', 0),
                            'followsCount': user_data.get('edge_follow', {}).get('count', 0),
                            'postsCount': user_data.get('edge_owner_to_timeline_media', {}).get('count', 0),
                            'profilePicUrl': user_data.get('profile_pic_url', ''),
                            'isVerified': user_data.get('is_verified', False),
                            'isPrivate': user_data.get('is_private', False),
                            'externalUrl': user_data.get('external_url', ''),
                            'source': 'ig_web_fallback'
                        }
                        logger.info(f"[IG Profile Fallback] ✅ @{username}: {profile['followersCount']} 粉丝")
                        return profile
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"[IG Profile Fallback] sharedData解析失败: {e}")

            # 尝试从 ld+json 提取基本信息
            ld_match = re.search(
                r'<script type="application/ld\+json">({.+?})</script>',
                html, re.DOTALL
            )
            if ld_match:
                try:
                    ld_data = json.loads(ld_match.group(1))
                    if ld_data.get('@type') == 'ProfilePage':
                        profile = {
                            'username': username,
                            'fullName': ld_data.get('name', ''),
                            'biography': ld_data.get('description', ''),
                            'followersCount': 0,
                            'followsCount': 0,
                            'postsCount': 0,
                            'profilePicUrl': ld_data.get('image', {}).get('contentUrl', ''),
                            'isVerified': False,
                            'isPrivate': False,
                            'externalUrl': ld_data.get('url', ''),
                            'source': 'ig_ldjson_fallback'
                        }
                        logger.info(f"[IG Profile Fallback] ✅ @{username} (ld+json, 粉丝数不可用)")
                        return profile
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"[IG Profile Fallback] ld+json解析失败: {e}")

            logger.warning(f"[IG Profile Fallback] 无法从页面提取数据: @{username}")
            return None

        except Exception as e:
            logger.error(f"[IG Profile Fallback] 降级方案失败: {e}")
            return None

    def _get_posts_fallback(self, username: str, max_posts: int = 20) -> List[Dict]:
        """
        Instagram Posts网页抓取降级方案

        尝试从Instagram页面HTML中提取帖子信息
        """
        posts = []
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            })

            url = f"https://www.instagram.com/{username}/"
            resp = session.get(url, timeout=15, allow_redirects=True)

            if resp.status_code != 200:
                logger.warning(f"[IG Posts Fallback] HTTP {resp.status_code}")
                return []

            html = resp.text

            # 尝试提取 window._sharedData 中的帖子
            shared_data_match = re.search(
                r'window\._sharedData\s*=\s*({.+?})\s*;</script>',
                html, re.DOTALL
            )

            if shared_data_match:
                try:
                    shared_data = json.loads(shared_data_match.group(1))
                    edges = (shared_data
                             .get('entry_data', {})
                             .get('ProfilePage', [{}])[0]
                             .get('graphql', {})
                             .get('user', {})
                             .get('edge_owner_to_timeline_media', {})
                             .get('edges', []))

                    for edge in edges[:max_posts]:
                        node = edge.get('node', {})
                        posts.append({
                            'id': node.get('id', ''),
                            'shortCode': node.get('shortcode', ''),
                            'caption': (node.get('edge_media_to_caption', {})
                                        .get('edges', [{}])[0]
                                        .get('node', {})
                                        .get('text', '')),
                            'likesCount': node.get('edge_media_preview_like', {}).get('count', 0),
                            'commentsCount': node.get('edge_media_to_comment', {}).get('count', 0),
                            'timestamp': str(node.get('taken_at_timestamp', '')),
                            'type': 'Video' if node.get('is_video', False) else 'Image',
                            'displayUrl': node.get('display_url', ''),
                            'url': f"https://www.instagram.com/p/{node.get('shortcode', '')}/",
                            'source': 'ig_web_fallback'
                        })

                    if posts:
                        logger.info(f"[IG Posts Fallback] ✅ @{username}: {len(posts)} 条帖子")
                        return posts
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"[IG Posts Fallback] sharedData解析失败: {e}")

            logger.warning(f"[IG Posts Fallback] 无法从页面提取帖子: @{username}")
            return []

        except Exception as e:
            logger.error(f"[IG Posts Fallback] 降级方案失败: {e}")
            return []

    def analyze_posts(self, posts: List[Dict], period_start: str, period_end: str) -> Dict:
        """
        分析帖子数据，筛选监测周期内的帖子

        Args:
            posts: 帖子列表
            period_start: 周期开始 YYYY-MM-DD
            period_end: 周期结束 YYYY-MM-DD
        """
        if not posts:
            return {
                'total_posts': 0,
                'period_posts': [],
                'avg_likes': 0,
                'avg_comments': 0,
                'video_posts': 0,
                'image_posts': 0,
                'top_posts': [],
                'posting_frequency': 0,
                'content_types': {}
            }

        # 筛选周期内帖子
        period_posts = []
        for post in posts:
            timestamp = post.get('timestamp', '')
            if not timestamp:
                continue
            try:
                post_date = timestamp[:10] if len(timestamp) >= 10 else ''
                if period_start <= post_date <= period_end:
                    period_posts.append(post)
            except:
                # 保留无法判断日期的帖子
                period_posts.append(post)

        total = len(period_posts)
        if total == 0:
            return {
                'total_posts': len(posts),
                'period_posts': [],
                'avg_likes': 0,
                'avg_comments': 0,
                'video_posts': 0,
                'image_posts': 0,
                'top_posts': [],
                'posting_frequency': 0,
                'content_types': {}
            }

        # 统计
        total_likes = sum(p.get('likesCount', p.get('likes', 0)) for p in period_posts)
        total_comments = sum(p.get('commentsCount', p.get('comments', 0)) for p in period_posts)

        video_posts = sum(1 for p in period_posts if p.get('type') in ('Video', 'Reel', 'IGTV'))
        image_posts = sum(1 for p in period_posts if p.get('type') in ('Image', 'Sidecar'))

        # 内容类型分布
        content_types = {}
        for p in period_posts:
            ptype = p.get('type', 'Unknown')
            content_types[ptype] = content_types.get(ptype, 0) + 1

        # 高互动帖子Top 10
        sorted_posts = sorted(period_posts,
                             key=lambda x: x.get('likesCount', x.get('likes', 0)) + x.get('commentsCount', x.get('comments', 0)),
                             reverse=True)
        top_posts = sorted_posts[:10]

        # 发布频次
        posting_frequency = round(total / 30, 2)  # 简化：按30天算

        return {
            'total_posts': len(posts),
            'period_posts_count': total,
            'period_posts': period_posts,
            'avg_likes': total_likes // max(total, 1),
            'avg_comments': total_comments // max(total, 1),
            'video_posts': video_posts,
            'image_posts': image_posts,
            'top_posts': top_posts,
            'posting_frequency': posting_frequency,
            'content_types': content_types
        }

    def identify_influencers(self, tagged_posts: List[Dict], brand_username: str) -> Dict:
        """
        从Tagged区帖子中识别合作红人

        关键逻辑：tagged_posts中每条帖子的owner就是tag了品牌的人
        这才是需求里说的"看品牌tag区域识别合作红人"

        Args:
            tagged_posts: Tagged区帖子列表
            brand_username: 品牌自己的IG账号（排除品牌自己）
        """
        if not tagged_posts:
            return {
                'total_influencers': 0,
                'total_exposure': 0,
                'platform_distribution': {},
                'tier_distribution': {},
                'influencer_list': [],
                'top_tagged_posts': []
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

        # 提取红人信息
        influencer_map = {}  # username -> info
        tier_distribution = {}
        total_exposure = 0
        analyzed_posts = []

        for post in tagged_posts:
            owner = post.get('owner', {})
            username = owner.get('username', '')
            if not username or username.lower() == brand_username.lower():
                continue  # 排除品牌自己的帖子

            followers = owner.get('edge_followed_by', {}).get('count',
                         owner.get('followersCount',
                         owner.get('followers', 0)))
            tier = get_tier(followers)

            # 判断合作类型
            is_paid = post.get('is_paid_partnership', False)
            is_ad = post.get('is_ad', False)
            is_affiliate = post.get('is_affiliate', False)

            if username not in influencer_map:
                influencer_map[username] = {
                    'username': username,
                    'full_name': owner.get('full_name', ''),
                    'followers': followers,
                    'tier': tier,
                    'is_verified': owner.get('is_verified', False),
                    'platform': 'Instagram',
                    'collab_type': 'paid' if is_paid else ('ad' if is_ad else ('affiliate' if is_affiliate else 'organic')),
                    'posts': [],
                    'total_engagement': 0
                }
                tier_distribution[tier] = tier_distribution.get(tier, 0) + 1
                total_exposure += followers

            # 关联帖子
            engagement = (post.get('like_count', post.get('likesCount', 0)) +
                         post.get('comment_count', post.get('commentsCount', 0)))
            influencer_map[username]['posts'].append({
                'short_code': post.get('short_code', post.get('shortCode', '')),
                'caption': (post.get('caption', '') or '')[:200],
                'likes': post.get('like_count', post.get('likesCount', 0)),
                'comments': post.get('comment_count', post.get('commentsCount', 0)),
                'views': post.get('video_view_count', post.get('videoViewCount', 0)),
                'is_paid_partnership': is_paid,
                'url': f"https://www.instagram.com/p/{post.get('short_code', post.get('shortCode', ''))}/"
            })
            influencer_map[username]['total_engagement'] += engagement

            analyzed_posts.append({
                'username': username,
                'tier': tier,
                'engagement': engagement,
                'caption': (post.get('caption', '') or '')[:100],
                'is_paid_partnership': is_paid,
                'url': f"https://www.instagram.com/p/{post.get('short_code', post.get('shortCode', ''))}/"
            })

        # 排序
        influencer_list = sorted(influencer_map.values(),
                                key=lambda x: x['total_engagement'],
                                reverse=True)

        # 高互动tagged帖子
        top_tagged = sorted(analyzed_posts, key=lambda x: x['engagement'], reverse=True)[:10]

        return {
            'total_influencers': len(influencer_map),
            'total_exposure': total_exposure,
            'platform_distribution': {'Instagram': len(influencer_map)},
            'tier_distribution': tier_distribution,
            'influencer_list': influencer_list,
            'top_tagged_posts': top_tagged
        }
