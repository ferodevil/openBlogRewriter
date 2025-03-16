import os
import platform
import yaml

def get_base_dir():
    """
    获取基础目录，根据不同操作系统返回适当的路径
    优先级：环境变量 > 配置文件 > 默认路径
    """
    # 首先尝试从环境变量获取
    base_dir = os.environ.get('BLOG_REWRITER_BASE_DIR')
    if base_dir:
        return base_dir
    
    # 尝试从配置文件获取
    try:
        # 使用相对于当前脚本的路径查找配置文件
        config_path = os.environ.get('BLOG_REWRITER_CONFIG_PATH')
        if not config_path:
            # 使用默认配置路径
            if platform.system() == 'Windows':
                default_base = os.path.join(os.path.expanduser('~'), 'myblog')
            else:
                default_base = os.path.join(os.path.expanduser('~'), 'myblog')
            config_path = os.path.join(default_base, 'config', 'config.yaml')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config and 'paths' in config and 'base_dir' in config['paths']:
                    return os.path.expanduser(config['paths']['base_dir'])
    except Exception:
        # 如果读取配置文件失败，使用默认路径
        pass
    
    # 默认路径：使用项目根目录
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return current_dir

def get_data_dir():
    """获取数据目录"""
    return os.path.join(get_base_dir(), 'data')

def get_log_dir():
    """获取日志目录"""
    return os.path.join(get_base_dir(), 'logs')

def get_config_dir():
    """获取配置目录"""
    return os.path.join(get_base_dir(), 'config')

def get_config_path():
    """获取配置文件路径"""
    config_path = os.environ.get('BLOG_REWRITER_CONFIG_PATH')
    if config_path:
        return config_path
    return os.path.join(get_config_dir(), 'config.yaml')