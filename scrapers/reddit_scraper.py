"""
Reddit 爬虫
使用PRAW库调用Reddit API
需要注册应用获取client_id和client_secret
注册地址: https://www.reddit.com/prefs/apps
"""

import praw
import time
from datetime import datetime
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedditScraper:
    """Reddit数据爬虫"""
    
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        """
        初始化Reddit API客户端
        
        Args:
            client_id: Reddit应用ID
            client_secret: Reddit应用密钥
            user_agent: 用户代理字符串
        """
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        logger.info("Reddit API客户端初始化完成")
    
    def search_brand_mentions(self, 
                              brand_name: str,
                              product_keywords: List[str],
                              start_date: datetime,
                              end_date: datetime,
                              limit: int = 100) -> List[Dict]:
        """
        搜索品牌提及
        
        Args:
            brand_name: 品牌名称
            product_keywords: 产品关键词列表
            start_date: 开始日期
            end_date: 结束日期
            limit: 获取帖子数量
            
        Returns:
            帖子列表
        """
        all_posts = []
        
        # 构建搜索查询
        search_terms = [brand_name] + product_keywords
        
        # 搜索相关subreddit
        subreddits = [
            'all',  # 全站搜索
            'gadgets',
            'technology',
            'reviews',
            'BuyItForLife'
        ]
        
        for term in search_terms:
            for subreddit_name in subreddits[:3]:  # 限制搜索范围
                try:
                    logger.info(f"搜索: {term} in r/{subreddit_name}")
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    # 搜索帖子
                    search_results = subreddit.search(
                        term,
                        sort='new',
                        time_filter='month',
                        limit=limit // len(search_terms)
                    )
                    
                    for post in search_results:
                        # 检查日期范围
                        post_date = datetime.fromtimestamp(post.created_utc)
                        if start_date <= post_date <= end_date:
                            post_data = self._parse_post(post)
                            if post_data:
                                all_posts.append(post_data)
                    
                    time.sleep(1)  # 请求间隔
                    
                except Exception as e:
                    logger.error(f"搜索失败 {term} in r/{subreddit_name}: {e}")
                    continue
        
        # 去重
        seen_ids = set()
        unique_posts = []
        for post in all_posts:
            post_id = post.get('id', '')
            if post_id and post_id not in seen_ids:
                seen_ids.add(post_id)
                unique_posts.append(post)
        
        logger.info(f"共获取 {len(unique_posts)} 条唯一帖子")
        return unique_posts[:limit]
    
    def get_post_comments(self, post_id: str, limit: int = 50) -> List[Dict]:
        """
        获取帖子评论
        
        Args:
            post_id: 帖子ID
            limit: 评论数量
            
        Returns:
            评论列表
        """
        comments = []
        
        try:
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)  # 移除MoreComments
            
            for comment in submission.comments[:limit]:
                comment_data = {
                    'id': comment.id,
                    'author': str(comment.author) if comment.author else '[deleted]',
                    'body': comment.body,
                    'score': comment.score,
                    'created_utc': comment.created_utc,
                    'replies_count': len(comment.replies)
                }
                comments.append(comment_data)
                
        except Exception as e:
            logger.error(f"获取评论失败 {post_id}: {e}")
        
        return comments
    
    def _parse_post(self, post) -> Optional[Dict]:
        """解析帖子数据"""
        try:
            return {
                'id': post.id,
                'title': post.title,
                'body': post.selftext,
                'author': str(post.author) if post.author else '[deleted]',
                'subreddit': post.subreddit.display_name,
                'score': post.score,
                'upvote_ratio': post.upvote_ratio,
                'num_comments': post.num_comments,
                'url': post.url,
                'permalink': f"https://reddit.com{post.permalink}",
                'created_utc': post.created_utc,
                'created_date': datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
                'is_video': post.is_video,
                'media_url': post.url if not post.is_self else ''
            }
        except Exception as e:
            logger.error(f"解析帖子失败: {e}")
            return None
    
    def analyze_sentiment(self, posts: List[Dict]) -> Dict:
        """
        简单情感分析
        
        基于关键词的情感判断（简化版）
        实际使用建议接入OpenAI API或开源情感分析模型
        
        Returns:
            情感分析结果
        """
        if not posts:
            return {
                'total_posts': 0,
                'positive': 0,
                'negative': 0,
                'neutral': 0,
                'sentiment_score': 0,
                'key_topics': []
            }
        
        # 情感关键词
        positive_words = ['good', 'great', 'excellent', 'amazing', 'love', 'best', 
                         'recommend', 'awesome', 'perfect', 'happy', 'satisfied',
                         '喜欢', '推荐', '好用', '不错', '满意']
        
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'problem',
                         'issue', 'broken', 'disappointed', 'return', 'refund',
                         '差', '垃圾', '失望', '问题', '退货', '坏了']
        
        positive = 0
        negative = 0
        neutral = 0
        
        all_text = ''
        
        for post in posts:
            text = (post.get('title', '') + ' ' + post.get('body', '')).lower()
            all_text += text + ' '
            
            pos_count = sum(1 for word in positive_words if word in text)
            neg_count = sum(1 for word in negative_words if word in text)
            
            if pos_count > neg_count:
                positive += 1
            elif neg_count > pos_count:
                negative += 1
            else:
                neutral += 1
        
        total = len(posts)
        sentiment_score = (positive - negative) / total if total > 0 else 0
        
        # 提取热门话题（简单词频）
        import re
        from collections import Counter
        
        words = re.findall(r'\b\w+\b', all_text.lower())
        # 过滤常见停用词
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                     'through', 'during', 'before', 'after', 'above', 'below',
                     'between', 'under', 'and', 'but', 'or', 'yet', 'so',
                     'if', 'because', 'although', 'though', 'while', 'where',
                     'when', 'that', 'which', 'who', 'whom', 'whose', 'what',
                     'this', 'these', 'those', 'i', 'me', 'my', 'myself', 'we',
                     'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself',
                     'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself',
                     'it', 'its', 'itself', 'they', 'them', 'their', 'theirs',
                     'themselves', 'what', 'which', 'who', 'whom', 'this', 'that',
                     'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be',
                     'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does',
                     'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or',
                     'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for',
                     'with', 'about', 'against', 'between', 'into', 'through',
                     'during', 'before', 'after', 'above', 'below', 'to', 'from',
                     'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under',
                     'again', 'further', 'then', 'once', 'here', 'there', 'when',
                     'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few',
                     'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
                     'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't',
                     'just', 'don', 'now'}
        
        filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
        top_topics = Counter(filtered_words).most_common(10)
        
        return {
            'total_posts': total,
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'positive_rate': round(positive / total * 100, 2),
            'negative_rate': round(negative / total * 100, 2),
            'neutral_rate': round(neutral / total * 100, 2),
            'sentiment_score': round(sentiment_score, 2),
            'key_topics': [{'word': word, 'count': count} for word, count in top_topics]
        }


if __name__ == "__main__":
    # 测试
    import json
    
    scraper = RedditScraper(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        user_agent="CompetitorMonitor/1.0"
    )
    
    # 搜索品牌提及
    posts = scraper.search_brand_mentions(
        brand_name="example brand",
        product_keywords=["product x"],
        start_date=datetime(2025, 4, 1),
        end_date=datetime(2025, 5, 31),
        limit=50
    )
    
    # 情感分析
    sentiment = scraper.analyze_sentiment(posts)
    print(json.dumps(sentiment, indent=2, ensure_ascii=False))