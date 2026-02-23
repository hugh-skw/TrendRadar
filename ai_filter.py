import os
import requests
import sqlite3
import pandas as pd
from datetime import datetime

# 配置
API_KEY = os.getenv("AI_API_KEY")
API_URL = "https://api.openai.com/v1/chat/completions" 

def ai_process(content):
    if not API_KEY: return "错误: 未配置 AI_API_KEY"
    prompt = f"你是一个情报专家，请从以下热搜数据中挑选5-10条最有价值的新闻，进行分类总结并提供Markdown格式输出：\n{content}"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o-mini", 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=60)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"AI 处理异常: {e}"

if __name__ == "__main__":
    # 根据日志，数据库位于 output/news/YYYY-MM-DD.db
    today = datetime.now().strftime('%Y-%m-%d')
    db_path = f"output/news/{today}.db"
    
    print(f"--- 尝试读取数据库: {db_path} ---")
    
    if os.path.exists(db_path):
        try:
            # 连接数据库读取新闻
            conn = sqlite3.connect(db_path)
            # TrendRadar 的表名通常是 news
            query = "SELECT title, url, source FROM news ORDER BY create_time DESC LIMIT 50"
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                refined_md = "数据库中暂无今日新增数据。"
            else:
                content_str = df.to_string(index=False)
                refined_md = ai_process(content_str)
            
            with open("AI_Ready_Notes.md", "w", encoding="utf-8") as f:
                f.write(f"---\ntags: #TrendRadar\n---\n{refined_md}")
            print("✅ 简报已成功根据数据库内容生成")
            
        except Exception as e:
            print(f"数据库读取失败: {e}")
            with open("AI_Ready_Notes.md", "w") as f: f.write(f"数据库读取失败: {e}")
    else:
        print(f"❌ 未发现数据库文件: {db_path}")
        with open("AI_Ready_Notes.md", "w") as f: f.write("今日尚未生成数据库文件，请确认爬虫是否运行。")
