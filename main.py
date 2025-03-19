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
from src.utils.image_processor import ImageProcessor

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
    
    # 步骤2: 使用大模型改写内容并进行SEO优化
    rewrite_result = step2_rewrite_and_optimize_content(blog_data, model_name, config, config_path, logger, max_iterations)
    if not rewrite_result:
        return False
    
    # 步骤3: 发布到WordPress（如果需要）
    if publish:
        publish_result = step3_publish_content(
            rewrite_result['title'],
            rewrite_result['content'],
            rewrite_result['description'],
            config_path,
            logger,
            images=rewrite_result.get('images', [])
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
        f"original_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "original",
        file_format='md'
    )
    
    # 保存元数据
    metadata_path = file_handler.save_json(
        blog_data['metadata'],
        f"metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        "metadata"
    )
    
    # 保存图片信息（如果有）
    images_info = blog_data.get('images', [])
    if images_info:
        images_info_path = file_handler.save_json(
            images_info,
            f"images_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "images"
        )
        logger.info(f"图片信息已保存到: {images_info_path}")
        logger.info(f"共爬取到 {len(images_info)} 张图片")
    
    logger.info(f"原始内容已保存到: {original_content_path}")
    logger.info(f"元数据已保存到: {metadata_path}")
    
    return blog_data

