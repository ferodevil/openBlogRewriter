@echo off
echo 正在安装博客内容采集与改写发布系统...

REM 创建虚拟环境
python -m venv venv
call venv\Scripts\activate

REM 安装依赖
pip install -e .

echo 安装完成！
echo 使用方法：
echo myblog --help