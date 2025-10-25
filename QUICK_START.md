# Twitter Product Trends - 快速使用指南

## 🎯 项目目标

整合 **Twitter Monitor** 和 **Product Knowledge** 两个项目，实现：

1. ✅ 采集 Top 300 KOL 的 Twitter 推文
2. ✅ 使用 Product Knowledge 提取和匹配产品
3. ✅ 精准区分新产品 vs 已有产品
4. ✅ 自动更新 Product Knowledge 数据库
5. ✅ 生成包含产品元数据的趋势分析报告

---

## 🚀 快速开始

### 方式 1: 使用已有数据（推荐用于测试）

```bash
cd /Users/wenyongteng/vibe_coding/twitter_product_trends-20251022/scripts
python3 complete_workflow.py --use-existing
```

### 方式 2: 采集新数据

```bash
cd /Users/wenyongteng/vibe_coding/twitter_product_trends-20251022/scripts
python3 complete_workflow.py --days 7 --kol-count 300
```

---

## 📊 数据流程

```
Step 1: Twitter 原始数据采集
   ↓
   使用: /Users/wenyongteng/twitter hot news/weekly_monitor/collect_data.py
   输出: raw_data.json (2000+ 条推文)

Step 2: 产品提取和分析
   ↓
   使用: analyze_tweets.py (现有工具)
   输出: analysis_summary.json (600+ 个产品)

Step 3: Product Knowledge 集成 ⭐
   ↓
   使用: integrate_product_knowledge.py (新创建)
   功能:
   - 与知识库对比,区分新产品 vs 已有产品
   - 更新 Product Knowledge 数据库
   输出:
   - product_classification.json (分类结果)
   - enhanced_report.md (增强版报告)

Step 4: 综合报告生成
   ↓
   使用: complete_workflow.py (新创建)
   输出: comprehensive_report.md
   内容:
   - 第一部分: 产品分析 (新产品 + 已有产品)
   - 第二部分: 趋势分析 (基于全量推文)
```

---

## 📁 关键文件

### 输入文件

```
/Users/wenyongteng/twitter hot news/weekly_monitor/weekly_reports/week_*/
└── raw_data.json                    # Twitter 原始数据
```

### 输出文件

```
/Users/wenyongteng/twitter hot news/weekly_monitor/weekly_reports/week_*/
├── analysis_summary.json            # 产品提取结果
├── product_classification.json      # ⭐ 新旧产品分类
├── enhanced_report.md               # ⭐ 产品增强报告
└── comprehensive_report.md          # ⭐ 综合分析报告
```

### Product Knowledge 更新

```
/Users/wenyongteng/vibe_coding/product_knowledge-20251022/versions/
└── v2_twitter_YYYYMMDD/             # 新版本
    ├── products_list.json           # 更新后的产品列表
    └── metadata.json                # 变更记录
```

---

## 🔧 核心脚本

### 1. integrate_product_knowledge.py

**作用**: 连接 Twitter 分析和 Product Knowledge 数据库

**用法**:
```bash
python3 scripts/integrate_product_knowledge.py <analysis_summary.json>
```

**功能**:
- 读取 Twitter 分析的产品列表
- 与 Product Knowledge 数据库对比
- 区分新产品、已有产品、模糊匹配
- 将新产品添加到数据库
- 生成增强版报告

### 2. complete_workflow.py

**作用**: 完整的端到端工作流

**用法**:
```bash
# 使用已有数据
python3 scripts/complete_workflow.py --use-existing

# 采集新数据
python3 scripts/complete_workflow.py --days 7 --kol-count 300
```

**流程**:
1. 采集 Twitter 数据（或使用已有）
2. 调用 analyze_tweets.py 提取产品
3. 调用 integrate_product_knowledge.py 集成
4. 生成综合报告

---

## ✅ 验证结果

### 1. 检查 Product Knowledge 数据库更新

```bash
# 查看新版本
ls -la /Users/wenyongteng/vibe_coding/product_knowledge-20251022/versions/

# 查看新版本元数据
cat /Users/wenyongteng/vibe_coding/product_knowledge-20251022/versions/v2_twitter_*/metadata.json
```

预期输出:
```json
{
  "version": "v2_twitter_20251025",
  "changes": {
    "new_products_added": 30,
    "original_product_count": 0,
    "new_product_count": 30
  },
  "new_products_list": ["Claude", "OpenAI", "Gemini", ...]
}
```

