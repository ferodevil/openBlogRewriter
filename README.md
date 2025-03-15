# 博客内容采集与改写发布系统

一个自动化工具，用于爬取博客内容，使用大模型改写，进行SEO优化，并可选择性地发布到WordPress。

## 功能特点

- **多平台支持**：跨平台设计，支持Windows、Linux和macOS
- **内容爬取**：自动从URL爬取博客内容和元数据
- **智能改写**：支持多种大模型（OpenAI、Azure OpenAI、Anthropic、百度文心一言、Ollama）
- **SEO优化**：自动分析内容并提供SEO建议，支持多轮优化迭代
- **WordPress发布**：一键发布到WordPress网站
- **GUI界面**：提供图形用户界面，方便操作
- **命令行支持**：支持命令行操作，便于自动化和批处理

## 安装

### 环境要求

- Python 3.8+
- 依赖包：见`requirements.txt`

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/yourusername/openBlogRewriter.git
cd openBlogRewriter

2. python main.py https://example.com/blog-post
3. python main.py https://example.com/blog-post --model openai
4. python main.py https://example.com/blog-post --publish
5. python main.py https://example.com/blog-post --config path/to/config.yaml