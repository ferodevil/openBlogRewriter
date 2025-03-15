from setuptools import setup, find_packages

setup(
    name="myblog",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.2",
        "beautifulsoup4>=4.11.2",
        "pyyaml>=6.0",
        "readability-lxml>=0.8.1",
        "openai>=0.27.8",
        "anthropic>=0.3.6",
    ],
    entry_points={
        'console_scripts': [
            'myblog=main:main',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="博客内容采集与改写发布系统",
    keywords="blog, scraper, rewriter, publisher",
    url="https://github.com/yourusername/myblog",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.7",
)