from src.models.base_model import BaseModel
import requests
import json
import time
import logging

class OllamaModel(BaseModel):
    """Ollama本地模型接口"""
    
    def __init__(self, config_path=None):
        """初始化Ollama模型"""
        super().__init__('ollama', config_path)
        
        # 获取模型配置
        self.base_url = self.model_config.get('base_url', 'http://localhost:11434')
        self.model = self.model_config.get('model', 'llama2')
        self.temperature = self.model_config.get('temperature', 0.7)
        self.max_tokens = self.model_config.get('max_tokens', 2000)
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def rewrite_content(self, content, metadata=None, prompt=None):
        """使用Ollama模型重写内容"""
        if not prompt:
            prompt = self._generate_rewrite_prompt(content, metadata)
        
        try:
            # 重试机制
            max_retries = 3
            retry_delay = 5
            
            for attempt in range(max_retries):
                try:
                    url = f"{self.base_url}/api/generate"
                    
                    payload = {
                        "model": self.model,
                        "prompt": prompt,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens
                    }
                    
                    headers = {
                        "Content-Type": "application/json"
                    }
                    
                    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=360)
                    response.raise_for_status()
                    
                    result = response.json()
                    return result.get("response", "")
                
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"API调用失败，正在重试 ({attempt+1}/{max_retries}): {e}")
                        time.sleep(retry_delay)
                    else:
                        raise
        
        except Exception as e:
            self.logger.error(f"内容重写失败: {e}")
            return None
    
    def _generate_rewrite_prompt(self, content, metadata=None):
        """Generate rewrite prompt from config"""
        title = metadata.get('title', '') if metadata else ''
        keywords = metadata.get('keywords', '') if metadata else ''
        
        prompt_template = self._get_prompt_template('rewrite_user')
        prompt = prompt_template.format(
            title=title,
            keywords=keywords,
            content=content
        )
        
        return prompt
    
    def generate_seo_title(self, content, metadata=None):
        """生成SEO友好的标题"""
        return super().generate_seo_title(content, metadata)
    
    def generate_seo_description(self, content, metadata=None):
        """生成SEO友好的描述"""
        return super().generate_seo_description(content, metadata)
    
    def _get_prompt_template(self, prompt_key):
        """Get prompt template by key from prompts.yaml
        
        First try to get model-specific prompt from model_specific_prompts,
        if not found, fallback to base prompt from base_prompts.
        """
        try:
            # Try to get model-specific prompt first
            model_specific = self.prompts.get('model_specific_prompts', {}).get('ollama', {}).get(prompt_key)
            if model_specific:
                return model_specific
            
            # Fallback to base prompt
            return super()._get_prompt_template(prompt_key)
        except Exception as e:
            self.logger.error(f"Failed to get prompt template: {e}")
            return ''
            
    def optimize_content(self, content, optimization_prompt):
        """根据SEO建议优化内容"""
        try:
            # 重试机制
            max_retries = 3
            retry_delay = 5
            
            for attempt in range(max_retries):
                try:
                    url = f"{self.base_url}/api/generate"
                    
                    payload = {
                        "model": self.model,
                        "prompt": optimization_prompt,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens
                    }
                    
                    headers = {
                        "Content-Type": "application/json"
                    }
                    
                    response = requests.post(url, headers=headers, data=json.dumps(payload))
                    response.raise_for_status()
                    
                    result = response.json()
                    return result.get("response", content)
                
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"API调用失败，正在重试 ({attempt+1}/{max_retries}): {e}")
                        time.sleep(retry_delay)
                    else:
                        raise
        
        except Exception as e:
            self.logger.error(f"内容优化失败: {e}")
            return content  # 如果失败，返回原始内容
    
    def optimize_title(self, title, title_suggestions):
        """根据SEO建议优化标题"""
        if not title_suggestions:
            return title
        
        prompt_template = self._get_prompt_template('optimize_title')
        prompt = prompt_template.format(
            title=title,
            suggestions=', '.join(title_suggestions)
        )
        
        try:
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "temperature": self.temperature,
                "max_tokens": 100
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", title)
        
        except Exception as e:
            self.logger.error(f"标题优化失败: {e}")
            return title  # 如果失败，返回原始标题
    
    def optimize_description(self, description, description_suggestions):
        """根据SEO建议优化描述"""
        if not description_suggestions:
            return description
        
        prompt_template = self._get_prompt_template('optimize_description')
        prompt = prompt_template.format(
            description=description,
            suggestions=', '.join(description_suggestions)
        )
        
        try:
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "temperature": self.temperature,
                "max_tokens": 200
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", description)
        
        except Exception as e:
            self.logger.error(f"描述优化失败: {e}")
            return description  # 如果失败，返回原始描述