def step2_rewrite_and_optimize_content(blog_data, model_name, config, config_path, logger, max_iterations=3, max_rewrite_attempts=3):
    """步骤2: 使用大模型改写内容并进行SEO优化
    
    将内容质量评估和SEO优化深度整合，实现智能内容优化
    """
    logger.info(f"步骤2: 使用{model_name}模型改写内容并进行SEO优化")
    model = ModelFactory.get_model(model_name, config_path)
    content_evaluator = ContentEvaluator(config_path)
    seo_analyzer = SEOAnalyzer(config)
    file_handler = FileHandler()
    
    original_content = blog_data['content']
    metadata = blog_data['metadata']
    rewritten_content = None
    seo_title = None
    seo_description = None
    quality_result = {'suggestions': []}
    seo_analysis = None
    
    # 获取图片信息
    images = blog_data.get('images', [])
    if images:
        logger.info(f"博客包含 {len(images)} 张图片，将在重写后嵌入")
    
    # 第一阶段：内容重写和初步质量评估
    for attempt in range(max_rewrite_attempts):
        # 构建提示词
        prompt = generate_rewrite_prompt(original_content, metadata)
        if attempt > 0:
            logger.info(f"第{attempt+1}次尝试改写内容")
            # 如果是重写，添加上一次的质量评估建议
            prompt += "\n\n上一次改写的问题：\n" + "\n".join(quality_result.get('suggestions', []))
        
        # 如果有图片，在提示词中添加图片信息
        if images and "image" not in prompt.lower():
            prompt += f"\n\nNote: The original content contains {len(images)} images. Please consider these images while rewriting and add image reference tags [IMAGE] at appropriate positions where you want to insert images."
        
        logger.info(f"生成的改写提示词: {prompt[:100]}...")
        
        # 改写内容
        rewritten_content = model.rewrite_content(original_content, metadata, prompt)
        
        if not rewritten_content:
            logger.error("内容改写失败")
            continue
        
        # 评估内容质量
        quality_result = content_evaluator.evaluate_content(rewritten_content, original_content)
        
        # 生成SEO标题和描述
        seo_title = model.generate_seo_title(rewritten_content, metadata)
        seo_description = model.generate_seo_description(rewritten_content, metadata)
        
        # 进行初步SEO分析
        content_analysis = seo_analyzer.analyze_content(rewritten_content, metadata.get('keywords', ''))
        title_analysis = seo_analyzer.analyze_title(seo_title)
        description_analysis = seo_analyzer.analyze_meta_description(seo_description)
        
        seo_suggestions = seo_analyzer.get_seo_suggestions(
            content_analysis,
            title_analysis,
            description_analysis
        )
        
        seo_analysis = {
            'content_analysis': content_analysis,
            'title_analysis': title_analysis,
            'description_analysis': description_analysis,
            'suggestions': seo_suggestions,
            'iteration': 1
        }
        
        # 计算综合评分
        combined_score = calculate_combined_score(quality_result, seo_analysis)
        
        # 保存改写后的内容和评估结果
        rewritten_content_path = file_handler.save_content(
            rewritten_content,
            f"rewritten_attempt{attempt+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "rewritten",
            file_format='md'
        )
        
        evaluation_result = {
            'quality_result': quality_result,
            'seo_analysis': seo_analysis,
            'combined_score': combined_score
        }
        
        evaluation_path = file_handler.save_json(
            evaluation_result,
            f"evaluation_attempt{attempt+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "evaluation"
        )
       
        import pdb
        pdb.set_trace()
        logger.info(f"改写后的内容已保存到: {rewritten_content_path}")
        logger.info(f"评估结果已保存到: {evaluation_path}")
        logger.info(f"内容质量评分: {quality_result.get('quality_score', 0)}")
        logger.info(f"SEO评分: {calculate_seo_score(content_analysis, title_analysis, description_analysis)}")
        logger.info(f"综合评分: {combined_score}")
        
        # 确定优化策略
        strategy = determine_optimization_strategy(quality_result, seo_analysis)
        logger.info(f"优化策略: {strategy}")
        
        # 检查内容质量是否达标
        quality_threshold = config.get('content_quality', {}).get('threshold', 70)
        seo_threshold = config.get('seo', {}).get('threshold', 80)
        combined_threshold = (quality_threshold * 0.6) + (seo_threshold * 0.4)
        
        if combined_score >= combined_threshold:
            logger.info(f"综合评分达标 ({combined_score} >= {combined_threshold})，跳过后续优化")
            # 直接返回结果，不再进行额外优化
            return {
                'content': rewritten_content,
                'title': seo_title,
                'description': seo_description,
                'quality_result': quality_result,
                'seo_analysis': seo_analysis,
                'quality_score': quality_result.get('quality_score', 0),
                'seo_score': calculate_seo_score(content_analysis, title_analysis, description_analysis),
                'combined_score': combined_score,
                'images': images
            }
        
        # 第二阶段：SEO优化，只有在改写未达标时才进行
        logger.info(f"改写后综合评分未达标 ({combined_score} < {combined_threshold})，开始额外优化")
        
        optimized_content = rewritten_content
        
        # 根据优化策略构建提示词
        if strategy == "focus_on_quality":
            optimization_prompt = f"""
            Please optimize the following content, focusing primarily on content quality issues. Important notes:
            1. Directly optimize the article content itself
            2. Do not add any additional meta information or evaluation information
            3. Maintain the original structure and format of the article
            4. Do not add any introductory or concluding paragraphs about the optimization process
            5. Maintain all [IMAGE] tags in their original positions or place them at appropriate locations
            
            Quality issues to improve:
            {', '.join(quality_result.get('suggestions', []))}
            
            Secondary SEO considerations:
            {', '.join(seo_analysis['suggestions'].get('content', [])[:3])}
            
            Original content:
            {rewritten_content}
            """
        elif strategy == "focus_on_seo":
            optimization_prompt = f"""
            Please optimize the following content, focusing primarily on SEO issues. Important notes:
            1. Directly optimize the article content itself
            2. Do not add any additional meta information or evaluation information
            3. Maintain the original structure and format of the article
            4. Do not add any introductory or concluding paragraphs about the optimization process
            5. Maintain all [IMAGE] tags in their original positions or place them at appropriate locations
            
            SEO optimization suggestions:
            {', '.join(seo_analysis['suggestions'].get('content', []))}
            
            Secondary quality considerations:
            {', '.join(quality_result.get('suggestions', [])[:3])}
            
            Original content:
            {rewritten_content}
            """
        else:
            merged_suggestions = merge_suggestions(quality_result.get('suggestions', []), seo_analysis['suggestions'])
            
            optimization_prompt = f"""
            Please comprehensively optimize the following content, considering both content quality and SEO performance. Important notes:
            1. Directly optimize the article content itself
            2. Do not add any additional meta information or evaluation information
            3. Maintain the original structure and format of the article
            4. Do not add any introductory or concluding paragraphs about the optimization process
            5. Maintain all [IMAGE] tags in their original positions or place them at appropriate locations
            
            Optimization suggestions:
            {', '.join(merged_suggestions)}
            
            Original content:
            {rewritten_content}
            """
        
        # 执行优化
        logger.info(f"开始额外优化...")
        optimized_content = model.optimize_content(rewritten_content, optimization_prompt)
        
        if not optimized_content:
            logger.error("内容优化失败，使用改写后的内容")
            optimized_content = rewritten_content
        
        # 验证优化后的内容
        # 检查是否包含额外的信息标记
        if optimized_content.startswith("Here's the optimized") or "I've optimized" in optimized_content[:100]:
            logger.warning("检测到优化后内容包含额外信息，尝试清理...")
            optimized_content = clean_model_output(optimized_content)
        
        # 检查图片标记是否已插入
        if images and "[IMAGE]" not in optimized_content:
            logger.warning("优化后的内容中没有找到[IMAGE]标记，尝试重新插入...")
            # 使用image_processor重新分配图片位置
            image_processor = ImageProcessor(config_path)
            optimized_content = image_processor.redistribute_images(optimized_content, len(images))
        
        # 重新评估优化后的内容
        optimized_quality_result = content_evaluator.evaluate_content(optimized_content, original_content)
        optimized_content_analysis = seo_analyzer.analyze_content(optimized_content, metadata.get('keywords', ''))
        
        # 如果有图片，嵌入到最终内容中
        if images:
            # 导入ImageProcessor
            image_processor = ImageProcessor(config_path)
            
            # 检查是否需要重新插入图片标记
            if "[IMAGE]" not in optimized_content:
                logger.warning("优化后的内容中没有找到[IMAGE]标记，尝试重新插入...")
                optimized_content = image_processor.redistribute_images(optimized_content, len(images))
            
            # 将图片嵌入到内容中，替换为实际的Markdown图片链接
            optimized_content = image_processor.embed_images_in_content(optimized_content, images)
            logger.info(f"已将 {len(images)} 张图片嵌入到最终内容中")
        
        # 保存最终的优化内容（包含实际图片链接）
        final_content_path = file_handler.save_content(
            optimized_content,
            f"final_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "final",
            file_format='md'
        )
        logger.info(f"最终内容已保存到: {final_content_path}")
        
        return {
            'content': optimized_content,
            'title': seo_title,
            'description': seo_description,
            'quality_result': optimized_quality_result,
            'seo_analysis': {
                'content_analysis': optimized_content_analysis,
                'title_analysis': title_analysis,
                'description_analysis': description_analysis
            },
            'quality_score': optimized_quality_result.get('quality_score', 0),
            'seo_score': calculate_seo_score(
                optimized_content_analysis,
                title_analysis,
                description_analysis
            ),
            'combined_score': calculate_combined_score(optimized_quality_result, {
                'content_analysis': optimized_content_analysis,
                'title_analysis': title_analysis,
                'description_analysis': description_analysis
            }),
            'images': images
        }

