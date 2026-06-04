"""
YouTube 爬虫 v2.0
通过Apify Actor抓取YT频道视频
"""
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubeScraper:
    """YouTube数据采集 - 基于Apify Actor"""

    def __init__(self, apify_client, config: Dict = None):
        self.client = apify_client
        self.config = config or {}

    def get_channel_videos(self, channel_id: str, max_results: int = 50) -> List[Dict]:
        """
        获取YouTube频道视频

        使用Actor: streamers/youtube-scraper
        输入: searchQueries或startUrls
        输出: 视频详情列表
        """
        logger.info(f"[YT] 采集频道: {channel_id}")

        # 判断是搜索词还是URL
        if channel_id.startswith('http'):
            run_input = {
                "startUrls": [{"url": channel_id}],
                "maxResults": max_results,
            }
        else:
            # 使用频道名搜索
            search_query = channel_id.lstrip('@')
            run_input = {
                "searchQueries": [search_query],
                "maxResults": max_results,
            }

        results = self.client.run_actor(
            actor_id="streamers/youtube-scraper",
            run_input=run_input,
            timeout=300
        )

        if not results:
            logger.warning(f"[YT] 无结果: {channel_id}")
            return []

        logger.info(f"[YT] ✅ {channel_id}: {len(results)} 条结果")
        return results

    def analyze_videos(self, videos: List[Dict], period_start: str, period_end: str) -> Dict:
        """分析YouTube视频数据"""
        if not videos:
            return {
                'total_videos': 0,
                'period_videos_count': 0,
                'avg_views': 0,
                'avg_likes': 0,
                'top_videos': [],
                'posting_frequency': 0
            }

        # 筛选周期内视频
        period_videos = []
        for video in videos:
            publish_date = video.get('publishedAt', video.get('publishDate', ''))
            if not publish_date:
                continue
            try:
                post_date = str(publish_date)[:10]
                if period_start <= post_date <= period_end:
                    period_videos.append(video)
            except:
                period_videos.append(video)

        total = len(period_videos)
        total_views = sum(v.get('viewCount', v.get('views', 0)) or 0 for v in period_videos)
        total_likes = sum(v.get('likeCount', v.get('likes', 0)) or 0 for v in period_videos)

        sorted_videos = sorted(period_videos,
                              key=lambda x: x.get('viewCount', x.get('views', 0)) or 0,
                              reverse=True)

        return {
            'total_videos': len(videos),
            'period_videos_count': total,
            'avg_views': total_views // max(total, 1),
            'avg_likes': total_likes // max(total, 1),
            'top_videos': sorted_videos[:10],
            'posting_frequency': round(total / 30, 2)
        }
