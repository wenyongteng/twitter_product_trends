# Twitter Product Trends

> 完整的 Twitter 产品趋势分析系统：数据采集 + 产品识别 + Product Knowledge 集成

## 🎯 核心功能

1. **Twitter 数据采集** - 采集 Top N KOL 过去 N 天的推文
2. **产品识别与分类** - 自动识别85+产品，匹配899+产品知识库
3. **Product Knowledge 集成** - 区分新产品、已有产品、公司实体
4. **趋势分析报告** - 生成综合分析报告

## 📁 项目结构

```
twitter_product_trends-20251022/
├── weekly_monitor.py           # 统一入口脚本（数据采集 + 分析 + PK集成）
│
├── twitter_monitor/            # Twitter 数据采集模块
│   ├── collect_data.py         # 数据采集脚本
│   ├── analyze_tweets.py       # 推文分析脚本
│   ├── core/                   # 核心功能模块
│   │   ├── data_collector.py  # TwitterIO API 采集器
│   │   ├── product_extractor.py
│   │   └── ...
│   ├── config/                 # 配置文件
│   └── product kol_ranking_weighted.csv  # KOL 列表
│
├── scripts/                    # Product Knowledge 集成脚本
│   ├── integrate_product_knowledge_v3.py  # 主集成脚本
│   ├── complete_workflow.py
│   └── ...
│
├── config/                     # 全局配置
│   └── integration_config.json # 集成配置
│
├── weekly_reports/             # 历史数据和报告
│   └── week_YYYY-MM-DD_to_YYYY-MM-DD/
│       ├── raw_data.json                    # 原始推文
│       ├── analysis_summary.json            # 分析摘要
│       ├── product_classification_v3.json   # 产品分类
│       └── enhanced_report_v3.md            # 增强报告
│
├── data_sources/               # 数据源（已弃用，保留兼容）
├── reports/                    # 报告输出（已弃用，保留兼容）
│
└── docs/                       # 文档
    ├── README.md
    ├── INTEGRATION_DESIGN.md   # 集成设计文档
    └── QUICK_START.md          # 快速开始
```

## 🚀 快速开始

### 1. 完整工作流（推荐）

采集数据 → 分析 → Product Knowledge 集成，一键完成：

```bash
# 采集 Top 300 KOL 过去7天的推文，并自动分析
python3 weekly_monitor.py --days 7 --kol-count 300
```

**参数说明**:
- `--days N`: 采集过去N天的推文（默认7天）
- `--kol-count N`: 采集Top N个KOL（100/200/300，默认200）
- `--model MODEL`: 指定分析模型（可选）
- `--skip-collection`: 跳过数据采集，仅运行分析
- `--skip-pk-integration`: 跳过 Product Knowledge 集成

### 2. 分步执行

如果需要分步控制，可以分别运行：

```bash
# 步骤 1: 数据采集
cd twitter_monitor
python3 collect_data.py --days 7 --kol-count 300

# 步骤 2: 推文分析
python3 analyze_tweets.py ../weekly_reports/week_*/raw_data.json

# 步骤 3: Product Knowledge 集成
cd ../scripts
python3 integrate_product_knowledge_v3.py ../weekly_reports/week_*/raw_data.json
```

## 📊 输出结果

运行完成后，在 `weekly_reports/week_YYYY-MM-DD_to_YYYY-MM-DD/` 目录下生成：

### 1. `raw_data.json`
原始推文数据，包含：
- 推文文本、时间、互动数
- KOL 信息（username, rank, followers）
- 元数据（日期范围、API成本等）

### 2. `analysis_summary.json`
分析摘要，包含：
- Top 30 产品统计
- 话题分布
- 新产品发现

### 3. `product_classification_v3.json` ⭐
Product Knowledge 分类结果：

