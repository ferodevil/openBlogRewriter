import logging
import re
from src.utils.path_utils import get_config_path
import yaml

class ContentEvaluator:
    """内容质量评估工具，用于评估内容质量并决定是否需要重写"""
    
    def __init__(self, config_path=None):
        """初始化内容质量评估器"""
        self.config = self._load_config(config_path)
        self.quality_config = self.config.get('content_quality', {})
        
        # 设置质量评估参数
        self.min_readability_score = self.quality_config.get('min_readability_score', 60)
        self.min_originality_score = self.quality_config.get('min_originality_score', 70)
        self.max_avg_sentence_length = self.quality_config.get('max_avg_sentence_length', 25)
        self.min_paragraph_count = self.quality_config.get('min_paragraph_count', 5)
        self.quality_threshold = self.quality_config.get('threshold', 70)
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self, config_path=None):
        """加载配置文件"""
        if config_path is None:
            config_path = get_config_path()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def evaluate_content(self, content, original_content=None):
        """评估内容质量"""
        if not content:
            return {
                'status': 'error',
                'message': '内容为空',
                'score': 0,
                'needs_rewrite': True
            }
        
        # 计算可读性分数
        readability_score = self._calculate_readability_score(content)
        
        # 计算原创性分数（如果有原始内容）
        originality_score = self._calculate_originality_score(content, original_content) if original_content else 100
        
        # 计算平均句子长度
        avg_sentence_length = self._calculate_avg_sentence_length(content)
        
        # 计算段落数量
        paragraph_count = self._count_paragraphs(content)
        
        # 计算总体质量分数
        quality_score = self._calculate_quality_score(
            readability_score,
            originality_score,
            avg_sentence_length,
            paragraph_count
        )
        
        # 判断是否需要重写
        needs_rewrite = quality_score < self.quality_threshold
        
        # 返回评估结果
        return {
            'status': 'success',
            'readability_score': readability_score,
            'originality_score': originality_score,
            'avg_sentence_length': avg_sentence_length,
            'paragraph_count': paragraph_count,
            'quality_score': quality_score,
            'needs_rewrite': needs_rewrite,
            'suggestions': self._get_quality_suggestions(
                readability_score,
                originality_score,
                avg_sentence_length,
                paragraph_count
            )
        }
    
    def _calculate_readability_score(self, content):
        """计算可读性分数（简化版Flesch-Kincaid可读性测试）"""
        # 分割句子
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0
        
        # 计算单词数
        words = content.split()
        word_count = len(words)
        
        if word_count == 0:
            return 0
        
        # 计算平均句子长度
        avg_sentence_length = word_count / len(sentences)
        
        # 计算平均单词长度
        avg_word_length = sum(len(word) for word in words) / word_count
        
        # 简化版Flesch-Kincaid可读性公式
        readability = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_word_length)
        
        # 将分数限制在0-100之间
        readability = max(0, min(100, readability))
        
        return round(readability, 2)
    
    def _calculate_originality_score(self, content, original_content):
        """计算原创性分数（简化版）"""
        if not original_content:
            return 100
        
        # 将内容分割成句子
        content_sentences = re.split(r'[.!?]+', content)
        content_sentences = [s.strip() for s in content_sentences if s.strip()]
        
        original_sentences = re.split(r'[.!?]+', original_content)
        original_sentences = [s.strip() for s in original_sentences if s.strip()]
        
        if not content_sentences or not original_sentences:
            return 0
        
        # 计算相似句子数量
        similar_count = 0
        for c_sentence in content_sentences:
            for o_sentence in original_sentences:
                # 简单的相似度检查（可以使用更复杂的算法）
                if len(c_sentence) > 10 and c_sentence in original_content:
                    similar_count += 1
                    break
        
        # 计算原创性分数
        originality = 100 - (similar_count / len(content_sentences) * 100)
        
        return round(originality, 2)
    
    def _calculate_avg_sentence_length(self, content):
        """计算平均句子长度"""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0
        
        words = content.split()
        return round(len(words) / len(sentences), 2)
    
    def _count_paragraphs(self, content):
        """计算段落数量"""
        paragraphs = content.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        return len(paragraphs)
    
    def _calculate_quality_score(self, readability_score, originality_score, avg_sentence_length, paragraph_count):
        """计算总体质量分数"""
        # 可读性评分（30%）
        readability_factor = 0.3 * (readability_score / self.min_readability_score * 100)
        readability_factor = min(30, readability_factor)
        
        # 原创性评分（40%）
        originality_factor = 0.4 * (originality_score / self.min_originality_score * 100)
        originality_factor = min(40, originality_factor)
        
        # 句子长度评分（15%）
        sentence_length_factor = 0
        if avg_sentence_length > 0:
            if avg_sentence_length <= self.max_avg_sentence_length:
                sentence_length_factor = 15
            else:
                sentence_length_factor = 15 * (self.max_avg_sentence_length / avg_sentence_length)
        
        # 段落数量评分（15%）
        paragraph_factor = 0
        if paragraph_count >= self.min_paragraph_count:
            paragraph_factor = 15
        else:
            paragraph_factor = 15 * (paragraph_count / self.min_paragraph_count)
        
        # 总分
        total_score = readability_factor + originality_factor + sentence_length_factor + paragraph_factor
        
        return round(min(100, total_score), 2)
    
    def _get_quality_suggestions(self, readability_score, originality_score, avg_sentence_length, paragraph_count):
        """获取质量改进建议"""
        suggestions = []
        
        # 可读性建议
        if readability_score < self.min_readability_score:
            suggestions.append(f"可读性分数较低 ({readability_score})，建议简化句子结构，使用更通俗的语言")
        
        # 原创性建议
        if originality_score < self.min_originality_score:
            suggestions.append(f"原创性分数较低 ({originality_score})，建议使用更多原创表达，避免与原文过于相似")
        
        # 句子长度建议
        if avg_sentence_length > self.max_avg_sentence_length:
            suggestions.append(f"平均句子长度过长 ({avg_sentence_length})，建议缩短句子，提高可读性")
        
        # 段落数量建议
        if paragraph_count < self.min_paragraph_count:
            suggestions.append(f"段落数量较少 ({paragraph_count})，建议增加段落数量，提高文章结构性")
        
        return suggestions