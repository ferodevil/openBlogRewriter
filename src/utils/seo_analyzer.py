import re
import logging

class SEOAnalyzer:
    """SEO分析工具，用于分析和优化内容的SEO表现"""
    
    def __init__(self, config=None):
        """初始化SEO分析器"""
        self.config = config or {}
        
        # 设置SEO参数
        self.min_word_count = self.config.get('min_word_count', 800)
        self.keyword_density = self.config.get('keyword_density', 0.02)
        self.meta_description_length = self.config.get('meta_description_length', 160)
        self.title_max_length = self.config.get('title_max_length', 60)
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def analyze_content(self, content, keywords=None):
        """分析内容的SEO表现"""
        if not content:
            return {
                'status': 'error',
                'message': '内容为空'
            }
        
        # 计算字数
        word_count = len(content)
        
        # 分析关键词密度
        keyword_density_results = {}
        if keywords:
            if isinstance(keywords, str):
                keywords = [kw.strip() for kw in keywords.split(',')]
            
            for keyword in keywords:
                if keyword:
                    count = len(re.findall(re.escape(keyword), content, re.IGNORECASE))
                    density = count / word_count if word_count > 0 else 0
                    keyword_density_results[keyword] = {
                        'count': count,
                        'density': density,
                        'status': 'good' if self.keyword_density * 0.5 <= density <= self.keyword_density * 1.5 else 'bad'
                    }
        
        # 返回分析结果
        return {
            'status': 'success',
            'word_count': word_count,
            'word_count_status': 'good' if word_count >= self.min_word_count else 'bad',
            'keyword_density': keyword_density_results
        }
    
    def analyze_title(self, title):
        """分析标题的SEO表现"""
        if not title:
            return {
                'status': 'error',
                'message': '标题为空'
            }
        
        # 计算标题长度
        title_length = len(title)
        
        # 返回分析结果
        return {
            'status': 'success',
            'title_length': title_length,
            'title_length_status': 'good' if title_length <= self.title_max_length else 'bad'
        }
    
    def analyze_meta_description(self, description):
        """分析元描述的SEO表现"""
        if not description:
            return {
                'status': 'error',
                'message': '描述为空'
            }
        
        # 计算描述长度
        description_length = len(description)
        
        # 返回分析结果
        return {
            'status': 'success',
            'description_length': description_length,
            'description_length_status': 'good' if description_length <= self.meta_description_length else 'bad'
        }
    
    def get_seo_suggestions(self, content_analysis, title_analysis, description_analysis):
        """获取SEO优化建议"""
        suggestions = {
            'content': [],
            'title': [],
            'description': []
        }
        
        # 内容建议
        if content_analysis.get('keyword_density', 0) < self.min_keyword_density:
            suggestions['content'].append(f"关键词密度过低 ({content_analysis.get('keyword_density', 0)}%)，建议增加关键词出现频率")
        elif content_analysis.get('keyword_density', 0) > self.max_keyword_density:
            suggestions['content'].append(f"关键词密度过高 ({content_analysis.get('keyword_density', 0)}%)，建议减少关键词出现频率")
        
        if content_analysis.get('readability_score', 0) < 60:
            suggestions['content'].append("可读性较低，建议简化句子结构，使用更通俗的语言")
        
        if content_analysis.get('avg_sentence_length', 0) > 25:
            suggestions['content'].append(f"平均句子长度过长 ({content_analysis.get('avg_sentence_length', 0)}词)，建议缩短句子")
        
        if content_analysis.get('paragraph_count', 0) < 5:
            suggestions['content'].append("段落数量较少，建议增加段落以提高可读性")
        
        # 标题建议
        if title_analysis.get('length', 0) > 60:
            suggestions['title'].append(f"标题过长 ({title_analysis.get('length', 0)}字符)，建议缩短至60字符以内")
        elif title_analysis.get('length', 0) < 30:
            suggestions['title'].append(f"标题过短 ({title_analysis.get('length', 0)}字符)，建议增加至30-60字符")
        
        if not title_analysis.get('has_keyword', False):
            suggestions['title'].append("标题中未包含关键词，建议添加主要关键词")
        
        # 描述建议
        if description_analysis.get('length', 0) > 160:
            suggestions['description'].append(f"描述过长 ({description_analysis.get('length', 0)}字符)，建议缩短至160字符以内")
        elif description_analysis.get('length', 0) < 70:
            suggestions['description'].append(f"描述过短 ({description_analysis.get('length', 0)}字符)，建议增加至70-160字符")
        
        if not description_analysis.get('has_keyword', False):
            suggestions['description'].append("描述中未包含关键词，建议添加主要关键词")
        
        return suggestions