```json
{
  "new_products": [        // 新产品（数据库中不存在）
    {
      "name": "Vercel",
      "twitter_data": {
        "mention_count": 5,
        "top_kols": ["rauchg", "DeepLearningAI"],
        "sentiment": {...},
        "total_engagement": 150
      }
    }
  ],
  "existing_products": [   // 已有产品（数据库中存在）
    {
      "name": "Claude",
      "kb_canonical_name": "Claude",
      "twitter_data": {...},
      "knowledge_data": {  // 来自 Product Knowledge 数据库
        "company": "Anthropic",
        "mention_count": 850
      }
    }
  ],
  "companies": [           // 公司实体（单独分类）
    {
      "name": "Google",
      "twitter_data": {...}
    }
  ]
}
```

### 4. `enhanced_report_v3.md`
可读性强的综合报告，包含：
- 执行摘要
- 新产品列表（详细信息）
- 已有产品列表（含知识库数据）
- 公司实体统计

## 🎨 核心特性

### Product Knowledge 集成 v3

1. **产品识别**
   - 使用正则表达式精准识别 85+ 产品
   - 覆盖 AI 模型、工具、平台、公司

2. **知识库匹配**
   - 加载 899+ 产品知识库
   - 精确匹配 + 模糊匹配
   - 别名处理

3. **智能分类**
   - **新产品**: Vercel, Qwen2.5, Llama 3/4等
   - **已有产品**: Claude, ChatGPT, Gemini等
   - **公司实体**: Google, Microsoft, Meta等（单独分类）
   - **模糊匹配**: 需要人工确认

4. **数据规范化**
   - ✅ 大小写归一化（Google/GOOGLE → Google）
   - ✅ 保留版本差异（Gemini 3 ≠ gemini 3 pro）
   - ✅ 公司实体过滤

## 🔧 配置

### 主配置文件: `config/integration_config.json`

```json
{
  "twitter": {
    "kol_count": 300,
    "days": 7,
    "collector_path": ".../twitter_monitor",
    "weekly_reports_dir": ".../weekly_reports"
  },
  "product_knowledge": {
    "project_path": ".../product_knowledge-20251022",
    "current_version": "v1_cleaned_20251025"
  },
  "integration": {
    "script_version": "v3",
    "enable_company_filtering": true,
    "enable_name_normalization": true,
    "preserve_version_differences": true
  }
}
```

### Twitter Monitor 配置: `twitter_monitor/config/config.py`

数据采集参数、LLM 配置等。

## 🤖 Claude Agent Skill 集成

本项目已集成到 Claude Code Agent Skill：**Twitter Weekly Monitor**

### 使用方法

在 Claude Code 中直接说：

```
帮我分析过去一周 Top 300 KOL 的产品动态
```

或

```
生成 twitter 周报
```

Agent 会自动：
1. 采集数据
2. 运行 Product Knowledge 集成
3. 生成综合分析报告
4. 展示核心洞察

## 📖 文档

- [INTEGRATION_DESIGN.md](INTEGRATION_DESIGN.md) - 完整设计文档
- [QUICK_START.md](QUICK_START.md) - 快速开始指南
- [COMPLETION_SUMMARY.md](COMPLETION_SUMMARY.md) - 项目完成总结

## 🔗 相关项目

- **Product Knowledge**: `/Users/wenyongteng/vibe_coding/product_knowledge-20251022`
  - 产品知识库（899+ 产品）
  - 版本管理
  - Web 验证功能

## 📝 更新日志

### v3 (2025-10-25)
- ✅ 完整迁移 Twitter Monitor 到统一项目
- ✅ 创建 `weekly_monitor.py` 统一入口
- ✅ Product Knowledge v3 集成
- ✅ 产品名标准化 + 公司实体过滤
- ✅ 更新 Agent Skill 路径

### v2 (2025-10-25)
- 处理所有产品（从 raw_data.json）
- 修复只处理 Top 30 的问题

### v1 (2025-10-22)
- 初始版本
- 基础 Product Knowledge 集成

## 📄 License

MIT

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
