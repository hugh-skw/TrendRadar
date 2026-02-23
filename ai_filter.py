import os
import requests
import pandas as pd
from datetime import datetime

# 调试打印：查看当前环境
print("--- 诊断模式启动 ---")
print(f"当前工作目录: {os.getcwd()}")
if os.path.exists("data"):
    print(f"data 目录下的文件: {os.listdir('data')}")
else:
    print("警告: 根目录下未发现 data 文件夹")

# 配置 OpenAI 参数
API_KEY = os.getenv("AI_API_KEY")
API_URL = "https://api.openai.com/v1/chat/completions" 

def ai_process(content):
    if not API_KEY:
        return "错误: 未配置 AI_API_KEY"
    
    prompt = f"请简要总结以下新闻并按格式输出 Markdown:\n{content}"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o-mini", 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"API 请求异常: {e}")
        return None

if __name__ == "__main__":
    # 自动探测 TrendRadar 可能生成的各种数据路径
    possible_paths = ["data/data.csv", "data.csv", "data/result.csv"]
    target_path = None
    
    for p in possible_paths:
        if os.path.exists(p):
            target_path = p
            print(f"成功找到数据源: {p}")
            break
    
    if target_path:
        try:
            df = pd.read_csv(target_path)
            # 如果内容为空，生成占位符防止报错
            if df.empty:
                refined_md = "今日无新资讯更新。"
            else:
                latest_data = df.tail(20).to_string()
                refined_md = ai_process(latest_data) or "AI 处理未能生成内容。"
            
            with open("AI_Ready_Notes.md", "w", encoding="utf-8") as f:
                f.write(refined_md)
            print("✅ 成功生成 AI_Ready_Notes.md")
            
        except Exception as e:
            print(f"数据解析失败: {e}")
    else:
        print("❌ 未能找到任何数据文件，无法生成简报。")
        # 创建一个空文件防止 Action 报错中止
        with open("AI_Ready_Notes.md", "w") as f:
            f.write("数据源缺失，请检查爬虫状态。")
