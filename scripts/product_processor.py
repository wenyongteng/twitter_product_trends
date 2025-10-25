#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Product Processor - Module 2
调用 product_knowledge 提取和匹配产品信息
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import time

# 添加 product_knowledge 到 Python Path
PRODUCT_KNOWLEDGE_PATH = Path("/Users/wenyongteng/vibe_coding/product_knowledge-20251022")
sys.path.insert(0, str(PRODUCT_KNOWLEDGE_PATH))

try:
    from openai import OpenAI
except ImportError:
    print("❌ 需要安装 openai 库")
    print("   pip3 install openai")
    sys.exit(1)


class ProductProcessor:
    """产品提取和匹配处理器"""

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化处理器

        Args:
            config: 配置字典
        """
        if config is None:
            config_path = Path(__file__).parent.parent / "config" / "integration_config.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                full_config = json.load(f)
                extraction_config = full_config['extraction']
                pk_config = full_config['product_knowledge']
                self.classification_config = full_config.get('classification', {})

        else:
            extraction_config = config.get('extraction', {})
            pk_config = config.get('product_knowledge', {})
            self.classification_config = config.get('classification', {})

        # 提取配置
        self.model = extraction_config.get('model', 'openai/gpt-4o')
        self.api_key = extraction_config.get('api_key')
        self.base_url = extraction_config.get('base_url', 'https://openrouter.ai/api/v1')
        self.batch_size = extraction_config.get('batch_size', 10)
        self.max_workers = extraction_config.get('max_workers', 8)
        self.rate_limit_delay = extraction_config.get('rate_limit_delay', 0.5)

        # Product Knowledge 配置
        self.pk_project_path = Path(pk_config.get('project_path'))
        self.pk_current_version = pk_config.get('current_version')
        self.pk_versions_dir = Path(pk_config.get('versions_dir'))

        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

        # 加载现有产品数据库
        self.existing_products = self._load_existing_products()

        # 提取结果
        self.extraction_result = None

    def _load_existing_products(self) -> Dict:
        """加载现有的产品数据库"""
        print(f"📚 加载现有产品数据库...")

        version_path = self.pk_versions_dir / self.pk_current_version
        products_file = version_path / "products_list.json"

        if not products_file.exists():
            print(f"   ⚠️  未找到产品数据库: {products_file}")
            return {}

        with open(products_file, 'r', encoding='utf-8') as f:
            products = json.load(f)

        print(f"   ✅ 加载完成: {len(products)} 个产品")

        return products

    def process(self, tweets: List[Dict]) -> Dict:
        """
        处理推文,提取和匹配产品

        Args:
            tweets: 推文列表

        Returns:
            提取结果
        """
        print(f"\n🔍 开始提取和匹配产品...")
        print(f"   - 推文数: {len(tweets)}")
        print(f"   - 批处理大小: {self.batch_size}")

        # 提取产品
        extracted_products = self._extract_products(tweets)

        # 匹配现有产品
        matched_results = self._match_products(extracted_products, tweets)

        # 保存结果
        self.extraction_result = {
            "extraction_metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_tweets": len(tweets),
                "model_used": self.model
            },
            "summary": {
                "total_products_extracted": len(extracted_products),
                "new_products": len(matched_results['new_products']),
                "matched_existing": len(matched_results['matched_products']),
                "new_releases": len(matched_results['new_releases'])
            },
            "products": extracted_products,
            "new_products": matched_results['new_products'],
            "matched_products": matched_results['matched_products'],
            "new_releases": matched_results['new_releases'],
            "product_tweet_map": matched_results['product_tweet_map']
        }

        # 保存到文件
        self._save_extraction_result()

        print(f"\n   ✅ 提取完成:")
        print(f"      - 总产品数: {len(extracted_products)}")
        print(f"      - 新产品: {len(matched_results['new_products'])}")
        print(f"      - 已有产品: {len(matched_results['matched_products'])}")
        print(f"      - 新版本: {len(matched_results['new_releases'])}")

        return self.extraction_result

    def _extract_products(self, tweets: List[Dict]) -> List[Dict]:
        """使用 GPT-4o 提取产品信息"""

        print(f"\n   🤖 使用 {self.model} 提取产品...")

        all_products = []
        product_names_seen = set()

        # 分批处理
        for i in range(0, len(tweets), self.batch_size):
            batch = tweets[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(tweets) + self.batch_size - 1) // self.batch_size

            print(f"      批次 {batch_num}/{total_batches} ({len(batch)} 条推文)...")

            # 构建批次文本
            batch_text = self._build_batch_text(batch)

            # 调用 LLM 提取
            products = self._call_llm_extract(batch_text, batch)

            # 去重
            for product in products:
                product_name = product.get('name', '').lower()
                if product_name and product_name not in product_names_seen:
                    all_products.append(product)
                    product_names_seen.add(product_name)

            # 速率限制
            if i + self.batch_size < len(tweets):
                time.sleep(self.rate_limit_delay)

        print(f"   ✅ 提取完成: {len(all_products)} 个不同产品")

        return all_products

    def _build_batch_text(self, tweets: List[Dict]) -> str:
        """构建批次文本"""
        batch_lines = []

        for idx, tweet in enumerate(tweets, 1):
            text = tweet.get('text', '')
            batch_lines.append(f"[Tweet {idx}] {text}")

        return "\n\n".join(batch_lines)

    def _call_llm_extract(self, batch_text: str, tweets: List[Dict]) -> List[Dict]:
        """调用 LLM 提取产品"""

        prompt = f"""你是一个专业的产品信息提取助手。请从以下推文中提取所有提到的**技术产品、工具、服务、平台或应用**。

