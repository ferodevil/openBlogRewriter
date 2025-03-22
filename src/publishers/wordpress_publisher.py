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
        
        # 获取基本配置
        self.api_url = self.wp_config.get('url', '')
        self.username = self.wp_config.get('username', '')
        self.app_password = self.wp_config.get('app_password', '')
        self.categories = self.wp_config.get('categories', [])
        self.tags = self.wp_config.get('tags', [])
        self.status = self.wp_config.get('status', 'draft')
        
        # 确保API URL格式正确
        if self.api_url and not self.api_url.endswith('/wp/v2'):
            if '/wp-json/' in self.api_url:
                self.api_url = f"{self.api_url.split('/wp-json/')[0]}/wp-json/wp/v2"
            else:
                self.api_url = f"{self.api_url.rstrip('/')}/wp-json/wp/v2"
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # 记录配置信息
        self.logger.info(f"WordPress发布器初始化，API URL: {self.api_url}")
    
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
        """获取认证头，使用应用程序密码"""
        credentials = f"{self.username}:{self.app_password}"
        token = base64.b64encode(credentials.encode()).decode()
        return {'Authorization': f'Basic {token}'}
    
    def _check_credentials(self):
        """检查认证凭据是否有效"""
        if not self.api_url or not self.username or not self.app_password:
            self.logger.error("WordPress认证信息不完整，请检查配置")
            return False
        
        # 尝试获取用户信息以验证凭据
        try:
            endpoint = f"{self.api_url.rstrip('/wp-json/wp/v2')}/wp-json/wp/v2/users/me"
            headers = self._get_auth_header()
            
            self.logger.debug(f"验证WordPress认证信息: {endpoint}")
            self.logger.debug(f"用户名: {self.username}")
            
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_info = response.json()
                self.logger.info(f"WordPress认证成功，用户: {user_info.get('name', self.username)}")
                return True
            else:
                self.logger.error(f"WordPress认证失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"WordPress认证检查失败: {e}")
            return False
    
    def publish_post(self, title, content, excerpt='', featured_media=0, meta=None, categories=None, tags=None, max_retries=3, retry_delay=5):
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
            'categories': categories if categories is not None else self.categories,
            'tags': tags if tags is not None else self.tags
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
        
        # 先检查认证信息
        if not self._check_credentials():
            self.logger.error("WordPress认证失败，无法上传媒体")
            return None
            
        # 确保API URL格式正确
        if not self.api_url.endswith('/wp/v2'):
            if '/wp-json/' in self.api_url:
                self.api_url = f"{self.api_url.split('/wp-json/')[0]}/wp-json/wp/v2"
            else:
                self.api_url = f"{self.api_url.rstrip('/')}/wp-json/wp/v2"
            
            self.logger.info(f"已调整WordPress API URL: {self.api_url}")
        
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
    
    def get_categories(self):
        """获取WordPress站点的所有分类目录"""
        if not self.api_url:
            self.logger.error("WordPress API URL未配置")
            return []
        
        try:
            endpoint = f"{self.api_url}/categories"
            headers = self._get_auth_header()
            
            # 获取所有分类（每页100个）
            params = {
                'per_page': 100,
                'page': 1
            }
            
            all_categories = []
            while True:
                response = requests.get(endpoint, headers=headers, params=params)
                response.raise_for_status()
                
                categories = response.json()
                if not categories:
                    break
                    
                all_categories.extend(categories)
                
                # 检查是否有更多页
                if len(categories) < params['per_page']:
                    break
                    
                params['page'] += 1
            
            self.logger.info(f"成功获取WordPress分类目录，共{len(all_categories)}个分类")
            return all_categories
            
        except Exception as e:
            self.logger.error(f"获取WordPress分类目录失败: {e}")
            return []
    
    def get_tags(self):
        """获取WordPress站点的所有标签"""
        if not self.api_url:
            self.logger.error("WordPress API URL未配置")
            return []
        
        try:
            endpoint = f"{self.api_url}/tags"
            headers = self._get_auth_header()
            
            # 获取所有标签（每页100个）
            params = {
                'per_page': 100,
                'page': 1
            }
            
            all_tags = []
            while True:
                response = requests.get(endpoint, headers=headers, params=params)
                response.raise_for_status()
                
                tags = response.json()
                if not tags:
                    break
                    
                all_tags.extend(tags)
                
                # 检查是否有更多页
                if len(tags) < params['per_page']:
                    break
                    
                params['page'] += 1
            
            self.logger.info(f"成功获取WordPress标签，共{len(all_tags)}个标签")
            return all_tags
            
        except Exception as e:
            self.logger.error(f"获取WordPress标签失败: {e}")
            return []
    
    def auto_categorize(self, title, content, keywords=None):
        """根据博客内容自动选择合适的分类目录
        
        Args:
            title (str): 博客标题
            content (str): 博客内容
            keywords (list, optional): 博客关键词
            
        Returns:
            list: 分类ID列表
        """
        # 获取所有分类
        categories = self.get_categories()
        if not categories:
            self.logger.warning("无法获取分类目录，使用默认分类")
            return self.categories
        
        # 提取博客的关键信息
        blog_text = f"{title} {content[:1000]}"  # 使用标题和内容前1000个字符
        if keywords:
            blog_text += " " + " ".join(keywords)
        
        blog_text = blog_text.lower()
        
        # 计算每个分类的匹配分数
        category_scores = []
        for category in categories:
            score = 0
            cat_name = category.get('name', '').lower()
            cat_desc = category.get('description', '').lower()
            
            # 分类名称在标题中，加高分
            if cat_name in title.lower():
                score += 10
            
            # 分类名称在内容中出现的次数
            name_count = blog_text.count(cat_name)
            score += name_count * 2
            
            # 分类描述中的关键词在内容中出现
            if cat_desc:
                desc_words = [w for w in cat_desc.split() if len(w) > 3]
                for word in desc_words:
                    if word in blog_text:
                        score += 1
            
            category_scores.append({
                'id': category.get('id'),
                'name': category.get('name'),
                'score': score
            })
        
        # 按分数排序
        category_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # 选择得分最高的最多3个分类
        selected_categories = []
        for cat in category_scores[:3]:
            if cat['score'] > 0:
                selected_categories.append(cat)
                self.logger.info(f"自动选择分类: {cat['name']} (ID: {cat['id']}, 得分: {cat['score']})")
        
        # 如果没有匹配的分类，使用默认分类
        if not selected_categories:
            self.logger.warning("没有找到匹配的分类，使用默认分类")
            return self.categories
        
        return [cat['id'] for cat in selected_categories]
    
    def publish_post_with_images(self, title, content, images, excerpt='', meta=None, keywords=None, categories=None, tags=None, max_retries=3, retry_delay=5):
        """先上传图片，然后发布带有图片的文章
        
        Args:
            title (str): 文章标题
            content (str): 文章内容
            images (list): 图片信息列表，每个元素为字典，包含local_path和filename
            excerpt (str, optional): 文章摘要
            meta (dict, optional): 文章元数据
            keywords (list, optional): 关键词列表
            categories (list, optional): 分类ID列表
            tags (list, optional): 标签ID列表
            max_retries (int, optional): 最大重试次数
            retry_delay (int, optional): 重试延迟时间
            
        Returns:
            dict: 发布结果
        """
        if not self.api_url:
            self.logger.error("WordPress API URL未配置")
            return None
        
        # 上传图片并获取媒体ID
        uploaded_images = []
        featured_media_id = 0
        
        for i, img in enumerate(images):
            local_path = img.get('local_path')
            if not local_path or not os.path.exists(local_path):
                self.logger.warning(f"图片路径不存在: {local_path}")
                continue
                
            self.logger.info(f"上传图片 ({i+1}/{len(images)}): {local_path}")
            media_result = self.upload_media(local_path)
            
            if media_result:
                media_id = media_result.get('id')
                media_url = media_result.get('source_url')
                
                uploaded_images.append({
                    'media_id': media_id,
                    'media_url': media_url
                })
                
                # 将第一张图片设为特色图片
                if i == 0:
                    featured_media_id = media_id
        
        # 简化图片替换逻辑：直接用上传后的图片URL替换[IMAGE]标记
        updated_content = content
        for img in uploaded_images:
            media_url = img['media_url']
            # 替换第一个[IMAGE]标记
            if "[IMAGE]" in updated_content:
                # 构建Markdown格式的图片链接
                img_markdown = f"![图片]({media_url})"
                updated_content = updated_content.replace("[IMAGE]", img_markdown, 1)
            else:
                # 如果没有更多[IMAGE]标记，则忽略多余的图片
                self.logger.warning(f"内容中[IMAGE]标记数量少于图片数量，忽略多余的图片: {media_url}")
                break  # 跳出循环，不再处理剩余图片
        
        # 如果没有提供分类，则自动选择
        if categories is None:
            categories = self.auto_categorize(title, updated_content, keywords)
            self.logger.info(f"自动选择的分类: {categories}")
        
        # 发布带有更新后图片的文章
        self.logger.info(f"发布文章: {title}")
        return self.publish_post(
            title=title,
            content=updated_content,
            excerpt=excerpt,
            featured_media=featured_media_id,
            meta=meta,
            categories=categories,
            tags=tags,
            max_retries=max_retries,
            retry_delay=retry_delay
        )
