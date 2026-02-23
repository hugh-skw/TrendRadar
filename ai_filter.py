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
    prompt = f"你是一个情报专家，请从以下热搜数据中挑选最有价值的新闻，分类总结并提供Markdown格式输出：\n{content}"
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
    # 获取北京时间（Action 默认是 UTC，需要对齐爬虫的文件名）
    today = datetime.now().strftime('%Y-%m-%d')
    db_path = f"output/news/{today}.db"
    
    print(f"--- 诊断模式: 检查数据库 {db_path} ---")
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 1. 自动探测所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"探测到数据库中的表: {tables}")
            
            if not tables:
                print("❌ 数据库是空的，没有表。")
                refined_md = "今日数据库尚未写入内容。"
            else:
                # 2. 尝试寻找包含新闻数据的表
                # 优先找 'news'，如果没有，就找列表里的第一个表
                target_table = 'news' if 'news' in tables else tables[0]
                print(f"📡 正在从表 [{target_table}] 读取数据...")
                
                # 3. 读取列名，防止列名也不叫 title/url
                cursor.execute(f"PRAGMA table_info({target_table})")
                columns = [col[1] for col in cursor.fetchall()]
                print(f"表列名: {columns}")
                
                # 构造通用的查询语句（取前3列或已知列）
                query = f"SELECT * FROM {target_table} ORDER BY rowid DESC LIMIT 60"
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                if df.empty:
                    refined_md = "表内暂无数据。"
                else:
                    # 转化为字符串交给 AI
                    content_str = df.to_string(index=False)
                    refined_md = ai_process(content_str)
            
            with open("AI_Ready_Notes.md", "w", encoding="utf-8") as f:
                f.write(f"---\ntags: #TrendRadar\n---\n{refined_md}")
            print("✅ 简报处理完成")
            
        except Exception as e:
            print(f"❌ 运行中出错: {e}")
            with open("AI_Ready_Notes.md", "w") as f: f.write(f"脚本运行出错: {e}")
    else:
        print(f"❌ 未发现数据库文件: {db_path}")
        # 如果是因为时区问题没找到，列出 output/news 下的所有文件参考
        if os.path.exists("output/news"):
            print(f"output/news 目录下的实际文件: {os.listdir('output/news')}")
