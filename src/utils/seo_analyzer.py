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
        self.min_internal_links = self.config.get('min_internal_links', 2)
        self.min_images = self.config.get('min_images', 1)
        self.min_h2_tags = self.config.get('min_h2_tags', 2)
        self.min_h3_tags = self.config.get('min_h3_tags', 3)
        
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
        
        # 分析内部链接数量
        internal_links_count = len(re.findall(r'<a\s+[^>]*href=["\'][^"\'>]*["\'][^>]*>', content, re.IGNORECASE))
        
        # 分析图片数量
        images_count = len(re.findall(r'<img\s+[^>]*src=["\'][^"\'>]*["\'][^>]*>', content, re.IGNORECASE))
        
        # 分析标题标签
        h2_tags_count = len(re.findall(r'<h2[^>]*>.*?</h2>', content, re.IGNORECASE | re.DOTALL))
        h3_tags_count = len(re.findall(r'<h3[^>]*>.*?</h3>', content, re.IGNORECASE | re.DOTALL))
        
        # 返回分析结果
        return {
            'status': 'success',
            'word_count': word_count,
            'word_count_status': 'good' if word_count >= self.min_word_count else 'bad',
            'keyword_density': keyword_density_results,
            'internal_links': {
                'count': internal_links_count,
                'status': 'good' if internal_links_count >= self.min_internal_links else 'bad'
            },
            'images': {
                'count': images_count,
                'status': 'good' if images_count >= self.min_images else 'bad'
            },
            'h2_tags': {
                'count': h2_tags_count,
                'status': 'good' if h2_tags_count >= self.min_h2_tags else 'bad'
            },
            'h3_tags': {
                'count': h3_tags_count,
                'status': 'good' if h3_tags_count >= self.min_h3_tags else 'bad'
            }
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
        keyword_density_data = content_analysis.get('keyword_density', {})
        if keyword_density_data:
            for keyword, data in keyword_density_data.items():
                density = data.get('density', 0)
                if density < self.min_keyword_density:
                    suggestions['content'].append(f"Keyword '{keyword}' density is too low ({density:.2%}), consider increasing frequency")
                elif density > self.max_keyword_density:
                    suggestions['content'].append(f"Keyword '{keyword}' density is too high ({density:.2%}), consider reducing frequency")
        
        if content_analysis.get('readability_score', 0) < 60:
            suggestions['content'].append("Low readability score, consider simplifying sentence structure and using more common language")
        
        if content_analysis.get('avg_sentence_length', 0) > 25:
            suggestions['content'].append(f"Average sentence length is too long ({content_analysis.get('avg_sentence_length', 0)} words), consider shortening sentences")
        
        if content_analysis.get('paragraph_count', 0) < 5:
            suggestions['content'].append("Too few paragraphs, consider adding more paragraphs to improve readability")
        
        # 内部链接建议
        internal_links = content_analysis.get('internal_links', {})
        if internal_links.get('status') == 'bad':
            suggestions['content'].append(f"Too few internal links ({internal_links.get('count', 0)}), consider adding at least {self.min_internal_links} internal links to improve SEO")
        
        # 图片建议
        images = content_analysis.get('images', {})
        if images.get('status') == 'bad':
            suggestions['content'].append(f"Too few images ({images.get('count', 0)}), consider adding at least {self.min_images} images with alt text to improve SEO")
        
        # 标题标签建议
        h2_tags = content_analysis.get('h2_tags', {})
        if h2_tags.get('status') == 'bad':
            suggestions['content'].append(f"Too few H2 headings ({h2_tags.get('count', 0)}), consider adding at least {self.min_h2_tags} H2 headings to improve structure and SEO")
        
        h3_tags = content_analysis.get('h3_tags', {})
        if h3_tags.get('status') == 'bad':
            suggestions['content'].append(f"Too few H3 headings ({h3_tags.get('count', 0)}), consider adding at least {self.min_h3_tags} H3 headings to improve structure and SEO")
        
        # Title suggestions
        if title_analysis.get('title_length', 0) > self.title_max_length:
            suggestions['title'].append(f"Title is too long ({title_analysis.get('title_length', 0)} characters), consider shortening to {self.title_max_length} characters or less")
        elif title_analysis.get('title_length', 0) < 30:
            suggestions['title'].append(f"Title is too short ({title_analysis.get('title_length', 0)} characters), consider extending to 30-{self.title_max_length} characters")
        
        if not title_analysis.get('has_keyword', False):
            suggestions['title'].append("Title does not contain keywords, consider adding main keywords")
        
        # Description suggestions
        if description_analysis.get('description_length', 0) > self.meta_description_length:
            suggestions['description'].append(f"Description is too long ({description_analysis.get('description_length', 0)} characters), consider shortening to {self.meta_description_length} characters or less")
        elif description_analysis.get('description_length', 0) < 70:
            suggestions['description'].append(f"Description is too short ({description_analysis.get('description_length', 0)} characters), consider extending to 70-{self.meta_description_length} characters")
        
        if not description_analysis.get('has_keyword', False):
            suggestions['description'].append("Description does not contain keywords, consider adding main keywords")
        
        return suggestions