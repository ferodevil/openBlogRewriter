from src.models.base_model import BaseModel
import requests
import json
import time

class BaiduModel(BaseModel):
    """百度文心一言模型接口"""
    
    def __init__(self, config_path=None):
        """初始化百度模型"""
        super().__init__('baidu', config_path)
        
        # 设置API密钥
        self.api_key = self.model_config.get('api_key', '')
        self.secret_key = self.model_config.get('secret_key', '')
        
        # 获取模型配置
        self.temperature = self.model_config.get('temperature', 0.7)
        self.max_tokens = self.model_config.get('max_tokens', 2000)
        
        # 获取访问令牌
        self.access_token = self._get_access_token()
    
    def _get_access_token(self):
        """获取百度API访问令牌"""
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        try:
            response = requests.post(url, params=params)
            result = response.json()
            return result.get("access_token")
        except Exception as e:
            self.logger.error(f"获取百度访问令牌失败: {e}")
            return None
    
    def rewrite_content(self, content, metadata=None, prompt=None):
        """使用百度模型重写内容"""
        if not self.access_token:
            self.logger.error("百度访问令牌无效")
            return None
        
        if not prompt:
            prompt = self._generate_rewrite_prompt(content, metadata)
        
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={self.access_token}"
        
        payload = json.dumps({
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位专业的内容创作者，擅长改写文章使其更加生动有趣，同时保持专业性和SEO友好。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens
        })
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        try:
            # 重试机制
            max_retries = 3
            retry_delay = 5
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(url, headers=headers, data=payload)
                    result = response.json()
                    
                    if "result" in result:
                        return result["result"]
                    else:
                        self.logger.error(f"百度API返回错误: {result}")
                        return None
                
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
        # 与其他模型使用相同的提示格式
        title = metadata.get('title', '') if metadata else ''
        keywords = metadata.get('keywords', '') if metadata else ''
        
        prompt = f"""
        请改写以下博客文章，使其更加生动有趣，同时保持专业性和SEO友好。
        
        要求：
        1. 保持原文的主要观