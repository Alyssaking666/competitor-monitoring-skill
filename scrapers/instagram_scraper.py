"""
Instagram 爬虫
通过公开网页抓取品牌账号数据
注意：Instagram有反爬机制，需要控制请求频率
"""

import requests
import json
import re
import time
from typing import Dict, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InstagramScraper:
    """Instagram公开数据爬虫"""
    
    BASE_URL = "https://www.instagram.com"
    
    def __init__(self, delay: int = 3):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        })
    
    def get_profile_info(self, username: str) -> Optional[Dict]:
        """
        获取账号基本信息
        
        Args:
            username: Instagram账号名（不含@）
            
        Returns:
            账号信息字典
        """
        url = f"{self.BASE_URL}/{username}/"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # 从页面中提取sharedData
            html = response.text
            
            # 查找用户数据
            user_data = self._extract_user_data(html)
            
            if not user_data:
                logger.error(f"无法获取用户 {username} 的数据")
                return None
            
            profile = {
                'username': username,
                'full_name': user_data.get('full_name', ''),
                'biography': user_data.get('biography', ''),
                'followers': user_data.get('edge_followed_by', {}).get('count', 0),
                'following': user_data.get('edge_follow', {}).get('count', 0),
                'posts_count': user_data.get('edge_owner_to_timeline_media', {}).get('count', 0),
                'is_verified': user_data.get('is_verified', False),
                'profile_pic_url': user_data.get('profile_pic_url', ''),
                'external_url': user_data.get('external_url', '')
            }
            
            logger.info(f"获取到 {username} 的信息: {profile['followers']} 粉丝")
            return profile
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取 {username} 信息失败: {e}")
            return None
    
    def get_recent_posts(self, username: str, count: int = 30) -> List[Dict]:
        """
        获取最近发布的帖子
        
        Args:
            username: Instagram账号名
            count: 获取帖子数量
            
        Returns:
            帖子列表
        """
        posts = []
        
        # 首先获取用户页面
        url = f"{self.BASE_URL}/{username}/"
        
        try:
            response = self.session.get(url, timeout=30)
            html = response.text
            
            # 提取用户ID和初始帖子数据
            user_data = self._extract_user_data(html)
            
            if not user_data:
                return posts
            
            user_id = user_data.get('id')
            
            # 从初始数据中提取帖子
            media_edges = user_data.get('edge_owner_to_timeline_media', {}).get('edges', [])
            
            for edge in media_edges[:count]:
                node = edge.get('node', {})
                post = self._parse_post_node(node)
                if post:
                    posts.append(post)
            
            logger.info(f"获取到 {username} 的 {len(posts)} 条帖子")
            return posts
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取 {username} 帖子失败: {e}")
            return posts
    
    def get_tagged_users(self, username: str, count: int = 50) -> List[Dict]:
        """
        获取品牌账号tag区域出现的账号（合作红人）
        
        Args:
            username: Instagram账号名
            count: 获取数量
            
        Returns:
            被标记的账号列表
        """
        tagged_users = []
        
        try:
            # 访问tagged页面
            url = f"{self.BASE_URL}/{username}/tagged/"
            response = self.session.get(url, timeout=30)
            html = response.text
            
            # 提取被标记的帖子
            user_data = self._extract_user_data(html)
            
            if not user_data:
                return tagged_users
            
            # 从被标记的帖子中提取用户信息
            # 注意：这里需要访问具体的帖子来获取标记信息
            # 简化实现：从帖子描述中提取@提及
            
            posts = self.get_recent_posts(username, count)
            
            mentioned_users = set()
            for post in posts:
                caption = post.get('caption', '')
                mentions = re.findall(r'@(\w+)', caption)
                mentioned_users.update(mentions)
            
            # 过滤掉品牌自己的账号
            mentioned_users.discard(username)
            
            # 获取提及用户的基本信息
            for mentioned in list(mentioned_users)[:count]:
                user_info = self.get_profile_info(mentioned)
                if user_info:
                    tagged_users.append({
                        'username': mentioned,
                        'full_name': user_info.get('full_name', ''),
                        'followers': user_info.get('followers', 0),
                        'is_verified': user_info.get('is_verified', False)
                    })
                time.sleep(self.delay)
            
            logger.info(f"获取到 {len(tagged_users)} 个合作红人账号")
            return tagged_users
            
        except Exception as e:
            logger.error(f"获取tagged users失败: {e}")
            return tagged_users
    
    def _extract_user_data(self, html: str) -> Optional[Dict]:
        """从HTML中提取用户数据"""
        try:
            # 方法1: 查找sharedData
            match = re.search(r'window\._sharedData\s*=\s*({.+?});</script>', html)
            if match:
                data = json.loads(match.group(1))
                user_data = data.get('entry_data', {}).get('ProfilePage', [{}])[0].get('graphql', {}).get('user', {})
                return user_data
            
            # 方法2: 查找额外的数据
            match = re.search(r'"user":\s*({"biography".+?})', html)
            if match:
                # 需要更精确的匹配
                pass
            
            return None
            
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"解析用户数据失败: {e}")
            return None
    
    def _parse_post_node(self, node: Dict) -> Optional[Dict]:
        """解析帖子节点"""
        try:
            post = {
                'id': node.get('id', ''),
                'shortcode': node.get('shortcode', ''),
                'url': f"https://www.instagram.com/p/{node.get('shortcode', '')}/",
                'timestamp': node.get('taken_at_timestamp', 0),
                'likes': node.get('edge_liked_by', {}).get('count', 0),
                'comments': node.get('edge_media_to_comment', {}).get('count', 0),
                'caption': '',
                'is_video': node.get('is_video', False),
                'video_views': node.get('video_view_count', 0) if node.get('is_video') else 0,
                'media_url': node.get('display_url', ''),
            }
            
            # 提取caption
            edge_media_to_caption = node.get('edge_media_to_caption', {}).get('edges', [])
            if edge_media_to_caption:
                post['caption'] = edge_media_to_caption[0].get('node', {}).get('text', '')
            
            # 计算互动率（简化）
            # 实际互动率需要粉丝数，这里先记录原始数据
            post['engagement'] = post['likes'] + post['comments']
            
            return post
            
        except Exception as e:
            logger.error(f"解析帖子失败: {e}")
            return None
    
    def analyze_posts(self, posts: List[Dict]) -> Dict:
        """
        分析帖子数据
        
        Returns:
            分析结果
        """
        if not posts:
            return {
                'total_posts': 0,
                'avg_likes': 0,
                'avg_comments': 0,
                'avg_engagement': 0,
                'video_posts': 0,
                'image_posts': 0,
                'top_posts': [],
                'posting_frequency': 0
            }
        
        total_posts = len(posts)
        total_likes = sum(p['likes'] for p in posts)
        total_comments = sum(p['comments'] for p in posts)
        total_engagement = sum(p['engagement'] for p in posts)
        
        video_posts = sum(1 for p in posts if p['is_video'])
        
        # 排序获取高互动帖子
        sorted_posts = sorted(posts, key=lambda x: x['engagement'], reverse=True)
        top_posts = sorted_posts[:10]
        
        # 计算发布频次（如果有时间数据）
        posting_frequency = 0
        if posts and posts[0].get('timestamp'):
            timestamps = [p['timestamp'] for p in posts if p.get('timestamp')]
            if len(timestamps) > 1:
                time_span = max(timestamps) - min(timestamps)
                days = time_span / (24 * 3600)
                posting_frequency = len(timestamps) / max(days, 1)
        
        return {
            'total_posts': total_posts,
            'avg_likes': total_likes // total_posts,
            'avg_comments': total_comments // total_posts,
            'avg_engagement': total_engagement // total_posts,
            'video_posts': video_posts,
            'image_posts': total_posts - video_posts,
            'top_posts': top_posts,
            'posting_frequency': round(posting_frequency, 2)
        }


if __name__ == "__main__":
    # 测试
    scraper = InstagramScraper()
    
    # 获取账号信息
    profile = scraper.get_profile_info("nike")
    if profile:
        print(json.dumps(profile, indent=2, ensure_ascii=False))
    
    # 获取最近帖子
    posts = scraper.get_recent_posts("nike", 10)
    analysis = scraper.analyze_posts(posts)
    print(json.dumps(analysis, indent=2, ensure_ascii=False))