import os
import argparse
import yaml
from datetime import datetime

from src.scrapers.scraper_factory import ScraperFactory
from src.models.model_factory import ModelFactory
from src.publishers.wordpress_publisher import WordPressPublisher
from src.utils.file_handler import FileHandler
from src.utils.seo_analyzer import SEOAnalyzer
from src.utils.content_evaluator import ContentEvaluator
from src.utils.path_utils import get_config_path
from src.utils.logger import get_logger

def load_config(config_path=None):
    """加载配置文件"""
    if config_path is None:
        config_path = get_config_path()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"加载配置文件失败: {e}")
        return {}

def process_blog(url, publish=False, config_path=None, max_iterations=3):
    """处理博客内容"""
    logger = get_logger(__name__)
    config = load_config(config_path)
    model_name = config.get('models', {}).get('active_model', 'openai')
    
    logger.info(f"开始处理博客: {url}")
    logger.info(f"使用模型: {model_name}")
    
    # 步骤1: 爬取博客内容
    blog_data = step1_scrape_content(url, config_path, logger)
    if not blog_data:
        return False
    
    # 步骤2: 使用大模型改写内容
    rewrite_result = step2_rewrite_content(blog_data, model_name, config_path, logger)
    if not rewrite_result:
        return False
    
    # 步骤3: SEO分析和内容优化
    seo_result = step3_seo_optimization(
        rewrite_result['content'], 
        rewrite_result['title'], 
        rewrite_result['description'], 
        blog_data['metadata'], 
        model_name, 
        config, 
        config_path, 
        logger,
        max_iterations=max_iterations
    )
    if not seo_result:
        return False
    
    # 步骤4: 发布到WordPress（如果需要）
    if publish:
        publish_result = step4_publish_content(
            seo_result['title'],
            seo_result['content'],
            seo_result['description'],
            config_path,
            logger
        )
        if not publish_result:
            return False
    
    logger.info("博客处理完成")
    return True

def step1_scrape_content(url, config_path, logger):
    """步骤1: 爬取博客内容"""
    logger.info("步骤1: 爬取博客内容")
    scraper = ScraperFactory.get_scraper(url, config_path)
    blog_data = scraper.scrape(url)
    
    if not blog_data:
        logger.error("爬取博客内容失败")
        return None
    
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
    
    return blog_data

def step2_rewrite_content(blog_data, model_name, config_path, logger, max_rewrite_attempts=3):
    """步骤2: 使用大模型改写内容，包含质量评估和自动重写"""
    logger.info(f"步骤2: 使用{model_name}模型改写内容")
    model = ModelFactory.get_model(model_name, config_path)
    content_evaluator = ContentEvaluator(config_path)
    
    original_content = blog_data['content']
    rewritten_content = None
    seo_title = None
    seo_description = None
    quality_result = {'suggestions': []}
    
    for attempt in range(max_rewrite_attempts):
        # 构建提示词
        prompt = generate_rewrite_prompt(original_content, blog_data['metadata'])
        if attempt > 0:
            logger.info(f"第{attempt+1}次尝试改写内容")
            # 如果是重写，添加上一次的质量评估建议
            prompt += "\n\n上一次改写的问题：\n" + "\n".join(quality_result.get('suggestions', []))
        
        logger.info(f"生成的改写提示词: {prompt[:100]}...")
        
        # 改写内容
        rewritten_content = model.rewrite_content(original_content, blog_data['metadata'], prompt)
        
        if not rewritten_content:
            logger.error("内容改写失败")
            continue
        
        # 评估内容质量
        quality_result = content_evaluator.evaluate_content(rewritten_content, original_content)
        
        # 保存改写后的内容和质量评估结果
        file_handler = FileHandler()
        rewritten_content_path = file_handler.save_content(
            rewritten_content,
            f"rewritten_attempt{attempt+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "rewritten"
        )
        
        quality_result_path = file_handler.save_json(
            quality_result,
            f"quality_result_attempt{attempt+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "quality"
        )
        
        logger.info(f"改写后的内容已保存到: {rewritten_content_path}")
        logger.info(f"质量评估结果已保存到: {quality_result_path}")
        logger.info(f"内容质量评分: {quality_result.get('quality_score', 0)}")
        
        # 检查内容质量是否达标
        if not quality_result.get('needs_rewrite', False):
            logger.info("内容质量评估通过，无需重写")
            # 内容质量达标，立即生成SEO标题和描述
            seo_title = model.generate_seo_title(rewritten_content, blog_data['metadata'])
            seo_description = model.generate_seo_description(rewritten_content, blog_data['metadata'])
            
            return {
                'content': rewritten_content,
                'title': seo_title,
                'description': seo_description,
                'quality_result': quality_result
            }
        
        if attempt < max_rewrite_attempts - 1:
            logger.warning("内容质量评估未通过，将进行重写")
            logger.info(f"质量问题: {', '.join(quality_result.get('suggestions', []))}")
        else:
            logger.warning(f"已达到最大重写次数 ({max_rewrite_attempts})，使用当前最佳结果")
    
    # 如果所有尝试都未通过质量评估或达到最大重写次数，使用最后一次结果
    seo_title = model.generate_seo_title(rewritten_content, blog_data['metadata'])
    seo_description = model.generate_seo_description(rewritten_content, blog_data['metadata'])
    
    return {
        'content': rewritten_content,
        'title': seo_title,
        'description': seo_description,
        'quality_result': quality_result
    }

