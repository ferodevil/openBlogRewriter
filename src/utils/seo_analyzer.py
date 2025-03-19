import re
import logging

class SEOAnalyzer:
    """SEO分析工具，用于分析和优化内容的SEO表现
    
    该类实现了一套完整的SEO评分系统，主要从以下几个方面进行评估：
    1. 内容质量：包括文章字数、关键词密度、段落数量等
    2. 结构优化：包括标题标签(H2/H3)的使用、内部链接数量等
    3. 多媒体元素：如图片的使用数量
    4. 元数据优化：包括标题和描述的长度及关键词使用
    
    评分标准基于业界常见SEO最佳实践，可通过配置文件进行自定义调整
    """
    
    def __init__(self, config=None):
        """初始化SEO分析器
        
        Args:
            config (dict, optional): SEO参数配置，如果为None则使用默认配置
        
        SEO参数说明：
            - min_word_count: 文章最小字数要求，默认800字
            - keyword_density: 理想关键词密度，默认2%
            - meta_description_length: 元描述最大长度，默认160字符
            - title_max_length: 标题最大长度，默认60字符
            - min_internal_links: 最少内部链接数量，默认2个
            - min_images: 最少图片数量，默认1张
            - min_h2_tags: 最少H2标签数量，默认2个
            - min_h3_tags: 最少H3标签数量，默认3个
        """
        self.config = config or {}
        
        # 设置SEO参数
        self.min_word_count = self.config.get('min_word_count', 800)  # 文章最小字数要求
        self.keyword_density = self.config.get('keyword_density', 0.02)  # 理想关键词密度(2%)
        self.min_keyword_density = self.keyword_density * 0.5  # 关键词密度下限(1%)
        self.max_keyword_density = self.keyword_density * 1.5  # 关键词密度上限(3%)
        self.meta_description_length = self.config.get('meta_description_length', 160)  # 元描述最大长度
        self.title_max_length = self.config.get('title_max_length', 60)  # 标题最大长度
        self.min_internal_links = self.config.get('min_internal_links', 2)  # 最少内部链接数量
        self.min_images = self.config.get('min_images', 1)  # 最少图片数量
        self.min_h2_tags = self.config.get('min_h2_tags', 2)  # 最少H2标签数量
        self.min_h3_tags = self.config.get('min_h3_tags', 3)  # 最少H3标签数量
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def analyze_content(self, content, keywords=None):
        """分析内容的SEO表现
        
        对文章内容进行全面的SEO分析，包括以下几个方面：
        1. 字数统计：检查文章是否达到最低字数要求(默认800字)
        2. 关键词密度：计算每个关键词在文章中的出现频率，理想密度为2%(可配置)
        3. 内部链接：检查文章中的内部链接数量，至少需要2个(可配置)
        4. 图片使用：检查文章中的图片数量，至少需要1张(可配置)
        5. 标题结构：检查H2和H3标签的使用情况，分别至少需要2个和3个(可配置)
        
        Args:
            content (str): 需要分析的文章内容
            keywords (str or list): 关键词列表或逗号分隔的关键词字符串
            
        Returns:
            dict: 包含各项SEO指标分析结果的字典
        """
        if not content:
            return {
                'status': 'error',
                'message': 'Content is empty'
            }
        
        # 计算字数 - SEO标准：文章至少应达到最低字数要求(默认800字)
        # 字数过少会被搜索引擎视为内容不充实，影响排名
        word_count = len(content)
        
        # 分析关键词密度 - SEO标准：关键词密度应在1%-3%之间(默认)
        # 密度过低：关键词出现次数不足，难以被搜索引擎识别为相关内容
        # 密度过高：可能被视为关键词堆砌，导致搜索引擎惩罚
        keyword_density_results = {}
        if keywords:
            if isinstance(keywords, str):
                keywords = [kw.strip() for kw in keywords.split(',')]
            
            for keyword in keywords:
                if keyword:
                    # 计算关键词出现次数和密度
                    count = len(re.findall(re.escape(keyword), content, re.IGNORECASE))
                    density = count / word_count if word_count > 0 else 0
                    keyword_density_results[keyword] = {
                        'count': count,
                        'density': density,
                        'status': 'good' if self.keyword_density * 0.5 <= density <= self.keyword_density * 1.5 else 'bad'
                    }
        
        # 分析内部链接数量 - SEO标准：至少包含2个内部链接(默认)
        # 内部链接有助于建立网站结构，提高页面间的关联性，便于搜索引擎爬取
        internal_links_count = len(re.findall(r'<a\s+[^>]*href=["\'][^"\'>]*["\'][^>]*>', content, re.IGNORECASE))
        
        # 修改：改进图片计数逻辑，同时支持HTML和Markdown格式
        # 原代码只检测HTML图片标签
        html_images_count = len(re.findall(r'<img\s+[^>]*src=["\'][^"\'>]*["\'][^>]*>', content, re.IGNORECASE))
        markdown_images_count = len(re.findall(r'!\[.*?\]\(.*?\)', content))
        image_tags_count = content.count('[IMAGE]')
        
        # 累计所有图片数量
        total_images_count = html_images_count + markdown_images_count + image_tags_count
        
        # 分析标题标签 - SEO标准：H2标签至少2个，H3标签至少3个(默认)
        # 合理的标题结构有助于搜索引擎理解内容层次，同时提高用户阅读体验
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
                'count': total_images_count,
                'status': 'good' if total_images_count >= self.min_images else 'bad'
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
        """分析标题的SEO表现
        
        评估页面标题的SEO友好程度，主要检查标题长度是否符合搜索引擎推荐标准
        
        SEO标准：
        - 标题长度应控制在60个字符以内(默认，可配置)
        - 过长的标题在搜索结果中会被截断，影响点击率
        - 过短的标题可能无法充分表达页面内容，不利于SEO
        - 理想标题长度为30-60个字符
        
        Args:
            title (str): 页面标题
            
        Returns:
            dict: 包含标题长度分析结果的字典
        """
        if not title:
            return {
                'status': 'error',
                'message': 'Title is empty'
            }
        
        # 计算标题长度 - 搜索引擎通常显示前60个字符
        title_length = len(title)
        
        # 返回分析结果
        return {
            'status': 'success',
            'title_length': title_length,
            'title_length_status': 'good' if title_length <= self.title_max_length else 'bad'
        }
    
    def analyze_meta_description(self, description):
        """分析元描述的SEO表现
        
        评估页面元描述的SEO友好程度，主要检查描述长度是否符合搜索引擎推荐标准
        
        SEO标准：
        - 元描述长度应控制在160个字符以内(默认，可配置)
        - 过长的描述在搜索结果中会被截断，影响用户体验
        - 过短的描述可能无法充分概括页面内容，降低点击率
        - 理想描述长度为70-160个字符
        
        Args:
            description (str): 页面元描述
            
        Returns:
            dict: 包含元描述长度分析结果的字典
        """
        if not description:
            return {
                'status': 'error',
                'message': 'Description is empty'
            }
        
        # 计算描述长度 - 搜索引擎通常显示前160个字符
        description_length = len(description)
        
        # 返回分析结果
        return {
            'status': 'success',
            'description_length': description_length,
            'description_length_status': 'good' if description_length <= self.meta_description_length else 'bad'
        }
    
    def get_seo_suggestions(self, content_analysis, title_analysis, description_analysis):
        """获取SEO优化建议
        
        基于内容、标题和元描述的分析结果，生成具体的SEO优化建议
        
        建议生成逻辑：
        1. 内容建议：针对字数、关键词密度、内部链接、图片数量、标题标签等
        2. 标题建议：针对标题长度和关键词使用情况
        3. 元描述建议：针对描述长度和关键词使用情况
        
        每项建议都包含问题描述和改进方向，便于内容创作者进行针对性优化
        
        Args:
            content_analysis (dict): 内容分析结果
            title_analysis (dict): 标题分析结果
            description_analysis (dict): 元描述分析结果
            
        Returns:
            dict: 包含各类SEO优化建议的字典
        """
        suggestions = {
            'content': [],  # 内容相关建议
            'title': [],   # 标题相关建议
            'description': []  # 元描述相关建议
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