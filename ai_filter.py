import os
import requests
import json
from datetime import datetime

# 配置
API_KEY = os.getenv("AI_API_KEY")
API_URL = "https://api.openai.com/v1/chat/completions" # 如果用其它平台请修改

def ai_process(content):
    prompt = f"""
    你是一个专业的情报官。请从以下新闻中筛选出高质量、有深度的技术或行业动态。
    要求：
    1. 剔除所有标题党、推销广告和纯粹的八卦。
    2. 对于保留的内容，请按类别分组（如：AI动态、开发工具、数码硬件）。
    3. 每条内容提供一个简短的深度总结，并附带原链接。
    
    待分析数据：
    {content}
    
    请直接输出 Markdown 格式。
    """
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"AI 处理出错: {str(e)}"

if __name__ == "__main__":
    csv_path = "data/data.csv"
    if os.path.exists(csv_path):
        # 读取最新的 20 条数据进行分析，避免 Token 超限
        df = pd.read_csv(csv_path)
        latest_data = df.tail(20).to_string()
        
        refined_md = ai_process(latest_data)
        
        # 生成 Obsidian 格式文件
        with open("AI_Ready_Notes.md", "w", encoding="utf-8") as f:
            f.write(f"--- \ncategory: Intelligence\nstatus: #未读\n---\n")
            f.write(f"# 🤖 TrendRadar AI 简报 ({datetime.now().strftime('%Y-%m-%d')})\n\n")
            f.write(refined_md)
    else:
        print("未找到数据文件 data/data.csv")
