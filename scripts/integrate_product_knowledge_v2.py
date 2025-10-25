#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Product Knowledge 集成脚本 v2 - 修复版
修复：
1. 正确加载 Product Knowledge 数据库（支持列表格式）
2. 处理所有 643 个产品，不只是 Top 30
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Product Knowledge 路径
PK_PATH = Path("/Users/wenyongteng/vibe_coding/product_knowledge-20251022")
PK_VERSION = "v1_cleaned_20251025"


def load_product_knowledge():
    """加载 Product Knowledge 数据库（支持多种格式）"""
    print("📚 加载 Product Knowledge 数据库...")

    version_path = PK_PATH / "versions" / PK_VERSION
    products_file = version_path / "products_list.json"

    if not products_file.exists():
        print(f"   ⚠️  数据库不存在: {products_file}")
        return {}

    with open(products_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 处理不同格式的数据
    products_dict = {}

    if isinstance(data, dict):
        if 'products' in data and isinstance(data['products'], list):
            # 格式: {"total_products": N, "products": [{...}, ...]}
            print(f"   检测到列表格式，共 {data.get('total_products', len(data['products']))} 个产品")
            for product in data['products']:
                if isinstance(product, dict) and 'name' in product:
                    name = product['name']
                    products_dict[name] = product
        else:
            # 格式: {"product_name": {...}, ...}
            for k, v in data.items():
                if isinstance(v, dict):
                    products_dict[k] = v

    elif isinstance(data, list):
        # 格式: [{"name": "...", ...}, ...]
        for product in data:
            if isinstance(product, dict) and 'name' in product:
                name = product['name']
                products_dict[name] = product

    print(f"   ✅ 成功加载 {len(products_dict)} 个产品")

    # 显示示例
    if products_dict:
        sample = list(products_dict.keys())[:5]
        print(f"   示例产品: {', '.join(sample)}")

    return products_dict


def load_twitter_analysis(analysis_file):
    """加载 Twitter 分析结果（所有产品，不只是 Top 30）"""
    print(f"\n📊 加载 Twitter 分析结果...")
    print(f"   文件: {analysis_file}")

    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 获取所有产品（不限制数量）
    products = data.get('products', {})
    new_products = data.get('new_products', {})

    print(f"   ✅ 分析中识别了 {len(products)} 个产品")
    print(f"   ✅ 其中 {len(new_products)} 个标记为新产品")

    return data


def classify_products(twitter_products, knowledge_db):
    """
    对比 Twitter 产品和知识库，分类为：新产品 vs 已有产品
    处理**所有** Twitter 产品
    """
    print("\n🔍 对比产品与知识库...")
    print(f"   - Twitter 产品数: {len(twitter_products)}")
    print(f"   - 知识库产品数: {len(knowledge_db)}")

    new_products = []
    existing_products = []
    ambiguous = []

    # 创建知识库的规范化索引（包括别名）
    kb_normalized = {}
    for kb_name, kb_data in knowledge_db.items():
        if not isinstance(kb_data, dict):
            continue

        normalized_name = kb_name.lower().strip()
        kb_normalized[normalized_name] = {
            'original_name': kb_name,
            'data': kb_data
        }

        # 索引别名（如果有）
        aliases = kb_data.get('aliases', [])
        if not isinstance(aliases, list):
            aliases = []

        for alias in aliases:
            if alias:
                kb_normalized[alias.lower().strip()] = {
                    'original_name': kb_name,
                    'data': kb_data
                }

    print(f"   - 知识库索引（含别名）: {len(kb_normalized)} 个条目")

    # 对比每个 Twitter 产品
    for product_name, twitter_data in twitter_products.items():
        normalized = product_name.lower().strip()

        if normalized in kb_normalized:
            # 精确匹配：已有产品
            kb_match = kb_normalized[normalized]
            existing_products.append({
                'name': product_name,
                'twitter_data': twitter_data,
                'knowledge_data': kb_match['data'],
                'kb_canonical_name': kb_match['original_name']
            })
        else:
            # 模糊匹配（包含关系）
            fuzzy_match = None
            for kb_norm, kb_info in kb_normalized.items():
                if normalized in kb_norm or kb_norm in normalized:
                    fuzzy_match = kb_info
                    break

            if fuzzy_match:
                # 模糊匹配
                ambiguous.append({
                    'name': product_name,
                    'twitter_data': twitter_data,
                    'possible_match': fuzzy_match['original_name'],
                    'knowledge_data': fuzzy_match['data']
                })
            else:
                # 真正的新产品
                new_products.append({
                    'name': product_name,
                    'twitter_data': twitter_data
                })

    print(f"   ✅ 分类完成:")
    print(f"      - 新产品: {len(new_products)}")
    print(f"      - 已有产品（精确匹配）: {len(existing_products)}")
    print(f"      - 模糊匹配: {len(ambiguous)}")

    return {
        'new_products': new_products,
        'existing_products': existing_products,
        'ambiguous': ambiguous
    }


def update_knowledge_db(new_products):
    """将新产品添加到 Product Knowledge"""
    if not new_products:
        print("\n   ℹ️  没有新产品，跳过数据库更新")
        return None

    print(f"\n💾 更新 Product Knowledge 数据库...")
    print(f"   新产品数: {len(new_products)}")

    # 加载当前版本
    current_version_path = PK_PATH / "versions" / PK_VERSION
    current_products_file = current_version_path / "products_list.json"

    with open(current_products_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 处理不同格式
    if isinstance(data, dict) and 'products' in data:
        products_list = data['products']
        original_count = len(products_list)
    else:
        products_list = []
        original_count = 0

    # 添加新产品
    next_id = max([p.get('id', 0) for p in products_list], default=0) + 1

    for product in new_products:
        product_name = product['name']
        twitter_data = product['twitter_data']

        new_product = {
            'id': next_id,
            'name': product_name,
            'company': 'Unknown',
            'versions': [],
            'mention_count': twitter_data.get('mention_count', 0),
            'first_mention_time': datetime.now().isoformat(),
            'source': 'twitter_monitor',
            'confidence': 0.8
        }

        products_list.append(new_product)
        next_id += 1

    # 创建新版本
    new_version_name = f"v2_twitter_{datetime.now().strftime('%Y%m%d_%H%M')}"
    new_version_path = PK_PATH / "versions" / new_version_name
    new_version_path.mkdir(parents=True, exist_ok=True)

    # 保存新产品列表
    new_data = {
        "total_products": len(products_list),
        "products": products_list
    }

    new_products_file = new_version_path / "products_list.json"
    with open(new_products_file, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)

    # 保存元数据
    metadata = {
        "version": new_version_name,
        "created_at": datetime.now().isoformat(),
        "based_on": PK_VERSION,
        "type": "twitter_update",
        "changes": {
            "new_products_added": len(new_products),
            "original_product_count": original_count,
            "new_product_count": len(products_list)
        },
        "new_products_list": [p['name'] for p in new_products]
    }

    metadata_file = new_version_path / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"   ✅ 数据库已更新:")
    print(f"      - 原产品数: {original_count}")
    print(f"      - 新产品数: {len(products_list)}")
    print(f"      - 新版本: {new_version_name}")
    print(f"      - 路径: {new_version_path}")

    return new_version_name


def generate_enhanced_report(twitter_analysis, classification, output_file):
    """生成增强版报告"""
    print(f"\n📝 生成增强版报告...")

    report = f"""# Twitter Product Trends Report (Enhanced)
## {twitter_analysis['summary']['date_range']['start']} 至 {twitter_analysis['summary']['date_range']['end']}

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**数据来源**: Twitter Monitor + Product Knowledge

---

## 📋 执行摘要

**数据概览**
- 总推文数: {twitter_analysis['summary']['total_tweets']:,}
- 识别产品: {twitter_analysis['summary']['unique_products']} 个
  - **🆕 新产品**: {len(classification['new_products'])} 个
  - **📦 已有产品（精确匹配）**: {len(classification['existing_products'])} 个
  - **❓ 模糊匹配**: {len(classification['ambiguous'])} 个

---

## 🆕 新产品发现 ({len(classification['new_products'])}个)

这些产品在 Product Knowledge 数据库中不存在：

"""

    # 新产品列表
    for i, product in enumerate(sorted(classification['new_products'],
                                      key=lambda x: x['twitter_data'].get('mention_count', 0),
                                      reverse=True)[:50], 1):
        name = product['name']
        data = product['twitter_data']

        report += f"""### {i}. {name}

- 提及次数: {data.get('mention_count', 0)} 次
- 总互动数: {data.get('total_engagement', 0)}
- Top KOLs: {', '.join([f"@{k}" for k in data.get('top_kols', [])[:3]])}

---

"""

    # 已有产品列表
    report += f"""

## 📦 已有产品 ({len(classification['existing_products'])}个)

这些产品在 Product Knowledge 数据库中已存在：

"""

    for i, product in enumerate(sorted(classification['existing_products'],
                                      key=lambda x: x['twitter_data'].get('mention_count', 0),
                                      reverse=True)[:50], 1):
        name = product['kb_canonical_name']
        twitter_data = product['twitter_data']
        kb_data = product['knowledge_data']

        report += f"""### {i}. {name}

**知识库信息**
- 公司: {kb_data.get('company', 'Unknown')}
- 历史提及: {kb_data.get('mention_count', 0)} 次

**本周数据**
- 提及次数: {twitter_data.get('mention_count', 0)} 次
- 总互动数: {twitter_data.get('total_engagement', 0)}

---

"""

    # 模糊匹配
    if classification['ambiguous']:
        report += f"""

## ❓ 模糊匹配 ({len(classification['ambiguous'])}个)

这些产品可能与知识库中的产品相关，需要人工确认：

"""
        for i, product in enumerate(classification['ambiguous'][:20], 1):
            report += f"""### {i}. {product['name']}

- 可能匹配: {product['possible_match']}
- 提及次数: {product['twitter_data'].get('mention_count', 0)} 次

---

"""

    # 保存报告
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"   ✅ 报告已生成: {output_file}")
    return output_file


