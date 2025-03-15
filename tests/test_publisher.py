import unittest
import sys
import os
import responses
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.join('d:', 'Python', 'myblog'))

from src.publishers.wordpress_publisher import WordPressPublisher

class TestWordPressPublisher(unittest.TestCase):
    """测试WordPress发布器"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 创建测试配置
        self.test_config = {
            'wordpress': {
                'url': 'https://example.com/wp-json/wp/v2',
                'username': 'testuser',
                'password': 'testpass',
                'categories': [1, 2],
                'tags': [3, 4],
                'status': 'draft'
            }
        }
        
        # 创建发布器实例
        self.publisher = WordPressPublisher()
        self.publisher.config = self.test_config
        self.publisher.wp_config = self.test_config['wordpress']
        self.publisher.api_url = self.test_config['wordpress']['url']
        self.publisher.username = self.test_config['wordpress']['username']
        self.publisher.password = self.test_config['wordpress']['password']
        self.publisher.categories = self.test_config['wordpress']['categories']
        self.publisher.tags = self.test_config['wordpress']['tags']
        self.publisher.status = self.test_config['wordpress']['status']
    
    @responses.activate
    def test_publish_post(self):
        """测试发布文章"""
        # 模拟WordPress API响应
        responses.add(
            responses.POST,
            f"{self.publisher.api_url}/posts",
            json={
                'id': 123,
                'link': 'https://example.com/test-post',
                'title': {'rendered': 'Test Title'},
                'content': {'rendered': 'Test Content'},
                'status': 'draft'
            },
            status=201
        )
        
        # 调用方法
        result = self.publisher.publish_post(
            title="Test Title",
            content="Test Content",
            excerpt="Test Excerpt"
        )
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result.get('link'), 'https://example.com/test-post')
        
        # 验证请求
        self.assertEqual(len(responses.calls), 1)
        request_body = json.loads(responses.calls[0].request.body)
        self.assertEqual(request_body['title'], 'Test Title')
        self.assertEqual(request_body['content'], 'Test Content')
        self.assertEqual(request_body['status'], 'draft')
        self.assertEqual(request_body['categories'], [1, 2])
        self.assertEqual(request_body['tags'], [3, 4])

if __name__ == '__main__':
    unittest.main()