def step3_publish_content(title, content, description, config_path, logger, images=None):
    """步骤3: 发布到WordPress"""
    logger.info("步骤3: 发布到WordPress")
    publisher = WordPressPublisher(config_path)
    
    # 如果有图片，确保它们已经嵌入到内容中
    if images and len(images) > 0:
        logger.info(f"准备发布包含 {len(images)} 张图片的文章")
        # 图片已经在前面步骤中嵌入到内容中，这里不需要额外处理
    
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
    content_prompt = "Please optimize the content based on the following SEO suggestions:\n\n"
    if content_suggestions:
        content_prompt += f"Content optimization suggestions:\n{', '.join(content_suggestions)}\n\n"
    
    content_prompt += f"Title optimization suggestions:\n{title_prompt}\n\n"
    content_prompt += f"Description optimization suggestions:\n{description_prompt}\n\n"
    content_prompt += f"Original content:\n{content}"
    
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

def calculate_combined_score(quality_result, seo_analysis):
    """计算内容的综合评分（质量+SEO）"""
    quality_score = quality_result.get('quality_score', 0)
    seo_score = calculate_seo_score(
        seo_analysis['content_analysis'],
        seo_analysis['title_analysis'],
        seo_analysis['description_analysis']
    )
    
    # 质量占60%，SEO占40%
    combined_score = quality_score * 0.6 + seo_score * 0.4
    
    return round(combined_score, 2)

