import os
import requests
import sqlite3
import pandas as pd
from datetime import datetime

# --- 配置区 ---
API_KEY = os.getenv("FILTER_AI_API_KEY")
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

def is_valid_url(url):
    """【过滤逻辑】踢掉各平台的热榜主页/广告链接，只留详情页"""
    url_str = str(url).lower()
    junk_keywords = [
        'billboard', 'hot-search', 'trending', 'top/list', 
        'hub', 'search?q=', 'topic/index', 'category', 'index.html'
    ]
    # 过滤掉过短的链接或包含上述关键词的链接
    if len(url_str) < 25 or any(k in url_str for k in junk_keywords):
        return False
    return True

def ai_process(content):
    if not API_KEY: return "错误: 未配置 FILTER_AI_API_KEY"
    
    prompt = (
        "你是一个专业的情报分析师。请分析以下热搜数据：\n"
        "1. 严格剔除标题重复或链接无效的内容。\n"
        "2. 保留具体的社会动态、科技进展和行业深度分析。\n"
        "3. 按领域分类，用 Markdown 列表输出，包含简要概括和原始链接。\n"
        f"数据内容：\n{content}"
    )
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-ai/DeepSeek-V3", 
        "messages": [
            {"role": "system", "content": "你是一个冷酷、严谨的简报助手，只保留具备详情页链接的高价值信息。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"AI 处理异常: {str(e)}"

if __name__ == "__main__":
    # 获取北京时间对应的文件名
    today = datetime.now().strftime('%Y-%m-%d')
    db_path = f"output/news/{today}.db"
    
    print(f"--- 尝试读取数据库: {db_path} ---")
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 【自动探测表名逻辑】解决 no such table: news 问题
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            all_tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence']
            
            if not all_tables:
                refined_md = "数据库已创建但内部没有数据表。"
            else:
                # 寻找名为 news 的表，如果没有，取第一个
                target_table = 'news' if 'news' in all_tables else all_tables[0]
                print(f"📡 探测到表名: {all_tables}，正在读取: [{target_table}]")
                
                # 读取数据
                query = f"SELECT * FROM {target_table} ORDER BY rowid DESC LIMIT 150"
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                if df.empty:
                    refined_md = "数据表内内容为空。"
                else:
                    # 1. 尝试动态寻找 url 所在的列
                    url_col = [c for c in df.columns if 'url' in c.lower() or 'link' in c.lower()]
                    
                    # 2. 预过滤：在交给 AI 前先删掉主页链接
                    if url_col:
                        df = df[df[url_col[0]].apply(is_valid_url)]
                    
                    if df.empty:
                        refined_md = "⚠️ 筛选后的有效新闻条数为 0（全是主页链接），已跳过今日简报。"
                    else:
                        # 3. 截取前 40 条交给 AI 提炼
                        content_str = df.head(40).to_string(index=False)
                        refined_md = ai_process(content_str)
            
            with open("AI_Ready_Notes.md", "w", encoding="utf-8") as f:
                f.write(f"---\ntags: #TrendRadar\n---\n\n{refined_md}")
            print("✅ 处理流程已顺利完成")
            
        except Exception as e:
            print(f"脚本运行出错: {e}")
            with open("AI_Ready_Notes.md", "w") as f: f.write(f"处理失败: {e}")
    else:
        # 时差/文件缺失处理
        print("❌ 未发现今日数据库文件")
        with open("AI_Ready_Notes.md", "w") as f: f.write("未发现今日数据源，请检查爬虫状态或时区设置。")
