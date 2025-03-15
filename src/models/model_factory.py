class ModelFactory:
    """模型工厂，用于创建不同的大模型实例"""
    
    @staticmethod
    def get_model(model_name, config_path=None):
        """根据模型名称获取相应的模型实例"""
        if model_name == 'openai':
            from src.models.openai_model import OpenAIModel
            return OpenAIModel(config_path)
        elif model_name == 'azure_openai':
            from src.models.azure_openai_model import AzureOpenAIModel
            return AzureOpenAIModel(config_path)
        elif model_name == 'anthropic':
            from src.models.anthropic_model import AnthropicModel
            return AnthropicModel(config_path)
        elif model_name == 'baidu':
            from src.models.baidu_model import BaiduModel
            return BaiduModel(config_path)
        elif model_name == 'ollama':
            from src.models.ollama_model import OllamaModel
            return OllamaModel(config_path)
        else:
            raise ValueError(f"不支持的模型: {model_name}")