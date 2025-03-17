import asyncio
import os
import re
import json
import logging
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from datetime import datetime

try:
    from crawl4ai import AsyncWebCrawler, CacheMode
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logging.warning("crawl4ai 库未安装，Crawl4AIScraper 将无法使用。请使用 pip install crawl4ai 安装。")

from src.scrapers.base_scraper import BaseScraper
from src.utils.file_handler import FileHandler
from src.utils.image_processor import ImageProcessor

class Crawl4AIScraper(BaseScraper):
    """基于crawl4ai的爬虫，提供更强大的内容提取和清理功能"""
    
    def __init__(self, config_path=None):
        """初始化爬虫"""
        super().__init__(config_path)
        self.config_path = config_path  # 保存config_path以便后续使用
        self.images = []
        self.file_handler = FileHandler()
        self.image_processor = ImageProcessor(config_path)
        
        # 从配置中加载crawl4ai特定配置
        self.crawl4ai_config = self.config.get('crawl4ai', {})
        
        # 从配置中获取路径配置
        self.paths_config = self.config.get('paths', {})
        self.data_dir = os.path.abspath(self.paths_config.get('data_dir', './data'))
        self.output_dir = os.path.join(self.data_dir, 'output')
        self.images_dir = os.path.join(self.data_dir, 'images')
        
        # 检查crawl4ai是否可用
        if not CRAWL4AI_AVAILABLE:
            self.logger.warning("crawl4ai 库未安装，将使用基本爬虫功能。请使用 pip install crawl4ai 安装。")
    
    async def async_scrape(self, url):
        """异步爬取内容并返回结构化数据"""
        if not CRAWL4AI_AVAILABLE:
            self.logger.error("crawl4ai 库未安装，无法使用异步爬取功能。")
            return self.scrape(url)  # 回退到同步方法
        
        self.logger.info(f"开始异步爬取: {url}")
        self.images = []
        
        try:
            async with AsyncWebCrawler() as crawler:
                # 从配置中获取爬取参数
                remove_selectors = self.crawl4ai_config.get('remove_selectors', [
                    "nav", "footer", ".header", ".footer", ".sidebar", ".navigation", ".menu",
                    ".ads", ".advertisement", ".social-share", ".related-posts", ".comments",
                    ".cookie-banner"
                ])
                
                # 执行爬取
                result = await crawler.arun(
                    url=url,
                    cache_mode=CacheMode.BYPASS,
                    exclude_external_images=self.crawl4ai_config.get('exclude_external_images', False),
                    content_type=self.crawl4ai_config.get('content_type', "article"),
                    word_count_threshold=self.crawl4ai_config.get('word_count_threshold', 100),
                    only_text=self.crawl4ai_config.get('only_text', False),
                    keep_data_attributes=self.crawl4ai_config.get('keep_data_attributes', True),
                    remove_forms=self.crawl4ai_config.get('remove_forms', True),
                    scan_full_page=self.crawl4ai_config.get('scan_full_page', True),
                    magic=self.crawl4ai_config.get('magic', True),
                    remove_selectors=remove_selectors,
                    exclude_social_media_links=self.crawl4ai_config.get('exclude_social_media_links', True),
                    exclude_external_links=self.crawl4ai_config.get('exclude_external_links', True),
                )
                
                # 提取内容
                content = self._extract_content_from_result(result)
                
                # 提取元数据
                metadata = self._extract_metadata_from_result(result)
                
                # 处理图片
                if hasattr(result, 'media') and 'images' in result.media:
                    self._process_images(result.media['images'], url)
                
                # 构建结果
                scrape_result = {
                    'url': url,
                    'content': content,
                    'metadata': metadata,
                    'images': self.images,
                    'timestamp': self._get_timestamp()
                }
                
                self.logger.info(f"异步爬取完成: {url}")
                return scrape_result
                
        except Exception as e:
            self.logger.error(f"异步爬取过程中出错: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def scrape(self, url):
        """同步爬取内容并返回结构化数据（覆盖基类方法）"""
        if CRAWL4AI_AVAILABLE:
            # 如果crawl4ai可用，使用异步方法
            return asyncio.run(self.async_scrape(url))
        else:
            # 否则使用基类的同步方法
            return super().scrape(url)
    
    def extract_content(self, url):
        """提取内容（实现抽象方法）"""
        if CRAWL4AI_AVAILABLE:
            # 如果crawl4ai可用，使用异步方法提取内容
            result = asyncio.run(self.async_scrape(url))
            return result['content'] if result else None
        else:
            # 否则使用基本方法
            html = self.get_page(url)
            if not html:
                return None
            
            # 使用BeautifulSoup提取内容
            soup = BeautifulSoup(html, 'html.parser')
            
            # 移除不需要的元素
            for selector in self.crawl4ai_config.get('remove_selectors', []):
                for element in soup.select(selector):
                    element.extract()
            
            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.extract()
            
            # 获取文本
            text = soup.get_text(separator='\n')
            
            # 清理文本
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
    
    def extract_metadata(self, url):
        """提取元数据（实现抽象方法）"""
        if CRAWL4AI_AVAILABLE:
            # 如果crawl4ai可用，使用异步方法提取元数据
            result = asyncio.run(self.async_scrape(url))
            return result['metadata'] if result else {}
        else:
            # 否则使用基本方法
            soup = self.get_soup(url)
            if not soup:
                return {}
            
            metadata = {}
            
            # 提取标题
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.text.strip()
            
            # 提取描述
            description_tag = soup.find('meta', attrs={'name': 'description'})
            if description_tag:
                metadata['description'] = description_tag.get('content', '')
            
            # 提取关键词
            keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
            if keywords_tag:
                metadata['keywords'] = keywords_tag.get('content', '')
            
            # 提取作者
            author_tag = soup.find('meta', attrs={'name': 'author'})
            if author_tag:
                metadata['author'] = author_tag.get('content', '')
            
            # 提取发布日期
            date_tag = soup.find('meta', attrs={'property': 'article:published_time'})
            if date_tag:
                metadata['published_date'] = date_tag.get('content', '')
            
            return metadata
    
    def save_content(self, content, save_dir=None, filename=None, format='md'):
        """保存内容到文件
        
        Args:
            content (str): 要保存的内容
            save_dir (str, optional): 保存目录。如果为None，将使用默认目录
            filename (str, optional): 文件名。如果为None，将使用时间戳生成
            format (str, optional): 文件格式，默认为'md'(Markdown)
            
        Returns:
            str: 保存的文件路径
        """
        if save_dir is None:
            save_dir = self.output_dir
        
        # 确保目录存在
        os.makedirs(save_dir, exist_ok=True)
        
        return self.file_handler.save_content(content, filename, os.path.basename(save_dir), format)
    
    def save_images(self, images, save_dir=None):
        """保存图片信息到文件
        
        Args:
            images (list): 图片信息列表
            save_dir (str, optional): 保存目录。如果为None，将使用默认目录
            
        Returns:
            str: 保存的文件路径
        """
        if save_dir is None:
            save_dir = self.output_dir
        
        # 确保目录存在
        os.makedirs(save_dir, exist_ok=True)
        
        # 保存图片信息
        images_info_path = os.path.join(save_dir, 'images_info.json')
        with open(images_info_path, 'w', encoding='utf-8') as f:
            json.dump(images, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"图片信息已保存到: {images_info_path}")
        return images_info_path
    
    def save_metadata(self, metadata, save_dir=None):
        """保存元数据到文件
        
        Args:
            metadata (dict): 元数据
            save_dir (str, optional): 保存目录。如果为None，将使用默认目录
            
        Returns:
            str: 保存的文件路径
        """
        if save_dir is None:
            save_dir = self.output_dir
        
        # 确保目录存在
        os.makedirs(save_dir, exist_ok=True)
        
        # 保存元数据
        metadata_path = os.path.join(save_dir, 'metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"元数据已保存到: {metadata_path}")
        return metadata_path
    
    def save_all(self, result, save_dir=None):
        """保存所有内容到文件
        
        Args:
            result (dict): 爬取结果
            save_dir (str, optional): 保存目录。如果为None，将使用默认目录
            
        Returns:
            dict: 保存的文件路径字典
        """
        if save_dir is None:
            save_dir = self.output_dir
        
        # 确保目录存在
        os.makedirs(save_dir, exist_ok=True)
        
        # 确保图片目录存在
        img_dir = os.path.join(save_dir, 'images')
        os.makedirs(img_dir, exist_ok=True)
        
        # 保存内容
        content_path = self.save_content(result['content'], save_dir)
        
        # 保存元数据
        metadata_path = self.save_metadata(result['metadata'], save_dir)
        
        # 保存图片信息
        images_info_path = self.save_images(result['images'], save_dir)
        
        return {
            'content': content_path,
            'metadata': metadata_path,
            'images_info': images_info_path
        }
    
    def _extract_content_from_result(self, result):
        """从crawl4ai结果中提取内容"""
        if not hasattr(result, 'markdown') and not hasattr(result, 'text'):
            self.logger.error("crawl4ai结果中没有内容")
            return None
        
        # 优先使用markdown内容
        if hasattr(result, 'markdown'):
            content = result.markdown
        else:
            content = result.text
        
        # 清理内容
        cleaned_content = self._clean_content(content, result.title if hasattr(result, 'title') else None)
        
        return cleaned_content
        
    def _clean_content(self, content, title=None):
        """清理内容
        
        Args:
            content (str): 原始内容
            title (str, optional): 标题
            
        Returns:
            str: 清理后的内容
        """
        # 从配置中获取需要跳过的关键词
        skip_keywords = self.crawl4ai_config.get('skip_keywords', [
            'Save up to', 'Free Shipping', 'Shop All', 'Browse', 
            'Getting Started', 'Sale', 'GIFTING', 'collection', 
            'Add to cart', 'View all', 'Subscribe', 'Newsletter', 'Sign up',
            'Follow us', 'Facebook', 'Twitter', 'Instagram', 'Pinterest',
            'Copyright', 'Terms of Service', 'Privacy Policy', 'Refund Policy',
            'Shopping Cart', 'Your Cart is Empty', 'Subtotal', 'currency',
            'Leave a comment', 'Comments will be approved',
            'Name *', 'Email *', 'Comment *', 'Related Blog Posts', 'Footer menu'
        ])
        
        # 清理内容
        cleaned_lines = []
        real_content_start = False
        real_title = ""
        content_ended = False
        current_section = None
        
        # 按行处理内容
        for line in content.split('\n'):
            line = line.strip()
            
            # 跳过空行和分隔符
            if not line or line in ['---', '***', '___']:
                if cleaned_lines:  # 只有在已有内容时才保留空行
                    cleaned_lines.append('')
                continue
            
            # 检查是否是标题行
            if line.startswith('# '):
                if not real_content_start:  # 第一个标题作为文章标题
                    real_title = line.replace('# ', '')
                    real_content_start = True
                    cleaned_lines.append(line)
                    continue
                else:  # 其他标题作为章节标题
                    current_section = line
                    cleaned_lines.append('\n' + line)
                    continue
            
            # 检查是否是子标题
            if line.startswith('## ') or line.startswith('### '):
                current_section = line
                cleaned_lines.append('\n' + line)
                continue
            
            # 如果还没找到真正的内容起点，继续查找
            if not real_content_start:
                if title and title.lower() in line.lower():
                    real_content_start = True
                else:
                    continue
            
            # 检测内容是否已经结束
            if any(marker in line.lower() for marker in [
                'leave a comment', 'related blog posts', 'footer menu',
                'share this post', 'about the author', 'popular posts'
            ]):
                content_ended = True
                continue
            
            # 如果内容已经结束，跳过后续内容
            if content_ended:
                continue
            
            # 检查是否包含需要跳过的关键词
            should_skip = False
            for keyword in skip_keywords:
                if keyword.lower() in line.lower():
                    should_skip = True
                    break
            
            if not should_skip:
                # 保持段落结构
                if line.startswith('- ') or line.startswith('* ') or line.startswith('1. '):
                    cleaned_lines.append(line)  # 列表项
                elif line.startswith('> '):
                    cleaned_lines.append(line)  # 引用
                elif line.startswith('```'):
                    cleaned_lines.append(line)  # 代码块
                elif current_section and len(cleaned_lines) > 0 and cleaned_lines[-1].startswith(current_section):
                    cleaned_lines.append(line)  # 章节内容
                else:
                    cleaned_lines.append(line)
        
        # 组织内容
        cleaned_content = '\n'.join(cleaned_lines)
        
        # 如果内容为空，使用更宽松的过滤条件
        if not cleaned_content.strip():
            self.logger.warning("过滤后的内容为空，尝试使用更宽松的过滤条件")
            cleaned_lines = []
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('#'):
                    cleaned_lines.append(line)
                    continue
                
                # 只过滤明显的干扰内容
                if any(marker in line.lower() for marker in [
                    'leave a comment', 'footer menu', 'shopping cart', 'currency',
                    'share this', 'follow us', 'subscribe', 'newsletter'
                ]):
                    continue
                
                cleaned_lines.append(line)
            
            cleaned_content = '\n'.join(cleaned_lines)
        
        # 处理标题重复问题
        if title:
            # 移除所有标题行
            content_lines = cleaned_content.split('\n')
            title_pattern = re.compile(r'^# .*$')
            non_title_lines = [line for line in content_lines if not title_pattern.match(line)]
            
            # 移除可能的日期和阅读时间信息
            filtered_lines = []
            for line in non_title_lines:
                # 跳过日期和阅读时间信息
                if line.strip().startswith('* ') and ('min read' in line.lower() or re.search(r'\b\d{4}\b', line)):
                    continue
                filtered_lines.append(line)
            
            # 重新组织内容，确保只有一个标题
            clean_content = '\n'.join(filtered_lines)
            final_content = f"# {title}\n\n{clean_content}"
        else:
            final_content = cleaned_content
        
        return final_content
    
    def _extract_metadata_from_result(self, result):
        """从crawl4ai结果中提取元数据"""
        metadata = {}
        
        # 提取标题
        if hasattr(result, 'title'):
            metadata['title'] = result.title
        
        # 提取其他元数据
        if hasattr(result, 'metadata'):
            metadata.update(result.metadata)
        
        # 提取URL
        if hasattr(result, 'url'):
            metadata['url'] = result.url
            # 提取域名
            parsed_url = urlparse(result.url)
            metadata['domain'] = parsed_url.netloc
        
        return metadata
    
    def _process_images(self, images, base_url):
        """处理图片
        
        Args:
            images (list): crawl4ai提取的图片列表
            base_url (str): 基础URL
        """
        import concurrent.futures
        import threading
        
        # 确保图片目录存在
        img_dir = self.images_dir
        os.makedirs(img_dir, exist_ok=True)
        
        # 线程安全的图片列表
        images_lock = threading.Lock()
        
        # 从配置中获取最大图片数量，默认为5张
        max_images = self.crawl4ai_config.get('max_images', 5)
        
        # 过滤图片，只保留正文中的相关图片
        content_images = []
        for img in images:
            # 跳过小图标和装饰性图片
            if 'width' in img and 'height' in img:
                if int(img.get('width', 0)) < 100 or int(img.get('height', 0)) < 100:
                    continue
            
            # 检查图片是否在正文中
            is_in_content = False
            
            # 检查图片是否有content_node属性，表示它在正文中
            if img.get('content_node', False):
                is_in_content = True
            
            # 检查图片的父元素是否为正文相关元素
            parent_tag = img.get('parent_tag', '').lower()
            if parent_tag in ['p', 'div', 'article', 'section', 'main', 'figure']:
                is_in_content = True
            
            # 检查图片是否有意义的alt文本或标题
            has_meaningful_text = False
            alt_text = img.get('alt', '')
            title = img.get('title', '')
            if alt_text and len(alt_text.strip()) > 3:
                has_meaningful_text = True
            if title and len(title.strip()) > 3:
                has_meaningful_text = True
            
            # 检查图片是否有合理的尺寸
            has_reasonable_size = False
            if 'width' in img and 'height' in img:
                width = int(img.get('width', 0))
                height = int(img.get('height', 0))
                if width >= 200 and height >= 200:
                    has_reasonable_size = True
            
            # 如果图片在正文中，或者有意义的文本或合理的尺寸，认为它是正文中的图片
            if is_in_content or has_meaningful_text or has_reasonable_size:
                content_images.append(img)
        
        # 限制图片数量，最多处理max_images张图片
        if len(content_images) > max_images:
            # 根据图片质量和相关性排序
            # 优先选择有意义的alt文本、合理尺寸的图片
            def image_score(img):
                score = 0
                # 有意义的alt文本或标题加分
                alt_text = img.get('alt', '')
                title = img.get('title', '')
                if alt_text and len(alt_text.strip()) > 3:
                    score += 3
                if title and len(title.strip()) > 3:
                    score += 2
                # 合理尺寸加分
                if 'width' in img and 'height' in img:
                    width = int(img.get('width', 0))
                    height = int(img.get('height', 0))
                    if width >= 400 and height >= 400:
                        score += 3
                    elif width >= 300 and height >= 300:
                        score += 2
                    elif width >= 200 and height >= 200:
                        score += 1
                return score
            
            # 按分数排序并取前max_images张
            content_images = sorted(content_images, key=image_score, reverse=True)[:max_images]
        
        self.logger.info(f"从 {len(images)} 张图片中筛选出 {len(content_images)} 张正文相关图片，将处理 {min(len(content_images), max_images)} 张")
        
        def process_single_image(img):
            try:
                img_url = img['src']
                # 下载图片
                img_content, filename, local_path = self.image_processor.download_image(img_url, base_url)
                if local_path:
                    # 构建图片信息
                    image_info = {
                        'filename': filename,
                        'original_url': img_url,
                        'local_path': local_path,
                        'alt_text': img.get('alt', ''),
                        'title': img.get('title', ''),
                        'width': img.get('width', ''),
                        'height': img.get('height', ''),
                        'position': img.get('position', 0)  # 记录图片在文章中的位置
                    }
                    
                    # 线程安全地添加到图片列表
                    with images_lock:
                        self.images.append(image_info)
                    
                    self.logger.info(f"已下载图片: {img_url} -> {local_path}")
                    return image_info
            except Exception as e:
                self.logger.error(f"处理图片失败: {e}")
                return None
        
        # 使用线程池并发处理图片
        max_workers = min(len(content_images), self.crawl4ai_config.get('max_concurrent_downloads', 5))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有下载任务
            futures = [executor.submit(process_single_image, img) for img in content_images]
            
            # 等待所有任务完成
            concurrent.futures.wait(futures)
    
    def embed_images_in_content(self, content):
        """将图片嵌入到内容中
        
        Args:
            content (str): 文章内容
            
        Returns:
            str: 嵌入图片后的内容
        """
        # 如果没有图片，直接返回原内容
        if not self.images:
            return content
            
        # 检查内容中是否有[IMAGE]标记
        if '[IMAGE]' in content:
            # 如果有[IMAGE]标记，按顺序替换为图片
            image_index = 0
            lines = content.split('\n')
            result_lines = []
            
            for line in lines:
                if '[IMAGE]' in line and image_index < len(self.images):
                    # 替换[IMAGE]标记为图片引用
                    img = self.images[image_index]
                    alt_text = img.get('alt_text', f"图片{image_index+1}")
                    if not alt_text.strip():
                        alt_text = f"图片{image_index+1}"
                    
                    # 使用相对路径
                    rel_path = os.path.join('images', img['filename'])
                    image_reference = f"![{alt_text}]({rel_path})"
                    
                    # 替换标记
                    line = line.replace('[IMAGE]', image_reference)
                    image_index += 1
                
                result_lines.append(line)
            
            # 如果还有未使用的图片，添加到内容末尾
            if image_index < len(self.images):
                result_lines.append("\n## 其他图片\n")
                for i in range(image_index, len(self.images)):
                    img = self.images[i]
                    alt_text = img.get('alt_text', f"图片{i+1}")
                    if not alt_text.strip():
                        alt_text = f"图片{i+1}"
                    
                    # 使用相对路径
                    rel_path = os.path.join('images', img['filename'])
                    result_lines.append(f"![{alt_text}]({rel_path})\n")
            
            return '\n'.join(result_lines)
        else:
            # 如果没有[IMAGE]标记，尝试智能插入图片
            # 将内容分段
            paragraphs = content.split('\n\n')
            result_paragraphs = []
            images_per_section = max(1, len(self.images) // max(1, len(paragraphs) - 2))
            image_index = 0
            
            # 跳过第一段（通常是标题或介绍）
            if paragraphs:
                result_paragraphs.append(paragraphs[0])
            
            # 在段落之间插入图片
            for i in range(1, len(paragraphs)):
                result_paragraphs.append(paragraphs[i])
                
                # 每隔几个段落插入一张图片
                if i % 3 == 0 and image_index < len(self.images):
                    img = self.images[image_index]
                    alt_text = img.get('alt_text', f"图片{image_index+1}")
                    if not alt_text.strip():
                        alt_text = f"图片{image_index+1}"
                    
                    # 使用相对路径
                    rel_path = os.path.join('images', img['filename'])
                    result_paragraphs.append(f"![{alt_text}]({rel_path})")
                    image_index += 1
            
            # 如果还有未使用的图片，添加到内容末尾
            if image_index < len(self.images):
                result_paragraphs.append("\n## 其他图片\n")
                for i in range(image_index, len(self.images)):
                    img = self.images[i]
                    alt_text = img.get('alt_text', f"图片{i+1}")
                    if not alt_text.strip():
                        alt_text = f"图片{i+1}"
                    
                    # 使用相对路径
                    rel_path = os.path.join('images', img['filename'])
                    result_paragraphs.append(f"![{alt_text}]({rel_path})")
            
            return '\n\n'.join(result_paragraphs)