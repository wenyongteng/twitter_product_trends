#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Product Knowledge 集成脚本 v3
直接从 raw_data.json 提取所有产品（不限于 Top 30）
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Set


# ============ 产品提取逻辑 (复用 analyze_tweets.py) ============

def extract_products(text: str) -> List[str]:
    """从文本中提取产品名"""
    products = set()

    # 产品提取规则 (复用 analyze_tweets.py 的逻辑)
    patterns = [
        # AI 模型和产品
        r'\b(GPT-[0-9o]+(?:\s+(?:mini|turbo|pro|high|minimal|codex))?)\b',
        r'\b(Claude(?:\s+[0-9.]+)?(?:\s+(?:Opus|Sonnet|Haiku))?)\b',
        r'\b(Gemini(?:\s+[0-9.]+)?(?:\s+(?:Pro|Flash|Ultra|Nano\s+Banana))?)\b',
        r'\b(Llama\s+[0-9.]+)\b',
        r'\b(Mistral\s+[0-9.]+)\b',
        r'\b(DeepSeek(?:\s+V[0-9.]+)?(?:\s+(?:Exp|R1))?)\b',
        r'\b(Qwen(?:[0-9.]+)?)\b',

        # 公司和平台
        r'\b(OpenAI|Anthropic|Google|Meta|xAI|Microsoft)\b',
        r'\b(ChatGPT|Copilot|Cursor|Midjourney)\b',
        r'\b(GitHub\s+Copilot|VS\s+Code)\b',

        # 工具和应用
        r'\b(Sora|DALL-E|Stable\s+Diffusion|Seedream)\b',
        r'\b(NotebookLM|Lovable|Replit|Vercel)\b',
        r'\b(Perplexity|Grok)\b',
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) > 0:
                products.add(match.group(1) if match.group(1) else match.group(0))
            else:
                products.add(match.group(0))

    return list(products)


def get_sentiment(text: str) -> str:
    """简单情感分析"""
    positive_words = ['love', 'amazing', 'great', 'awesome', 'excellent', 'fantastic', 'incredible', 'best']
    negative_words = ['hate', 'terrible', 'awful', 'bad', 'poor', 'disappointed', 'worst', 'sucks']

    text_lower = text.lower()
    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)

    if pos_count > neg_count:
        return 'positive'
    elif neg_count > pos_count:
        return 'negative'
    else:
        return 'neutral'


# ============ Product Knowledge 数据库操作 ============

