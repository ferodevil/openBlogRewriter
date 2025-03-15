import sys
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import queue
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.join('d:', 'Python', 'myblog'))

from main import process_blog, load_config
from src.scrapers.scraper_factory import ScraperFactory
from src.models.model_factory import ModelFactory
from src.publishers.wordpress_publisher import WordPressPublisher
from src.utils.file_handler import FileHandler

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
    
    def __init__(self, root):
        """初始化GUI"""
        self.root = root
        self.root.title("博客内容采集与改写发布系统")
        self.root.geometry("800x600")
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建选项卡
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 创建各个选项卡
        self.create_scrape_tab()
        self.create_rewrite_tab()
        self.create_publish_tab()
        self.create_process_tab()
        self.create_settings_tab()
        
        # 创建日志区域
        self.create_log_area()
        
        # 重定向标准输出到日志区域
        self.redirect = RedirectText(self.log_text)
        sys.stdout = self.redirect
        sys.stderr = self.redirect
        
        # 加载配置
        self.config = load_config()
        
        # 初始化文件处理器
        self.file_handler = FileHandler()
    
    def create_scrape_tab(self):
        """创建爬取选项卡"""
        scrape_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(scrape_tab, text="爬取")
        
        # URL输入
        ttk.Label(scrape_tab, text="博客URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.scrape_url_var = tk.StringVar()
        ttk.Entry(scrape_tab, textvariable=self.scrape_url_var, width=50).grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        
        # 输出文件
        ttk.Label(scrape_tab, text="输出文件:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.scrape_output_var = tk.StringVar()
        ttk.Entry(scrape_tab, textvariable=self.scrape_output_var, width=50).grid(row=1, column=1, sticky=tk.W+tk.E, pady=5)
        ttk.Button(scrape_tab, text="浏览...", command=self.browse_scrape_output).grid(row=1, column=2, padx=5, pady=5)
        
        # 爬取按钮
        ttk.Button(scrape_tab, text="爬取", command=self.scrape).grid(row=2, column=1, pady=10)
        
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
        self.rewrite_model_var = tk.StringVar(value="openai")
        model_combo = ttk.Combobox(rewrite_tab, textvariable=self.rewrite_model_var, width=20)
        model_combo['values'] = ('openai', 'azure_openai', 'anthropic', 'baidu', 'ollama')
        model_combo.grid(row=1, column=1, sticky=tk.W, pady=5)

        # 模型选择
        ttk.Label(process_tab, text="模型:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.process_model_var = tk.StringVar(value="openai")
        model_combo = ttk.Combobox(process_tab, textvariable=self.process_model_var, width=20)
        model_combo['values'] = ('openai', 'azure_openai', 'anthropic', 'baidu', 'ollama')
        model_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 输出文件
        ttk.Label(rewrite_tab, text="输出文件:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.rewrite_output_var = tk.StringVar()
        ttk.Entry(rewrite_tab, textvariable=self.rewrite_output_var, width=50).grid(row=2, column=1, sticky=tk.W+tk.E, pady=5)
        ttk.Button(rewrite_tab, text="浏览...", command=self.browse_rewrite_output).grid(row=2, column=2, padx=5, pady=5)
        
        # 改写按钮
        ttk.Button(rewrite_tab, text="改写", command=self.rewrite).grid(row=3, column=1, pady=10)
        
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
        
        # 标题
        ttk.Label(publish_tab, text="标题:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.publish_title_var = tk.StringVar()
        ttk.Entry(publish_tab, textvariable=self.publish_title_var, width=50).grid(row=1, column=1, sticky=tk.W+tk.E, pady=5)
        
        # 摘要
        ttk.Label(publish_tab, text="摘要:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.publish_excerpt_var = tk.StringVar()
        ttk.Entry(publish_tab, textvariable=self.publish_excerpt_var, width=50).grid(row=2, column=1, sticky=tk.W+tk.E, pady=5)
        
        # 发布按钮
        ttk.Button(publish_tab, text="发布", command=self.publish).grid(row=3, column=1, pady=10)
        
        # 配置网格
        publish_tab.columnconfigure(1, weight=1)
    
    def create_process_tab(self):
        """创建处理选项卡"""
        process_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(process_tab, text="完整处理")
        
        # URL输入
        ttk.Label(process_tab, text="博客URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.process_url_var = tk.StringVar()
        ttk.Entry(process_tab, textvariable=self.process_url_var, width=50).grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        
        # 模型选择
        ttk.Label(process_tab, text="模型:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.process_model_var = tk.StringVar(value="openai")
        model_combo = ttk.Combobox(process_tab, textvariable=self.process_model_var, width=20)
        model_combo['values'] = ('openai', 'azure_openai', 'anthropic', 'baidu')
        model_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 发布选项
        self.process_publish_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(process_tab, text="发布到WordPress", variable=self.process_publish_var).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 处理按钮
        ttk.Button(process_tab, text="处理", command=self.process).grid(row=3, column=1, pady=10)
        
        # 配置网格
        process_tab.columnconfigure(1, weight=1)
    
    def create_settings_tab(self):
        """创建设置选项卡"""
        settings_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(settings_tab, text="设置")
        
        # 配置文件路径
        ttk.Label(settings_tab, text="配置文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.config_path_var = tk.StringVar(value=os.path.join('d:', 'Python', 'myblog', 'config', 'config.yaml'))
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
        model_name = self.rewrite_model_var.get()
        output = self.rewrite_output_var.get()
        
        if not input_file:
            messagebox.showerror("错误", "请选择输入文件")
            return
        
        if not os.path.exists(input_file):
            messagebox.showerror("错误", f"输入文件不存在: {input_file}")
            return
        
        def _rewrite():
            print(f"开始使用{model_name}模型改写内容")
            
            try:
                # 加载内容
                content = self.file_handler.load_content(input_file)
                
                if not content:
                    print(f"无法加载内容: {input_file}")
                    return
                
                # 加载元数据（如果有）
                metadata = None
                metadata_path = f"{os.path.splitext(input_file)[0]}_metadata.json"
                if os.path.exists(metadata_path):
                    metadata = self.file_handler.load_json(metadata_path)
                
                # 改写内容
                model = ModelFactory.get_model(model_name, self.config_path_var.get())
                rewritten_content = model.rewrite_content(content, metadata)
                
                if not rewritten_content:
                    print("内容改写失败")
                    return
                
                # 保存改写后的内容
                output_path = self.file_handler.save_content(
                    rewritten_content,
                    output,
                    "rewritten"
                )
                
                print(f"改写后的内容已保存到: {output_path}")
                
                messagebox.showinfo("成功", "内容改写完成")
            
            except Exception as e:
                print(f"改写过程中发生错误: {e}")
                messagebox.showerror("错误", f"改写失败: {e}")
        
        self.run_in_thread(_rewrite)
    
    def publish(self):
        """发布到WordPress"""
        input_file = self.publish_input_var.get()
        title = self.publish_title_var.get()
        excerpt = self.publish_excerpt_var.get()
        
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
                content = self.file_handler.load_content(input_file)
                
                if not content:
                    print(f"无法加载内容: {input_file}")
                    return
                
                # 发布内容
                publisher = WordPressPublisher(self.config_path_var.get())
                
                result = publisher.publish_post(
                    title=title,
                    content=content,
                    excerpt=excerpt
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
    
    def process(self):
        """完整处理（爬取+改写+发布）"""
        url = self.process_url_var.get()
        model_name = self.process_model_var.get()
        publish = self.process_publish_var.get()
        
        if not url:
            messagebox.showerror("错误", "请输入博客URL")
            return
        
        def _process():
            print(f"开始处理: {url}")
            
            try:
                success = process_blog(url, model_name, publish, self.config_path_var.get())
                
                if success:
                    print("处理完成")
                    messagebox.showinfo("成功", "博客处理完成")
                else:
                    print("处理失败")
                    messagebox.showerror("错误", "博客处理失败")
            
            except Exception as e:
                print(f"处理过程中发生错误: {e}")
                messagebox.showerror("错误", f"处理失败: {e}")
        
        self.run_in_thread(_process)

if __name__ == "__main__":
    root = tk.Tk()
    app = BlogProcessorGUI(root)
    root.mainloop()