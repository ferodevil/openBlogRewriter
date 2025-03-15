import sys
import os
import csv
import time

# 添加项目根目录到Python路径
sys.path.append(os.path.join('d:', 'Python', 'myblog'))

from main import process_blog

def batch_process(csv_file, model_name="openai", publish=False, delay=5):
    """批量处理多个博客URL"""
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # 跳过标题行
        
        for row in reader:
            url = row[0]
            print(f"处理: {url}")
            
            process_blog(url, model_name, publish)
            
            # 添加延迟，避免请求过于频繁
            print(f"等待 {delay} 秒...")
            time.sleep(delay)

if __name__ == "__main__":
    # 示例：批量处理博客
    csv_file = os.path.join('d:', 'Python', 'myblog', 'examples', 'urls.csv')
    batch_process(csv_file, "openai", False, 10)