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
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
                    
                    response = requests.post(url, headers=headers, data=json.dumps(payload))
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
        """生成重写提示"""
        title = metadata.get('title', '') if metadata else ''
        keywords = metadata.get('keywords', '') if metadata else ''
        
        prompt = f"""
        请改写以下博客文章，使其更加生动有趣，同时保持专业性和SEO友好。
        
        要求：
        1. 保持原文的主要观点和信息
        2. 使用更吸引人的标题和开头
        3. 增加生动的例子和比喻
        4. 使用更多的小标题和列表，提高可读性
        5. 确保文章包含以下关键词：{keywords}
        6. 文章应该符合SEO要求，包括适当的关键词密度
        7. 文章应该有清晰的结构：引言、主体和结论
        8. 增加一些号召性用语(CTA)
        9. 总字数不少于原文
        
        原文标题：{title}
        
        原文内容：
        {content}
        
        请直接返回改写后的完整文章，包括标题。
        """
        
        return prompt
    
    def generate_seo_title(self, content, metadata=None):
        """生成SEO友好的标题"""
        title = metadata.get('title', '') if metadata else ''
        keywords = metadata.get('keywords', '') if metadata else ''
        
        prompt = f"""
        请为以下博客文章生成一个SEO友好的标题。
        
        要求：
        1. 标题应该包含主要关键词
        2. 标题应该吸引人，引起读者兴趣
        3. 标题长度应该在60个字符以内
        4. 标题应该清晰地表达文章的主题
        
        原文标题：{title}
        关键词：{keywords}
        
        文章内容：
        {content[:500]}...
        
        请直接返回生成的标题，不要包含任何其他内容。
        """
        
        try:
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "temperature": 0.7,
                "max_tokens": 100
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
        
        except Exception as e:
            self.logger.error(f"生成SEO标题失败: {e}")
            return title
    
    def generate_seo_description(self, content, metadata=None):
        """生成SEO友好的描述"""
        description = metadata.get('description', '') if metadata else ''
        keywords = metadata.get('keywords', '') if metadata else ''
        
        prompt = f"""
        请为以下博客文章生成一个SEO友好的元描述。
        
        要求：
        1. 描述应该包含主要关键词
        2. 描述应该简洁明了，概括文章的主要内容
        3. 描述长度应该在150-160个字符之间
        4. 描述应该吸引人，引起读者兴趣
        
        原文描述：{description}
        关键词：{keywords}
        
        文章内容：
        {content[:500]}...
        
        请直接返回生成的元描述，不要包含任何其他内容。
        """
        
        try:
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "temperature": 0.7,
                "max_tokens": 200
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
        
        except Exception as e:
            self.logger.error(f"生成SEO描述失败: {e}")
            return description