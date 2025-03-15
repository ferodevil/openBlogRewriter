# 博客内容采集与改写发布系统

这是一个功能强大的博客内容采集、改写和发布系统，支持多种大模型，能够生成符合SEO要求的高质量内容。

## 功能特点

1. **内容采集**：自动从URL采集博客内容和元数据
2. **多模型支持**：支持OpenAI、Azure OpenAI、Anthropic Claude、百度文心一言和本地Ollama等多种大模型
3. **内容改写**：使用AI模型将采集的内容改写为生动有趣、专业且符合SEO要求的文章
4. **WordPress发布**：自动将改写后的内容发布到WordPress网站
5. **SEO分析**：提供内容的SEO分析和优化建议
6. **可扩展性**：模块化设计，易于扩展新的爬虫、模型和发布平台

## 安装

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/blog-processor.git
cd blog-processor

2. python main.py https://example.com/blog-post
3. python main.py https://example.com/blog-post --model openai
4. python main.py https://example.com/blog-post --publish
5. python main.py https://example.com/blog-post --config path/to/config.yaml