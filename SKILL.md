---
name: competitor-monitoring
version: "2.0"
description: 竞品全维度监测Skill v2.0，基于Apify真实爬虫架构，覆盖品牌新品、社媒数据(IG/TK/YT/FB)、红人合作(tag区识别)、UGC舆情、PR稿件、Meta广告六大板块。每月1号出上月报告。Invoke when user needs to monitor competitor brand activities, social media performance, influencer campaigns, advertising strategies, or generate monthly competitor reports.
---

# 竞品监测 Skill v2.0

## 1. Skill 概述

本Skill用于执行竞品品牌的全维度监测，基于Apify真实爬虫+免费搜索API架构，覆盖6大核心板块，输出结构化的月度监测报告。

### 1.1 核心原则
- **真实爬虫**：所有社媒数据通过Apify Actor抓取，不依赖similarweb/modash等第三方分析工具
- **低成本可落地**：~$5-10/品牌/月，中小型公司可用
- **LLM增强分析**：利用Coze内置LLM做内容分类、情感分析、脚本拆解等深度分析

### 1.2 监测维度与数据源

| 板块 | 监测内容 | 数据源 | Apify Actor / API |
|------|---------|--------|-------------------|
| **品牌新品动向** | 新品上线时间、主推卖点、近期主推产品 | 品牌官网+社媒 | 官网fetch + IG Posts分析 |
| **社媒数据** | Post数量、涨粉数、曝光量、发布频次、高互动内容 | IG/TK/YT/FB | `apify/instagram-profile-scraper` + `apify/instagram-post-scraper` + `apify/tiktok-profile-scraper` + `streamers/youtube-scraper` |
| **红人合作** | 红人数量、曝光、量级、类型、推广产品、高互动视频 | IG Tagged区 | `scrapio/instagram-tagged-mentions-posts-scraper` + TK profile分析 |
| **UGC舆情** | Reddit讨论、用户反馈、评论区舆情 | Reddit+社媒评论 | 搜索引擎检索Reddit帖文 + `apify/instagram-comment-scraper` |
| **PR稿件** | PR篇数、媒体、量级、内容方向、推广重点 | 新闻搜索 | 搜索引擎检索PR新闻 |
| **Meta广告** | 广告条数、新广告、素材文案、主推产品 | Meta Ad Library | `automation-lab/facebook-ads-library` |

### 1.3 报告周期
- **监测周期**: 上月1日至上月最后一日
- **报告时间**: 每月1日生成并输出
- **输出格式**: 飞书云文档 / Markdown

---

## 2. 输入参数

执行本Skill前，需要收集以下信息：

### 2.1 基础配置
```yaml
monitoring_config:
  report_period: "YYYY-MM"          # 报告周期，如 "2026-05"
  output_format: "lark_doc"         # 输出格式：飞书文档
  language: "zh"                    # 报告语言

brands:                             # 监测品牌列表（最多5个）
  - name: "品牌A"                   # 品牌名称
    website: "https://brand-a.com"  # 官网
    social_accounts:
      instagram: "brand_a"          # 不含@
      tiktok: "brand_a"             # 不含@
      facebook: "brand.a.official"  # Facebook Page名或URL
      youtube: "@BrandAOfficial"    # YouTube频道
    product_keywords:
      - "BrandA Product X"
      - "BrandA Pro"
    facebook_page_url: "https://www.facebook.com/branda/"  # 用于Meta广告按Page抓取

  - name: "品牌B"
    # ... 同上
```

### 2.2 API 配置
```yaml
api_config:
  # Apify（核心，已有Token）
  apify:
    api_token: "${APIFY_API_TOKEN}"   # 读取方式: os.getenv("APIFY_API_TOKEN")
  
  # 以下均通过搜索引擎替代，无需额外API Key
  # Reddit舆情 → 搜索引擎检索 "site:reddit.com 品牌名"
  # PR稿件   → 搜索引擎检索 "品牌名 press release / news"
```

### 2.3 Apify Actor 清单

| Actor ID | 用途 | 单价(Starter) |
|----------|------|--------------|
| `apify/instagram-profile-scraper` | IG账号信息+粉丝数 | $1.60/1k profiles |
| `apify/instagram-post-scraper` | IG帖子详情+评论 | $1.00/1k posts |
| `scrapio/instagram-tagged-mentions-posts-scraper` | IG Tagged区帖子(红人识别) | $14.99/月 |
| `apify/tiktok-profile-scraper` | TK账号信息+帖子 | 按量 |
| `streamers/youtube-scraper` | YT频道视频搜索 | $2.40/1k videos |
| `automation-lab/facebook-ads-library` | Meta广告库 | $0.0005/ad |
| `apify/instagram-comment-scraper` | IG评论(舆情) | 按量 |

