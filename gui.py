import sys
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import queue
from datetime import datetime
import yaml

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import process_blog, load_config
from src.scrapers.scraper_factory import ScraperFactory
from src.models.model_factory import ModelFactory
from src.publishers.wordpress_publisher import WordPressPublisher
from src.utils.file_handler import FileHandler
from src.utils.path_utils import get_base_dir, get_config_path
from src.utils.logger import get_logger

class RedirectText:
    """重定向文本到GUI"""
    
    def __init__(self, text_widget):
        """初始化"""
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.update_timer = None
        
    def write(self, string):
        """写入文本"""
        self.queue.put(string)
        if self.update_timer is None:
            self.update_timer = self.text_widget.after(100, self.update)
    
    def update(self):
        """更新文本控件"""
        self.update_timer = None
        try:
            while True:
                string = self.queue.get_nowait()
                self.text_widget.configure(state="normal")
                self.text_widget.insert("end", string)
                self.text_widget.see("end")
                self.text_widget.configure(state="disabled")
                self.queue.task_done()
        except queue.Empty:
            self.update_timer = self.text_widget.after(100, self.update)
    
    def flush(self):
        """刷新"""
        pass

class BlogProcessorGUI:
    """博客处理器GUI"""
    
    def __init__(self, master):
        self.master = master
        master.title("Blog Processor")
        master.geometry("1000x700")
        
        # 加载配置 - 确保在创建选项卡之前加载配置
        self.config = load_config()
        
        # 初始化文件处理器
        self.file_handler = FileHandler()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create main frame for log area
        self.main_frame = ttk.Frame(master)
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 创建日志区域
        self.create_log_area()
        
        # 重定向标准输出到日志区域
        self.redirect = RedirectText(self.log_text)
        sys.stdout = self.redirect
        sys.stderr = self.redirect
        
        # Create tabs
        self.create_process_tab()
        self.create_publish_tab()
        self.create_scrape_tab()
        self.create_rewrite_tab()
        self.create_settings_tab()
        
        print("博客处理器GUI已启动")
    
    def create_scrape_tab(self):
        """创建爬取选项卡"""
        scrape_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(scrape_tab, text="爬取")
        
        # URL输入（多行文本框）
        ttk.Label(scrape_tab, text="博客URL列表:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.scrape_urls_text = scrolledtext.ScrolledText(scrape_tab, width=50, height=6)
        self.scrape_urls_text.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        
        # 从配置加载URL按钮
        ttk.Button(scrape_tab, text="从配置加载URL", command=self.load_scrape_urls_from_config).grid(row=0, column=2, padx=5, pady=5)
        
        # 爬虫类型选择
        ttk.Label(scrape_tab, text="爬虫类型:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.scrape_type_var = tk.StringVar(value=self.config.get('scrapers', {}).get('default_scraper', 'crawl4ai'))
        scraper_combo = ttk.Combobox(scrape_tab, textvariable=self.scrape_type_var, width=20)
        scraper_combo['values'] = ('crawl4ai', 'general')
        scraper_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 输出目录
        ttk.Label(scrape_tab, text="输出目录:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.scrape_output_dir_var = tk.StringVar(value=os.path.join(get_base_dir(), 'data', 'raw'))
        ttk.Entry(scrape_tab, textvariable=self.scrape_output_dir_var, width=50).grid(row=2, column=1, sticky=tk.W+tk.E, pady=5)
        ttk.Button(scrape_tab, text="浏览...", command=self.browse_scrape_output_dir).grid(row=2, column=2, padx=5, pady=5)
        
        # 爬取按钮
        ttk.Button(scrape_tab, text="爬取", command=self.scrape_multiple).grid(row=3, column=1, pady=10)
        
        # 配置网格
        scrape_tab.columnconfigure(1, weight=1)
    
    def create_rewrite_tab(self):
        """创建改写选项卡"""
        rewrite_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(rewrite_tab, text="改写")
        
        # 输入文件
        ttk.Label(rewrite_tab, text="输入文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.rewrite_input_var = tk.StringVar()
        ttk.Entry(rewrite_tab, textvariable=self.rewrite_input_var, width=50).grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        ttk.Button(rewrite_tab, text="浏览...", command=self.browse_rewrite_input).grid(row=0, column=2, padx=5, pady=5)
        
        # 模型选择
        ttk.Label(rewrite_tab, text="模型:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # 获取配置中的活跃模型
        active_model = self.config.get('models', {}).get('active_model', 'openai')
        self.rewrite_model_var = tk.StringVar(value=active_model)
        
        # 获取配置中的所有模型
        available_models = list(self.config.get('models', {}).keys())
        # 移除'active_model'，因为它不是实际的模型
        if 'active_model' in available_models:
            available_models.remove('active_model')
        
        model_combo = ttk.Combobox(rewrite_tab, textvariable=self.rewrite_model_var, width=20)
        model_combo['values'] = available_models
        model_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # SEO优化迭代次数
        ttk.Label(rewrite_tab, text="SEO优化迭代次数:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.rewrite_iterations_var = tk.IntVar(value=self.config.get('cli', {}).get('max_iterations', 3))
        ttk.Spinbox(rewrite_tab, from_=1, to=10, textvariable=self.rewrite_iterations_var, width=5).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 输出文件
        ttk.Label(rewrite_tab, text="输出文件:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.rewrite_output_var = tk.StringVar()
        ttk.Entry(rewrite_tab, textvariable=self.rewrite_output_var, width=50).grid(row=3, column=1, sticky=tk.W+tk.E, pady=5)
        ttk.Button(rewrite_tab, text="浏览...", command=self.browse_rewrite_output).grid(row=3, column=2, padx=5, pady=5)
        
        # 改写按钮
        ttk.Button(rewrite_tab, text="改写", command=self.rewrite).grid(row=4, column=1, pady=10)
        
        # 配置网格
        rewrite_tab.columnconfigure(1, weight=1)
    
    def create_publish_tab(self):
        """创建发布选项卡"""
        publish_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(publish_tab, text="发布")
        
        # 输入文件
        ttk.Label(publish_tab, text="输入文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.publish_input_var = tk.StringVar()
        ttk.Entry(publish_tab, textvariable=self.publish_input_var, width=50).grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        ttk.Button(publish_tab, text="浏览...", command=self.browse_publish_input).grid(row=0, column=2, padx=5, pady=5)
        
        # 文章标题
        ttk.Label(publish_tab, text="文章标题:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.publish_title_var = tk.StringVar()
        ttk.Entry(publish_tab, textvariable=self.publish_title_var, width=50).grid(row=1, column=1, sticky=tk.W+tk.E, pady=5)
        
        # 文章摘要
        ttk.Label(publish_tab, text="文章摘要:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.publish_excerpt_var = tk.StringVar()
        ttk.Entry(publish_tab, textvariable=self.publish_excerpt_var, width=50).grid(row=2, column=1, sticky=tk.W+tk.E, pady=5)
        
        # 图片文件夹
        ttk.Label(publish_tab, text="图片文件夹:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.publish_images_var = tk.StringVar(value=os.path.join(get_base_dir(), 'data', 'images'))
        ttk.Entry(publish_tab, textvariable=self.publish_images_var, width=50).grid(row=3, column=1, sticky=tk.W+tk.E, pady=5)
        ttk.Button(publish_tab, text="浏览...", command=self.browse_publish_images).grid(row=3, column=2, padx=5, pady=5)
        
        # WordPress设置框架
        wp_frame = ttk.LabelFrame(publish_tab, text="WordPress设置", padding="5")
        wp_frame.grid(row=4, column=0, columnspan=3, sticky=tk.W+tk.E, pady=10)
        
        # WordPress状态
        ttk.Label(wp_frame, text="发布状态:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.publish_status_var = tk.StringVar(value=self.config.get('wordpress', {}).get('status', 'draft'))
        status_combo = ttk.Combobox(wp_frame, textvariable=self.publish_status_var, width=20)
        status_combo['values'] = ('draft', 'publish', 'private', 'pending')
        status_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 发布按钮
        ttk.Button(publish_tab, text="发布", command=self.publish_post).grid(row=5, column=1, pady=10)
        
        # 配置网格
        publish_tab.columnconfigure(1, weight=1)
    
    def create_process_tab(self):
        """创建处理选项卡"""
        process_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(process_tab, text="完整处理")
        
        # URL输入（多行文本框）
        ttk.Label(process_tab, text="博客URL列表:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.process_urls_text = scrolledtext.ScrolledText(process_tab, width=50, height=6)
        self.process_urls_text.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        
        # 从配置加载URL按钮
        ttk.Button(process_tab, text="从配置加载URL", command=self.load_urls_from_config).grid(row=0, column=2, padx=5, pady=5)
        
        # 模型选择
        ttk.Label(process_tab, text="模型:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # 获取配置中的活跃模型
        active_model = self.config.get('models', {}).get('active_model', 'openai')
        self.process_model_var = tk.StringVar(value=active_model)
        
        # 获取配置中的所有模型
        available_models = list(self.config.get('models', {}).keys())
        # 移除'active_model'，因为它不是实际的模型
        if 'active_model' in available_models:
            available_models.remove('active_model')
        
        model_combo = ttk.Combobox(process_tab, textvariable=self.process_model_var, width=20)
        model_combo['values'] = available_models
        model_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # SEO优化迭代次数
        ttk.Label(process_tab, text="SEO优化迭代次数:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.process_iterations_var = tk.IntVar(value=self.config.get('cli', {}).get('max_iterations', 3))
        ttk.Spinbox(process_tab, from_=1, to=10, textvariable=self.process_iterations_var, width=5).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 发布选项
        self.process_publish_var = tk.BooleanVar(value=self.config.get('cli', {}).get('publish', False))
        ttk.Checkbutton(process_tab, text="发布到WordPress", variable=self.process_publish_var).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # 处理按钮
        ttk.Button(process_tab, text="处理", command=self.process_multiple).grid(row=4, column=1, pady=10)
        
        # 配置网格
        process_tab.columnconfigure(1, weight=1)
    
    def load_urls_from_config(self):
        """从配置文件加载URL列表"""
        urls = self.config.get('cli', {}).get('blog_urls', [])
        if urls:
            self.process_urls_text.delete(1.0, tk.END)
            self.process_urls_text.insert(tk.END, '\n'.join(urls))
            print(f"已从配置加载 {len(urls)} 个URL")
        else:
            messagebox.showinfo("提示", "配置文件中没有找到URL列表")
    
    # Add the missing method here
    def load_scrape_urls_from_config(self):
        """从配置文件加载URL列表到爬取选项卡"""
        urls = self.config.get('cli', {}).get('blog_urls', [])
        if urls:
            self.scrape_urls_text.delete(1.0, tk.END)
            self.scrape_urls_text.insert(tk.END, '\n'.join(urls))
            print(f"已从配置加载 {len(urls)} 个URL到爬取选项卡")
        else:
            messagebox.showinfo("提示", "配置文件中没有找到URL列表")
    
    def process_multiple(self):
        """处理多个博客URL"""
        # 获取URL列表
        urls_text = self.process_urls_text.get(1.0, tk.END).strip()
        if not urls_text:
            messagebox.showerror("错误", "请输入至少一个博客URL")
            return
        
        # 分割URL（支持换行分隔）
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        # 获取其他参数
        model_name = self.process_model_var.get()
        iterations = self.process_iterations_var.get()
        publish = self.process_publish_var.get()
        
        print(f"开始处理 {len(urls)} 个博客URL")
        print(f"使用模型: {model_name}")
        print(f"SEO优化迭代次数: {iterations}")
        print(f"是否发布: {'是' if publish else '否'}")
        
        def _process_all():
            for i, url in enumerate(urls):
                print(f"\n处理第 {i+1}/{len(urls)} 个URL: {url}")
                try:
                    process_blog(
                        url=url,
                        model_name=model_name,
                        max_iterations=iterations,
                        publish=publish
                    )
                    print(f"URL处理完成: {url}")
                except Exception as e:
                    print(f"处理URL时出错: {url}")
                    print(f"错误信息: {e}")
            
            print("\n所有URL处理完成!")
        
        # 在新线程中运行，避免GUI卡死
        threading.Thread(target=_process_all).start()
        
        # 配置网格
        process_tab.columnconfigure(1, weight=1)
    
    def create_settings_tab(self):
        """创建设置选项卡"""
        settings_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(settings_tab, text="设置")
        
        # 配置文件路径
        ttk.Label(settings_tab, text="配置文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.config_path_var = tk.StringVar(value=get_config_path())
        ttk.Entry(settings_tab, textvariable=self.config_path_var, width=50).grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        ttk.Button(settings_tab, text="浏览...", command=self.browse_config).grid(row=0, column=2, padx=5, pady=5)
        
        # 加载配置按钮
        ttk.Button(settings_tab, text="加载配置", command=self.load_config).grid(row=1, column=1, pady=10)
        
        # 配置网格
        settings_tab.columnconfigure(1, weight=1)
    
    def create_log_area(self):
        """创建日志区域"""
        log_frame = ttk.LabelFrame(self.main_frame, text="日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 创建滚动文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, width=80, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state="disabled")
        
        # 清除日志按钮
        ttk.Button(log_frame, text="清除日志", command=self.clear_log).pack(pady=5)
    
    def clear_log(self):
        """清除日志"""
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state="disabled")
    
    def browse_scrape_output(self):
        """浏览爬取输出文件"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            self.scrape_output_var.set(filename)
    
    # Add the missing method here
    def browse_scrape_output_dir(self):
        """浏览爬取输出目录"""
        folder = filedialog.askdirectory()
        if folder:
            self.scrape_output_dir_var.set(folder)
    
    # Add the missing scrape_multiple method
    def scrape_multiple(self):
        """爬取多个博客URL"""
        # 获取URL列表
        urls_text = self.scrape_urls_text.get(1.0, tk.END).strip()
        if not urls_text:
            messagebox.showerror("错误", "请输入至少一个博客URL")
            return
        
        # 分割URL（支持换行分隔）
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        # 获取爬虫类型和输出目录
        scraper_type = self.scrape_type_var.get()
        output_dir = self.scrape_output_dir_var.get()
        
        print(f"开始爬取 {len(urls)} 个博客URL")
        print(f"爬虫类型: {scraper_type}")
        print(f"输出目录: {output_dir}")
        
        def _scrape_all():
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 创建爬虫
            scraper_factory = ScraperFactory()
            
            for i, url in enumerate(urls):
                print(f"\n爬取第 {i+1}/{len(urls)} 个URL: {url}")
                try:
                    # 生成输出文件名
                    url_parts = url.split('/')
                    filename = url_parts[-1] if url_parts[-1] else url_parts[-2]
                    output_file = os.path.join(output_dir, f"{filename}.md")
                    
                    # 创建爬虫并爬取
                    scraper = scraper_factory.create_scraper(scraper_type, self.config)
                    result = scraper.scrape(url)
                    
                    # 保存结果
                    if result:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(result)
                        print(f"爬取成功，保存到: {output_file}")
                    else:
                        print(f"爬取失败: {url}")
                
                except Exception as e:
                    print(f"爬取URL时出错: {url}")
                    print(f"错误信息: {e}")
            
            print("\n所有URL爬取完成!")
        
        # 在新线程中运行，避免GUI卡死
        threading.Thread(target=_scrape_all).start()
    
    def browse_rewrite_input(self):
        """浏览改写输入文件"""
        filename = filedialog.askopenfilename(
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            self.rewrite_input_var.set(filename)
    
    def browse_rewrite_output(self):
        """浏览改写输出文件"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            self.rewrite_output_var.set(filename)
    
    def browse_publish_input(self):
        """浏览发布输入文件"""
        filename = filedialog.askopenfilename(
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            self.publish_input_var.set(filename)
    
    # Add the missing method here
    def browse_publish_images(self):
        """浏览发布图片文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.publish_images_var.set(folder)
    
    def browse_config(self):
        """浏览配置文件"""
        filename = filedialog.askopenfilename(
            filetypes=[("YAML文件", "*.yaml"), ("所有文件", "*.*")]
        )
        if filename:
            self.config_path_var.set(filename)
    
    def load_config(self):
        """加载配置"""
        config_path = self.config_path_var.get()
        if os.path.exists(config_path):
            self.config = load_config(config_path)
            print(f"配置已加载: {config_path}")
        else:
            messagebox.showerror("错误", f"配置文件不存在: {config_path}")
    
    def run_in_thread(self, func, *args, **kwargs):
        """在线程中运行函数"""
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
    
    def scrape(self):
        """爬取博客内容"""
        url = self.scrape_url_var.get()
        output = self.scrape_output_var.get()
        
        if not url:
            messagebox.showerror("错误", "请输入博客URL")
            return
        
        def _scrape():
            print(f"开始爬取: {url}")
            
            try:
                scraper = ScraperFactory.get_scraper(url, self.config_path_var.get())
                blog_data = scraper.scrape(url)
                
                if not blog_data:
                    print("爬取失败")
                    return
                
                # 保存内容
                content_path = self.file_handler.save_content(
                    blog_data['content'],
                    output,
                    "scraped"
                )
                
                # 保存元数据
                metadata_filename = f"{os.path.splitext(output)[0]}_metadata.json" if output else None
                metadata_path = self.file_handler.save_json(
                    blog_data['metadata'],
                    metadata_filename,
                    "scraped"
                )
                
                print(f"内容已保存到: {content_path}")
                print(f"元数据已保存到: {metadata_path}")
                
                messagebox.showinfo("成功", "爬取完成")
            
            except Exception as e:
                print(f"爬取过程中发生错误: {e}")
                messagebox.showerror("错误", f"爬取失败: {e}")
        
        self.run_in_thread(_scrape)
    
    def rewrite(self):
        """改写博客内容"""
        input_file = self.rewrite_input_var.get()
        output_file = self.rewrite_output_var.get()
        model_name = self.rewrite_model_var.get()
        iterations = self.rewrite_iterations_var.get()
        
        if not input_file:
            messagebox.showerror("错误", "请选择输入文件")
            return
        
        if not os.path.exists(input_file):
            messagebox.showerror("错误", f"输入文件不存在: {input_file}")
            return
        
        if not output_file:
            messagebox.showerror("错误", "请选择输出文件")
            return
        
        print(f"开始改写博客内容")
        print(f"输入文件: {input_file}")
        print(f"输出文件: {output_file}")
        print(f"使用模型: {model_name}")
        print(f"SEO优化迭代次数: {iterations}")
        
        def _rewrite():
            try:
                # 加载内容
                with open(input_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not content:
                    print(f"无法加载内容: {input_file}")
                    return
                
                # 创建模型
                model_factory = ModelFactory()
                model = model_factory.create_model(model_name, self.config)
                
                # 改写内容
                print("开始改写内容...")
                rewritten_content = content
                
                for i in range(iterations):
                    print(f"执行第 {i+1}/{iterations} 次SEO优化...")
                    rewritten_content = model.rewrite_content(rewritten_content)
                
                # 保存结果
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(rewritten_content)
                
                print(f"改写完成，已保存到: {output_file}")
                messagebox.showinfo("成功", f"博客内容已改写并保存到: {output_file}")
            
            except Exception as e:
                print(f"改写过程中发生错误: {e}")
                messagebox.showerror("错误", f"改写失败: {e}")
        
        # 在新线程中运行，避免GUI卡死
        threading.Thread(target=_rewrite).start()
    
    # Change this method name from 'publish' to 'publish_post'
    def publish_post(self):
        """发布到WordPress"""
        input_file = self.publish_input_var.get()
        title = self.publish_title_var.get()
        excerpt = self.publish_excerpt_var.get()
        status = self.publish_status_var.get()
        
        if not input_file:
            messagebox.showerror("错误", "请选择输入文件")
            return
        
        if not os.path.exists(input_file):
            messagebox.showerror("错误", f"输入文件不存在: {input_file}")
            return
        
        if not title:
            messagebox.showerror("错误", "请输入文章标题")
            return
        
        def _publish():
            print(f"开始发布文章: {title}")
            
            try:
                # 加载内容
                with open(input_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not content:
                    print(f"无法加载内容: {input_file}")
                    return
                
                # 发布内容
                publisher = WordPressPublisher(self.config)
                
                result = publisher.publish_post(
                    title=title,
                    content=content,
                    excerpt=excerpt,
                    status=status
                )
                
                if result:
                    print(f"文章已发布: {result.get('link', '')}")
                    messagebox.showinfo("成功", f"文章已发布: {result.get('link', '')}")
                else:
                    print("文章发布失败")
                    messagebox.showerror("错误", "文章发布失败")
            
            except Exception as e:
                print(f"发布过程中发生错误: {e}")
                messagebox.showerror("错误", f"发布失败: {e}")
        
        self.run_in_thread(_publish)

if __name__ == "__main__":
    root = tk.Tk()
    app = BlogProcessorGUI(root)
    root.mainloop()