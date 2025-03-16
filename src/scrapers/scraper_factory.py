from src.scrapers.general_scraper import GeneralScraper
import re
import logging
from urllib.parse import urlparse

# 尝试导入Crawl4AIScraper
try:
    from src.scrapers.crawl4ai_scraper import Crawl4AIScraper, CRAWL4AI_AVAILABLE
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logging.warning("无法导入Crawl4AIScraper，将使用GeneralScraper作为替代。")

class ScraperFactory:
    """爬虫工厂，根据URL选择合适的爬虫"""
    
    @staticmethod
    def get_scraper(url, config_path=None, force_scraper=None):
        """根据URL获取合适的爬虫
        
        Args:
            url (str): 要爬取的URL
            config_path (str, optional): 配置文件路径
            force_scraper (str, optional): 强制使用的爬虫类型，可选值：'general', 'crawl4ai'
            
        Returns:
            BaseScraper: 爬虫实例
        """
        # 如果强制指定爬虫类型
        if force_scraper:
            if force_scraper.lower() == 'crawl4ai' and CRAWL4AI_AVAILABLE:
                return Crawl4AIScraper(config_path)
            elif force_scraper.lower() == 'general':
                return GeneralScraper(config_path)
        
        # 从配置中获取默认爬虫类型
        try:
            import yaml
            from src.utils.path_utils import get_config_path
            
            if config_path is None:
                config_path = get_config_path()
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                default_scraper = config.get('scrapers', {}).get('default_scraper', 'general')
                
                # 如果配置指定使用crawl4ai且可用
                if default_scraper.lower() == 'crawl4ai' and CRAWL4AI_AVAILABLE:
                    return Crawl4AIScraper(config_path)
        except Exception as e:
            logging.warning(f"加载配置文件失败: {e}，将使用默认爬虫")
        
        # 根据域名选择特定爬虫
        domain = urlparse(url).netloc
        
        # 如果crawl4ai可用，优先使用
        if CRAWL4AI_AVAILABLE:
            return Crawl4AIScraper(config_path)
        else:
            # 根据域名选择特定爬虫
            # 这里可以扩展添加更多特定网站的爬虫
            if 'medium.com' in domain:
                # 未来可以添加Medium专用爬虫
                return GeneralScraper(config_path)
            elif 'wordpress.com' in domain:
                # 未来可以添加WordPress专用爬虫
                return GeneralScraper(config_path)
            else:
                # 默认使用通用爬虫
                return GeneralScraper(config_path)