**月度成本估算(1品牌)**:
- IG Profile + Posts: ~$0.5
- IG Tagged: ~$14.99/月(固定)
- TK Profile: ~$0.5
- YT Scraper: ~$0.3
- Meta Ads: ~$0.05
- **合计: ~$16-20/品牌/月**（含搜索降级方案则更低）

---

## 3. 执行流程

### 3.1 主流程
```
1. 读取config → 确认品牌列表、社媒账号、报告周期
2. 依次执行6大板块数据采集（每品牌）
   ├── 板块1: 品牌新品动向（官网fetch + IG帖子新品识别）
   ├── 板块2: 社媒数据（IG/TK/YT三平台profile+posts）
   ├── 板块3: 红人合作（IG Tagged区 + TK合作视频识别）
   ├── 板块4: UGC舆情（搜索Reddit + IG评论区）
   ├── 板块5: PR稿件（搜索引擎检索新闻）
   └── 板块6: Meta广告（Apify Actor抓取Ad Library）
3. LLM深度分析
   ├── 内容方向分类（product review/sponsorship/campaign/giveaway）
   ├── 情感分析（Reddit+评论区）
   ├── 卖点提取（从文案和广告中）
   └── 视频脚本拆解（高互动视频）
4. 数据整合 → 生成报告
5. 输出至飞书文档
```

### 3.2 数据采集详细流程

#### 板块1: 品牌新品动向
```
数据源:
1. 品牌官网 → fetch /products, /new-arrivals 页面
2. IG帖子 → 识别含"new launch"/"new product"/"just dropped"等关键词的帖子

输出:
- new_products: [{name, launch_date, main_selling_point, price, source_url}]
- main_products: [{name, main_selling_point, promotion_focus}]
```

#### 板块2: 社媒数据
```
数据采集步骤:
1. Apify: instagram-profile-scraper → 获取粉丝数、bio、帖子数
2. Apify: instagram-post-scraper → 获取最近30-60条帖子详情
3. Apify: tiktok-profile-scraper → 获取TK账号信息+帖子
4. Apify: streamers/youtube-scraper → 搜索品牌频道视频

数据维度:
- 各平台 Post 数量（按月筛选）
- 粉丝数快照（当前值，如需环比需存历史）
- 各平台 高曝光/高互动帖文 Top 10
- 发布频次（总帖子数/天数）
- 内容类型分布（视频/图片/Carousel占比）

LLM分析:
- 内容方向分类: 将每条帖子分为 product_review / brand_sponsorship / campaign / giveaway / educational / other
- 核心宣传卖点提取: 从caption中提取主推卖点
```

#### 板块3: 红人合作
```
关键修正: 看品牌官方账号的"tag区"（别人tag了品牌的帖子），不是品牌@mention的人

数据采集步骤:
1. Apify: scrapio/instagram-tagged-mentions-posts-scraper
   - 输入品牌IG username
   - 输出: 别人tag了该品牌的帖子列表，含帖子owner信息
2. 从tagged帖子的owner中识别红人
   - 提取owner的username, followers, bio
   - 判断is_paid_partnership / is_ad
3. 交叉验证TK平台红人合作

数据维度:
- 红人总数量、总曝光（粉丝数之和）
- 平台分布（IG/TK）
- 红人量级: Nano(<1K) / Micro(1K-100K) / Macro(100K-1M) / Mega(>1M)
- 红人类型: lifestyle/pet/health/vet/other（LLM从bio分类）
- 推广产品 & 强调卖点（LLM从caption提取）
- 高互动/高曝光视频列表
- 脚本结构拆解（LLM分析top视频caption+comment）
```

#### 板块4: UGC舆情
```
数据采集步骤:
1. 搜索引擎: "site:reddit.com 品牌名 OR 产品名"
   - 提取相关帖子标题、链接、摘要
2. Apify: instagram-comment-scraper (可选)
   - 抓取品牌高互动帖子下的评论

LLM分析:
- Reddit帖子情感分类: positive/neutral/negative
- 评论区情感分析: 对推广活动的反馈
- 整体舆情总结
- 关键投诉/好评提取

输出:
- reddit_discussions: [{title, url, sentiment, key_points, subreddit}]
- comment_sentiment: {positive_rate, neutral_rate, negative_rate}
- overall_sentiment: 整体舆情总结
```

