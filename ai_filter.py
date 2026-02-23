import os
import requests
import sqlite3
import pandas as pd
from datetime import datetime

# 配置 SiliconFlow
API_KEY = os.getenv("AI_API_KEY")
# 接口地址
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

def ai_process(content):
    if not API_KEY: return "错误: 未配置 AI_API_KEY"
    
    prompt = (
        "你是一个专业的情报分析师。请分析以下热搜数据，剔除无意义的娱乐八卦，"
        "保留技术、社会动态和行业新闻。请用 Markdown 列表输出，包含分类、简要概括和原始链接。\n"
        f"数据内容：\n{content}"
    )
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 使用 deepseek-v3 或 deepseek-r1
    payload = {
        "model": "deepseek-ai/DeepSeek-V3", 
        "messages": [
            {"role": "system", "content": "你是一个高效、客观的简报助手。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
        res_json = response.json()
        
        if response.status_code != 200:
            error_msg = res_json.get('error', {}).get('message', '未知错误')
            return f"AI 平台报错 (状态码 {response.status_code}): {error_msg}"
            
        return res_json['choices'][0]['message']['content']
    except Exception as e:
        return f"请求异常: {str(e)}"

if __name__ == "__main__":
    # 数据库读取逻辑保持不变
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
                # 选取前 60 条数据，增加信息覆盖面
                query = f"SELECT * FROM {target_table} ORDER BY rowid DESC LIMIT 60"
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                if df.empty:
                    refined_md = "数据表内没有找到内容。"
                else:
                    # 提取前三列 (title, url, source)
                    content_str = df.iloc[:, :3].to_string(index=False)
                    refined_md = ai_process(content_str)
            
            with open("AI_Ready_Notes.md", "w", encoding="utf-8") as f:
                f.write(f"---\ntags: #TrendRadar #DeepSeek\ncreated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n---\n\n{refined_md}")
            print("✅ 简报处理完成 (SiliconFlow)")
            
        except Exception as e:
            with open("AI_Ready_Notes.md", "w") as f: f.write(f"数据库读取异常: {e}")
    else:
        # 如果找不到今日 DB，尝试找最新的 DB 防止时差导致失败
        latest_file = ""
        if os.path.exists("output/news"):
            dbs = [f for f in os.listdir("output/news") if f.endswith(".db")]
            if dbs: latest_file = sorted(dbs)[-1]
        
        with open("AI_Ready_Notes.md", "w") as f: 
            f.write(f"未发现今日数据库文件。目录内最新文件为: {latest_file}\n请确认爬虫是否成功运行。")
