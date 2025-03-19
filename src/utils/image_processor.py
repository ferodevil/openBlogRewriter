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
import re

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
        """将图片嵌入到内容中，替换[IMAGE]标记为实际的Markdown图片引用
        
        Args:
            content (str): 包含[IMAGE]标记的内容
            images (list): 图片信息列表，每个元素应包含 path 和可选的 alt_text
            
        Returns:
            str: 嵌入实际图片后的内容
        """
        if not images:
            return content
        
        # 首先检查图片分布是否合理
        is_distribution_good, distribution_message = self.check_image_distribution(content, len(images))
        if not is_distribution_good:
            self.logger.warning(f"图片分布检查: {distribution_message}")
            # 如果图片分布不合理，重新分配图片位置
            content = self.redistribute_images(content, len(images))
        
        # 计算有多少[IMAGE]标记
        image_count = content.count('[IMAGE]')
        
        # 确保图片数量与标记数量匹配
        if image_count != len(images):
            self.logger.warning(f"图片标记数量({image_count})与实际图片数量({len(images)})不匹配")
            if image_count < len(images):
                # 如果标记少于图片，添加额外的标记
                content = self.redistribute_images(content, len(images))
        
        # 替换[IMAGE]标记为实际图片链接
        image_index = 0
        parts = []
        remaining = content
        
        while '[IMAGE]' in remaining and image_index < len(images):
            # 分割文本
            before, after = remaining.split('[IMAGE]', 1)
            parts.append(before)
            
            # 获取当前图片信息
            image = images[image_index]
            image_path = image.get('local_path', '')
            alt_text = image.get('alt_text', f'图片{image_index+1}')
            
            # 生成Markdown图片引用
            # 使用相对路径并处理路径分隔符
            if image_path:
                image_path = image_path.replace('\\', '/')
                # 添加实际图片引用
                parts.append(f"\n\n![{alt_text}]({image_path})\n\n")
            else:
                # 如果没有图片路径，保留标记
                parts.append('[IMAGE]')
            
            remaining = after
            image_index += 1
        
        # 添加剩余部分
        parts.append(remaining)
        
        # 合并所有部分
        return ''.join(parts)
    
    def redistribute_images(self, content, number_of_images):
        """重新分配图片位置，使其更适合Markdown格式
        
        Args:
            content (str): 原始内容
            number_of_images (int): 图片数量
        
        Returns:
            str: 重新分配图片位置后的内容
        """
        # 移除现有的[IMAGE]标记
        content_without_images = content.replace('[IMAGE]', '')
        
        # 使用更好的Markdown分块方法
        blocks = self._split_markdown_blocks(content_without_images)
        
        if not blocks:
            return content
        
        # 计算最佳图片插入位置，避开标题和不适合插入图片的位置
        suitable_positions = []
        for i, block in enumerate(blocks):
            # 跳过标题和代码块等不适合插入图片的位置
            if not block.startswith('#') and not block.startswith('```') and len(block.strip()) > 20:
                suitable_positions.append(i)
        
        # 如果没有合适的位置，使用所有位置
        if not suitable_positions:
            suitable_positions = list(range(len(blocks)))
        
        # 计算均匀间隔
        image_positions = []
        if number_of_images == 1 and suitable_positions:
            # 如果只有一张图片，放在中间位置
            middle_index = len(suitable_positions) // 2
            image_positions = [suitable_positions[middle_index]]
        elif number_of_images == 2 and len(suitable_positions) >= 2:
            # 如果有两张图片，分别放在1/3和2/3处
            first_pos = suitable_positions[len(suitable_positions) // 3]
            second_pos = suitable_positions[2 * len(suitable_positions) // 3]
            image_positions = [first_pos, second_pos]
        elif suitable_positions:
            # 如果有多张图片，均匀分布
            step = max(1, len(suitable_positions) // (number_of_images + 1))
            indices = [min(len(suitable_positions) - 1, i * step) for i in range(1, number_of_images + 1)]
            image_positions = [suitable_positions[i] for i in indices]
        
        # 确保不重复
        image_positions = sorted(list(set(image_positions)))
        
        # 如果计算出的位置不够，添加更多位置
        while len(image_positions) < number_of_images and suitable_positions:
            # 找出间隔最大的地方插入新位置
            if len(image_positions) >= 2:
                # 找出最大间隔
                max_gap = 0
                insert_at = 0
                for i in range(len(image_positions) - 1):
                    gap = image_positions[i+1] - image_positions[i]
                    if gap > max_gap:
                        max_gap = gap
                        insert_at = (image_positions[i] + image_positions[i+1]) // 2
            
                if insert_at not in image_positions:
                    image_positions.append(insert_at)
            else:
                # 如果只有一个位置，在开始或结束添加
                if 0 not in image_positions and suitable_positions[0] not in image_positions:
                    image_positions.append(suitable_positions[0])
                elif suitable_positions[-1] not in image_positions:
                    image_positions.append(suitable_positions[-1])
            
            # 确保不重复并排序
            image_positions = sorted(list(set(image_positions)))
        
        # 截断到所需图片数
        image_positions = image_positions[:number_of_images]
        
        # 插入图片标记
        result = []
        for i, block in enumerate(blocks):
            result.append(block)
            if i in image_positions:
                result.append('[IMAGE]')
        
        return '\n\n'.join(result)
    
    def _split_markdown_blocks(self, content):
        """更智能地分割Markdown内容为逻辑块
        
        考虑Markdown特殊格式如标题、列表等
        """
        # 首先按照空行分割
        raw_paragraphs = re.split(r'\n\s*\n', content)
        paragraphs = []
        
        for para in raw_paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 检查是否是标题行
            if re.match(r'^#{1,6}\s+', para):
                paragraphs.append(para)
                continue
            
            # 检查是否是列表
            if re.match(r'^[-*+]\s+', para) or re.match(r'^\d+\.\s+', para):
                # 处理列表项
                list_items = re.split(r'\n(?=[-*+]\s+|\d+\.\s+)', para)
                for item in list_items:
                    if item.strip():
                        paragraphs.append(item)
                continue
            
            # 检查是否是代码块
            if para.startswith('```') and para.endswith('```'):
                paragraphs.append(para)
                continue
            
            # 其他普通段落
            paragraphs.append(para)
        
        return paragraphs
    
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

    def check_image_distribution(self, content, number_of_images):
        """检查图片标记在内容中的分布是否合理"""
        # 使用更适合Markdown的段落分割方法
        paragraphs = self._split_markdown_blocks(content)
        
        image_positions = []
        for i, para in enumerate(paragraphs):
            if '[IMAGE]' in para:
                image_positions.append(i)
        
        # 检查图片是否过度集中
        if len(image_positions) > 1:
            avg_distance = len(paragraphs) / (len(image_positions) + 1)
            actual_distances = []
            last_pos = -1
            for pos in image_positions:
                if last_pos >= 0:
                    actual_distances.append(pos - last_pos)
                last_pos = pos
            
            # 如果实际距离变异过大，说明分布不均
            if actual_distances and max(actual_distances) > avg_distance * 2:
                return False, "图片分布不均匀，建议更平均地分布图片"
        
        return True, "图片分布合理"