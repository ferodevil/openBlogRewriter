import requests
import logging
import yaml
import os
from abc import abstractmethod
from bs4 import BeautifulSoup
from src.utils.path_utils import get_config_path

class BaseScraper:
    """爬虫基类，提供基本的爬取功能"""
    
    def __init__(self, config_path=None):
        """初始化爬虫"""
        self.config = self._load_config(config_path)
        self.scraper_config = self.config.get('scrapers', {})
        
        # 设置请求头
        self.headers = {
            'User-Agent': self.scraper_config.get('user_agent', 'Mozilla/5.0'),
        }
        
        # 更新额外的请求头
        self.headers.update(self.scraper_config.get('headers', {}))
        
        # 设置超时时间
        self.timeout = self.scraper_config.get('timeout', 30)
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
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
    
    def get_page(self, url):
        """获取页面内容"""
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            self.logger.error(f"获取页面失败: {e}")
            return None
    
    def get_soup(self, url):
        """获取BeautifulSoup对象"""
        html = self.get_page(url)
        if html:
            return BeautifulSoup(html, 'html.parser')
        return None
    
    @abstractmethod
    def extract_content(self, url):
        """提取内容，子类必须实现此方法"""
        pass
    
    @abstractmethod
    def extract_metadata(self, url):
        """提取元数据，子类必须实现此方法"""
        pass
    
    def scrape(self, url):
        """爬取内容并返回结构化数据"""
        self.logger.info(f"开始爬取: {url}")
        
        content = self.extract_content(url)
        metadata = self.extract_metadata(url)
        
        if not content:
            self.logger.error(f"爬取内容失败: {url}")
            return None
        
        result = {
            'url': url,
            'content': content,
            'metadata': metadata,
            'timestamp': self._get_timestamp()
        }
        
        self.logger.info(f"爬取完成: {url}")
        return result
    
    def _get_timestamp(self):
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')