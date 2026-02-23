import os
import requests
import sqlite3
import pandas as pd
from datetime import datetime

# 配置
API_KEY = os.getenv("FILTER_AI_API_KEY")
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

def is_valid_url(url):
    """过滤掉各平台的热榜主页/广告链接"""
    junk_keywords = [
        'billboard', 'hot-search', 'trending', 
        'top/list', 'hub', 'search?q=', 'topic/index'
    ]
    # 如果链接太短或者包含垃圾关键词，判定为无效
    if len(str(url)) < 25 or any(k in str(url).lower() for k in junk_keywords):
        return False
    return True

def ai_process(content):
    if not API_KEY: return "错误: 未配置 FILTER_AI_API_KEY"
    
    # 强制 AI 检查链接有效性
    prompt = (
        "你是一个极其严谨的情报官。我会给你一份抓取到的数据。\n"
        "任务要求：\n"
        "1. 严格剔除标题重复、链接为平台主页（如 billboard, hot-search）的内容。\n"
        "2. 必须保留具体的详情页链接。如果是单纯的列表页，直接舍弃。\n"
        "3. 按领域（科技、硬件、社会）分类，每条内容概括核心点。\n"
        f"待处理数据：\n{content}"
    )
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-ai/DeepSeek-V3", 
        "messages": [
            {"role": "system", "content": "你只输出有价值的深度简报，拒绝任何无效的主页链接。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2 # 降低随机性，提高筛选严谨度
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"请求异常: {str(e)}"

if __name__ == "__main__":
    today = datetime.now().strftime('%Y-%m-%d')
    db_path = f"output/news/{today}.db"
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            # 增加筛选：只读取包含具体 ID 或长路径的新闻，初步过滤掉主页
            query = "SELECT title, url, source FROM news ORDER BY create_time DESC LIMIT 100"
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # --- 关键步骤：在喂给 AI 前进行代码级预过滤 ---
            df['is_real_news'] = df['url'].apply(is_valid_url)
            clean_df = df[df['is_real_news'] == True].drop(columns=['is_real_news'])
            
            if clean_df.empty:
                refined_md = "⚠️ 警报：今日抓取到的全是平台主页或无效链接，已自动拦截。"
            else:
                # 只给 AI 最新的 40 条有效数据，保证质量
                content_str = clean_df.head(40).to_string(index=False)
                refined_md = ai_process(content_str)
            
            with open("AI_Ready_Notes.md", "w", encoding="utf-8") as f:
                f.write(f"---\ntags: #TrendRadar\n---\n\n{refined_md}")
            print("✅ 深度过滤简报处理完成")
            
        except Exception as e:
            print(f"出错: {e}")
