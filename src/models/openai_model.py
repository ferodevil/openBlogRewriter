from src.models.base_model import BaseModel
import openai
import time

class OpenAIModel(BaseModel):
    """OpenAI模型接口"""
    
    def __init__(self, config_path=None):
        """初始化OpenAI模型"""
        super().__init__('openai', config_path)
        
        # 设置API密钥
        openai.api_key = self.model_config.get('api_key', '')
        
        # 获取模型配置
        self.model = self.model_config.get('model', 'gpt-4')
        self.temperature = self.model_config.get('temperature', 0.7)
        self.max_tokens = self.model_config.get('max_tokens', 2000)
    
    def rewrite_content(self, content, metadata=None, prompt=None):
        """使用OpenAI模型重写内容"""
        if not prompt:
            prompt = self._generate_rewrite_prompt(content, metadata)
        
        try:
            # 重试机制
            max_retries = 3
            retry_delay = 5
            
            for attempt in range(max_retries):
                try:
                    response = openai.ChatCompletion.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "你是一位专业的内容创作者，擅长改写文章使其更加生动有趣，同时保持专业性和SEO友好。"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )
                    
                    return response.choices[0].message.content.strip()
                
                except (openai.error.RateLimitError, openai.error.APIError, openai.error.ServiceUnavailableError) as e:
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

    def optimize_content(self, content, optimization_prompt):
        """根据SEO建议优化内容"""
        # 使用OpenAI API优化内容
        try:
            response = self.client.chat.completions.create(
                model=self.model_config.get('model', 'gpt-3.5-turbo'),
                messages=[
                    {"role": "system", "content": "你是一位SEO专家，擅长优化文章内容以提高搜索引擎排名。"},
                    {"role": "user", "content": optimization_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            optimized_content = response.choices[0].message.content.strip()
            return optimized_content
        
        except Exception as e:
            self.logger.error(f"内容优化失败: {e}")
            return content  # 如果失败，返回原始内容
    
    def optimize_title(self, title, title_suggestions):
        """根据SEO建议优化标题"""
        if not title_suggestions:
            return title
        
        prompt = f"""
        请根据以下SEO建议优化文章标题:
        
        当前标题: {title}
        
        优化建议:
        {', '.join(title_suggestions)}
        
        请直接返回优化后的标题，不要包含任何解释或其他文字。
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_config.get('model', 'gpt-3.5-turbo'),
                messages=[
                    {"role": "system", "content": "你是一位SEO专家，擅长优化文章标题以提高搜索引擎排名。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            optimized_title = response.choices[0].message.content.strip()
            return optimized_title
        
        except Exception as e:
            self.logger.error(f"标题优化失败: {e}")
            return title  # 如果失败，返回原始标题
    
    def optimize_description(self, description, description_suggestions):
        """根据SEO建议优化描述"""
        if not description_suggestions:
            return description
        
        prompt = f"""
        请根据以下SEO建议优化文章描述:
        
        当前描述: {description}
        
        优化建议:
        {', '.join(description_suggestions)}
        
        请直接返回优化后的描述，不要包含任何解释或其他文字。
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_config.get('model', 'gpt-3.5-turbo'),
                messages=[
                    {"role": "system", "content": "你是一位SEO专家，擅长优化文章描述以提高搜索引擎排名。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            optimized_description = response.choices[0].message.content.strip()
            return optimized_description
        
        except Exception as e:
            self.logger.error(f"描述优化失败: {e}")
            return description  # 如果失败，返回原始描述