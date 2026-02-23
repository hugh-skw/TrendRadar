import os
import requests
import sqlite3
import pandas as pd
from datetime import datetime

# 配置 Gemini
API_KEY = os.getenv("AI_API_KEY")
# 使用 Gemini 1.5 Flash，速度快且免费额度高
# 1. 切换到 v1 正式版接口
API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

def ai_process(content):
    if not API_KEY: return "错误: 未配置 AI_API_KEY"
    
    # 稍微优化一下 Prompt，让 Gemini 输出更适合 Obsidian 的格式
    prompt = (
        "你是一个专业的情报分析师。请分析以下热搜数据，剔除无意义的娱乐八卦，"
        "保留技术、社会动态和行业新闻。请用 Markdown 列表输出，包含分类、简要概括和原始链接。\n"
        f"数据内容：\n{content}"
    )
    
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=60)
        res_json = response.json()
        
        # 调试报错信息
        if "error" in res_json:
            error_msg = res_json['error'].get('message', '未知错误')
            # 如果 v1 还是不行，尝试 v1beta1
            return f"Gemini API 报错 ({res_json['error'].get('code')}): {error_msg}"
            
        # 提取路径
        try:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            return f"解析失败，API 返回结果异常: {res_json}"
            
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
