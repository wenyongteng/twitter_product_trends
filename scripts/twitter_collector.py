#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Data Collector - Module 1
调用 twitterio API 采集 Top KOL 推文
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class TwitterCollector:
    """Twitter 数据采集器"""

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化采集器

        Args:
            config: 配置字典 (如果为None则从文件读取)
        """
        if config is None:
            config_path = Path(__file__).parent.parent / "config" / "integration_config.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                full_config = json.load(f)
                config = full_config['twitter']

        self.kol_count = config.get('kol_count', 300)
        self.days = config.get('days', 7)
        self.collector_path = Path(config.get('collector_path'))
        self.output_dir = Path(config.get('output_dir'))

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def collect(self, days: Optional[int] = None, kol_count: Optional[int] = None) -> List[Dict]:
        """
        采集 Twitter 数据

        Args:
            days: 时间范围(天) - 覆盖配置
            kol_count: KOL数量 - 覆盖配置

        Returns:
            推文列表
        """
        days = days or self.days
        kol_count = kol_count or self.kol_count

        print(f"📱 开始采集 Twitter 数据...")
        print(f"   - KOL 数量: {kol_count}")
        print(f"   - 时间范围: 过去 {days} 天")

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 检查是否有可用的历史数据
        existing_data = self._check_existing_data(start_date, end_date)

        if existing_data:
            print(f"   ✅ 找到已有数据: {existing_data['file_path']}")
            print(f"      - 日期范围: {existing_data['start_date']} 至 {existing_data['end_date']}")
            print(f"      - 推文数: {existing_data['tweet_count']}")

            # 询问是否使用已有数据
            use_existing = input(f"\n   使用已有数据? (y/n, 默认y): ").strip().lower()
            if use_existing != 'n':
                return self._load_existing_data(existing_data['file_path'])

        # 采集新数据
        raw_tweets = self._collect_new_data(days, kol_count)

        # 保存到本地
        output_file = self._save_data(raw_tweets, start_date, end_date)
        print(f"   ✅ 数据已保存: {output_file}")

        return raw_tweets

    def _check_existing_data(self, start_date: datetime, end_date: datetime) -> Optional[Dict]:
        """检查是否有已存在的数据"""

        # 检查本地 data_sources/
        for file_path in self.output_dir.glob("*_raw_tweets.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                metadata = data.get('metadata', {})
                date_range = metadata.get('date_range', {})

                if date_range:
                    # 检查日期范围是否匹配
                    data_start = datetime.fromisoformat(date_range['start'])
                    data_end = datetime.fromisoformat(date_range['end'])

                    # 允许 ±1 天的误差
                    if abs((data_start - start_date).days) <= 1 and \
                       abs((data_end - end_date).days) <= 1:
                        return {
                            'file_path': str(file_path),
                            'start_date': date_range['start'],
                            'end_date': date_range['end'],
                            'tweet_count': metadata.get('tweet_count', len(data.get('tweets', [])))
                        }
            except Exception as e:
                continue

        # 检查 twitter monitor 的周报目录
        monitor_reports_dir = self.collector_path / "weekly_reports"
        if monitor_reports_dir.exists():
            for week_dir in monitor_reports_dir.glob("week_*"):
                raw_data_file = week_dir / "raw_data.json"
                if raw_data_file.exists():
                    try:
                        with open(raw_data_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        metadata = data.get('metadata', {})
                        date_range = metadata.get('date_range', {})

                        if date_range:
                            data_start = datetime.fromisoformat(date_range['start'])
                            data_end = datetime.fromisoformat(date_range['end'])

                            if abs((data_start - start_date).days) <= 1 and \
                               abs((data_end - end_date).days) <= 1:
                                return {
                                    'file_path': str(raw_data_file),
                                    'start_date': date_range['start'],
                                    'end_date': date_range['end'],
                                    'tweet_count': metadata.get('total_tweets', len(data.get('tweets', [])))
                                }
                    except Exception as e:
                        continue

        return None

    def _load_existing_data(self, file_path: str) -> List[Dict]:
        """加载已存在的数据"""
        print(f"   📂 加载已有数据: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        tweets = data.get('tweets', data.get('all_tweets', []))
        print(f"   ✅ 加载完成: {len(tweets)} 条推文")

        return tweets

    def _collect_new_data(self, days: int, kol_count: int) -> List[Dict]:
        """采集新数据"""
        print(f"\n   🔄 开始采集新数据...")

        # 调用 twitter monitor 的采集脚本
        collect_script = self.collector_path / "collect_data.py"

        if not collect_script.exists():
            raise FileNotFoundError(f"采集脚本不存在: {collect_script}")

        # 执行采集命令
        cmd = [
            sys.executable,
            str(collect_script),
            '--days', str(days),
            '--kol-count', str(kol_count)
        ]

        print(f"   执行命令: {' '.join(cmd)}")
        print(f"   (这可能需要几分钟...)\n")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.collector_path),
                capture_output=True,
                text=True,
                timeout=1800  # 30分钟超时
            )

            if result.returncode != 0:
                print(f"   ❌ 采集失败:")
                print(result.stderr)
                raise RuntimeError(f"Twitter 数据采集失败: {result.stderr}")

            print(result.stdout)

            # 查找最新生成的数据文件
            latest_data_file = self._find_latest_data_file()

            if not latest_data_file:
                raise FileNotFoundError("未找到采集的数据文件")

            # 加载数据
            with open(latest_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            tweets = data.get('tweets', data.get('all_tweets', []))
            print(f"   ✅ 采集完成: {len(tweets)} 条推文")

            return tweets

        except subprocess.TimeoutExpired:
            raise RuntimeError("采集超时 (30分钟)")

    def _find_latest_data_file(self) -> Optional[Path]:
        """查找最新生成的数据文件"""

        # 查找 weekly_reports/ 下最新的 raw_data.json
        reports_dir = self.collector_path / "weekly_reports"

        if not reports_dir.exists():
            return None

        week_dirs = sorted(
            [d for d in reports_dir.glob("week_*") if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        for week_dir in week_dirs:
            raw_data_file = week_dir / "raw_data.json"
            if raw_data_file.exists():
                return raw_data_file

        return None

    def _save_data(self, tweets: List[Dict], start_date: datetime, end_date: datetime) -> Path:
        """保存数据到本地"""

        date_str = datetime.now().strftime("%Y%m%d")
        output_file = self.output_dir / f"{date_str}_raw_tweets.json"

        data = {
            "metadata": {
                "collection_date": datetime.now().isoformat(),
                "kol_count": self.kol_count,
                "tweet_count": len(tweets),
                "date_range": {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d")
                }
            },
            "tweets": tweets
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return output_file


def main():
    """测试入口"""
    import argparse

    parser = argparse.ArgumentParser(description='Twitter 数据采集器')
    parser.add_argument('--days', type=int, default=7, help='时间范围(天)')
    parser.add_argument('--kol-count', type=int, default=300, help='KOL数量')

    args = parser.parse_args()

    collector = TwitterCollector()
    tweets = collector.collect(days=args.days, kol_count=args.kol_count)

    print(f"\n✅ 采集完成!")
    print(f"   推文数: {len(tweets)}")


if __name__ == "__main__":
    main()
