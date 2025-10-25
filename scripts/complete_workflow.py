#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter 产品趋势分析 - 完整工作流
正确的顺序：采集 → Product Knowledge 处理 → 综合报告生成
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def step1_collect_twitter_data(days=7, kol_count=300):
    """
    Step 1: 采集 Twitter 原始数据
    使用现有的 collect_data.py
    """
    print("\n" + "=" * 80)
    print("Step 1/4: 📱 采集 Twitter 原始数据")
    print("=" * 80)

    twitter_monitor_path = Path("/Users/wenyongteng/twitter hot news/weekly_monitor")
    collect_script = twitter_monitor_path / "collect_data.py"

    print(f"参数: days={days}, kol_count={kol_count}")
    print(f"脚本: {collect_script}")

    # 执行采集
    cmd = [sys.executable, str(collect_script), '--days', str(days), '--kol-count', str(kol_count)]

    print("开始采集...")
    result = subprocess.run(cmd, cwd=str(twitter_monitor_path), capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ 采集失败: {result.stderr}")
        return None

    print(result.stdout)

    # 找到最新的数据文件
    reports_dir = twitter_monitor_path / "weekly_reports"
    latest_week = sorted(reports_dir.glob("week_*"), key=lambda x: x.stat().st_mtime, reverse=True)[0]
    raw_data_file = latest_week / "raw_data.json"

    print(f"✅ Step 1 完成: {raw_data_file}")

    return {
        'raw_data_file': str(raw_data_file),
        'week_dir': str(latest_week)
    }


def step2_product_knowledge_processing(raw_data_file):
    """
    Step 2: Product Knowledge 处理
    提取产品 + 匹配现有数据库 + 生成产品-推文映射

    这一步的关键输出：
    - 每个产品对应的推文列表（product_tweets_map.json）
    - 新产品列表
    - 已有产品列表
    """
    print("\n" + "=" * 80)
    print("Step 2/4: 🔍 Product Knowledge 处理")
    print("=" * 80)

    print(f"输入: {raw_data_file}")

    # 调用现有的 analyze_tweets.py (它已经有产品提取逻辑)
    twitter_monitor_path = Path("/Users/wenyongteng/twitter hot news/weekly_monitor")
    analyze_script = twitter_monitor_path / "analyze_tweets.py"

    cmd = [sys.executable, str(analyze_script), raw_data_file]

    print("分析推文中...")
    result = subprocess.run(cmd, cwd=str(twitter_monitor_path), capture_output=True, text=True)

    if result.returncode != 0:
        print(f"⚠️  分析出错: {result.stderr}")
        # 继续执行，因为可能只是警告

    print(result.stdout)

    # 分析结果文件
    analysis_file = raw_data_file.replace('raw_data.json', 'analysis_summary.json')

    # 运行 Product Knowledge 集成
    pk_integrate_script = Path(__file__).parent / "integrate_product_knowledge.py"

    cmd = [sys.executable, str(pk_integrate_script), analysis_file]

    print("\n整合 Product Knowledge...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ 集成失败: {result.stderr}")
        return None

    print(result.stdout)

    # 读取分类结果
    classification_file = analysis_file.replace('analysis_summary.json', 'product_classification.json')

    with open(classification_file, 'r', encoding='utf-8') as f:
        classification = json.load(f)

    print(f"✅ Step 2 完成:")
    print(f"   - 新产品: {len(classification['new_products'])}")
    print(f"   - 已有产品: {len(classification['existing_products'])}")

    return {
        'analysis_file': analysis_file,
        'classification_file': classification_file,
        'classification': classification
    }


def step3_generate_comprehensive_report(raw_data_file, analysis_file, classification_file):
    """
    Step 3: 生成综合报告

    分两部分：
    A) 产品分析 - 使用 Product Knowledge 处理后的数据
    B) 趋势和小事分析 - 使用全部原始推文
    """
    print("\n" + "=" * 80)
    print("Step 3/4: 📝 生成综合报告")
    print("=" * 80)

    # 加载数据
    with open(raw_data_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    with open(classification_file, 'r', encoding='utf-8') as f:
        classification = json.load(f)

    tweets = raw_data.get('tweets', [])
    metadata = raw_data.get('metadata', {})

    print(f"数据加载完成:")
    print(f"  - 原始推文: {len(tweets)}")
    print(f"  - 分析产品: {len(analysis.get('products', {}))}")
    print(f"  - 新产品: {len(classification['new_products'])}")
    print(f"  - 已有产品: {len(classification['existing_products'])}")

    # 生成报告
    report_file = raw_data_file.replace('raw_data.json', 'comprehensive_report.md')

    report = generate_report_content(
        tweets=tweets,
        metadata=metadata,
        analysis=analysis,
        classification=classification
    )

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ Step 3 完成: {report_file}")

    return report_file


def generate_report_content(tweets, metadata, analysis, classification):
    """生成报告内容"""

    date_range = metadata.get('date_range', {})

    report = f"""# Twitter 产品趋势分析报告
## {date_range.get('start', 'N/A')} 至 {date_range.get('end', 'N/A')}

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**数据来源**: Twitter Monitor + Product Knowledge 集成

---

## 📋 执行摘要

**数据概览**
- 监控 KOL: {metadata.get('kol_count', 'N/A')} 个
- 分析推文: {len(tweets):,} 条
- 识别产品: {len(analysis.get('products', {}))} 个
  - **🆕 新产品**: {len(classification['new_products'])} 个
  - **📦 已有产品**: {len(classification['existing_products'])} 个

**核心发现**
1. 本周发现 {len(classification['new_products'])} 个新产品
2. {len(classification['existing_products'])} 个已有产品继续活跃
3. [其他关键趋势...]

---

## 第一部分: 产品分析 (基于 Product Knowledge)

### 🆕 新产品发现 ({len(classification['new_products'])} 个)

"""

    # A) 新产品详情 (使用 Product Knowledge 数据)
    for i, product in enumerate(classification['new_products'][:20], 1):
        name = product['name']
        twitter_data = product['twitter_data']

        report += f"""#### {i}. {name}

**基本信息**
- 提及次数: {twitter_data.get('mention_count', 0)} 次
- 总互动数: {twitter_data.get('total_engagement', 0)}
- 讨论热度: {'⭐' * min(5, twitter_data.get('mention_count', 0) // 5 + 1)}

**Top KOLs**
{chr(10).join(f"- @{kol}" for kol in twitter_data.get('top_kols', [])[:3]) if twitter_data.get('top_kols') else '- (无)'}

**示例推文**
```
{twitter_data.get('sample_tweets', [{}])[0].get('text', 'N/A')[:200] if twitter_data.get('sample_tweets') else 'N/A'}
```

---

"""

    # B) 已有产品热度 (使用 Product Knowledge 数据)
    report += f"""

### 📦 热门已有产品 Top 20

"""

    for i, product in enumerate(classification['existing_products'][:20], 1):
        name = product['kb_canonical_name']
        twitter_data = product['twitter_data']
        kb_data = product['knowledge_data']

        report += f"""#### {i}. {name}

**产品信息** (来自知识库)
- 公司: {kb_data.get('company', 'Unknown')}
- 类别: {kb_data.get('category', 'Unknown')}

**本周动态**
- 提及次数: {twitter_data.get('mention_count', 0)} 次
- 总互动数: {twitter_data.get('total_engagement', 0)}

---

"""

    # C) 趋势分析 (使用全部原始推文)
    report += f"""

---

## 第二部分: 趋势与小事分析 (基于全部推文)

### 📈 宏观趋势

**热门话题**
"""

    top_topics = analysis.get('summary', {}).get('top_topics', {})
    for topic, count in sorted(top_topics.items(), key=lambda x: x[1], reverse=True)[:10]:
        report += f"- {topic}: {count} 次提及\n"

    report += f"""

### 💎 值得注意的小事

[TODO: 基于全部推文的深度分析，识别少数人提到但重要的内容]

---

## 📊 数据附录

### Top KOL 活跃度
"""

    top_kols = analysis.get('top_kols', {})
    for kol, count in sorted(top_kols.items(), key=lambda x: x[1], reverse=True)[:10]:
        report += f"- @{kol}: {count} 条推文\n"

    report += f"""

---

**报告生成**: Claude Code - Twitter Product Trends Analyzer
**数据源**: Twitter API + Product Knowledge Database
"""

    return report


def main(days=7, kol_count=300, use_existing_data=False):
    """完整工作流主函数"""

    print("=" * 80)
    print("🚀 Twitter 产品趋势分析 - 完整工作流")
    print("=" * 80)
    print(f"参数: days={days}, kol_count={kol_count}")
    print(f"使用已有数据: {use_existing_data}")
    print("=" * 80)

    start_time = datetime.now()

    try:
        # Step 1: 采集数据
        if use_existing_data:
            print("\n🧪 使用已有数据模式")
            twitter_monitor_path = Path("/Users/wenyongteng/twitter hot news/weekly_monitor")
            reports_dir = twitter_monitor_path / "weekly_reports"
            latest_week = sorted(reports_dir.glob("week_*"), key=lambda x: x.stat().st_mtime, reverse=True)[0]

            step1_result = {
                'raw_data_file': str(latest_week / "raw_data.json"),
                'week_dir': str(latest_week)
            }
            print(f"使用: {step1_result['raw_data_file']}")
        else:
            step1_result = step1_collect_twitter_data(days, kol_count)
            if not step1_result:
                return False

        # Step 2: Product Knowledge 处理
        step2_result = step2_product_knowledge_processing(step1_result['raw_data_file'])
        if not step2_result:
            return False

        # Step 3: 生成综合报告
        report_file = step3_generate_comprehensive_report(
            raw_data_file=step1_result['raw_data_file'],
            analysis_file=step2_result['analysis_file'],
            classification_file=step2_result['classification_file']
        )

        # 总结
        elapsed = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 80)
        print("✅ 完整流程执行成功!")
        print("=" * 80)
        print(f"⏱️  总耗时: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
        print(f"📁 工作目录: {step1_result['week_dir']}")
        print(f"📄 综合报告: {report_file}")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ 流程失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Twitter 产品趋势分析 - 完整工作流')
    parser.add_argument('--days', type=int, default=7, help='时间范围(天)')
    parser.add_argument('--kol-count', type=int, default=300, help='KOL数量')
    parser.add_argument('--use-existing', action='store_true', help='使用已有数据')

    args = parser.parse_args()

    success = main(
        days=args.days,
        kol_count=args.kol_count,
        use_existing_data=args.use_existing
    )

    sys.exit(0 if success else 1)
