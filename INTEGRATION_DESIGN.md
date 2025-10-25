# Twitter Product Trends Integration Design
## 数据流程架构设计

**设计日期**: 2025-10-25
**目标**: 整合 Twitter 监控、Product Knowledge 和趋势报告生成

---

## 🎯 核心目标

1. **自动化数据采集** - 使用 twitterio API 采集 Top 300 KOL 过去一周推文
2. **智能产品识别** - 使用 product_knowledge 提取和匹配产品
3. **知识库更新** - 将新产品信息同步到 product_knowledge 数据库
4. **新旧产品区分** - 明确标识新产品 vs 已有产品的新版本
5. **增强报告生成** - 生成包含准确产品信息的趋势分析报告

---

## 📊 完整数据流程

```
┌─────────────────┐
│ 1. Twitter API  │
│  采集 KOL 推文   │
└────────┬────────┘
         │
         ├─ Top 300 KOL
         ├─ 过去 7 天
         ├─ 保存到 raw_data.json
         │
         v
┌─────────────────────────┐
│ 2. Product Knowledge    │
│  提取 & 匹配产品        │
└────────┬────────────────┘
         │
         ├─ GPT-4o 提取产品信息
         ├─ 智能匹配现有产品
         ├─ 识别新产品
         ├─ 识别新版本
         │
         v
┌─────────────────────────┐
│ 3. Knowledge DB 更新    │
│  同步新产品到数据库      │
└────────┬────────────────┘
         │
         ├─ 新产品 → 插入 products 表
         ├─ 新版本 → 插入 releases 表
         ├─ 推文 → 插入 tweets 表
         ├─ 关联 → product_mentions 表
         │
         v
┌─────────────────────────┐
│ 4. 产品分类             │
│  新产品 vs 旧产品       │
└────────┬────────────────┘
         │
         ├─ 新产品: 本周首次出现
         ├─ 旧产品: 数据库中已存在
         ├─ 新版本: 同产品不同version
         │
         v
┌─────────────────────────┐
│ 5. 报告生成             │
│  增强版产品趋势分析      │
└─────────────────────────┘
         │
         ├─ 新产品发现 (with metadata)
         ├─ 热门产品 (旧产品讨论)
         ├─ 版本更新 (releases)
         ├─ 趋势分析
         │
         v
      输出文件:
      - analysis_report.md
      - product_summary.json
      - updated_knowledge_db
```

---

## 🔧 技术架构

### 模块划分

#### Module 1: Twitter Data Collector
**位置**: `twitter_product_trends/scripts/twitter_collector.py`

**功能**:
- 调用 twitterio API 采集推文
- 支持增量采集(避免重复)
- 数据验证和预处理

**输入**:
- KOL 数量 (默认 300)
- 时间范围 (默认 7 天)

**输出**:
```json
{
  "metadata": {
    "collection_date": "2025-10-25",
    "kol_count": 300,
    "tweet_count": 2000,
    "date_range": {"start": "2025-10-18", "end": "2025-10-25"}
  },
  "tweets": [
    {
      "id": "tweet_id",
      "text": "...",
      "created_at": "...",
      "author": {...},
      "metrics": {...}
    }
  ]
}
```

---

#### Module 2: Product Extractor & Matcher
**位置**: `twitter_product_trends/scripts/product_processor.py`

**功能**:
- 调用 product_knowledge 的 API
- 提取产品信息 (使用 GPT-4o)
- 匹配现有产品
- 识别新产品和新版本

**依赖**:
```python
from product_knowledge.scripts.api.interface import ProductKnowledgeAPI
from product_knowledge.scripts.ingest_new_data import DataPreprocessor
```

**核心逻辑**:
```python
api = ProductKnowledgeAPI(config={...})
api.initialize()

for tweet in tweets:
    result = api.extract_and_store(
        text=tweet['text'],
        source_url=tweet_url,
        source_type='twitter',
        timestamp=tweet['created_at']
    )

    # result 包含:
    # - new_products: 新产品
    # - new_releases: 新版本
    # - matched_products: 匹配到的已有产品
```

**输出**:
```json
{
  "extraction_summary": {
    "total_tweets_processed": 2000,
    "products_extracted": 150,
    "new_products": 25,
    "new_releases": 15,
    "existing_products": 110
  },
  "new_products": [...],
  "new_releases": [...],
  "existing_products": [...],
  "product_tweet_map": {...}
}
```

---

#### Module 3: Product Classifier
**位置**: `twitter_product_trends/scripts/product_classifier.py`

**功能**:
- 读取 product_knowledge 数据库
- 对比本周提取的产品
- 分类: 新产品 / 旧产品 / 新版本

**核心逻辑**:
```python
# 读取上一个版本的产品列表
previous_db = load_version('v1_cleaned_20251025')
previous_products = set(previous_db['products'].keys())

# 对比本周提取的产品
current_products = extraction_result['products']

new_products = []
old_products = []
new_releases = []

for product in current_products:
    if product['name'] not in previous_products:
        new_products.append(product)
    else:
        # 检查是否有新版本
        if has_new_version(product):
            new_releases.append(product)
        else:
            old_products.append(product)
```

