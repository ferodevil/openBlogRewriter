import os
import logging
from datetime import datetime
from .path_utils import get_log_dir

def setup_logging(verbose=False, log_name=None):
    """设置统一的日志配置
    
    Args:
        verbose (bool): 是否显示详细日志
        log_name (str): 日志文件名前缀，默认为None
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    log_dir = get_log_dir()
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_prefix = log_name if log_name else 'app'
    log_file = os.path.join(log_dir, f"{log_prefix}_{timestamp}.log")
    
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def get_logger(name=None, verbose=False, log_name=None):
    """获取配置好的日志记录器
    
    Args:
        name (str): 日志记录器名称
        verbose (bool): 是否显示详细日志
        log_name (str): 日志文件名前缀
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    if not logging.getLogger().handlers:
        setup_logging(verbose, log_name)
    
    return logging.getLogger(name)