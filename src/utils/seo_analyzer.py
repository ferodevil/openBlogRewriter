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
        self.min_keyword_density = self.keyword_density * 0.5
        self.max_keyword_density = self.keyword_density * 1.5
        self.meta_description_length = self.config.get('meta_description_length', 160)
        self.title_max_length = self.config.get('title_max_length', 60)
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def analyze_content(self, content, keywords=None):
        """分析内容的SEO表现"""
        if not content:
            return {
                'status': 'error',
                'message': 'Content is empty'
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
                'message': 'Title is empty'
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
                'message': 'Description is empty'
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
            suggestions['content'].append(f"Keyword density is too low ({content_analysis.get('keyword_density', 0)}%), consider increasing keyword frequency")
        elif content_analysis.get('keyword_density', 0) > self.max_keyword_density:
            suggestions['content'].append(f"Keyword density is too high ({content_analysis.get('keyword_density', 0)}%), consider reducing keyword frequency")
        
        if content_analysis.get('readability_score', 0) < 60:
            suggestions['content'].append("Low readability score, consider simplifying sentence structure and using more common language")
        
        if content_analysis.get('avg_sentence_length', 0) > 25:
            suggestions['content'].append(f"Average sentence length is too long ({content_analysis.get('avg_sentence_length', 0)} words), consider shortening sentences")
        
        if content_analysis.get('paragraph_count', 0) < 5:
            suggestions['content'].append("Too few paragraphs, consider adding more paragraphs to improve readability")
        
        # Title suggestions
        if title_analysis.get('length', 0) > 60:
            suggestions['title'].append(f"Title is too long ({title_analysis.get('length', 0)} characters), consider shortening to 60 characters or less")
        elif title_analysis.get('length', 0) < 30:
            suggestions['title'].append(f"Title is too short ({title_analysis.get('length', 0)} characters), consider extending to 30-60 characters")
        
        if not title_analysis.get('has_keyword', False):
            suggestions['title'].append("Title does not contain keywords, consider adding main keywords")
        
        # Description suggestions
        if description_analysis.get('length', 0) > 160:
            suggestions['description'].append(f"Description is too long ({description_analysis.get('length', 0)} characters), consider shortening to 160 characters or less")
        elif description_analysis.get('length', 0) < 70:
            suggestions['description'].append(f"Description is too short ({description_analysis.get('length', 0)} characters), consider extending to 70-160 characters")
        
        if not description_analysis.get('has_keyword', False):
            suggestions['description'].append("Description does not contain keywords, consider adding main keywords")
        
        return suggestions