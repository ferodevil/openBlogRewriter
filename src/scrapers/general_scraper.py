from src.scrapers.base_scraper import BaseScraper
import re
from readability import Document

class GeneralScraper(BaseScraper):
    """通用爬虫，适用于大多数博客网站"""
    
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