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
        # 与其他模型使用相同的提示格式
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