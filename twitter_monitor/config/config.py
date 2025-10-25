"""
配置文件
"""

# 数据采集配置
DATA_COLLECTION = {
    'kol_range': 300,              # Top N KOL
    'days': 7,                      # 过去N天
    'exclude_retweets': True,       # 排除转发
    'min_engagement': 5,            # 最低互动数
}

# 新产品发现配置
PRODUCT_DISCOVERY = {
    'min_mentions': 1,              # 最少提及次数
    'min_kol_count': 1,             # 最少KOL数量
    'min_top100_kol': 0,            # 最少Top100 KOL（0表示不要求）
    'llm_batch_size': 50,           # LLM批处理大小
    'confidence_threshold': 0.6,    # LLM验证置信度阈值
}

# 行业洞察配置
INSIGHTS = {
    'n_topics': 10,                 # 提取话题数
    'clustering_method': 'hybrid',  # tfidf / llm / hybrid
    'top_quotes': 10,               # 关键引用数
    'min_topic_tweets': 5,          # 话题最少推文数
}

# LLM配置
LLM = {
    'provider': 'claude',           # claude / openai
    'model': 'claude-3-5-sonnet-20241022',
    'max_tokens': 4000,
    'temperature': 0.3,
    # API key从环境变量ANTHROPIC_API_KEY读取
}

# 输出配置
OUTPUT = {
    'format': ['markdown', 'json'],
    'output_dir': 'weekly_reports',
    'include_raw_data': True,
}

# 信号词库（用于新产品发现）
RELEASE_SIGNALS = {
    'launch': [
        'just released', 'just launched', 'just announced', 'just dropped',
        'now released', 'now available', 'now live', 'is out',
        'has launched', 'has released', 'officially launched',
        'new release', 'latest release', 'releasing', 'launched today',
        'released today', 'announcing', 'proud to announce',
    ],

    'new': [
        'new model', 'new tool', 'new AI', 'new product',
        'newest', 'brand new', 'all-new', 'introducing new',
        'new version', 'new update',
    ],

    'announcement': [
        'announced', 'unveiling', 'unveiled', 'introducing',
        'presents', 'debut', 'launches', 'releases',
        'rolling out', 'shipping',
    ],

    'availability': [
        'available now', 'now available', 'can try', 'try it now',
        'sign up', 'get access', 'early access', 'beta access',
        'open beta', 'public beta', 'waitlist',
    ],

    'comparison': [
        'better than', 'beats', 'outperforms', 'vs', 'compared to',
        'alternative to', 'competitor to', 'rival to',
    ],

    'excitement': [
        'amazing', 'incredible', 'wow', 'mind-blowing', 'game changer',
        'revolutionary', 'breakthrough', 'impressive',
    ],

    'testing': [
        'tried', 'tested', 'using', 'played with', 'experimenting with',
        'hands on', 'first look', 'review of', 'testing out',
    ]
}

# 排除词（避免误识别）
EXCLUDE_TERMS = [
    'AI', 'ChatGPT', 'GPT', 'LLM', 'ML', 'AGI', 'GenAI',
    'Google', 'OpenAI', 'Anthropic', 'Microsoft', 'Meta',
    'Twitter', 'X', 'Tesla', 'Apple', 'Amazon',
]