#### 板块5: PR稿件
```
数据采集步骤:
1. 搜索引擎: "品牌名 press release" / "品牌名 news" / "品牌名 announces"
   - 按日期筛选上月结果
2. 如有Google CSE API Key则用API，否则用搜索

LLM分析:
- 媒体量级分类: Tier1(Top媒体) / Tier2(知名媒体) / Tier3(垂直/小众)
- 媒体类型: 科技/生活/财经/垂直/宠物
- 推广重点: 促销/新品/横测/融资/合作
- PR突出信息提取

输出:
- pr_articles: [{title, url, media, media_tier, media_type, publish_date, focus, key_info}]
- pr_summary: PR推广重点总结
```

#### 板块6: Meta广告
```
数据采集步骤:
1. Apify: automation-lab/facebook-ads-library
   - 输入: searchQueries=[品牌名, 产品名] 或 pageUrls=[品牌FB页面URL]
   - 输出: 广告详情含文案、图片、视频、投放平台、spend估算

数据维度:
- 广告总条数
- 新上线广告（本月startDate的）
- 广告素材类型分布（image/video/carousel）
- 投放平台分布（FB/IG/Messenger）
- 主推产品（LLM从bodyText提取）
- 文案分析（CTA类型、卖点关键词）
- 视频脚本分析（LLM拆解视频广告脚本结构）

输出:
- ads_overview: {total_ads, new_ads, main_products, creative_type_dist, platform_dist}
- ads_details: [{adArchiveId, bodyText, title, ctaText, displayFormat, imageUrls, videoUrls, platforms, startDate, spend}]
- script_analysis: 视频广告脚本拆解
```

---

## 4. 报告结构

### 4.1 报告大纲
```
📊 竞品监测报告 - [品牌名称] - [YYYY年MM月]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 执行摘要（LLM生成）
   ├── 监测周期
   ├── 核心推广动作总结（2-3句）
   ├── 推广方向概括
   ├── 主推产品总结
   └── 关键发现 Top 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 板块概览 Dashboard
   | 板块 | 核心指标1 | 核心指标2 | 核心指标3 |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 1. 品牌新品动向
   > 板块总结（LLM生成，3句以内）
   ├── 新品上线列表（表格）
   └── 主推产品分析

📊 2. 社媒数据表现
   > 板块总结（LLM生成）
   ├── 核心数据 Dashboard（表格）
   │   | 平台 | 粉丝数 | 本月Post数 | 平均互动 | 发布频次 |
   ├── 高曝光/高互动帖文 Top 10（每平台）
   └── 内容方向分析（LLM分类结果）

👥 3. 红人合作数据
   > 板块总结（LLM生成）
   ├── 核心数据 Dashboard
   │   | 红人总数 | 总曝光 | 平台分布 | 量级分布 |
   ├── 红人明细列表（表格）
   │   | 红人账号 | 平台 | 粉丝数 | 量级 | 类型 | 推广产品 | 合作帖子链接 |
   ├── 推广产品 & 卖点分析
   └── 高互动视频 + 脚本拆解（LLM）

💬 4. UGC舆情监测
   > 板块总结（LLM生成）
   ├── Reddit 讨论概览（表格）
   ├── 情感分布（正面/中性/负面占比）
   ├── 热门讨论帖子（含链接）
   └── 社媒评论区舆情

📰 5. PR稿件监测
   > 板块总结（LLM生成）
   ├── 核心数据 Dashboard
   ├── 媒体分布（层级+类型）
   ├── PR稿件列表（含链接）
   └── 推广重点分析

🎯 6. Meta广告监测
   > 板块总结（LLM生成）
   ├── 核心数据 Dashboard
   ├── 广告素材分析（类型+平台分布）
   ├── 文案 & CTA分析
   └── 视频脚本分析（LLM拆解）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 附录
   ├── 数据来源说明（每个板块标注Actor/API）
   ├── 成本明细（本次run消耗）
   └── 数据限制声明
```

### 4.2 报告格式规范
```markdown
# 标题格式
📊 竞品监测报告 - {品牌名称} - {YYYY年MM月}

# 板块标题
## 📦 1. 品牌新品动向

# 板块总结（LLM生成，3句以内）
> **板块总结**: 本月品牌上线2款新品，主推Allergy产品线，核心卖点集中在...

# Dashboard 表格
| 指标 | 数值 | 环比变化 |

# 关键洞察框
:::info
**关键洞察**: ...
:::
```

