import os
import argparse
import logging
import yaml
from datetime import datetime

from src.scrapers.scraper_factory import ScraperFactory
from src.models.model_factory import ModelFactory
from src.publishers.wordpress_publisher import WordPressPublisher
from src.utils.file_handler import FileHandler
from src.utils.seo_analyzer import SEOAnalyzer

def setup_logging():
    """设置日志"""
    log_dir = os.path.join('d:', 'Python', 'myblog', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f"blog_processor_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def load_config(config_path=None):
    """加载配置文件"""
    if config_path is None:
        config_path = os.path.join('d:', 'Python', 'myblog', 'config', 'config.yaml')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"加载配置文件失败: {e}")
        return {}

def process_blog(url, model_name, publish=False, config_path=None):
    """处理博客内容"""
    logger = setup_logging()
    config = load_config(config_path)
    
    logger.info(f"开始处理博客: {url}")
    
    # 1. 爬取博客内容
    logger.info("步骤1: 爬取博客内容")
    scraper = ScraperFactory.get_scraper(url, config_path)
    blog_data = scraper.scrape(url)
    
    if not blog_data:
        logger.error("爬取博客内容失败")
        return False
    
    # 保存原始内容
    file_handler = FileHandler()
    original_content_path = file_handler.save_content(
        blog_data['content'],
        f"original_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        "original"
    )
    
    # 保存元数据
    metadata_path = file_handler.save_json(
        blog_data['metadata'],
        f"metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        "metadata"
    )
    
    logger.info(f"原始内容已保存到: {original_content_path}")
    logger.info(f"元数据已保存到: {metadata_path}")
    
    # 2. 使用大模型改写内容
    logger.info(f"步骤2: 使用{model_name}模型改写内容")
    model = ModelFactory.get_model(model_name, config_path)
    
    rewritten_content = model.rewrite_content(blog_data['content'], blog_data['metadata'])
    
    if not rewritten_content:
        logger.error("内容改写失败")
        return False
    
    # 生成SEO友好的标题和描述
    seo_title = model.generate_seo_title(blog_data['content'], blog_data['metadata'])
    seo_description = model.generate_seo_description(blog_data['content'], blog_data['metadata'])
    
    # 保存改写后的内容
    rewritten_content_path = file_handler.save_content(
        rewritten_content,
        f"rewritten_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        "rewritten"
    )
    
    logger.info(f"改写后的内容已保存到: {rewritten_content_path}")
    
    # 3. SEO分析
    logger.info("步骤3: 进行SEO分析")
    seo_analyzer = SEOAnalyzer(config.get('seo', {}))
    
    keywords = blog_data['metadata'].get('keywords', '')
    content_analysis = seo_analyzer.analyze_content(rewritten_content, keywords)
    title_analysis = seo_analyzer.analyze_title(seo_title)
    description_analysis = seo_analyzer.analyze_meta_description(seo_description)
    
    seo_suggestions = seo_analyzer.get_seo_suggestions(
        content_analysis,
        title_analysis,
        description_analysis
    )
    
    # 保存SEO分析结果
    seo_analysis = {
        'content_analysis': content_analysis,
        'title_analysis': title_analysis,
        'description_analysis': description_analysis,
        'suggestions': seo_suggestions
    }
    
    seo_analysis_path = file_handler.save_json(
        seo_analysis,
        f"seo_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        "seo"
    )
    
    logger.info(f"SEO分析结果已保存到: {seo_analysis_path}")
    
    # 4. 发布到WordPress（如果需要）
    if publish:
        logger.info("步骤4: 发布到WordPress")
        publisher = WordPressPublisher(config_path)
        
        result = publisher.publish_post(
            title=seo_title,
            content=rewritten_content,
            excerpt=seo_description
        )
        
        if result:
            logger.info(f"文章已发布: {result.get('link', '')}")
        else:
            logger.error("文章发布失败")
            return False
    
    logger.info("博客处理完成")
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='博客内容采集与改写发布系统')
    parser.add_argument('url', help='要采集的博客URL')
    parser.add_argument('--model', '-m', default='openai', 
                       choices=['openai', 'azure_openai', 'anthropic', 'baidu', 'ollama'], 
                       help='使用的大模型')
    parser.add_argument('--publish', '-p', action='store_true', help='是否发布到WordPress')
    parser.add_argument('--config', '-c', help='配置文件路径')
    
    args = parser.parse_args()
    
    process_blog(args.url, args.model, args.publish, args.config)

if __name__ == "__main__":
    main()