def step3_seo_optimization(content, title, description, metadata, model_name, config, config_path, logger, iteration=0, max_iterations=3):
    """步骤3: SEO分析和内容优化"""
    logger.info(f"步骤3: 进行SEO分析 (迭代 {iteration+1}/{max_iterations})")
    seo_analyzer = SEOAnalyzer(config.get('seo', {}))
    
    # 获取关键词
    keywords = metadata.get('keywords', '')
    
    # 分析内容
    content_analysis = seo_analyzer.analyze_content(content, keywords)
    title_analysis = seo_analyzer.analyze_title(title)
    description_analysis = seo_analyzer.analyze_meta_description(description)
    
    # 获取SEO建议
    seo_suggestions = seo_analyzer.get_seo_suggestions(
        content_analysis,
        title_analysis,
        description_analysis
    )
    
    # 保存SEO分析结果
    file_handler = FileHandler()
    seo_analysis = {
        'content_analysis': content_analysis,
        'title_analysis': title_analysis,
        'description_analysis': description_analysis,
        'suggestions': seo_suggestions,
        'iteration': iteration + 1
    }
    
    seo_analysis_path = file_handler.save_json(
        seo_analysis,
        f"seo_analysis_iter{iteration+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        "seo"
    )
    
    logger.info(f"SEO分析结果已保存到: {seo_analysis_path}")
    
    # 检查是否满足SEO要求
    seo_score = calculate_seo_score(content_analysis, title_analysis, description_analysis)
    seo_threshold = config.get('seo', {}).get('threshold', 80)
    
    logger.info(f"SEO评分: {seo_score}, 阈值: {seo_threshold}")
    
    if seo_score >= seo_threshold:
        logger.info("内容已满足SEO要求")
        return {
            'content': content,
            'title': title,
            'description': description,
            'seo_score': seo_score,
            'seo_analysis': seo_analysis
        }
    
    # 如果达到最大迭代次数，返回当前最佳结果
    if iteration >= max_iterations - 1:
        logger.warning(f"已达到最大迭代次数 ({max_iterations})，返回当前结果")
        return {
            'content': content,
            'title': title,
            'description': description,
            'seo_score': seo_score,
            'seo_analysis': seo_analysis
        }
    
    # 否则，使用SEO建议进行内容优化
    logger.info("内容未满足SEO要求，进行优化...")
    model = ModelFactory.get_model(model_name, config_path)
    
    # 构建优化提示词
    optimization_prompt = generate_optimization_prompt(content, title, description, seo_suggestions)
    logger.info(f"生成的优化提示词: {optimization_prompt[:100]}...")
    
    # 优化内容
    optimized_content = model.optimize_content(content, optimization_prompt)
    optimized_title = model.optimize_title(title, seo_suggestions.get('title', []))
    optimized_description = model.optimize_description(description, seo_suggestions.get('description', []))
    
    # 保存优化后的内容
    optimized_content_path = file_handler.save_content(
        optimized_content,
        f"optimized_iter{iteration+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        "optimized"
    )
    
    logger.info(f"优化后的内容已保存到: {optimized_content_path}")
    
    # 递归调用，进行下一轮优化
    return step3_seo_optimization(
        optimized_content, 
        optimized_title, 
        optimized_description, 
        metadata, 
        model_name, 
        config, 
        config_path, 
        logger, 
        iteration + 1, 
        max_iterations
    )