要求:
1. 只提取明确的产品名称(如 Claude, ChatGPT, VS Code, Cursor等)
2. 不要提取:
   - 公司名(除非公司名本身就是产品名,如 OpenAI)
   - 通用概念(如 AI, machine learning, API)
   - 动词或形容词(如 launched, released, drop)
3. 如果产品有版本号,请在 version 字段记录
4. 尽可能推断产品的公司和类别

推文内容:
{batch_text}

请以JSON格式返回,格式如下:
[
  {{
    "name": "产品名称",
    "company": "公司名(如果能推断出)",
    "category": "产品类别(如: AI Tool, IDE, Design Tool等)",
    "version": "版本号(如果提到)",
    "mentioned_in_tweet_indices": [1, 3]
  }}
]

注意: 只返回JSON数组,不要有其他文字。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000
            )

            content = response.choices[0].message.content.strip()

            # 提取JSON
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            content = content.strip()

            products = json.loads(content)

            # 添加推文引用
            for product in products:
                tweet_indices = product.get('mentioned_in_tweet_indices', [])
                product['related_tweets'] = [
                    tweets[idx - 1] for idx in tweet_indices
                    if 0 < idx <= len(tweets)
                ]

            return products

        except Exception as e:
            print(f"      ⚠️  提取失败: {e}")
            return []

    def _match_products(self, extracted_products: List[Dict], tweets: List[Dict]) -> Dict:
        """匹配现有产品"""

        print(f"\n   🔗 匹配现有产品...")

        new_products = []
        matched_products = []
        new_releases = []
        product_tweet_map = defaultdict(list)

        for product in extracted_products:
            product_name = product.get('name', '').lower()
            version = product.get('version')

            # 检查是否在现有数据库中
            existing = None
            for existing_name, existing_data in self.existing_products.items():
                # 跳过非字典类型的值
                if not isinstance(existing_data, dict):
                    continue

                if existing_name.lower() == product_name:
                    existing = existing_data
                    break

                # 检查别名
                aliases = existing_data.get('aliases', [])
                if product_name in [a.lower() for a in aliases]:
                    existing = existing_data
                    break

            if existing:
                # 已有产品
                matched_products.append({
                    **product,
                    'existing_data': existing,
                    'match_type': 'exact' if existing_name.lower() == product_name else 'alias'
                })

                # 检查是否有新版本
                if version:
                    existing_versions = existing.get('versions', [])
                    if version not in existing_versions:
                        new_releases.append({
                            'product_name': product.get('name'),
                            'version': version,
                            'company': product.get('company') or existing.get('company'),
                            'category': product.get('category') or existing.get('category'),
                            'related_tweets': product.get('related_tweets', [])
                        })
            else:
                # 新产品
                new_products.append(product)

            # 记录产品-推文映射
            for tweet in product.get('related_tweets', []):
                product_tweet_map[product.get('name')].append(tweet)

        print(f"   ✅ 匹配完成:")
        print(f"      - 新产品: {len(new_products)}")
        print(f"      - 已有产品: {len(matched_products)}")
        print(f"      - 新版本: {len(new_releases)}")

        return {
            'new_products': new_products,
            'matched_products': matched_products,
            'new_releases': new_releases,
            'product_tweet_map': dict(product_tweet_map)
        }

    def _save_extraction_result(self):
        """保存提取结果"""
        output_dir = Path(__file__).parent.parent / "data_sources"
        output_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y%m%d")
        output_file = output_dir / f"{date_str}_extracted_products.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.extraction_result, f, indent=2, ensure_ascii=False)

        print(f"\n   💾 提取结果已保存: {output_file}")

    def update_knowledge_db(self):
        """更新 Product Knowledge 数据库"""
        print(f"\n💾 更新 Product Knowledge 数据库...")

        if not self.extraction_result:
            print("   ⚠️  没有提取结果,跳过更新")
            return

        new_products = self.extraction_result.get('new_products', [])

        if not new_products:
            print("   ℹ️  没有新产品,无需更新数据库")
            return

        # 创建新版本
        new_version_name = f"v2_{datetime.now().strftime('%Y%m%d')}"
        new_version_path = self.pk_versions_dir / new_version_name

        print(f"   📂 创建新版本: {new_version_name}")
        new_version_path.mkdir(parents=True, exist_ok=True)

        # 复制当前版本的数据
        current_version_path = self.pk_versions_dir / self.pk_current_version
        current_products_file = current_version_path / "products_list.json"

        with open(current_products_file, 'r', encoding='utf-8') as f:
            all_products = json.load(f)

        # 添加新产品
        for product in new_products:
            product_name = product.get('name')
            all_products[product_name] = {
                'name': product_name,
                'company': product.get('company', 'Unknown'),
                'category': product.get('category', 'Unknown'),
                'first_seen': datetime.now().isoformat(),
                'version': product.get('version'),
                'aliases': [],
                'source': 'twitter_extraction'
            }

        # 保存新版本
        new_products_file = new_version_path / "products_list.json"
        with open(new_products_file, 'w', encoding='utf-8') as f:
            json.dump(all_products, f, indent=2, ensure_ascii=False)

        # 保存元数据
        metadata = {
            "version": new_version_name,
            "created_at": datetime.now().isoformat(),
            "based_on": self.pk_current_version,
            "type": "twitter_update",
            "changes": {
                "new_products_added": len(new_products),
                "original_product_count": len(self.existing_products),
                "new_product_count": len(all_products)
            }
        }

        metadata_file = new_version_path / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"   ✅ 数据库已更新:")
        print(f"      - 新增产品: {len(new_products)}")
        print(f"      - 总产品数: {len(all_products)}")
        print(f"      - 新版本路径: {new_version_path}")


def main():
    """测试入口"""
    # 加载测试数据
    data_file = Path(__file__).parent.parent / "data_sources" / "20251025_raw_tweets.json"

    if not data_file.exists():
        print(f"❌ 测试数据不存在: {data_file}")
        return

    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    tweets = data.get('tweets', [])[:50]  # 只测试前50条

    processor = ProductProcessor()
    result = processor.process(tweets)

    print(f"\n✅ 处理完成!")
    print(f"   提取产品: {result['summary']['total_products_extracted']}")
    print(f"   新产品: {result['summary']['new_products']}")


if __name__ == "__main__":
    main()
