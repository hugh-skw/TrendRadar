import os
import requests
import sqlite3
import pandas as pd
from datetime import datetime

# 配置 Gemini
API_KEY = os.getenv("AI_API_KEY")
# 使用 Gemini 1.5 Flash，速度快且免费额度高
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"

def ai_process(content):
    if not API_KEY: return "错误: 未配置 AI_API_KEY"
    
    prompt = f"你是一个情报专家，请从以下热搜数据中挑选最有价值的新闻，分类总结并提供Markdown格式输出：\n{content}"
    
    headers = {"Content-Type": "application/json"}
    # Gemini 的数据结构
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 2048,
        }
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=60)
        res_json = response.json()
        
        # 错误检查
        if "error" in res_json:
            return f"Gemini API 报错: {res_json['error'].get('message', '未知错误')}"
            
        # 提取 Gemini 的返回文字
        return res_json['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"Gemini 请求异常: {str(e)}"

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
                target_table = 'news' if 'news' in tables else tables[0]
                # 读取最新数据
                query = f"SELECT * FROM {target_table} ORDER BY rowid DESC LIMIT 60"
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                if df.empty:
                    refined_md = "数据表内没有找到内容。"
                else:
                    # 选取前 3 列通常是 title, url, source
                    content_str = df.iloc[:, :3].to_string(index=False)
                    refined_md = ai_process(content_str)
            
            with open("AI_Ready_Notes.md", "w", encoding="utf-8") as f:
                # 保持 Obsidian 友好的 Frontmatter
                f.write(f"---\ntags: #TrendRadar #Gemini\ncreated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n---\n\n{refined_md}")
            print("✅ Gemini 处理流程尝试完成")
            
        except Exception as e:
            with open("AI_Ready_Notes.md", "w") as f: f.write(f"数据库读取异常: {e}")
    else:
        # 如果是因为时差，尝试寻找目录下最新的 db
        if os.path.exists("output/news"):
            all_dbs = [f for f in os.listdir("output/news") if f.endswith(".db")]
            if all_dbs:
                latest_db = sorted(all_dbs)[-1]
                print(f"当前日期无库，改用最新库: {latest_db}")
                # 此处可增加逻辑递归调用，但为了初次运行建议先确认日期对齐
        with open("AI_Ready_Notes.md", "w") as f: f.write(f"未发现今日数据库文件: {db_path}")