---

## 5. LLM 分析逻辑

本Skill利用Coze内置LLM做深度分析，替代传统的关键词匹配方式。

### 5.1 内容方向分类
```
Prompt: 
分析以下社媒帖子的内容方向，将其分为以下类别之一：
- product_review: 产品评测/使用体验
- brand_sponsorship: 品牌赞助/付费合作
- campaign: 节日活动/campaign
- giveaway: 赠品/抽奖
- educational: 教育/科普内容
- ugc: 用户生成内容
- other: 其他

帖子内容: {caption}
回复格式: {"category": "xxx", "confidence": 0.9, "reason": "xxx"}
```

### 5.2 情感分析
```
Prompt:
分析以下用户评论/讨论的情感倾向：
- positive: 正面/推荐
- neutral: 中性/客观
- negative: 负面/批评

内容: {text}
回复格式: {"sentiment": "xxx", "confidence": 0.9, "key_points": ["..."]}
```

### 5.3 卖点提取
```
Prompt:
从以下广告/帖子文案中提取核心卖点，按重要性排序：
文案: {text}
产品类别: {category}
回复格式: {"selling_points": ["卖点1", "卖点2"], "main_product": "xxx", "promotion_type": "xxx"}
```

### 5.4 视频脚本拆解
```
Prompt:
拆解以下视频广告的脚本结构，分析其营销策略：
视频文案: {caption}
视频类型: {type}
互动数据: likes={likes}, views={views}

回复格式:
{
  "hook": "开头hook（前3秒）",
  "problem": "痛点描述",
  "solution": "产品解决方案",
  "proof": "信任背书（成分/数据/评价）",
  "cta": "行动号召",
  "strategy": "整体策略分析"
}
```

---

## 6. 降级策略

当Apify积分不足或Actor不可用时，采用搜索降级模式：

| 板块 | 正常模式(Apify) | 降级模式(搜索) |
|------|---------------|--------------|
| IG社媒 | Apify Actor直采 | 搜索 "品牌名 site:instagram.com" |
| TK社媒 | Apify Actor直采 | 搜索 "品牌名 site:tiktok.com" |
| YT社媒 | Apify Actor直采 | 搜索 "品牌名 site:youtube.com" |
| IG红人 | Tagged Posts Actor | 搜索 "品牌名 influencer" / "品牌名 sponsored" |
| Reddit | 搜索reddit帖文 | 同（已是搜索模式） |
| PR | 搜索新闻 | 同（已是搜索模式） |
| Meta广告 | Apify Ad Library | 搜索 "品牌名 site:facebook.com/ads" |

降级模式数据精度降低，但可保证报告不中断。

---

## 7. 数据质量保障

### 7.1 数据验证
```python
def validate_data(raw_data):
    """
    验证项:
    1. 完整性 - 关键字段是否缺失
    2. 时效性 - 数据是否在监测周期内
    3. 合理性 - 数值是否在合理范围
    4. 去重 - 跨Actor结果去重
    """
    pass
```

### 7.2 异常处理
| 异常情况 | 处理策略 |
|---------|---------|
| Apify积分不足 | 自动切换搜索降级模式 |
| Actor超时/失败 | 重试1次→降级→标记N/A |
| 搜索无结果 | 标记"暂无数据"+说明原因 |
| Actor返回空数据 | 可能是无内容，标记确认 |

---

## 8. 扩展监测维度（可选）

| 维度 | 监测内容 | 数据源 | 增量成本 |
|------|---------|--------|---------|
| **Amazon评论** | 产品评分、评论趋势 | Apify Amazon scraper | ~$1/品牌 |
| **Google Trends** | 品牌搜索热度趋势 | Google Trends(免费) | $0 |
| **TikTok创意趋势** | 赛道热门创意形式 | Apify TikTok scraper | ~$0.5 |
| **联盟营销** | Affiliate推广活动 | 搜索 "品牌名 affiliate" | $0 |

---

## 9. 版本记录

- **v2.0** - 全面重构：数据源切换为Apify真实爬虫+搜索架构；修复IG _sharedData失效问题；修复Meta Ad Library需access_token问题；修复红人识别逻辑(改为tag区识别)；新增TikTok/YouTube平台覆盖；新增LLM深度分析；新增降级策略
- **v1.0** - 初始版本，覆盖6大监测板块
