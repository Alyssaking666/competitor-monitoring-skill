# 竞品监测工具 v1.0

基于真实爬虫的竞品全维度月度监测方案，适合中小型公司使用。

## 核心特点

- **真实爬虫**: 直接调用各平台公开API和网页接口，不依赖第三方分析工具
- **低成本**: 主要使用免费API，月度成本可控
- **可落地**: 提供完整Python代码，配置后即可运行
- **结构化报告**: 输出Markdown格式报告，可直接导入飞书文档

## 监测维度（6大板块）

| 板块 | 监测内容 | 数据源 |
|------|---------|--------|
| **品牌新品动向** | 新品上线、主推产品、核心卖点 | Meta广告推断 + 社媒分析 |
| **社媒数据** | 发帖量、涨粉、曝光、互动、内容方向 | Instagram网页抓取 |
| **红人合作** | 红人数量、量级、类型、推广产品 | Instagram Tagged区域识别 |
| **UGC舆情** | Reddit讨论、用户反馈、情感分析 | Reddit API |
| **PR稿件** | PR篇数、媒体、量级、内容方向 | Google Custom Search API |
| **Meta广告** | 广告条数、素材、文案、主推产品 | Meta Ad Library API |

## 技术栈

| 工具 | 用途 | 成本 |
|------|------|------|
| Meta Ad Library API | Meta广告数据 | 免费 |
| Reddit API (PRAW) | Reddit帖子+评论 | 免费 |
| Google Custom Search API | PR/新闻检索 | 免费额度100次/天 |
| Requests + BeautifulSoup | 网页抓取 | 免费 |

## 项目结构

```
competitor-monitoring-skill/
├── config.yaml              # 配置文件
├── main.py                  # 主程序入口
├── report_generator.py      # 报告生成器
├── scrapers/                # 爬虫模块
│   ├── meta_ad_scraper.py   # Meta广告爬虫
│   ├── instagram_scraper.py # Instagram爬虫
│   ├── reddit_scraper.py    # Reddit爬虫
│   └── pr_scraper.py        # PR新闻爬虫
├── data/                    # 原始数据存储
├── reports/                 # 报告输出目录
└── README.md               # 使用文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install requests pyyaml praw
```

### 2. 配置API凭证

复制 `config.yaml` 并填写你的API凭证：

```yaml
# Reddit API (必需)
reddit:
  client_id: "YOUR_REDDIT_CLIENT_ID"
  client_secret: "YOUR_REDDIT_CLIENT_SECRET"

# Google Custom Search API (用于PR监测)
google:
  api_key: "YOUR_GOOGLE_API_KEY"
  cx: "YOUR_CUSTOM_SEARCH_ENGINE_ID"
```

**获取API凭证：**

- **Reddit**: https://www.reddit.com/prefs/apps → 创建script类型应用
- **Google**: https://developers.google.com/custom-search/v1/overview → 创建API Key和自定义搜索引擎

### 3. 配置监测品牌

在 `config.yaml` 中配置要监测的品牌：

```yaml
brands:
  - name: "BrandA"
    website: "https://brand-a.com"
    social_accounts:
      instagram: "brand_a"      # 账号名（不含@）
      facebook: "brand.a"
      youtube: "BrandAOfficial"
    product_keywords:
      - "BrandA Product X"
```

### 4. 运行监测

```bash
python main.py
```

报告将生成在 `reports/` 目录下。

## 报告内容

生成的Markdown报告包含：

1. **执行摘要** - 核心发现高度概括
2. **板块概览 Dashboard** - 6大板块核心指标总览
3. **品牌新品动向** - 新品列表 + 主推产品分析
4. **社媒数据表现** - 数据Dashboard + 高互动内容Top10
5. **红人合作数据** - 红人明细 + 量级/类型分布
6. **UGC舆情监测** - 情感分析 + 热门话题 + 典型评价
7. **PR稿件监测** - 媒体分布 + 推广重点分析
8. **Meta广告监测** - 广告素材分析 + 主推产品
9. **附录** - 数据来源说明 + 方法论 + 限制声明

## 数据存储

- **原始数据**: 保存为JSON格式，位于 `data/` 目录
- **报告**: Markdown格式，位于 `reports/` 目录
- **可直接导入飞书文档**: 复制Markdown内容粘贴到飞书文档即可

## 注意事项

1. **请求频率**: 各平台有反爬机制，已设置默认延迟（2-3秒/请求）
2. **API限制**: 
   - Reddit API: 60次/分钟
   - Google Custom Search: 100次/天
   - Meta Ad Library: 无明确限制，但建议控制频率
3. **数据准确性**: 基于公开数据，可能存在延迟或遗漏
4. **Instagram**: 反爬较严格，如遇问题可增加延迟或使用代理

## 扩展建议

如需更强大的功能，可考虑：

- **Apify**: 更稳定的社媒爬虫（$49/月）
- **SerpApi**: 更精准的Google搜索数据（$50/月）
- **代理IP**: 解决反爬问题
- **数据库**: 使用SQLite存储历史数据，便于趋势分析

## 版本记录

- **v1.0** - 初始版本，覆盖6大监测板块，支持Markdown报告输出