**输出**:
```json
{
  "classification_date": "2025-10-25",
  "new_products": [
    {
      "name": "Product A",
      "company": "Company X",
      "category": "AI Tool",
      "first_mentioned": "2025-10-23",
      "mention_count": 5,
      "related_tweets": [...]
    }
  ],
  "old_products": [...],
  "new_releases": [
    {
      "product_name": "Product B",
      "version": "v2.0",
      "release_date": "2025-10-22",
      "changes": "...",
      "mention_count": 12,
      "related_tweets": [...]
    }
  ]
}
```

---

#### Module 4: Enhanced Report Generator
**位置**: `twitter_product_trends/scripts/enhanced_report_generator.py`

**功能**:
- 使用分类结果生成报告
- 包含准确的产品元数据
- 区分新产品和旧产品
- 突出显示版本更新

**报告结构**:
```markdown
# Twitter Product Trends Report
## 2025-10-18 至 2025-10-25

---

## 📋 执行摘要

**数据概览**
- 监控 KOL: 300 个
- 分析推文: 2,000 条
- 识别产品: 150 个
  - **新产品**: 25 个 ⭐
  - **已有产品**: 110 个
  - **版本更新**: 15 个 🆕

**核心发现**
1. 本周发现 25 个新产品,主要集中在 AI 开发工具领域
2. Claude 3.5 Sonnet 发布,引发 87 条相关讨论
3. 开源 AI 模型热度持续上升 (+35%)

---

## 🆕 新产品发现 (25个)

### 1. [Product Name]

**基本信息**
- 公司: [Company Name]
- 类别: [Category]
- 首次提及: 2025-10-23
- 提及次数: 5 次

**产品描述**
[AI 生成的产品描述]

**KOL 评价**
- 正面: 3 条
- 中性: 2 条
- 负面: 0 条

**代表性推文**
...

---

## 🔥 热门产品 (已有产品讨论 Top 30)

### 1. Claude

**基本信息** (来自知识库)
- 公司: Anthropic
- 类别: AI Assistant
- 官网: https://claude.ai
- 首次收录: 2025-09-15

**本周动态**
- 提及次数: 87 次 (↑ 25% vs 上周)
- 讨论热度: ⭐⭐⭐⭐⭐
- **版本更新**: Claude 3.5 Sonnet (2025-10-22发布)

**观点分布**
...

---

## 🚀 版本更新 (15个)

### 1. Claude 3.5 Sonnet

**产品**: Claude
**公司**: Anthropic
**发布日期**: 2025-10-22

**主要更新**
- 性能提升 2倍
- 支持更长上下文
- 新增图像生成功能

**社区反应**
- 提及次数: 45 次
- 情绪: 87% 正面

---

## 📊 其他产品汇总

[表格形式列出所有其他产品]

---

## 📈 趋势分析

[原有的趋势分析内容]

---

## 💾 数据来源

- Twitter 原始数据: `raw_data.json`
- 产品数据库版本: `v2_20251025`
- 知识库变更: +25 新产品, +15 新版本
```

---

## 📦 文件组织

### 项目目录结构

```
twitter_product_trends-20251022/
├── scripts/
│   ├── twitter_collector.py          # Module 1: Twitter 采集
│   ├── product_processor.py          # Module 2: 产品提取匹配
│   ├── product_classifier.py         # Module 3: 产品分类
│   ├── enhanced_report_generator.py  # Module 4: 报告生成
│   └── main_workflow.py              # 主流程编排
│
├── data_sources/
│   ├── YYYYMMDD_raw_tweets.json      # 原始推文
│   ├── YYYYMMDD_extracted_products.json  # 提取的产品
│   └── YYYYMMDD_classified_products.json # 分类结果
│
├── reports/
│   ├── YYYYMMDD_产品趋势报告.md
│   └── YYYYMMDD_product_summary.json
│
└── config/
    └── integration_config.json       # 集成配置
```

### 配置文件示例

```json
{
  "twitter": {
    "kol_count": 300,
    "days": 7,
    "api_endpoint": "/Users/wenyongteng/twitter hot news/weekly_monitor"
  },
  "product_knowledge": {
    "project_path": "/Users/wenyongteng/vibe_coding/product_knowledge-20251022",
    "current_version": "v1_cleaned_20251025",
    "api_config": {
      "auto_verify_web": false,
      "fuzzy_threshold": 0.85
    }
  },
  "extraction": {
    "model": "openai/gpt-4o",
    "batch_size": 10,
    "max_workers": 8
  },
  "report": {
    "min_mentions_for_trending": 3,
    "include_product_metadata": true
  }
}
```

---

## 🔄 完整工作流

### 主流程脚本: `main_workflow.py`

