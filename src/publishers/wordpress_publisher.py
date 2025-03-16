import requests
import base64
import logging
import yaml
import os
import json
import time
from datetime import datetime
from src.utils.path_utils import get_base_dir, get_config_path

class WordPressPublisher:
    """WordPress发布器，用于将内容发布到WordPress网站"""
    
    def __init__(self, config_path=None):
        """初始化WordPress发布器"""
        self.config = self._load_config(config_path)
        self.wp_config = self.config.get('wordpress', {})
        
        self.api_url = self.wp_config.get('url', '')
        self.username = self.wp_config.get('username', '')
        self.password = self.wp_config.get('password', '')
        self.categories = self.wp_config.get('categories', [])
        self.tags = self.wp_config.get('tags', [])
        self.status = self.wp_config.get('status', 'draft')
        
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
    
    def _get_auth_header(self):
        """获取认证头"""
        credentials = f"{self.username}:{self.password}"
        token = base64.b64encode(credentials.encode()).decode()
        return {'Authorization': f'Basic {token}'}
    
    def publish_post(self, title, content, excerpt='', featured_media=0, meta=None, max_retries=3, retry_delay=5):
        """发布文章到WordPress，带有重试机制"""
        if not self.api_url:
            self.logger.error("WordPress API URL未配置")
            return None
        
        # 构建API端点
        endpoint = f"{self.api_url}/posts"
        
        # 构建请求数据
        data = {
            'title': title,
            'content': content,
            'status': self.status,
            'categories': self.categories,
            'tags': self.tags
        }
        
        # 添加摘要（如果有）
        if excerpt:
            data['excerpt'] = excerpt
        
        # 添加特色图片（如果有）
        if featured_media:
            data['featured_media'] = featured_media
        
        # 添加元数据（如果有）
        if meta:
            data['meta'] = meta
        
        # 发送请求，带有重试机制
        for attempt in range(max_retries):
            try:
                headers = self._get_auth_header()
                headers['Content-Type'] = 'application/json'
                
                response = requests.post(
                    endpoint,
                    headers=headers,
                    data=json.dumps(data)
                )
                
                response.raise_for_status()
                result = response.json()
                
                self.logger.info(f"文章发布成功: {result.get('link', '')}")
                return result
            
            except requests.exceptions.RequestException as e:
                self.logger.error(f"文章发布尝试 {attempt+1}/{max_retries} 失败: {e}")
                if hasattr(e, 'response') and e.response:
                    self.logger.error(f"响应内容: {e.response.text}")
                
                if attempt < max_retries - 1:
                    self.logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"已达到最大重试次数 ({max_retries})，发布失败")
                    return None
        
        return None
    
    def upload_media(self, file_path, title=None, max_retries=3, retry_delay=5):
        """上传媒体文件到WordPress，带有重试机制"""
        if not self.api_url:
            self.logger.error("WordPress API URL未配置")
            return None
        
        # 构建API端点
        endpoint = f"{self.api_url}/media"
        
        # 准备文件
        try:
            filename = os.path.basename(file_path)
            
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # 设置请求头
            headers = self._get_auth_header()
            headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            headers['Content-Type'] = self._get_content_type(filename)
            
            # 发送请求，带有重试机制
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        endpoint,
                        headers=headers,
                        data=file_data
                    )
                    
                    response.raise_for_status()
                    result = response.json()
                    
                    self.logger.info(f"媒体上传成功: {result.get('source_url', '')}")
                    return result
                
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"媒体上传尝试 {attempt+1}/{max_retries} 失败: {e}")
                    if hasattr(e, 'response') and e.response:
                        self.logger.error(f"响应内容: {e.response.text}")
                    
                    if attempt < max_retries - 1:
                        self.logger.info(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                    else:
                        self.logger.error(f"已达到最大重试次数 ({max_retries})，上传失败")
                        return None
        
        except Exception as e:
            self.logger.error(f"媒体上传失败: {e}")
            return None
    
    def _get_content_type(self, filename):
        """根据文件名获取内容类型"""
        ext = os.path.splitext(filename)[1].lower()
        
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        
        return content_types.get(ext, 'application/octet-stream')