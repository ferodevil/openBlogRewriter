from src.models.base_model import BaseModel
import anthropic
import time

class AnthropicModel(BaseModel):
    """Anthropic Claude模型接口"""
    
    def __init__(self, config_path=None):
        """初始化Anthropic模型"""
        super().__init__('anthropic', config_path)
        
        # 设置API密钥
        self.client = anthropic.Client(api_key=self.model_config.get('api_key', ''))
        
        # 获取模型配置
        self.model = self.model_config.get('model', 'claude-2')
        self.temperature = self.model_config.get('temperature', 0.7)
        self.max_tokens = self.model_config.get('max_tokens', 2000)
    
    def rewrite_content(self, content, metadata=None, prompt=None):
        """使用Anthropic模型重写内容"""
        if not prompt:
            prompt = self._generate_rewrite_prompt(content, metadata)
        
        try:
            # 重试机制
            max_retries = 3
            retry_delay = 5
            
            for attempt in range(max_retries):
                try:
                    response = self.client.completion(
                        prompt=f"{anthropic.HUMAN_PROMPT} {prompt} {anthropic.AI_PROMPT}",
                        model=self.model,
                        max_tokens_to_sample=self.max_tokens,
                        temperature=self.temperature
                    )
                    
                    return response.completion.strip()
                
                except (anthropic.APIError, anthropic.APIConnectionError, anthropic.RateLimitError) as e:
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
        
        prompt_template = self._get_prompt_template('rewrite_user')
        prompt = prompt_template.format(
            title=title,
            keywords=keywords,
            content=content
        )
        
        return prompt
        
    def _get_prompt_template(self, prompt_key):
        """Get prompt template by key from prompts.yaml
        
        First try to get model-specific prompt from model_specific_prompts,
        if not found, fallback to base prompt from base_prompts.
        """
        try:
            # Try to get model-specific prompt first
            model_specific = self.prompts.get('model_specific_prompts', {}).get('anthropic', {}).get(prompt_key)
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
                    response = self.client.completion(
                        prompt=f"{anthropic.HUMAN_PROMPT} {optimization_prompt} {anthropic.AI_PROMPT}",
                        model=self.model,
                        max_tokens_to_sample=self.max_tokens,
                        temperature=self.temperature
                    )
                    
                    return response.completion.strip()
                
                except (anthropic.APIError, anthropic.APIConnectionError, anthropic.RateLimitError) as e:
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
            response = self.client.completion(
                prompt=f"{anthropic.HUMAN_PROMPT} {prompt} {anthropic.AI_PROMPT}",
                model=self.model,
                max_tokens_to_sample=100,
                temperature=self.temperature
            )
            
            optimized_title = response.completion.strip()
            return optimized_title
        
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
            response = self.client.completion(
                prompt=f"{anthropic.HUMAN_PROMPT} {prompt} {anthropic.AI_PROMPT}",
                model=self.model,
                max_tokens_to_sample=200,
                temperature=self.temperature
            )
            
            optimized_description = response.completion.strip()
            return optimized_description
        
        except Exception as e:
            self.logger.error(f"描述优化失败: {e}")
            return description  # 如果失败，返回原始描述