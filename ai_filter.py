import os
import requests
import pandas as pd
from datetime import datetime

# 配置 OpenAI 参数
API_KEY = os.getenv("AI_API_KEY")
# 如果你使用官方接口，地址如下；如果使用代理转发，请替换为代理地址
API_URL = "https://api.openai.com/v1/chat/completions" 

def ai_process(content):
    # 针对 ChatGPT 优化的 Prompt
    prompt = f"""
    你是一个专业的高级情报分析师。请对以下抓取到的原始数据进行清洗和提炼。
    
    任务要求：
    1. 质量过滤：剔除所有标题党、毫无意义的简讯、推销广告。
    2. 智能分类：将内容分为 [技术趋势]、[数码硬件]、[行业大事件] 等逻辑清晰的板块。
    3. 深度摘要：为每条保留的内容撰写 1-2 句核心价值说明，并保留原始链接。
    
    原始数据：
    {content}
    
    请直接以 Markdown 格式输出。
    """
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 使用 gpt-3.5-turbo 或 gpt-4o (推荐使用 gpt-4o-mini，性价比最高且筛选能力强)
    data = {
        "model": "gpt-4o-mini", 
        "messages": [
            {"role": "system", "content": "你是一个严谨、高效的 Markdown 简报助手。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status() # 检查请求是否成功
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"ChatGPT 处理出错: {str(e)}"

if __name__ == "__main__":
    csv_path = "data/data.csv"
    if os.path.exists(csv_path):
        # 读取最新的 25 条数据
        try:
            df = pd.read_csv(csv_path)
            latest_data = df.tail(25).to_string()
            
            refined_md = ai_process(latest_data)
            
            # 生成符合 Obsidian 语法的 Markdown
            with open("AI_Ready_Notes.md", "w", encoding="utf-8") as f:
                f.write(f"---\ntags: #Intelligence/TrendRadar\nstatus: #未读\ncreated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n---\n")
                f.write(f"# 🤖 ChatGPT 精选简报 | {datetime.now().strftime('%Y-%m-%d')}\n\n")
                f.write(refined_md)
                f.write("\n\n---\n*本简报由 ChatGPT 自动筛选生成，仅保留具高价值内容。*")
        except Exception as e:
            print(f"数据读取或写入失败: {e}")
    else:
        print("未找到 data/data.csv 文件，请确认爬虫是否成功运行。")