def merge_suggestions(quality_suggestions, seo_suggestions):
    """智能合并质量和SEO建议，去除冲突和重复"""
    merged = []
    content_seo_suggestions = seo_suggestions.get('content', [])
    title_seo_suggestions = seo_suggestions.get('title', [])
    description_seo_suggestions = seo_suggestions.get('description', [])
    
    # 创建关键词映射，用于识别相似建议
    keyword_map = {
        "可读性": ["readability", "sentence", "句子", "段落", "结构"],
        "关键词": ["keyword", "关键词", "密度"],
        "长度": ["length", "长度", "字数", "too short", "too long", "太短", "太长"],
        "标题": ["heading", "标题", "h2", "h3"],
        "链接": ["link", "链接", "内部链接"],
        "图片": ["image", "图片", "alt"]
    }
    
    # 对每个质量建议，检查是否与SEO建议冲突或重复
    for q_suggestion in quality_suggestions:
        is_duplicate = False
        q_lower = q_suggestion.lower()
        
        # 检查是否与SEO内容建议重复或冲突
        for s_suggestion in content_seo_suggestions:
            s_lower = s_suggestion.lower()
            
            # 检查是否属于同一类别的建议
            for category, keywords in keyword_map.items():
                if any(kw in q_lower for kw in keywords) and any(kw in s_lower for kw in keywords):
                    # 如果是同一类别，选择更具体的建议
                    if len(s_suggestion) > len(q_suggestion):
                        is_duplicate = True
                        break
            
            if is_duplicate:
                break
        
        if not is_duplicate:
            merged.append(q_suggestion)
    
    # 添加所有SEO建议
    merged.extend(content_seo_suggestions)
    
    # 对标题和描述的建议单独处理，因为它们通常不会与内容质量建议冲突
    if title_seo_suggestions:
        merged.append("标题优化建议:")
        merged.extend(title_seo_suggestions)
    
    if description_seo_suggestions:
        merged.append("描述优化建议:")
        merged.extend(description_seo_suggestions)
    
    # 对建议进行分类和排序，使相关建议放在一起
    categorized_suggestions = {category: [] for category in keyword_map.keys()}
    categorized_suggestions["其他"] = []
    
    for suggestion in merged:
        categorized = False
        for category, keywords in keyword_map.items():
            if any(kw in suggestion.lower() for kw in keywords):
                categorized_suggestions[category].append(suggestion)
                categorized = True
                break
        
        if not categorized:
            categorized_suggestions["其他"].append(suggestion)
    
    # 重新组织建议
    final_merged = []
    for category, suggestions in categorized_suggestions.items():
        if suggestions:
            if category != "其他":
                final_merged.append(f"--- {category} Related Suggestions ---")
            final_merged.extend(suggestions)
    
    return final_merged

def determine_optimization_strategy(quality_result, seo_analysis):
    """根据评估结果确定最佳优化策略"""
    quality_score = quality_result.get('quality_score', 0)
    seo_score = calculate_seo_score(
        seo_analysis['content_analysis'],
        seo_analysis['title_analysis'],
        seo_analysis['description_analysis']
    )
    
    if quality_score < 50:
        return "focus_on_quality"
    elif seo_score < 50:
        return "focus_on_seo"
    else:
        return "balanced_optimization"

def main():
    """主函数"""
    # 加载配置文件
    config_path = get_config_path()
    config = load_config(config_path)
    cli_config = config.get('cli', {})
    
    # 从配置文件获取URL列表和其他参数
    blog_urls = cli_config.get('blog_urls', [])
    if not blog_urls:
        print("错误: 配置文件中未设置blog_urls参数或参数为空")
        return
    
    # 处理每个URL
    for i, url in enumerate(blog_urls):
        print(f"\n处理第 {i+1}/{len(blog_urls)} 个URL: {url}")
        
        # 使用配置文件中的参数处理当前URL
        success = process_blog(
            url,
            cli_config.get('publish', False),
            config_path,
            cli_config.get('max_iterations', 3)
        )
        
        if success:
            print(f"URL处理成功: {url}")
        else:
            print(f"URL处理失败: {url}")
        
        # 如果不是最后一个URL，添加延迟
        if i < len(blog_urls) - 1:
            delay = cli_config.get('delay_between_urls', 5)
            print(f"等待 {delay} 秒后处理下一个URL...")
            import time
            time.sleep(delay)

if __name__ == "__main__":
    main()
