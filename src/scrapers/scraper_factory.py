from src.scrapers.general_scraper import GeneralScraper
import re
from urllib.parse import urlparse

class ScraperFactory:
    """爬虫工厂，根据URL选择合适的爬虫"""
    
    @staticmethod
    def get_scraper(url, config_path=None):
        """根据URL获取合适的爬虫"""
        domain = urlparse(url).netloc
        
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