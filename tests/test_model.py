import unittest
import sys
import os
import mock

# 添加项目根目录到Python路径
sys.path.append(os.path.join('d:', 'Python', 'myblog'))

from src.models.openai_model import OpenAIModel

class TestOpenAIModel(unittest.TestCase):
    """测试OpenAI模型"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 使用mock配置，避免加载真实的API密钥
        self.mock_config = {
            'models': {
                'openai': {
                    'api_key': 'test_api_key',
                    'model': 'gpt-4',
                    'temperature': 0.7,
                    'max_tokens': 2000
                }
            }
        }
        
        # 使用patch模拟_load_config方法
        with mock.patch.object(OpenAIModel, '_load_config', return_value=self.mock_config):
            self.model = OpenAIModel()
    
    @mock.patch('openai.ChatCompletion.create')
    def test_rewrite_content(self, mock_create):
        """测试内容重写"""
        # 模拟OpenAI API响应
        mock_create.return_value.choices = [
            mock.MagicMock(message=mock.MagicMock(content="重写后的内容"))
        ]
        
        # 调用方法
        content = "原始内容"
        metadata = {"title": "测试标题", "keywords": "测试,关键词"}
        result = self.model.rewrite_content(content, metadata)
        
        # 验证结果
        self.assertEqual(result, "重写后的内容")
        
        # 验证API调用
        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        self.assertEqual(kwargs['model'], 'gpt-4')
        self.assertEqual(kwargs['temperature'], 0.7)
        self.assertEqual(kwargs['max_tokens'], 2000)
        self.assertEqual(len(kwargs['messages']), 2)
        self.assertEqual(kwargs['messages'][0]['role'], 'system')
        self.assertEqual(kwargs['messages'][1]['role'], 'user')
    
    @mock.patch('openai.ChatCompletion.create')
    def test_generate_seo_title(self, mock_create):
        """测试生成SEO标题"""
        # 模拟OpenAI API响应
        mock_create.return_value.choices = [
            mock.MagicMock(message=mock.MagicMock(content="SEO优化的标题"))
        ]
        
        # 调用方法
        content = "文章内容"
        metadata = {"title": "原始标题"}
        result = self.model.generate_seo_title(content, metadata)
        
        # 验证结果
        self.assertEqual(result, "SEO优化的标题")
        
        # 验证API调用
        mock_create.assert_called_once()

if __name__ == '__main__':
    unittest.main()