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
    """步骤3: SEO分析和内容优化
    
    对改写后的内容进行SEO分析和优化，通过迭代方式不断提升内容的SEO表现
    
    实现思路：
    1. 使用SEOAnalyzer对内容、标题和描述进行分析
    2. 计算当前内容的SEO评分，与阈值比较决定是否需要优化
    3. 如果需要优化，使用AI模型根据SEO建议进行内容调整
    4. 迭代优化过程，直到达到SEO评分阈值或达到最大迭代次数
    
    Args:
        content (str): 文章内容
        title (str): 文章标题
        description (str): 文章元描述
        metadata (dict): 文章元数据，包含关键词等信息
        model_name (str): 使用的AI模型名称
        config (dict): 配置信息
        config_path (str): 配置文件路径
        logger (Logger): 日志记录器
        iteration (int, optional): 当前迭代次数，默认为0
        max_iterations (int, optional): 最大迭代次数，默认为3
        
    Returns:
        dict: 包含优化后的内容、标题、描述和SEO评分的字典
    
    优化决策逻辑：
    - 如果SEO评分达到阈值（默认80分），则认为内容已满足SEO要求，直接返回
    - 如果达到最大迭代次数，即使未达到阈值也返回当前结果
    - 否则，根据SEO建议进行内容优化，然后递归调用进行下一轮优化
    
    SEO评分计算基于以下因素：
    - 内容字数是否达标
    - 关键词密度是否在合理范围内
    - 内部链接数量是否充足
    - 图片使用是否充分
    - 标题标签(H2/H3)使用是否合理
    - 标题长度是否合适
    - 元描述长度是否合适
    """
    
    # 分析内容、标题和描述
    seo_analyzer = SEOAnalyzer(config)
    content_analysis = seo_analyzer.analyze_content(content, metadata.get('keywords', ''))
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
    
    # 检查是否满足SEO要求 - 计算SEO评分并与阈值比较
    # SEO评分是对内容质量的综合评估，考虑多个因素并赋予不同权重
    seo_score = calculate_seo_score(content_analysis, title_analysis, description_analysis)
    seo_threshold = config.get('seo', {}).get('threshold', 80)  # 默认阈值为80分
    
    logger.info(f"SEO评分: {seo_score}, 阈值: {seo_threshold}")
    
    # 如果SEO评分达到或超过阈值，认为内容已满足SEO要求，无需进一步优化
    if seo_score >= seo_threshold:
        logger.info("内容已满足SEO要求")
        return {
            'content': content,
            'title': title,
            'description': description,
            'seo_score': seo_score,
            'seo_analysis': seo_analysis
        }
    
    # 迭代终止条件：如果达到最大迭代次数，即使SEO评分未达标也返回当前最佳结果
    # 这是为了避免无限循环优化，同时确保在有限资源下获得相对最优的结果
    if iteration >= max_iterations - 1:
        logger.warning(f"已达到最大迭代次数 ({max_iterations})，返回当前结果")
        return {
            'content': content,
            'title': title,
            'description': description,
            'seo_score': seo_score,
            'seo_analysis': seo_analysis
        }
    
    # 内容优化逻辑：使用SEO建议指导AI模型进行内容优化
    # 优化过程包括：调整关键词密度、增加内部链接、添加图片、优化标题结构等
    logger.info("内容未满足SEO要求，进行优化...")
    model = ModelFactory.get_model(model_name, config_path)  # 获取AI模型实例
    
    # 构建优化提示词 - 将SEO分析结果转化为AI模型可理解的优化指令
    # 提示词包含具体的SEO问题和优化方向，引导AI模型进行有针对性的内容调整
    optimization_prompt = generate_optimization_prompt(content, title, description, seo_suggestions)
    
    # 安全地记录日志，避免对非字符串类型进行切片操作
    # 这里考虑了提示词可能是字典或字符串的情况，确保日志记录不会出错
    if isinstance(optimization_prompt, dict):
        logger.info(f"生成的优化提示词: {str(optimization_prompt)[:100]}...")
    else:
        logger.info(f"生成的优化提示词: {str(optimization_prompt)[:100] if optimization_prompt else '无'}...")
    
    # 优化内容 - 分别优化文章内容、标题和元描述
    # 从优化提示词字典中提取内容提示词，用于指导AI模型进行内容优化
    content_prompt = optimization_prompt.get('content_prompt', '')
    
    # 如果没有内容提示词，则构建一个简单的提示词
    # 这是一个后备机制，确保即使提示词生成失败也能进行基本的优化
    if not content_prompt:
        content_suggestions = seo_suggestions.get('content', [])
        content_prompt = f"请根据以下SEO建议优化内容：\n\n"
        if content_suggestions:
            content_prompt += f"内容优化建议：\n{', '.join(content_suggestions)}\n\n"
        content_prompt += f"原始内容：\n{content}"
    
    # 调用AI模型进行内容优化
    # 分别优化三个部分：文章内容、标题和元描述
    optimized_content = model.optimize_content(content, content_prompt)  # 优化文章内容
    optimized_title = model.optimize_title(title, seo_suggestions.get('title', []))  # 优化标题
    optimized_description = model.optimize_description(description, seo_suggestions.get('description', []))  # 优化元描述
    
    # 保存优化后的内容
    optimized_content_path = file_handler.save_content(
        optimized_content,
        f"optimized_iter{iteration+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        "optimized"
    )
    
    logger.info(f"优化后的内容已保存到: {optimized_content_path}")
    
    # 递归调用，进行下一轮优化 - 实现迭代优化的核心机制
    # 将优化后的内容作为输入，进入下一轮SEO分析和优化
    # 迭代过程会不断提升内容的SEO表现，直到达到评分阈值或最大迭代次数
    #
    # 迭代优化的优势：
    # 1. 每轮优化都基于前一轮的结果，可以逐步解决复杂的SEO问题
    # 2. 通过多轮优化，可以平衡不同SEO因素之间的关系
    # 3. 避免一次性做过多修改导致内容质量下降
    return step3_seo_optimization(
        optimized_content,  # 优化后的内容
        optimized_title,   # 优化后的标题
        optimized_description,  # 优化后的元描述
        metadata,  # 原始元数据保持不变
        model_name,  # 使用相同的AI模型
        config,  # 配置信息
        config_path,  # 配置文件路径
        logger,  # 日志记录器
        iteration + 1,  # 迭代次数加1
        max_iterations  # 最大迭代次数
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
    
    # 构建内容优化提示词
    content_prompt = f"请根据以下SEO建议优化内容：\n\n"
    if content_suggestions:
        content_prompt += f"内容优化建议：\n{', '.join(content_suggestions)}\n\n"
    
    content_prompt += f"标题优化建议：\n{title_prompt}\n\n"
    content_prompt += f"描述优化建议：\n{description_prompt}\n\n"
    content_prompt += f"原始内容：\n{content}"
    
    # 返回字典，包含各种提示词
    return {
        'title_prompt': title_prompt,
        'description_prompt': description_prompt,
        'content_prompt': content_prompt
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