def step4_publish_content(title, content, description, config_path, logger):
    """步骤4: 发布到WordPress"""
    logger.info("步骤4: 发布到WordPress")
    publisher = WordPressPublisher(config_path)
    
    result = publisher.publish_post(
        title=title,
        content=content,
        excerpt=description
    )
    
    if result:
        logger.info(f"文章已发布: {result.get('link', '')}")
        return result
    else:
        logger.error("文章发布失败")
        return None

def generate_rewrite_prompt(content, metadata):
    """生成改写提示词"""
    title = metadata.get('title', '')
    description = metadata.get('description', '')
    keywords = metadata.get('keywords', '')
    
    # 从配置文件中读取提示词模板
    config = load_config()
    prompts = yaml.safe_load(open(get_config_path('prompts.yaml'), 'r', encoding='utf-8'))
    rewrite_prompt = prompts['base_prompts']['rewrite_user']
    
    # 替换模板中的变量
    prompt = rewrite_prompt.format(
        title=title,
        content=content,
        keywords=keywords
    )
    
    return prompt

def generate_optimization_prompt(content, title, description, seo_suggestions):
    """生成优化提示词"""
    content_suggestions = seo_suggestions.get('content', [])
    title_suggestions = seo_suggestions.get('title', [])
    description_suggestions = seo_suggestions.get('description', [])
    
    # 从配置文件中读取提示词模板
    prompts = yaml.safe_load(open(get_config_path('prompts.yaml'), 'r', encoding='utf-8'))
    
    # 根据不同的优化类型使用不同的模板
    title_prompt = prompts['base_prompts']['optimize_title'].format(
        title=title,
        suggestions='\n'.join(title_suggestions) if title_suggestions else 'None'
    )
    
    description_prompt = prompts['base_prompts']['optimize_description'].format(
        description=description,
        suggestions='\n'.join(description_suggestions) if description_suggestions else 'None'
    )
    
    return {
        'title_prompt': title_prompt,
        'description_prompt': description_prompt
    }

def calculate_seo_score(content_analysis, title_analysis, description_analysis):
    """计算SEO评分"""
    # 内容评分 (60%)
    content_score = content_analysis.get('score', 0) * 0.6
    
    # 标题评分 (25%)
    title_score = title_analysis.get('score', 0) * 0.25
    
    # 描述评分 (15%)
    description_score = description_analysis.get('score', 0) * 0.15
    
    # 总评分
    total_score = content_score + title_score + description_score
    
    return round(total_score, 2)

def main():
    """主函数"""
    # 加载配置文件
    config_path = get_config_path()
    config = load_config(config_path)
    cli_config = config.get('cli', {})
    
    # 从配置文件获取URL和其他参数
    blog_url = cli_config.get('blog_url', '')
    if not blog_url:
        print("错误: 配置文件中未设置blog_url参数")
        return
    
    # 使用配置文件中的参数
    process_blog(
        blog_url,
        cli_config.get('publish', False),
        config_path,
        cli_config.get('max_iterations', 3)
    )

if __name__ == "__main__":
    main()