def main(twitter_analysis_file, update_db=True):
    """主流程"""

    print("=" * 80)
    print("🚀 Product Knowledge 集成流程 v2")
    print("=" * 80)

    # 1. 加载数据
    knowledge_db = load_product_knowledge()
    twitter_analysis = load_twitter_analysis(twitter_analysis_file)

    # 2. 分类产品（处理所有产品）
    classification = classify_products(
        twitter_analysis.get('products', {}),
        knowledge_db
    )

    # 3. 更新数据库
    new_version = None
    if update_db and classification['new_products']:
        new_version = update_knowledge_db(classification['new_products'])

    # 4. 生成报告
    output_file = twitter_analysis_file.replace('analysis_summary.json', 'enhanced_report_v2.md')
    report_path = generate_enhanced_report(twitter_analysis, classification, output_file)

    # 5. 保存分类结果
    classification_file = twitter_analysis_file.replace('analysis_summary.json', 'product_classification_v2.json')
    with open(classification_file, 'w', encoding='utf-8') as f:
        json.dump(classification, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("✅ 集成完成!")
    print("=" * 80)
    print(f"📊 新产品: {len(classification['new_products'])}")
    print(f"📦 已有产品: {len(classification['existing_products'])}")
    print(f"❓ 模糊匹配: {len(classification['ambiguous'])}")
    if new_version:
        print(f"💾 数据库版本: {new_version}")
    print(f"📄 增强报告: {report_path}")
    print(f"📄 分类结果: {classification_file}")
    print("=" * 80)

    return {
        'classification': classification,
        'new_version': new_version,
        'report_path': report_path
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='集成 Twitter 分析和 Product Knowledge v2')
    parser.add_argument('analysis_file', help='Twitter 分析结果文件 (analysis_summary.json)')
    parser.add_argument('--no-update-db', action='store_true', help='不更新数据库')

    args = parser.parse_args()

    result = main(
        twitter_analysis_file=args.analysis_file,
        update_db=not args.no_update_db
    )
