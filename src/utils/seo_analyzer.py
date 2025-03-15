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
    
    def get_seo_suggestions(self, content_analysis, title_analysis=None, description_analysis=None):
        """获取SEO优化建议"""
        suggestions = []
        
        # 内容建议
        if content_analysis.get('status') == 'success':
            if content_analysis.get('word_count_status') == 'bad':
                suggestions.append(f"内容字数({content_analysis.get('word_count')})不足，建议增加到至少{self.min_word_count}字")
            
            for keyword, data in content_analysis.get('keyword_density', {}).items():
                if data.get('status') == 'bad':
                    if data.get('density', 0) < self.keyword_density * 0.5:
                        suggestions.append(f"关键词'{keyword}'出现次数过少，当前密度为{data.get('density', 0):.2%}，建议增加到{self.keyword_density:.2%}左右")
                    else:
                        suggestions.append(f"关键词'{keyword}'出现次数过多，当前密度为{data.get('density', 0):.2%}，建议减少到{self.keyword_density:.2%}左右")
        
        # 标题建议
        if title_analysis and title_analysis.get('status') == 'success':
            if title_analysis.get('title_length_status') == 'bad':
                suggestions.append(f"标题长度({title_analysis.get('title_length')})超过建议最大值{self.title_max_length}，建议缩短")
        
        # 描述建议
        if description_analysis and description_analysis.get('status') == 'success':
            if description_analysis.get('description_length_status') == 'bad':
                suggestions.append(f"元描述长度({description_analysis.get('description_length')})超过建议最大值{self.meta_description_length}，建议缩短")
        
        return suggestions