from src.scrapers.base_scraper import BaseScraper
import re
import yaml
from readability import Document
from bs4 import BeautifulSoup
from src.utils.path_utils import get_config_path

class GeneralScraper(BaseScraper):
    """通用爬虫，适用于大多数博客网站"""
    
    def __init__(self, config_path=None):
        """初始化爬虫"""
        super().__init__(config_path)
        self.config_path = config_path  # 保存config_path
        self.config = self._load_config(config_path)
        self.images = []
    
    def extract_content(self, url):
        """提取文章内容"""
        html = self.get_page(url)
        if not html:
            return None
        
        # 使用readability提取主要内容
        doc = Document(html)
        article_html = doc.summary()
        
        # 使用BeautifulSoup清理HTML
        soup = BeautifulSoup(article_html, 'html.parser')
        
        # 提取图片
        self.extract_images(soup, url)
        
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
        """提取元数据"""
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
    
    def _load_config(self, config_path=None):
        """加载配置文件"""
        if config_path is None:
            config_path = get_config_path()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return {}
            
    def extract_images(self, soup, base_url):
        """提取文章中的图片"""
        from src.utils.image_processor import ImageProcessor
        from urllib.parse import urljoin
        import re
        
        # 初始化图片处理器
        image_processor = ImageProcessor(self.config_path)
        
        # 存储所有找到的图片URL
        image_urls = set()
        
        # 1. 获取所有img标签
        for img in soup.find_all('img'):
            # 处理src属性
            src = img.get('src')
            if src:
                image_urls.add(src)
            
            # 处理srcset属性
            srcset = img.get('srcset')
            if srcset:
                # 提取srcset中的URL
                urls = re.findall(r'([^\s]+)(?:\s+[\d.]+[wx])?,?', srcset)
                image_urls.update(urls)
        
        # 2. 获取picture标签中的source
        for picture in soup.find_all('picture'):
            for source in picture.find_all('source'):
                srcset = source.get('srcset')
                if srcset:
                    urls = re.findall(r'([^\s]+)(?:\s+[\d.]+[wx])?,?', srcset)
                    image_urls.update(urls)
        
        # 3. 查找带有background-image样式的元素
        for tag in soup.find_all(style=True):
            style = tag.get('style', '')
            bg_urls = re.findall(r'background-image:\s*url\(["\']?([^\'"\)]+)["\']?\)', style)
            image_urls.update(bg_urls)
        
        # 4. 处理和下载图片
        self.logger.info(f"找到 {len(image_urls)} 张图片")
        for url in image_urls:
            # 处理相对路径
            absolute_url = urljoin(base_url, url)
            
            # 下载图片
            _, filename, local_path = image_processor.download_image(absolute_url, base_url)
            if local_path:
                # 添加到图片列表
                self.images.append({
                    'original_url': url,
                    'absolute_url': absolute_url,
                    'local_path': local_path,
                    'filename': filename,
                    'alt': ''
                })
                self.logger.info(f"已下载图片: {absolute_url} -> {local_path}")
    
    def scrape(self, url):
        """爬取内容并返回结构化数据"""
        self.logger.info(f"开始爬取: {url}")
        self.images = []
        
        content = self.extract_content(url)
        metadata = self.extract_metadata(url)
        
        if not content:
            self.logger.error(f"爬取内容失败: {url}")
            return None
        
        # 如果有图片，使用图片处理器将图片嵌入到内容中
        if self.images:
            from src.utils.image_processor import ImageProcessor
            image_processor = ImageProcessor(self.config_path)
            content = image_processor.embed_images_in_content(content, self.images)
            self.logger.info(f"已将 {len(self.images)} 张图片嵌入到内容中")
        
        result = {
            'url': url,
            'content': content,
            'metadata': metadata,
            'images': self.images,  # 添加图片信息
            'timestamp': self._get_timestamp()
        }
        
        self.logger.info(f"爬取完成: {url}")
        return result