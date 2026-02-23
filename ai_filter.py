import os
import requests
import sqlite3
import pandas as pd
from datetime import datetime

# 1. 使用 v1beta 版本的标准 API 节点
API_KEY = os.getenv("AI_API_KEY")
# 注意：模型名称包含在 URL 路径中，且前面必须带 models/
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

def ai_process(content):
    if not API_KEY: return "错误: 未配置 AI_API_KEY"
    
    prompt = (
        "你是一个专业的情报分析师。请分析以下热搜数据，剔除无意义的娱乐八卦，"
        "保留技术、社会动态和行业新闻。请用 Markdown 列表输出，包含分类、简要概括和原始链接。\n"
        f"数据内容：\n{content}"
    )
    
    # 2. 构造符合官方定义的 JSON 结构
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 4096,
            "responseMimeType": "text/plain",
        }
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        res_json = response.json()
        
        # 3. 错误处理增强
        if response.status_code != 200:
            error_info = res_json.get('error', {})
            return f"Gemini API 错误 (状态码 {response.status_code}): {error_info.get('message', '未知错误')}"
            
        # 4. 解析路径（需处理安全过滤可能导致的空结果）
        try:
            candidates = res_json.get('candidates', [])
            if not candidates:
                return "Gemini 未返回候选内容（可能是因为触发了安全审核过滤）。"
            
            return candidates[0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            return f"解析结果字段失败。原始响应: {res_json}"
            
    except Exception as e:
        return f"网络或脚本执行异常: {str(e)}"

# 下面的 __main__ 部分保持不变（即之前的数据库读取逻辑）
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
