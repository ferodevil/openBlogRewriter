import os
import json
import yaml
import logging
from datetime import datetime
from src.utils.path_utils import get_base_dir, get_data_dir

class FileHandler:
    """文件处理工具，用于保存和加载数据"""
    
    def __init__(self, base_dir=None):
        """初始化文件处理器"""
        if base_dir is None:
            self.base_dir = get_data_dir()
        else:
            self.base_dir = base_dir
        
        # 确保目录存在
        os.makedirs(self.base_dir, exist_ok=True)
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def save_content(self, content, filename=None, subfolder=None, file_format='md'):
        """保存内容到文件
        
        Args:
            content (str): 要保存的内容
            filename (str, optional): 文件名。如果为None，将使用时间戳生成
            subfolder (str, optional): 子文件夹名。如果为None，将保存到基础目录
            file_format (str, optional): 文件格式，默认为'md'(Markdown)，也可以是'txt'等
            
        Returns:
            str: 保存的文件路径，如果保存失败则返回None
        """
        try:
            # 确定保存路径
            if subfolder:
                save_dir = os.path.join(self.base_dir, subfolder)
                os.makedirs(save_dir, exist_ok=True)
            else:
                save_dir = self.base_dir
            
            # 如果没有提供文件名，使用时间戳生成
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"content_{timestamp}.{file_format}"
            
            # 确保文件名有扩展名
            if not os.path.splitext(filename)[1]:
                filename += f'.{file_format}'
            
            # 完整文件路径
            file_path = os.path.join(save_dir, filename)
            
            # 保存内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"内容已保存到: {file_path}")
            return file_path
        
        except Exception as e:
            self.logger.error(f"保存内容失败: {e}")
            return None
    
    def _load_config(self, config_path=None):
        """加载配置文件"""
        from src.utils.path_utils import get_config_path
        
        if config_path is None:
            config_path = get_config_path()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def save_json(self, data, filename=None, subfolder=None):
        """保存JSON数据到文件"""
        try:
            # 确定保存路径
            if subfolder:
                save_dir = os.path.join(self.base_dir, subfolder)
                os.makedirs(save_dir, exist_ok=True)
            else:
                save_dir = self.base_dir
            
            # 如果没有提供文件名，使用时间戳生成
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"data_{timestamp}.json"
            
            # 确保文件名有扩展名
            if not os.path.splitext(filename)[1]:
                filename += '.json'
            
            # 完整文件路径
            file_path = os.path.join(save_dir, filename)
            
            # 保存内容
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"JSON数据已保存到: {file_path}")
            return file_path
        
        except Exception as e:
            self.logger.error(f"保存JSON数据失败: {e}")
            return None
    
    def load_content(self, file_path):
        """从文件加载内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"加载内容失败: {e}")
            return None
    
    def load_json(self, file_path):
        """从文件加载JSON数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载JSON数据失败: {e}")
            return None