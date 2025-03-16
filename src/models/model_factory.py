class ModelFactory:
    """模型工厂，用于创建不同的大模型实例"""
    
    @staticmethod
    def get_model(model_name=None, config_path=None):
        """获取模型实例
        
        Args:
            model_name: 可选，指定要使用的模型名称。如果为None，则使用配置文件中的active_model
            config_path: 可选，配置文件路径
        """
        # 如果指定了model_name，优先使用命令行参数
        # 否则从配置文件中读取active_model
        if model_name is None:
            import yaml
            from src.utils.path_utils import get_config_path
            
            if config_path is None:
                config_path = get_config_path()
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                model_name = config.get('models', {}).get('active_model', 'openai')
        
        # 验证模型名称的有效性
        valid_models = ['openai', 'azure_openai', 'anthropic', 'baidu', 'ollama', 'siliconflow']
        if model_name not in valid_models:
            raise ValueError(f"不支持的模型: {model_name}。支持的模型: {', '.join(valid_models)}")

        
        # 根据模型名称创建相应的模型实例
        model_mapping = {
            'openai': ('src.models.openai_model', 'OpenAIModel'),
            'azure_openai': ('src.models.azure_openai_model', 'AzureOpenAIModel'),
            'anthropic': ('src.models.anthropic_model', 'AnthropicModel'),
            'baidu': ('src.models.baidu_model', 'BaiduModel'),
            'ollama': ('src.models.ollama_model', 'OllamaModel'),
            'siliconflow': ('src.models.siliconflow_model', 'SiliconFlowModel')
        }
        
        if model_name not in model_mapping:
            raise ValueError(f"不支持的模型: {model_name}")
            
        module_path, class_name = model_mapping[model_name]
        module = __import__(module_path, fromlist=[class_name])
        model_class = getattr(module, class_name)
        return model_class(config_path)