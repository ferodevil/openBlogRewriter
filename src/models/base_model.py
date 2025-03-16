from abc import ABC, abstractmethod
import yaml
import os
import logging
from src.utils.path_utils import get_config_path

class BaseModel(ABC):
    """Base class for large language models, defining common methods and interfaces"""
    
    def __init__(self, model_name, config_path=None):
        """Initialize the model"""
        self.prompts = self._load_prompts()
        self.model_name = model_name
        self.config = self._load_config(config_path)
        self.model_config = self.config.get('models', {}).get(model_name, {})
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self, config_path=None):
        """Load configuration file"""
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
    
    def _load_prompts(self, config_path=None):
        """Load prompt templates from prompts.yaml"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(get_config_path()), 'prompts.yaml')
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load prompts: {e}")
            return {}

    def _get_prompt_template(self, prompt_key):
        """Get base prompt template by key from prompts.yaml
        
        This method returns the base prompt template. Subclasses can override this method
        to provide model-specific prompts by implementing their own logic.
        """
        try:
            return self.prompts.get('base_prompts', {}).get(prompt_key, '')
        except Exception as e:
            self.logger.error(f"Failed to get prompt template: {e}")
            return ''

    def generate_seo_title(self, content, metadata=None):
        """Generate SEO-friendly title"""
        if content is None:
            self.logger.error("内容为空，无法生成SEO标题")
            return None
            
        title = metadata.get('title', '') if metadata else ''
        prompt_template = self._get_prompt_template('generate_seo_title')
        formatted_prompt = prompt_template.format(
            content=content[:500],  # Use first 500 characters only
            title=title
        )
        
        return self.rewrite_content(content, metadata, formatted_prompt)
    
    def generate_seo_description(self, content, metadata=None):
        """Generate SEO-friendly description"""
        description = metadata.get('description', '') if metadata else ''
        prompt_template = self._get_prompt_template('generate_seo_description')
        formatted_prompt = prompt_template.format(
            content=content[:1000],  # Use first 1000 characters only
            description=description
        )
        
        return self.rewrite_content(content, metadata, formatted_prompt)
    
    # 在现有方法之后添加以下方法
    
    def optimize_content(self, content, optimization_prompt):
        """Optimize content based on SEO suggestions"""
        # 这是一个基类方法，应该在子类中实现
        raise NotImplementedError("子类必须实现此方法")
    
    def optimize_title(self, title, title_suggestions):
        """Optimize title based on SEO suggestions"""
        prompt_template = self._get_prompt_template('optimize_title')
        prompt = prompt_template.format(
            title=title,
            suggestions=', '.join(title_suggestions) if title_suggestions else 'None'
        )
        
        # 这是一个基类方法，应该在子类中实现
        raise NotImplementedError("子类必须实现此方法")
    
    def optimize_description(self, description, description_suggestions):
        """Optimize description based on SEO suggestions"""
        prompt_template = self._get_prompt_template('optimize_description')
        prompt = prompt_template.format(
            description=description,
            suggestions=', '.join(description_suggestions) if description_suggestions else '无'
        )
        
        # 这是一个基类方法，应该在子类中实现
        raise NotImplementedError("子类必须实现此方法")