```python
#!/usr/bin/env python3
"""
Twitter 产品趋势分析 - 主工作流
整合 Twitter 采集、Product Knowledge 和报告生成
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 导入各模块
from twitter_collector import TwitterCollector
from product_processor import ProductProcessor
from product_classifier import ProductClassifier
from enhanced_report_generator import EnhancedReportGenerator

def main_workflow(days=7, kol_count=300):
    """主工作流"""

    start_time = datetime.now()
    print("=" * 70)
    print("🚀 Twitter 产品趋势分析 - 完整流程")
    print("=" * 70)

    # === Step 1: 采集 Twitter 数据 ===
    print("\n[1/5] 📱 采集 Twitter 数据...")
    collector = TwitterCollector()
    raw_tweets = collector.collect(days=days, kol_count=kol_count)
    print(f"   ✅ 采集完成: {len(raw_tweets)} 条推文")

    # === Step 2: 提取和匹配产品 ===
    print("\n[2/5] 🔍 提取和匹配产品...")
    processor = ProductProcessor()
    extraction_result = processor.process(raw_tweets)
    print(f"   ✅ 提取完成: {len(extraction_result['products'])} 个产品")
    print(f"      - 新产品: {len(extraction_result['new_products'])}")
    print(f"      - 新版本: {len(extraction_result['new_releases'])}")

    # === Step 3: 更新 Product Knowledge 数据库 ===
    print("\n[3/5] 💾 更新 Product Knowledge 数据库...")
    processor.update_knowledge_db()
    print("   ✅ 数据库已更新")

    # === Step 4: 分类产品 (新/旧) ===
    print("\n[4/5] 🏷️  分类产品...")
    classifier = ProductClassifier()
    classified = classifier.classify(extraction_result)
    print(f"   ✅ 分类完成:")
    print(f"      - 新产品: {len(classified['new_products'])} 个")
    print(f"      - 旧产品: {len(classified['old_products'])} 个")
    print(f"      - 版本更新: {len(classified['new_releases'])} 个")

    # === Step 5: 生成报告 ===
    print("\n[5/5] 📝 生成增强报告...")
    generator = EnhancedReportGenerator()
    report_path = generator.generate(
        tweets=raw_tweets,
        classified_products=classified,
        extraction_result=extraction_result
    )
    print(f"   ✅ 报告已生成: {report_path}")

    # === 总结 ===
    elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 70)
    print("✅ 完整流程执行成功!")
    print("=" * 70)
    print(f"⏱️  总耗时: {elapsed:.1f} 秒")
    print(f"📊 处理推文: {len(raw_tweets)} 条")
    print(f"🔍 识别产品: {len(extraction_result['products'])} 个")
    print(f"🆕 新产品: {len(classified['new_products'])} 个")
    print(f"📄 报告位置: {report_path}")
    print("=" * 70)

    return report_path

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Twitter 产品趋势分析')
    parser.add_argument('--days', type=int, default=7, help='时间范围(天)')
    parser.add_argument('--kol-count', type=int, default=300, help='KOL数量')

    args = parser.parse_args()

    main_workflow(days=args.days, kol_count=args.kol_count)
```

---

## 🎯 Claude Skill 集成

### 更新的 Skill 工作流

```markdown
# Twitter Weekly Monitor Skill (Enhanced Version)

## 新增功能

1. **产品知识库集成**
   - 自动提取产品信息并存入知识库
   - 智能匹配现有产品
   - 区分新产品和已有产品

2. **增强的产品分析**
   - 新产品发现(附完整元数据)
   - 旧产品讨论热度追踪
   - 版本更新识别

3. **自动化知识库更新**
   - 每次运行自动更新产品数据库
   - 版本管理(v1, v2, ...)
   - 变更日志记录

## 使用方式

用户只需说:
"帮我分析过去一周 Top 300 KOL 的产品动态"

Skill 会自动:
1. ✅ 采集推文
2. ✅ 提取产品
3. ✅ 更新知识库
4. ✅ 分类新旧产品
5. ✅ 生成增强报告
6. ✅ 展示核心发现

## 输出示例

用户会看到:
- 📊 数据概览 (推文数、产品数)
- 🆕 新产品列表 (25个)
- 🔥 热门产品讨论 (Top 30)
- 🚀 版本更新 (15个)
- 📈 趋势分析
- 💾 知识库变更摘要
```

---

## ✅ 下一步行动

1. **实现各模块代码**
   - [ ] twitter_collector.py
   - [ ] product_processor.py
   - [ ] product_classifier.py
   - [ ] enhanced_report_generator.py
   - [ ] main_workflow.py

2. **测试一周数据**
   - [ ] 采集最近7天推文
   - [ ] 运行完整流程
   - [ ] 验证产品数据库更新
   - [ ] 检查报告质量

3. **更新 Claude Skill**
   - [ ] 修改 SKILL.md
   - [ ] 添加新的工作流逻辑
   - [ ] 更新使用示例

4. **文档和优化**
   - [ ] 编写使用文档
   - [ ] 性能优化
   - [ ] 错误处理增强

---

**设计完成**: 2025-10-25
**设计者**: Claude Code
**下一步**: 开始实现各模块代码
