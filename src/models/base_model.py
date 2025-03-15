from abc import ABC, abstractmethod
import yaml
import os
import logging
from src.utils.path_utils import get_config_path

class BaseModel(ABC):
    """大模型基类，定义大模型的通用方法和接口"""
    
    def __init__(self, model_name, config_path=None):
        """初始化模型"""
        self.model_name = model_name
        self.config = self._load_config(config_path)
        self.model_config = self.config.get('models', {}).get(model_name, {})
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
    
    @abstractmethod
    def rewrite_content(self, content, metadata=None, prompt=None):
        """重写内容，子类必须实现此方法"""
        pass
    
    def generate_seo_title(self, content, metadata=None):
        """生成SEO友好的标题"""
        prompt = """
        请为以下内容生成一个SEO友好的标题。标题应该:
        1. 包含主要关键词
        2. 吸引人点击
        3. 不超过60个字符
        4. 清晰表达文章主题
        
        内容摘要:
        {content}
        
        原标题(如果有):
        {title}
        
        请直接返回标题，不要包含任何解释或其他文字。
        """
        
        title = metadata.get('title', '') if metadata else ''
        formatted_prompt = prompt.format(
            content=content[:500],  # 只使用内容的前500个字符
            title=title
        )
        
        return self.rewrite_content(content, metadata, formatted_prompt)
    
    def generate_seo_description(self, content, metadata=None):
        """生成SEO友好的描述"""
        prompt = """
        请为以下内容生成一个SEO友好的元描述。描述应该:
        1. 包含主要关键词
        2. 吸引人点击
        3. 不超过160个字符
        4. 简洁地总结文章内容
        
        内容摘要:
        {content}
        
        原描述(如果有):
        {description}
        
        请直接返回描述，不要包含任何解释或其他文字。
        """
        
        description = metadata.get('description', '') if metadata else ''
        formatted_prompt = prompt.format(
            content=content[:1000],  # 只使用内容的前1000个字符
            description=description
        )
        
        return self.rewrite_content(content, metadata, formatted_prompt)
    
    # 在现有方法之后添加以下方法
    
    def optimize_content(self, content, optimization_prompt):
        """根据SEO建议优化内容"""
        # 这是一个基类方法，应该在子类中实现
        raise NotImplementedError("子类必须实现此方法")
    
    def optimize_title(self, title, title_suggestions):
        """根据SEO建议优化标题"""
        prompt = f"""
        请根据以下SEO建议优化文章标题:
        
        当前标题: {title}
        
        优化建议:
        {', '.join(title_suggestions) if title_suggestions else '无'}
        
        请直接返回优化后的标题，不要包含任何解释或其他文字。
        """
        
        # 这是一个基类方法，应该在子类中实现
        raise NotImplementedError("子类必须实现此方法")
    
    def optimize_description(self, description, description_suggestions):
        """根据SEO建议优化描述"""
        prompt = f"""
        请根据以下SEO建议优化文章描述:
        
        当前描述: {description}
        
        优化建议:
        {', '.join(description_suggestions) if description_suggestions else '无'}
        
        请直接返回优化后的描述，不要包含任何解释或其他文字。
        """
        
        # 这是一个基类方法，应该在子类中实现
        raise NotImplementedError("子类必须实现此方法")