### 2. 检查分类结果

```bash
cat "/Users/wenyongteng/twitter hot news/weekly_monitor/weekly_reports/week_*/product_classification.json"
```

预期结构:
```json
{
  "new_products": [
    {
      "name": "Claude",
      "twitter_data": {
        "mention_count": 77,
        "total_engagement": 18812
      }
    }
  ],
  "existing_products": [
    {
      "name": "...",
      "kb_canonical_name": "...",
      "knowledge_data": {...}
    }
  ]
}
```

### 3. 检查生成的报告

```bash
# 查看综合报告
cat "/Users/wenyongteng/twitter hot news/weekly_monitor/weekly_reports/week_*/comprehensive_report.md"
```

预期内容:
- 📋 执行摘要 (新产品数、已有产品数)
- 🆕 新产品发现 (详细列表)
- 📦 热门已有产品 (带知识库元数据)
- 📈 宏观趋势
- 💎 值得注意的小事

---

## 🎯 核心改进

### 旧版本问题

❌ 无法区分新产品和已有产品
- Claude, ChatGPT 每周都被标记为"新产品"
- 没有历史记录

❌ 没有产品元数据
- 不知道产品的公司、类别
- 无法判断产品间关系

### 新版本解决方案

✅ **精准区分新旧产品**
- 首次出现在数据库 = 新产品
- 已在知识库中 = 已有产品
- 知识库持续积累,不会重复标记

✅ **丰富产品元数据**
- 每个产品都有公司、类别、首次出现时间
- 可追踪产品的版本更新

✅ **自动知识库更新**
- 每次运行自动更新
- 版本管理,可追溯历史

---

## 🔄 实际运行示例

```bash
$ python3 complete_workflow.py --use-existing

================================================================================
🚀 Twitter 产品趋势分析 - 完整工作流
================================================================================

Step 1/3: 📱 采集 Twitter 数据
使用已有数据: weekly_reports/week_2025-10-10_to_2025-10-17/raw_data.json
✅ Step 1 完成: 2,038 条推文

Step 2/3: 🔍 Product Knowledge 处理
分析推文中...
  识别产品: 643个
  新产品: 121个

整合 Product Knowledge...
  ✅ 分类完成:
     - 新产品: 30
     - 已有产品: 0
     - 模糊匹配: 0

  💾 数据库已更新:
     - 新增产品: 30
     - 新版本: v2_twitter_20251025

✅ Step 2 完成

Step 3/3: 📝 生成综合报告
✅ Step 3 完成: comprehensive_report.md

================================================================================
✅ 完整流程执行成功!
================================================================================
⏱️  总耗时: 0.3 秒
📁 工作目录: weekly_reports/week_2025-10-10_to_2025-10-17
📄 综合报告: comprehensive_report.md
================================================================================
```

---

## 🛠️ 配置

配置文件: `config/integration_config.json`

```json
{
  "twitter": {
    "kol_count": 300,
    "days": 7,
    "collector_path": "/Users/wenyongteng/twitter hot news/weekly_monitor"
  },
  "product_knowledge": {
    "project_path": "/Users/wenyongteng/vibe_coding/product_knowledge-20251022",
    "current_version": "v1_cleaned_20251025"
  }
}
```

---

## 📝 下一步

1. **使用 Claude Skill**
   - 现在可以直接说: "帮我分析过去一周 Top 300 KOL 的产品动态"
   - Skill 会自动运行完整流程

2. **定期运行**
   - 建议每周运行一次
   - 知识库会持续积累

3. **报告优化**
   - 基于反馈调整报告格式
   - 添加更多分析维度

---

## 🆘 故障排除

### 问题 1: 找不到脚本

确认路径:
```bash
ls /Users/wenyongteng/vibe_coding/twitter_product_trends-20251022/scripts/complete_workflow.py
```

### 问题 2: Product Knowledge 数据库为空

这是正常的！第一次运行时数据库是空的，会自动填充。

### 问题 3: 所有产品都是新产品

第一次运行时这是正常的。从第二次开始，会有已有产品。

---

## 📞 联系

如有问题，请查看:
- [INTEGRATION_DESIGN.md](INTEGRATION_DESIGN.md) - 完整设计文档
- [project.md](project.md) - 项目说明

---

**Created**: 2025-10-25
**Version**: 1.0
**Status**: ✅ 已测试可用
