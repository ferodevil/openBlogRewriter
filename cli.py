import argparse
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.join('d:', 'Python', 'myblog'))

from main import process_blog, load_config
from src.scrapers.scraper_factory import ScraperFactory
from src.models.model_factory import ModelFactory
from src.publishers.wordpress_publisher import WordPressPublisher
from src.utils.file_handler import FileHandler
from src.utils.path_utils import get_config_path
from src.utils.logger import get_logger

def scrape_command(args):
    """爬取命令"""
    logger = get_logger(__name__, args.verbose, "cli")
    logger.info(f"爬取URL: {args.url}")
    
    scraper = ScraperFactory.get_scraper(args.url, args.config)
    blog_data = scraper.scrape(args.url)
    
    if not blog_data:
        logger.error("爬取失败")
        return 1
    
    # 保存内容
    file_handler = FileHandler()
    content_path = file_handler.save_content(
        blog_data['content'],
        args.output,
        "scraped"
    )
    
    # 保存元数据
    metadata_filename = f"{os.path.splitext(args.output)[0]}_metadata.json" if args.output else None
    metadata_path = file_handler.save_json(
        blog_data['metadata'],
        metadata_filename,
        "scraped"
    )
    
    logger.info(f"内容已保存到: {content_path}")
    logger.info(f"元数据已保存到: {metadata_path}")
    
    return 0

def rewrite_command(args):
    """改写命令"""
    logger = get_logger(__name__, args.verbose, "cli")
    logger.info(f"使用{args.model}模型改写内容")
    
    # 加载内容
    file_handler = FileHandler()
    content = file_handler.load_content(args.input)
    
    if not content:
        logger.error(f"无法加载内容: {args.input}")
        return 1
    
    # 加载元数据（如果有）
    metadata = None
    metadata_path = f"{os.path.splitext(args.input)[0]}_metadata.json"
    if os.path.exists(metadata_path):
        metadata = file_handler.load_json(metadata_path)
    
    # 改写内容
    model = ModelFactory.get_model(args.model, args.config)
    rewritten_content = model.rewrite_content(content, metadata)
    
    if not rewritten_content:
        logger.error("内容改写失败")
        return 1
    
    # 保存改写后的内容
    output_path = file_handler.save_content(
        rewritten_content,
        args.output,
        "rewritten"
    )
    
    logger.info(f"改写后的内容已保存到: {output_path}")
    
    return 0

def publish_command(args):
    """发布命令"""
    logger = get_logger(__name__, args.verbose, "cli")
    logger.info(f"发布内容到WordPress")
    
    # 加载内容
    file_handler = FileHandler()
    content = file_handler.load_content(args.input)
    
    if not content:
        logger.error(f"无法加载内容: {args.input}")
        return 1
    
    # 发布内容
    publisher = WordPressPublisher(args.config)
    
    result = publisher.publish_post(
        title=args.title,
        content=content,
        excerpt=args.excerpt
    )
    
    if result:
        logger.info(f"文章已发布: {result.get('link', '')}")
        return 0
    else:
        logger.error("文章发布失败")
        return 1

def process_command(args):
    """处理命令（爬取+改写+发布）"""
    logger = get_logger(__name__, args.verbose, "cli")
    
    # 如果提供了CSV文件，从文件中读取URL列表
    if args.csv:
        import csv
        urls = []
        try:
            with open(args.csv, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # 跳过标题行
                for row in reader:
                    if row and row[0].strip():
                        urls.append(row[0].strip())
            logger.info(f"从CSV文件加载了 {len(urls)} 个URL")
        except Exception as e:
            logger.error(f"读取CSV文件失败: {e}")
            return 1
    else:
        # 否则使用命令行参数中的URL
        urls = [args.url]
    
    # 处理每个URL
    success_count = 0
    for i, url in enumerate(urls):
        logger.info(f"处理第 {i+1}/{len(urls)} 个URL: {url}")
        
        success = process_blog(url, args.publish, args.config, args.max_iterations)
        
        if success:
            logger.info(f"URL处理成功: {url}")
            success_count += 1
        else:
            logger.error(f"URL处理失败: {url}")
        
        # 如果不是最后一个URL，添加延迟
        if i < len(urls) - 1:
            logger.info(f"等待 {args.delay} 秒后处理下一个URL...")
            import time
            time.sleep(args.delay)
    
    logger.info(f"批量处理完成，成功: {success_count}/{len(urls)}")
    return 0 if success_count == len(urls) else 1

def load_config(config_path=None):
    """加载配置文件"""
    if config_path is None:
        config_path = get_config_path()
    
    return config_path

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='博客内容采集与改写发布系统')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细日志')
    
    # 创建子命令
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 爬取命令
    scrape_parser = subparsers.add_parser('scrape', help='爬取博客内容')
    scrape_parser.add_argument('url', help='博客URL')
    scrape_parser.add_argument('--output', '-o', help='输出文件名')
    
    # 改写命令
    rewrite_parser = subparsers.add_parser('rewrite', help='改写博客内容')
    rewrite_parser.add_argument('input', help='输入文件路径')
    rewrite_parser.add_argument('--model', '-m', default='openai', 
                               choices=['openai', 'azure_openai', 'anthropic', 'baidu', 'ollama'], 
                               help='使用的大模型')
    rewrite_parser.add_argument('--output', '-o', help='输出文件名')
    
    # 处理命令（爬取+改写+发布）
    process_parser = subparsers.add_parser('process', help='完整处理（爬取+改写+发布）')
    process_parser.add_argument('url', help='博客URL')
    process_parser.add_argument('--model', '-m', default='openai', 
                               choices=['openai', 'azure_openai', 'anthropic', 'baidu', 'ollama', 'siliconflow'], 
                               help='使用的大模型')
    process_parser.add_argument('--publish', '-p', action='store_true', help='是否发布到WordPress')
    process_parser.add_argument('--csv', help='包含多个URL的CSV文件路径')
    process_parser.add_argument('--delay', type=int, default=5, help='处理多个URL时的延迟时间（秒）')
    process_parser.add_argument('--max-iterations', type=int, default=3, help='SEO优化最大迭代次数')
    
    args = parser.parse_args()
    
    if args.command == 'scrape':
        return scrape_command(args)
    elif args.command == 'rewrite':
        return rewrite_command(args)
    elif args.command == 'publish':
        return publish_command(args)
    elif args.command == 'process':
        return process_command(args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())