def load_product_knowledge(pk_version_path: str) -> Dict[str, Dict]:
    """加载 Product Knowledge 数据库 (支持 list 格式)"""
    products_file = Path(pk_version_path) / "products_list.json"

    if not products_file.exists():
        print(f"⚠️  Product Knowledge 文件不存在: {products_file}")
        return {}

    with open(products_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 处理 list 格式: {"total_products": N, "products": [{...}, ...]}
    products_dict = {}

    if isinstance(data, dict) and 'products' in data:
        for product in data['products']:
            if isinstance(product, dict) and 'name' in product:
                name = product['name']
                # 也存储小写版本作为 alias
                products_dict[name] = product
                products_dict[name.lower()] = product

                # 处理别名
                if 'aliases' in product:
                    for alias in product.get('aliases', []):
                        products_dict[alias] = product
                        products_dict[alias.lower()] = product

    # 计算唯一产品数量 (通过 id)
    unique_products = set()
    for product in products_dict.values():
        if isinstance(product, dict) and 'id' in product:
            unique_products.add(product['id'])

    print(f"✅ 加载了 {len(unique_products)} 个产品 (含别名共 {len(products_dict)} 条记录)")

    return products_dict


def normalize_product_name(name: str) -> str:
    """标准化产品名（大小写敏感，保留版本号差异）"""
    # 去除多余空格
    name = ' '.join(name.split())
    name = name.strip()

    # 大小写归一化规则（只处理完全一致的名称）
    # 例如: "GOOGLE" -> "Google", "google" -> "Google"
    # 但保留: "Gemini 3" 和 "gemini 3 pro" 作为不同版本

    # 检查是否只是大小写不同（没有其他差异）
    lower_name = name.lower()

    # 公司名称大小写归一化
    company_mappings = {
        'google': 'Google',
        'microsoft': 'Microsoft',
        'meta': 'Meta',
        'openai': 'OpenAI',
        'anthropic': 'Anthropic'
    }

    if lower_name in company_mappings:
        return company_mappings[lower_name]

    # 产品名称大小写归一化（精确匹配）
    product_mappings = {
        'claude': 'Claude',
        'chatgpt': 'ChatGPT',
        'gemini': 'Gemini',
        'sora': 'Sora',
        'copilot': 'Copilot',
        'cursor': 'Cursor',
        'grok': 'Grok',
        'qwen': 'Qwen',
        'vercel': 'Vercel'
    }

    if lower_name in product_mappings:
        return product_mappings[lower_name]

    # 其他情况保持原样（保留版本号差异）
    return name


def match_product_to_knowledge(product_name: str, pk_dict: Dict) -> tuple:
    """
    匹配产品到知识库
    返回: (匹配类型, 规范名称, 知识数据)
    匹配类型: 'exact' | 'fuzzy' | 'new'
    """
    normalized = normalize_product_name(product_name)

    # 精确匹配
    if normalized in pk_dict:
        kb_product = pk_dict[normalized]
        return ('exact', kb_product.get('name', normalized), kb_product)

    # 大小写不敏感匹配
    if normalized.lower() in pk_dict:
        kb_product = pk_dict[normalized.lower()]
        return ('exact', kb_product.get('name', normalized), kb_product)

    # 模糊匹配 (简化版)
    for kb_name, kb_product in pk_dict.items():
        if kb_name.lower() == normalized.lower():
            return ('fuzzy', kb_product.get('name', kb_name), kb_product)

    # 没找到 -> 新产品
    return ('new', normalized, None)


# ============ 主处理流程 ============

def extract_all_products_from_raw_data(raw_data_file: str) -> Dict:
    """从 raw_data.json 提取所有产品 (不限于 Top 30)"""

    print(f"\n📂 读取原始推文数据: {raw_data_file}")

    with open(raw_data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    tweets = data.get('tweets', [])
    print(f"   - 推文总数: {len(tweets)}")

    # 产品统计
    product_mentions = defaultdict(list)  # product -> [tweets]
    sentiment_stats = defaultdict(Counter)  # product -> {positive: N, neutral: M, ...}
    kol_mentions = defaultdict(set)  # product -> {kol1, kol2, ...}

    print(f"\n🔍 提取所有产品...")

    for i, tweet in enumerate(tweets, 1):
        if i % 500 == 0:
            print(f"   处理进度: {i}/{len(tweets)}")

        text = tweet.get('text', '')
        author = tweet.get('author', {})
        kol = author.get('username', 'unknown') if isinstance(author, dict) else str(author)

        # 提取产品
        products = extract_products(text)

        for product in products:
            # 标准化产品名
            product = normalize_product_name(product)

            # 记录提及
            product_mentions[product].append({
                'text': text,
                'kol': kol,
                'rank': tweet.get('rank', 0),
                'followers': tweet.get('followers', 0),
                'likes': tweet.get('likes', 0),
                'retweets': tweet.get('retweets', 0),
                'created_at': tweet.get('created_at', ''),
                'sentiment': get_sentiment(text),
                'is_new': 'launch' in text.lower() or 'new' in text.lower()
            })

            # 统计
            sentiment_stats[product][get_sentiment(text)] += 1
            if kol:  # 确保 kol 不为空
                kol_mentions[product].add(kol)

    print(f"\n✅ 提取完成!")
    print(f"   - 识别产品: {len(product_mentions)} 个")

    # 构造 twitter_products 数据结构
    twitter_products = {}

    for product, mentions in product_mentions.items():
        # 按互动数排序
        sorted_mentions = sorted(
            mentions,
            key=lambda x: x['likes'] + x['retweets'],
            reverse=True
        )

        # Top KOLs (按提及次数)
        kol_counts = Counter([m['kol'] for m in mentions])
        top_kols = [kol for kol, _ in kol_counts.most_common(5)]

        twitter_products[product] = {
            'mention_count': len(mentions),
            'top_kols': top_kols,
            'sentiment': dict(sentiment_stats[product]),
            'total_engagement': sum(m['likes'] + m['retweets'] for m in mentions),
            'sample_tweets': sorted_mentions[:3]  # Top 3 推文
        }

    return twitter_products


def is_company_entity(product_name: str) -> bool:
    """判断是否为公司实体（而非产品）"""
    # 定义公司实体列表
    companies = {
        'Google', 'Microsoft', 'Meta', 'OpenAI', 'Anthropic',
        'xAI', 'NVIDIA', 'Apple', 'Amazon', 'Tesla',
        'DeepMind', 'Hugging Face', 'Stability AI'
    }

    return product_name in companies


def classify_products(twitter_products: Dict, pk_dict: Dict) -> Dict:
    """分类产品: 新产品 vs 已有产品 vs 公司实体"""

    new_products = []
    existing_products = []
    ambiguous = []
    companies = []  # 公司实体单独分类

    print(f"\n🔍 分类产品...")
    print(f"   - Twitter 产品数: {len(twitter_products)}")

    # 计算唯一产品数量
    unique_kb_products = set()
    for product in pk_dict.values():
        if isinstance(product, dict) and 'id' in product:
            unique_kb_products.add(product['id'])

    print(f"   - 知识库产品数: {len(unique_kb_products)}")

    for product_name, twitter_data in twitter_products.items():
        # 首先检查是否为公司实体
        if is_company_entity(product_name):
            companies.append({
                'name': product_name,
                'twitter_data': twitter_data,
                'type': 'company'
            })
            continue

        match_type, canonical_name, kb_data = match_product_to_knowledge(product_name, pk_dict)

        if match_type == 'exact':
            # 已有产品
            existing_products.append({
                'name': product_name,
                'twitter_data': twitter_data,
                'knowledge_data': kb_data,
                'kb_canonical_name': canonical_name
            })

        elif match_type == 'fuzzy':
            # 模糊匹配 - 需要人工确认
            ambiguous.append({
                'name': product_name,
                'twitter_data': twitter_data,
                'possible_match': canonical_name,
                'knowledge_data': kb_data
            })

        else:  # match_type == 'new'
            # 新产品
            new_products.append({
                'name': product_name,
                'twitter_data': twitter_data
            })

    # 按提及次数排序
    new_products.sort(key=lambda x: x['twitter_data']['mention_count'], reverse=True)
    existing_products.sort(key=lambda x: x['twitter_data']['mention_count'], reverse=True)
    companies.sort(key=lambda x: x['twitter_data']['mention_count'], reverse=True)

    print(f"\n📊 分类结果:")
    print(f"   - 新产品: {len(new_products)} 个")
    print(f"   - 已有产品: {len(existing_products)} 个")
    print(f"   - 公司实体: {len(companies)} 个")
    print(f"   - 模糊匹配: {len(ambiguous)} 个")

    return {
        'new_products': new_products,
        'existing_products': existing_products,
        'companies': companies,
        'ambiguous': ambiguous
    }


def generate_enhanced_report(classification: Dict, output_file: str, date_range: Dict):
    """生成增强版报告"""

    new_products = classification['new_products']
    existing_products = classification['existing_products']
    companies = classification.get('companies', [])
    ambiguous = classification['ambiguous']

    total_items = len(new_products) + len(existing_products) + len(companies) + len(ambiguous)

    report = f"""# Twitter Product Trends Report (Enhanced)
## {date_range.get('start', 'N/A')} 至 {date_range.get('end', 'N/A')}

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**数据来源**: Twitter Monitor + Product Knowledge

---

## 📋 执行摘要

**数据概览**
- 总推文数: {date_range.get('total_tweets', 'N/A')}
- 识别实体: {total_items} 个
  - **🆕 新产品**: {len(new_products)} 个
  - **📦 已有产品（精确匹配）**: {len(existing_products)} 个
  - **🏢 公司实体**: {len(companies)} 个
  - **❓ 模糊匹配**: {len(ambiguous)} 个

---

## 🆕 新产品发现 ({len(new_products)}个)

这些产品在 Product Knowledge 数据库中不存在：

"""

    for i, product in enumerate(new_products, 1):
        name = product['name']
        twitter_data = product['twitter_data']

        report += f"""### {i}. {name}

- 提及次数: {twitter_data.get('mention_count', 0)} 次
- 总互动数: {twitter_data.get('total_engagement', 0)}
- Top KOLs: {', '.join(['@' + k for k in twitter_data.get('top_kols', [])[:3]])}

---

"""

    report += f"""

## 📦 已有产品 ({len(existing_products)}个)

这些产品在 Product Knowledge 数据库中已存在：

"""

    for i, product in enumerate(existing_products, 1):
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

    if companies:
        report += f"""

## 🏢 公司实体 ({len(companies)}个)

这些是公司/组织名称（非产品）：

"""
        for i, company in enumerate(companies, 1):
            name = company['name']
            twitter_data = company['twitter_data']

            report += f"""### {i}. {name}

- 提及次数: {twitter_data.get('mention_count', 0)} 次
- 总互动数: {twitter_data.get('total_engagement', 0)}
- Top KOLs: {', '.join(['@' + k for k in twitter_data.get('top_kols', [])[:3]])}

---

"""

    if ambiguous:
        report += f"""

## ❓ 模糊匹配 ({len(ambiguous)}个)

这些产品可能与知识库中的产品相关，需要人工确认：

"""
        for i, product in enumerate(ambiguous, 1):
            name = product['name']
            possible_match = product['possible_match']
            twitter_data = product['twitter_data']

            report += f"""### {i}. {name}

- 可能匹配: {possible_match}
- 提及次数: {twitter_data.get('mention_count', 0)} 次

---

"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✅ 增强版报告已生成: {output_file}")


def update_product_knowledge(new_products: List[Dict], pk_version_path: str) -> str:
    """更新 Product Knowledge 数据库"""

    if not new_products:
        print("\n⚠️  没有新产品需要添加到数据库")
        return pk_version_path

    print(f"\n📝 准备更新 Product Knowledge 数据库...")
    print(f"   - 新产品数量: {len(new_products)}")

    # 加载当前版本
    current_version = Path(pk_version_path)
    products_file = current_version / "products_list.json"

    with open(products_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    original_count = data['total_products']
    products_list = data['products']

    # 计算新的 ID
    max_id = max([p.get('id', 0) for p in products_list], default=0)

    # 添加新产品
    for i, new_product in enumerate(new_products, 1):
        name = new_product['name']
        twitter_data = new_product['twitter_data']

        # 找到首次提及的推文
        first_tweet = twitter_data.get('sample_tweets', [{}])[-1]  # 最后一条通常最早

        products_list.append({
            'id': max_id + i,
            'name': name,
            'company': None,  # 需要人工补充
            'versions': [],
            'mention_count': twitter_data.get('mention_count', 0),
            'first_mention_time': first_tweet.get('created_at', datetime.now().isoformat()),
            'first_mention_tweet_id': None,  # 需要从原始数据获取
            'confidence': 0.7  # 默认置信度
        })

    # 创建新版本
    today = datetime.now().strftime('%Y%m%d')
    new_version_name = f"v2_twitter_{today}"
    new_version_path = current_version.parent / new_version_name

    new_version_path.mkdir(parents=True, exist_ok=True)

    # 保存更新后的产品列表
    new_data = {
        'total_products': len(products_list),
        'products': products_list
    }

    new_products_file = new_version_path / "products_list.json"
    with open(new_products_file, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    # 保存版本元数据
    metadata = {
        'version': new_version_name,
        'created_at': datetime.now().isoformat(),
        'based_on': current_version.name,
        'type': 'twitter_update',
        'changes': {
            'new_products_added': len(new_products),
            'original_product_count': original_count,
            'new_product_count': len(products_list)
        },
        'new_products_list': [p['name'] for p in new_products]
    }

    metadata_file = new_version_path / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Product Knowledge 已更新!")
    print(f"   - 原版本: {current_version.name} ({original_count} 个产品)")
    print(f"   - 新版本: {new_version_name} ({len(products_list)} 个产品)")
    print(f"   - 新增产品: {len(new_products)} 个")
    print(f"   - 新版本路径: {new_version_path}")

    return str(new_version_path)


def main(raw_data_file: str):
    """主流程"""

    print("=" * 80)
    print("🚀 Product Knowledge Integration v3 (处理所有产品)")
    print("=" * 80)

    # 1. 从 raw_data.json 提取所有产品
    twitter_products = extract_all_products_from_raw_data(raw_data_file)

    # 2. 加载 Product Knowledge
    config_file = Path(__file__).parent.parent / "config" / "integration_config.json"
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    pk_project_path = Path(config['product_knowledge']['project_path'])
    pk_current_version = config['product_knowledge']['current_version']
    pk_version_path = pk_project_path / "versions" / pk_current_version

    pk_dict = load_product_knowledge(str(pk_version_path))

    # 3. 分类产品
    classification = classify_products(twitter_products, pk_dict)

    # 4. 生成报告
    week_dir = Path(raw_data_file).parent
    output_file = week_dir / "enhanced_report_v3.md"

    with open(raw_data_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    date_range = raw_data.get('metadata', {}).get('date_range', {})
    date_range['total_tweets'] = len(raw_data.get('tweets', []))

    generate_enhanced_report(classification, str(output_file), date_range)

    # 5. 保存分类结果
    classification_file = week_dir / "product_classification_v3.json"
    with open(classification_file, 'w', encoding='utf-8') as f:
        json.dump(classification, f, ensure_ascii=False, indent=2)

    print(f"✅ 产品分类已保存: {classification_file}")

    # 6. 更新 Product Knowledge (可选)
    if classification['new_products']:
        update_pk = input(f"\n发现 {len(classification['new_products'])} 个新产品。是否更新 Product Knowledge? (y/n): ")
        if update_pk.lower() == 'y':
            new_version_path = update_product_knowledge(
                classification['new_products'],
                str(pk_version_path)
            )
            print(f"\n💡 提示: 记得更新配置文件中的 current_version 为: {Path(new_version_path).name}")

    print("\n" + "=" * 80)
    print("✅ 完成!")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python integrate_product_knowledge_v3.py <raw_data.json>")
        sys.exit(1)

    raw_data_file = sys.argv[1]
    main(raw_data_file)
