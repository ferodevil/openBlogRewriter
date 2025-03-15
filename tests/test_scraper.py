import unittest
import sys
import os
import responses

# 添加项目根目录到Python路径
sys.path.append(os.path.join('d:', 'Python', 'myblog'))

from src.scrapers.general_scraper import GeneralScraper

class TestGeneralScraper(unittest.TestCase):
    """测试通用爬虫"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.scraper = GeneralScraper()
        self.test_url = "https://example.com/blog-post"
    
    @responses.activate
    def test_get_page(self):
        """测试获取页面内容"""
        # 模拟HTTP响应
        responses.add(
            responses.GET,
            self.test_url,
            body="<html><body><h1>Test Blog</h1><p>Test content</p></body></html>",
            status=200
        )
        
        # 调用方法
        html = self.scraper.get_page(self.test_url)
        
        # 验证结果
        self.assertIsNotNone(html)
        self.assertIn("<h1>Test Blog</h1>", html)
    
    @responses.activate
    def test_extract_content(self):
        """测试提取内容"""
        # 模拟HTTP响应
        responses.add(
            responses.GET,
            self.test_url,
            body="""
            <html>
                <head>
                    <title>Test Blog Title</title>
                    <meta name="description" content="Test description">
                </head>
                <body>
                    <article>
                        <h1>Test Blog</h1>
                        <p>Test content paragraph 1</p>
                        <p>Test content paragraph 2</p>
                    </article>
                    <footer>Footer content</footer>
                </body>
            </html>
            """,
            status=200
        )
        
        # 调用方法
        content = self.scraper.extract_content(self.test_url)
        
        # 验证结果
        self.assertIsNotNone(content)
        self.assertIn("Test content paragraph", content)
    
    @responses.activate
    def test_extract_metadata(self):
        """测试提取元数据"""
        # 模拟HTTP响应
        responses.add(
            responses.GET,
            self.test_url,
            body="""
            <html>
                <head>
                    <title>Test Blog Title</title>
                    <meta name="description" content="Test description">
                    <meta name="keywords" content="test, blog, keywords">
                    <meta name="author" content="Test Author">
                    <meta property="article:published_time" content="2023-01-01">
                </head>
                <body>
                    <article>
                        <h1>Test Blog</h1>
                        <p>Test content</p>
                    </article>
                </body>
            </html>
            """,
            status=200
        )
        
        # 调用方法
        metadata = self.scraper.extract_metadata(self.test_url)
        
        # 验证结果
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.get('title'), "Test Blog Title")
        self.assertEqual(metadata.get('description'), "Test description")
        self.assertEqual(metadata.get('keywords'), "test, blog, keywords")
        self.assertEqual(metadata.get('author'), "Test Author")
        self.assertEqual(metadata.get('published_date'), "2023-01-01")

if __name__ == '__main__':
    unittest.main()