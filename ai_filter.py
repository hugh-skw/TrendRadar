import os
import requests
import json
from datetime import datetime

# 配置
API_KEY = os.getenv("AI_API_KEY")
API_URL = "https://api.openai.com/v1/chat/completions" # 如果用其它平台请修改

def ai_process(content):
    prompt = f"""
    你是一个专业的情报筛选专家。请分析以下新闻内容：
    1. 剔除广告、标题党、重复性极高的低质量简讯。
    2. 对高质量内容进行分类（如：技术、工具、行业动态）。
    3. 为每条保留的内容写一个50字以内的深度摘要，并保留原始链接。
    
    待处理内容：
    {content}
    
    请直接输出 Markdown 格式的结果。
    """
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    response = requests.post(API_URL, headers=headers, json=data)
    return response.json()['choices'][0]['message']['content']

if __name__ == "__main__":
    # TrendRadar 抓取后的结果通常保存在特定目录，假设为 data/
    # 这里读取最新的结果文件，建议根据 TrendRadar 实际输出路径调整
    try:
        with open("result.txt", "r", encoding="utf-8") as f:
            raw_data = f.read()
        
        refined_md = ai_process(raw_data)
        
        with open("AI_Ready_Notes.md", "w", encoding="utf-8") as f:
            f.write(f"# 🤖 AI 智能简报 ({datetime.now().strftime('%Y-%m-%d')})\n\n")
            f.write(refined_md)
    except Exception as e:
        print(f"处理失败: {e}")
