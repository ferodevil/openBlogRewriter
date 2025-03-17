import os
import requests
import logging
import uuid
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from io import BytesIO
from urllib.parse import urlparse, urljoin
from src.utils.file_handler import FileHandler
from src.utils.path_utils import get_base_dir
from src.models.model_factory import ModelFactory

class ImageProcessor:
    """图片处理工具，用于下载、保存和处理图片"""
    
    def __init__(self, config_path=None):
        """初始化图片处理器"""
        self.file_handler = FileHandler()
        self.config = self.file_handler._load_config(config_path)
        self.image_config = self.config.get('image_processing', {})
        
        # 图片保存目录
        self.save_dir = self.image_config.get('save_dir', './config/data/images')
        if not os.path.isabs(self.save_dir):
            base_dir = get_base_dir()
            self.save_dir = os.path.join(base_dir, self.save_dir.lstrip('./'))
        
        # 确保目录存在
        os.makedirs(self.save_dir, exist_ok=True)
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def download_image(self, image_url, base_url=None):
        """下载图片
        
        Args:
            image_url (str): 图片URL
            base_url (str, optional): 基础URL，用于处理相对路径
            
        Returns:
            tuple: (图片内容, 图片文件名, 保存路径)
        """
        try:
            # 处理以双斜杠开头的URL
            if image_url.startswith('//'):
                image_url = f'https:{image_url}'
            
            # 跳过数据URI和空白SVG占位符
            if (image_url.startswith('data:') or 
                '<svg' in image_url or 
                '%3Csvg' in image_url):
                self.logger.warning(f"跳过无效的图片URL: {image_url}")
                return None, None, None
            
            # 处理相对路径
            if base_url and not urlparse(image_url).netloc:
                image_url = urljoin(base_url, image_url)
            
            # 清理URL中的参数和版本信息
            parsed_url = urlparse(image_url)
            clean_path = parsed_url.path
            
            # 验证URL格式
            if not parsed_url.scheme or not parsed_url.netloc:
                self.logger.warning(f"无效的URL格式: {image_url}")
                return None, None, None
            
            # 获取文件名
            filename = os.path.basename(clean_path)
            
            # 检查文件是否已存在
            save_path = os.path.join(self.save_dir, filename)
            if os.path.exists(save_path):
                self.logger.info(f"图片已存在: {save_path}")
                with open(save_path, 'rb') as f:
                    return f.read(), filename, save_path
                
            # 下载图片
            response = requests.get(image_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 检测图片格式
            content_type = response.headers.get('Content-Type', '')
            detected_ext = self._get_extension_from_content_type(content_type)
            
            # 如果文件名为空、没有扩展名或扩展名不匹配，使用检测到的扩展名
            if not filename or '.' not in filename or not self._is_valid_image_extension(filename):
                filename = f"image_{uuid.uuid4().hex}{detected_ext}"
                save_path = os.path.join(self.save_dir, filename)
            
            # 将图片内容保存到BytesIO对象
            image_content = BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                image_content.write(chunk)
            
            # 保存图片
            with open(save_path, 'wb') as f:
                f.write(image_content.getvalue())
            
            self.logger.info(f"图片已下载并保存到: {save_path}")
            return image_content.getvalue(), filename, save_path
        
        except Exception as e:
            self.logger.error(f"下载图片失败: {e}")
            return None, None, None
    
    def rewrite_image(self, image_path, model_name=None):
        """使用AI改写图片
        
        Args:
            image_path (str): 图片路径
            model_name (str, optional): 使用的模型名称
            
        Returns:
            str: 改写后的图片路径
        """
        # 如果未启用图片改写，直接返回原图片路径
        if not self.image_config.get('rewrite_images', False):
            return image_path
        
        try:
            # 获取活跃模型
            if model_name is None:
                model_name = self.config.get('models', {}).get('active_model', 'openai')
            
            # 这里可以实现调用AI模型改写图片的逻辑
            # 目前只是简单返回原图片路径，实际实现需要根据具体的AI模型API
            self.logger.info(f"图片改写功能尚未实现，返回原图片: {image_path}")
            return image_path
        
        except Exception as e:
            self.logger.error(f"改写图片失败: {e}")
            return image_path
    
    def extract_images_from_html(self, html_content, base_url):
        """从HTML内容中提取图片
        
        Args:
            html_content (str): HTML内容
            base_url (str): 基础URL
            
        Returns:
            list: 图片信息列表，每个元素为字典，包含原始URL和本地路径
        """
        from bs4 import BeautifulSoup
        import concurrent.futures
        import threading
        
        soup = BeautifulSoup(html_content, 'html.parser')
        images = []
        images_lock = threading.Lock()
        
        def process_image(img):
            src = img.get('src')
            if not src:
                return None
                
            # 下载图片
            _, filename, local_path = self.download_image(src, base_url)
            if not local_path:
                return None
                
            # 如果需要改写图片
            if self.image_config.get('rewrite_images', False):
                local_path = self.rewrite_image(local_path)
                
            # 构建图片信息
            image_info = {
                'original_url': src,
                'local_path': local_path,
                'filename': filename,
                'alt_text': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', '')
            }
            
            # 线程安全地添加到图片列表
            with images_lock:
                images.append(image_info)
            
            return image_info
        
        # 获取所有图片标签
        img_tags = soup.find_all('img')
        
        # 使用线程池并发下载图片
        max_workers = min(len(img_tags), self.image_config.get('max_concurrent_downloads', 5))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有下载任务
            futures = [executor.submit(process_image, img) for img in img_tags]
            
            # 等待所有任务完成
            concurrent.futures.wait(futures)
        
        return images
    
    def embed_images_in_content(self, content, images):
        """将图片嵌入到内容中
        
        Args:
            content (str): 文章内容
            images (list): 图片信息列表
            
        Returns:
            str: 嵌入图片后的内容
        """
        # 如果未启用图片嵌入或没有图片，直接返回原内容
        if not self.image_config.get('embed_images', True) or not images:
            return content
        
        # 限制图片数量，最多使用5张图片
        max_images = self.image_config.get('max_images', 5)
        if len(images) > max_images:
            self.logger.info(f"图片数量超过限制，将只使用前 {max_images} 张图片")
            images = images[:max_images]
        
        # 检查内容中是否有[IMAGE]标记
        if '[IMAGE]' in content:
            # 如果有[IMAGE]标记，按顺序替换为图片
            image_index = 0
            lines = content.split('\n')
            result_lines = []
            
            for line in lines:
                if '[IMAGE]' in line and image_index < len(images):
                    # 替换[IMAGE]标记为图片引用
                    img = images[image_index]
                    alt_text = img.get('alt_text', '')
                    title = img.get('title', '')
                    caption = alt_text or title or f"图片{image_index+1}"
                    
                    # 使用相对路径
                    relative_path = os.path.relpath(img['local_path'], os.path.dirname(self.save_dir))
                    relative_path = relative_path.replace('\\', '/')
                    
                    # 添加图片引用，包含标题和尺寸信息
                    width = img.get('width', '')
                    height = img.get('height', '')
                    size_info = f" ({width}x{height})" if width and height else ""
                    
                    image_reference = f"![{caption}]({relative_path} \"{caption}{size_info}\")"
                    
                    # 替换标记
                    line = line.replace('[IMAGE]', image_reference)
                    image_index += 1
                
                result_lines.append(line)
            
            return '\n'.join(result_lines)
        else:
            # 如果没有[IMAGE]标记，智能插入图片
            # 将内容分段
            paragraphs = content.split('\n\n')
            result_paragraphs = []
            
            # 计算图片应该插入的位置
            total_paragraphs = len(paragraphs)
            if total_paragraphs <= 1:
                # 如果内容太少，直接在末尾添加图片
                result_paragraphs = paragraphs
                image_positions = [0]  # 在末尾添加所有图片
            else:
                # 确保图片均匀分布在文章中
                result_paragraphs = paragraphs
                
                # 跳过第一段（通常是标题或介绍）
                usable_paragraphs = max(1, total_paragraphs - 1)
                
                # 计算图片插入位置
                image_positions = []
                if len(images) == 1:
                    # 如果只有一张图片，放在文章1/3处
                    image_positions = [max(1, total_paragraphs // 3)]
                elif len(images) == 2:
                    # 如果有两张图片，分别放在1/3和2/3处
                    image_positions = [max(1, total_paragraphs // 3), max(2, 2 * total_paragraphs // 3)]
                else:
                    # 如果有多张图片，均匀分布
                    step = max(1, usable_paragraphs // (len(images) + 1))
                    image_positions = [min(total_paragraphs - 1, 1 + i * step) for i in range(len(images))]
            
            # 插入图片
            result = []
            for i, para in enumerate(result_paragraphs):
                result.append(para)
                
                # 检查是否需要在此处插入图片
                if i in image_positions:
                    img_index = image_positions.index(i)
                    if img_index < len(images):
                        img = images[img_index]
                        alt_text = img.get('alt_text', '')
                        title = img.get('title', '')
                        caption = alt_text or title or f"图片{img_index+1}"
                        
                        # 使用相对路径
                        relative_path = os.path.relpath(img['local_path'], os.path.dirname(self.save_dir))
                        relative_path = relative_path.replace('\\', '/')
                        
                        # 添加图片引用，包含标题和尺寸信息
                        width = img.get('width', '')
                        height = img.get('height', '')
                        size_info = f" ({width}x{height})" if width and height else ""
                        
                        result.append(f"![{caption}]({relative_path} \"{caption}{size_info}\")")
            
            # 如果所有图片都未插入（可能是因为image_positions为空），则在末尾添加
            inserted_images = len([pos for pos in image_positions if pos < len(result_paragraphs)])
            if inserted_images < len(images):
                for i in range(inserted_images, len(images)):
                    img = images[i]
                    alt_text = img.get('alt_text', '')
                    title = img.get('title', '')
                    caption = alt_text or title or f"图片{i+1}"
                    
                    # 使用相对路径
                    relative_path = os.path.relpath(img['local_path'], os.path.dirname(self.save_dir))
                    relative_path = relative_path.replace('\\', '/')
                    
                    # 添加图片引用，包含标题和尺寸信息
                    width = img.get('width', '')
                    height = img.get('height', '')
                    size_info = f" ({width}x{height})" if width and height else ""
                    
                    result.append(f"![{caption}]({relative_path} \"{caption}{size_info}\")")
            
            return '\n\n'.join(result)
    
    def _get_extension_from_content_type(self, content_type):
        """根据Content-Type获取文件扩展名"""
        content_type = content_type.lower()
        if 'jpeg' in content_type or 'jpg' in content_type:
            return '.jpg'
        elif 'png' in content_type:
            return '.png'
        elif 'gif' in content_type:
            return '.gif'
        elif 'webp' in content_type:
            return '.webp'
        elif 'svg' in content_type:
            return '.svg'
        elif 'bmp' in content_type:
            return '.bmp'
        elif 'tiff' in content_type:
            return '.tiff'
        else:
            # 尝试从二进制数据中检测图片格式
            return '.jpg'  # 默认使用jpg扩展名
            
    def download_images_parallel(self, image_urls, max_workers=5):
        """并行下载多个图片
        
        Args:
            image_urls (list): 图片URL列表，每个元素为(url, base_url)元组
            max_workers (int): 最大线程数
            
        Returns:
            list: 下载结果列表，每个元素为(content, filename, local_path)元组
        """
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有下载任务
            future_to_url = {executor.submit(self.download_image, url, base_url): (url, base_url)
                           for url, base_url in image_urls}
            
            # 获取下载结果
            for future in as_completed(future_to_url):
                url, base_url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"下载图片失败 {url}: {e}")
                    results.append((None, None, None))
        
        return results

    def _is_valid_image_extension(self, filename):
        """检查文件扩展名是否为有效的图片格式"""
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        ext = os.path.splitext(filename)[1].lower()
        return ext in valid_extensions