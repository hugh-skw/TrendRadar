import os
import requests
import sqlite3
import pandas as pd
from datetime import datetime

# 配置
API_KEY = os.getenv("AI_API_KEY")
API_URL = "https://api.openai.com/v1/chat/completions" 

def ai_process(content):
    if not API_KEY: return "错误: GitHub Secrets 中未配置 AI_API_KEY"
    
    prompt = f"你是一个情报专家，请从以下热搜数据中挑选最有价值的新闻，分类总结并提供Markdown格式输出：\n{content}"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o-mini", 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=60)
        res_json = response.json()
        
        # 增加对错误的捕捉
        if "error" in res_json:
            return f"OpenAI API 报错: {res_json['error'].get('message', '未知错误')}"
            
        return res_json['choices'][0]['message']['content']
    except Exception as e:
        return f"脚本请求异常: {str(e)}"

if __name__ == "__main__":
    today = datetime.now().strftime('%Y-%m-%d')
    db_path = f"output/news/{today}.db"
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence']
            
            if not tables:
                refined_md = "数据库中没有找到数据表。"
            else:
                # 寻找包含最多数据的表，或者默认选第一个
                target_table = 'news' if 'news' in tables else tables[0]
                query = f"SELECT * FROM {target_table} ORDER BY rowid DESC LIMIT 50"
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                if df.empty:
                    refined_md = "数据表内没有找到内容。"
                else:
                    # 只提取前几列（标题、来源等），避免数据量过大导致 Token 溢出
                    content_str = df.iloc[:, :3].to_string(index=False)
                    refined_md = ai_process(content_str)
            
            with open("AI_Ready_Notes.md", "w", encoding="utf-8") as f:
                f.write(f"---\ntags: #TrendRadar\ncreated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n---\n\n{refined_md}")
            print("✅ 处理步骤尝试完成")
            
        except Exception as e:
            with open("AI_Ready_Notes.md", "w") as f: f.write(f"数据库读取异常: {e}")
    else:
        with open("AI_Ready_Notes.md", "w") as f: f.write(f"未发现数据库文件: {db_path}")
