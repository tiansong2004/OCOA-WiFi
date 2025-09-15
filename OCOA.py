import sys
import os
import json
import re
import webbrowser
import subprocess
import urllib.request
import urllib.error
import logging
from logging.handlers import TimedRotatingFileHandler
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import scrolledtext


def enable_high_dpi_scaling():
	try:
		import ctypes
		ctypes.windll.shcore.SetProcessDpiAwareness(1)
	except Exception:
		pass


class App(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title("网络一键认证 - 控制台")
		self.configure(bg="#f5f7fb")
		
		# 设置窗口初始大小和最小大小
		self.geometry("600x500")  # 设置初始窗口大小
		self.minsize(500, 400)    # 设置最小窗口大小
		
		# 将窗口居中显示
		screen_width = self.winfo_screenwidth()
		screen_height = self.winfo_screenheight()
		x = (screen_width - 600) // 2
		y = (screen_height - 500) // 2
		self.geometry(f"600x500+{x}+{y}")

		# Settings
		# Persist user data under data/user_settings.json
		self.data_dir = os.path.join(os.path.dirname(__file__), "data")
		self.settings_path = os.path.join(self.data_dir, "user_settings.json")
		self.logs_dir = os.path.join(self.data_dir, "logs")
		self._setup_logging()
		logging.getLogger(__name__).info("应用启动中…")
		self.settings = {
			"wifi_ssid": "",
			"auth_url": ""
		}
		self._load_settings()

		self.style = ttk.Style()
		available_themes = self.style.theme_names()
		if "vista" in available_themes:
			self.style.theme_use("vista")
		elif "clam" in available_themes:
			self.style.theme_use("clam")
			
		# 配置版权信息标签样式
		self.style.configure("Subtle.TLabel", 
							foreground='#666666',  # 使用深灰色
							font=('微软雅黑', 9),   # 使用微软雅黑字体
							padding=(0, 2))

		self._configure_styles()
		self._build_ui()
		self._center_window(1200, 800)
		logging.getLogger(__name__).info("界面已初始化并居中")
		# 默认日志过滤级别
		self._ui_log_level = logging.INFO
		self._attach_ui_logger()

		# 启动后自动检测网络与目标WiFi
		self.after(400, self._auto_check_flow)

		# 主窗口淡入效果
		try:
			self.attributes("-alpha", 0.0)
			self.after(10, lambda: self._fade_in(self, target=1.0, step=0.06, interval=14))
		except Exception:
			pass

	def _configure_styles(self):
		default_font = ("Microsoft YaHei UI", 10)
		header_font = ("Microsoft YaHei UI", 12, "bold")

		self.option_add("*Font", default_font)

		self.style.configure(
			"Card.TFrame",
			background="#ffffff",
			borderwidth=0,
			relief="flat"
		)

		self.style.configure(
			"Header.TLabel",
			background="#ffffff",
			foreground="#1f2937",
			font=header_font
		)

		self.style.configure(
			"Subtle.TLabel",
			background="#ffffff",
			foreground="#6b7280"
		)

		self.style.configure(
			"Primary.TButton",
			font=default_font,
			padding=(14, 8)
		)

		self.style.map(
			"Primary.TButton",
			foreground=[("active", "#111827")],
			background=[("active", "#e5e7eb")]
		)

		# 悬停态按钮样式（轻微“放大”效果）
		self.style.configure(
			"PrimaryHover.TButton",
			font=default_font,
			padding=(16, 10)
		)

	def _build_ui(self):
		outer = ttk.Frame(self, padding=0)
		outer.pack(fill="both", expand=True)

		# 渐变抬头区域
		header = tk.Canvas(outer, height=90, highlightthickness=0, bd=0)
		header.pack(fill="x", side="top")
		self._draw_horizontal_gradient(header, "#4f46e5", "#06b6d4")
		header.create_text(24, 26, anchor="nw", text="网络一键认证", fill="#ffffff",
			font=("Microsoft YaHei UI", 16, "bold"))
		header.create_text(26, 58, anchor="nw", text="快速认证 · 一键断开 · 简洁设置", fill="#e5e7eb",
			font=("Microsoft YaHei UI", 10))

		# 内容区
		# 创建主内容区域
		content = ttk.Frame(outer, padding=20)
		content.pack(fill="both", expand=True)

		# 创建卡片容器
		card = ttk.Frame(content, style="Card.TFrame", padding=20)
		card.pack(fill="both", expand=True)

		# 创建内容区域
		main_content = ttk.Frame(card)
		main_content.pack(fill="both", expand=True)

		title = ttk.Label(main_content, text="网络一键认证", style="Header.TLabel")
		title.pack(anchor="w")

		sub = ttk.Label(main_content, text="欢迎你来到网络一键认证，当前版本为v2.0", style="Subtle.TLabel")
		sub.pack(anchor="w", pady=(2, 20))  # 增加底部间距

		# 功能按钮区域
		btns = ttk.Frame(main_content)
		btns.pack(fill="x", pady=(0, 20))  # 增加底部间距
		
		# 设置按钮网格的列权重
		btns.grid_columnconfigure(0, weight=1)
		btns.grid_columnconfigure(1, weight=1)
		btns.grid_columnconfigure(2, weight=1)
		btns.grid_columnconfigure(3, weight=1)

		button1 = ttk.Button(btns, text="🔗 一键认证", style="Primary.TButton", command=self.on_primary_action)
		button2 = ttk.Button(btns, text="⛔ 断开连接", style="Primary.TButton", command=self.on_disconnect)
		button3 = ttk.Button(btns, text="⚙️ 设置", style="Primary.TButton", command=self.on_settings)
		button4 = ttk.Button(btns, text="📶 连接WiFi", style="Primary.TButton", command=self.on_connect_wifi)

		button1.grid(row=0, column=0, sticky="ew", padx=(0, 8))
		button2.grid(row=0, column=1, sticky="ew", padx=8)
		button3.grid(row=0, column=2, sticky="ew", padx=8)
		button4.grid(row=0, column=3, sticky="ew", padx=(8, 0))

		# 添加分隔线
		separator = ttk.Separator(main_content, orient="horizontal")
		separator.pack(fill="x", pady=(0, 20))  # 增加底部间距

		btns.grid_columnconfigure(0, weight=1)
		btns.grid_columnconfigure(1, weight=1)
		btns.grid_columnconfigure(2, weight=1)
		btns.grid_columnconfigure(3, weight=1)

		# Log toolbar
		log_bar = ttk.Frame(main_content)
		log_bar.pack(fill="x", pady=(16, 6))
		log_label = ttk.Label(log_bar, text="运行日志", style="Subtle.TLabel")
		log_label.pack(side="left")
		# Level filter
		level_var = tk.StringVar(value="INFO")
		self._log_level_var = level_var
		levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
		level_menu = ttk.OptionMenu(log_bar, level_var, "INFO", *levels, command=lambda _=None: self._on_change_log_level())
		level_menu.pack(side="right")
		clear_btn = ttk.Button(log_bar, text="清空", style="Primary.TButton", command=lambda: self._clear_log_view())
		clear_btn.pack(side="right", padx=(0, 8))

		# Log viewer (dark, monospace, no wrap)
		self.log_text = scrolledtext.ScrolledText(
			main_content,
			height=12,
			wrap="none",
			state="disabled",
			bg="#0b1021",
			fg="#e5e7eb",
			insertbackground="#e5e7eb",
			borderwidth=0,
			highlightthickness=0,
			font=("Consolas", 10)
		)
		# Color tags for levels
		self.log_text.tag_configure("DEBUG", foreground="#67e8f9")
		self.log_text.tag_configure("INFO", foreground="#e5e7eb")
		self.log_text.tag_configure("WARNING", foreground="#fbbf24")
		self.log_text.tag_configure("ERROR", foreground="#f87171")
		self.log_text.pack(fill="both", expand=True)  # 让日志区域可以随窗口调整大小
		
		# 创建底部版权信息区域
		separator = ttk.Separator(card)
		separator.pack(fill="x", side="bottom", pady=(10, 0))
		
		footer = ttk.Label(card, text="© 2025 网络一键认证工具", style="Subtle.TLabel")
		footer.pack(side="bottom", pady=(10, 5))  # 调整上下边距

		# 悬停动效
		for b in (button1, button2, button3):
			self._apply_button_hover(b)
		for b in (button4,):
			self._apply_button_hover(b)

	def _center_window(self, width, height):
		self.update_idletasks()
		w = width
		h = height
		screen_w = self.winfo_screenwidth()
		screen_h = self.winfo_screenheight()
		x = int((screen_w / 2) - (w / 2))
		y = int((screen_h / 2) - (h / 2))
		self.geometry(f"{w}x{h}+{x}+{y}")
		self.minsize(w, h)

	def on_primary_action(self):
		url = (self.settings.get("auth_url") or "").strip()
		if not url:
			self._toast("请先在“设置”中配置认证 URL")
			logging.getLogger(__name__).warning("未配置认证URL，已打开设置")
			self._open_settings_dialog()
			return
		try:
			webbrowser.open(url, new=2)
			self._toast("已打开认证页面")
			logging.getLogger(__name__).info(f"正在打开认证链接：{url}")
		except Exception:
			self._toast("无法打开浏览器，请手动访问 URL")
			logging.getLogger(__name__).exception("打开认证链接失败")

	def _auto_check_flow(self):
		ssid_target = (self.settings.get("wifi_ssid") or "").strip()
		auth_url = (self.settings.get("auth_url") or "").strip()
		if not ssid_target:
			self._toast("未设置WiFi名称，请先到设置中配置")
			logging.getLogger(__name__).warning("未配置WiFi名称，跳过自动检测")
			return
		current = self._get_connected_ssid()
		logging.getLogger(__name__).info(f"当前WiFi：{current or '未连接'}，目标WiFi：{ssid_target}")
		if current and current == ssid_target:
			# 已连到目标WiFi，检测是否可用
			usable = self._is_network_usable()
			logging.getLogger(__name__).info(f"网络可用性（目标WiFi）：{usable}")
			if not usable and auth_url:
				self._toast("网络不可用，正在打开认证页面…")
				try:
					webbrowser.open(auth_url, new=2)
					logging.getLogger(__name__).info(f"网络不可用，打开认证链接：{auth_url}")
				except Exception:
					logging.getLogger(__name__).exception("网络不可用后打开认证链接失败")
			return
		# 未连接目标WiFi
		if messagebox.askyesno("提示", f"当前WiFi为：{current or '未连接'}\n是否连接指定WiFi：{ssid_target}？"):
			ok = self._connect_to_wifi(ssid_target)
			if not ok:
				self._toast("连接指令已发送，若失败请检查是否已创建同名配置文件")
				logging.getLogger(__name__).warning("WiFi连接指令返回异常或未知")
			# 简单等待后复检
			self.after(2500, self._auto_check_after_connect)
		else:
			self._toast("已取消自动连接")
			logging.getLogger(__name__).info("用户取消了自动连接")

	def _auto_check_after_connect(self):
		ssid_target = (self.settings.get("wifi_ssid") or "").strip()
		auth_url = (self.settings.get("auth_url") or "").strip()
		current = self._get_connected_ssid()
		if current != ssid_target:
			self._toast("未成功连接到目标WiFi")
			logging.getLogger(__name__).error("尝试后未能连接到目标WiFi")
			return
		if not self._is_network_usable() and auth_url:
			self._toast("网络不可用，正在打开认证页面…")
			try:
				webbrowser.open(auth_url, new=2)
				logging.getLogger(__name__).info("连接后网络仍不可用，打开认证链接")
			except Exception:
				logging.getLogger(__name__).exception("连接后打开认证链接失败")

	def on_disconnect(self):
		ssid = self._get_connected_ssid()
		try:
			res = subprocess.run(
				["netsh", "wlan", "disconnect"],
				capture_output=True,
				text=False,
				timeout=6
			)
			if res.returncode == 0:
				display_ssid = ssid if ssid and "\ufffd" not in ssid else "当前WiFi"
				self._toast(f"已断开：{display_ssid}")
				logging.getLogger(__name__).info(f"已断开WiFi：{ssid}")
			else:
				self._toast("断开失败，请重试或以管理员运行")
				logging.getLogger(__name__).error("WiFi断开指令失败")
		except Exception:
			self._toast("断开失败，请检查系统权限")
			logging.getLogger(__name__).exception("断开WiFi时发生异常")

	def on_connect_wifi(self):
		ssid_target = (self.settings.get("wifi_ssid") or "").strip()
		if not ssid_target:
			self._toast("未设置WiFi名称，请先到设置中配置")
			self._open_settings_dialog()
			return
		logging.getLogger(__name__).info(f"User requested connect to SSID: {ssid_target}")
		ok = self._connect_to_wifi(ssid_target)
		if ok:
			self._toast("已发送连接指令，正在尝试连接…")
			self.after(2500, self._auto_check_after_connect)
		else:
			self._toast("指令发送失败，可能需要管理员或未创建配置文件")
			logging.getLogger(__name__).error("Connect command failed or returned non-zero")

	def on_settings(self):
		self._open_settings_dialog()

	def _toast(self, message: str):
		toast = tk.Toplevel(self)
		toast.overrideredirect(True)
		toast.configure(bg="#111827")

		label = tk.Label(toast, text=message, bg="#111827", fg="#f9fafb", padx=14, pady=8)
		label.pack()

		self.update_idletasks()
		x = self.winfo_x() + self.winfo_width() - toast.winfo_reqwidth() - 16
		y = self.winfo_y() + self.winfo_height() - toast.winfo_reqheight() - 16
		toast.geometry(f"+{x}+{y}")

		# 淡入 + 自动淡出
		try:
			toast.attributes("-alpha", 0.0)
			self._fade_in(toast, target=0.96, step=0.12, interval=18)
			def _close():
				self._fade_out(toast, step=0.12, interval=18, on_done=toast.destroy)
			toast.after(1300, _close)
		except Exception:
			toast.after(1200, toast.destroy)

	def _apply_button_hover(self, btn):
		def on_enter(_):
			try:
				btn.configure(style="PrimaryHover.TButton")
				btn.configure(cursor="hand2")
			except Exception:
				pass
		def on_leave(_):
			try:
				btn.configure(style="Primary.TButton")
				btn.configure(cursor="")
			except Exception:
				pass
		btn.bind("<Enter>", on_enter)
		btn.bind("<Leave>", on_leave)

	def _fade_in(self, window, target=1.0, step=0.08, interval=16):
		try:
			alpha = float(window.attributes("-alpha"))
		except Exception:
			return
		alpha = min(target, alpha + step)
		try:
			window.attributes("-alpha", alpha)
		except Exception:
			return
		if alpha < target:
			self.after(interval, lambda: self._fade_in(window, target, step, interval))

	def _fade_out(self, window, step=0.08, interval=16, on_done=None):
		try:
			alpha = float(window.attributes("-alpha"))
		except Exception:
			if on_done:
				on_done()
			return
		alpha = max(0.0, alpha - step)
		try:
			window.attributes("-alpha", alpha)
		except Exception:
			if on_done:
				on_done()
			return
		if alpha > 0.0:
			self.after(interval, lambda: self._fade_out(window, step, interval, on_done))
		else:
			if on_done:
				on_done()

	def _draw_horizontal_gradient(self, canvas: tk.Canvas, start_hex: str, end_hex: str):
		# 左到右渐变（以细矩形模拟）
		canvas.delete("all")
		width = canvas.winfo_width() or canvas.winfo_reqwidth() or 900
		height = canvas.winfo_height() or canvas.winfo_reqheight() or 90
		steps = max(1, min(256, width))
		def hex_to_rgb(h):
			h = h.lstrip('#')
			return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
		r1, g1, b1 = hex_to_rgb(start_hex)
		r2, g2, b2 = hex_to_rgb(end_hex)
		for i in range(steps):
			r = int(r1 + (r2 - r1) * i / steps)
			g = int(g1 + (g2 - g1) * i / steps)
			b = int(b1 + (b2 - b1) * i / steps)
			color = f"#{r:02x}{g:02x}{b:02x}"
			canvas.create_rectangle(i * (width/steps), 0, (i+1) * (width/steps), height, outline='', fill=color)
		# 监听尺寸变化重绘
		def on_resize(_):
			self._draw_horizontal_gradient(canvas, start_hex, end_hex)
		canvas.bind("<Configure>", on_resize)

	def _get_connected_ssid(self) -> str:
		try:
			res = subprocess.run(
				["netsh", "wlan", "show", "interfaces"],
				capture_output=True,
				text=False,
				timeout=6
			)
			raw = res.stdout or b""
			output = self._decode_best_effort(raw)
			ssid_value = ""
			for raw_line in output.splitlines():
				line = raw_line.strip()
				if not line:
					continue
				# Skip BSSID lines
				if line.upper().startswith("BSSID"):
					continue
				if line.upper().startswith("SSID") and ":" in line:
					ssid_value = line.split(":", 1)[1].strip()
					break
			return ssid_value
		except Exception:
			logging.getLogger(__name__).exception("Failed to get connected SSID")
			return ""

	def _connect_to_wifi(self, ssid: str) -> bool:
		try:
			# 依据现有配置文件进行连接：profile 名通常与 SSID 相同
			res = subprocess.run(
				["netsh", "wlan", "connect", f"name={ssid}"],
				capture_output=True,
				text=False,
				timeout=8
			)
			return res.returncode == 0
		except Exception:
			logging.getLogger(__name__).exception("Exception during WiFi connect command")
			return False

	def _is_network_usable(self) -> bool:
		# 通过公共探测地址判断是否真正“可用”
		test_endpoints = [
			"https://www.gstatic.com/generate_204",
			"http://www.msftconnecttest.com/connecttest.txt"
		]
		for url in test_endpoints:
			try:
				req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
				with urllib.request.urlopen(req, timeout=3) as resp:
					code = getattr(resp, 'status', resp.getcode())
					final_url = getattr(resp, 'url', url)
					# 若被重定向到认证门户，则 final_url 变化明显
					redirected = (final_url and final_url.split('/')[2] != url.split('/')[2])
					if code == 204 and not redirected:
						return True
					if code == 200:
						content = resp.read(256).decode('utf-8', errors='ignore')
						if "Microsoft" in content or "Success" in content or len(content) <= 64:
							if not redirected:
								return True
			except Exception:
				logging.getLogger(__name__).warning(f"Probe failed: {url}")
				continue
		return False

	def _setup_logging(self):
		try:
			os.makedirs(self.logs_dir, exist_ok=True)
			logger = logging.getLogger()
			logger.setLevel(logging.INFO)
			file_handler = TimedRotatingFileHandler(
				filename=os.path.join(self.logs_dir, "app.log"), when="midnight", backupCount=7, encoding="utf-8"
			)
			file_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
			file_handler.setFormatter(file_fmt)
			logger.addHandler(file_handler)
			console = logging.StreamHandler()
			console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
			logger.addHandler(console)
		except Exception:
			logging.basicConfig(level=logging.INFO)

	def _attach_ui_logger(self):
		class TkTextHandler(logging.Handler):
			def __init__(self, widget):
				super().__init__()
				self.widget = widget
				self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
			def emit(self, record):
				try:
					msg = self.format(record)
					# Localize level and common phrases to Chinese for UI readability
					level = record.levelname
					level_cn = {"DEBUG": "调试", "INFO": "信息", "WARNING": "警告", "ERROR": "错误"}.get(level, level)
					msg = msg.replace(f"[{level}]", f"[{level_cn}]")
					translations = {
						"Application starting…": "应用启动中…",
						"UI initialized and window centered": "界面已初始化并居中",
						"Auth URL missing; prompting settings dialog": "未配置认证URL，已打开设置",
						"Opening auth URL: ": "正在打开认证链接：",
						"Failed to open auth URL": "打开认证链接失败",
						"No SSID configured; skipping auto check": "未配置WiFi名称，跳过自动检测",
						"Current SSID: ": "当前WiFi：",
						"Target SSID: ": "目标WiFi：",
						"Network usable on target SSID: ": "网络可用性（目标WiFi）：",
						"Opening auth URL due to unusable network: ": "网络不可用，打开认证链接：",
						"Failed to open auth URL after unusable check": "网络不可用后打开认证链接失败",
						"WiFi connect command returned non-zero or uncertain result": "WiFi连接指令返回异常或未知",
						"User cancelled auto-connect prompt": "用户取消了自动连接",
						"Failed to connect to target SSID after attempt": "尝试后未能连接到目标WiFi",
						"Opening auth URL after connect but network unusable": "连接后网络仍不可用，打开认证链接",
						"Failed to open auth URL after connect": "连接后打开认证链接失败",
						"Disconnected from WiFi: ": "已断开WiFi：",
						"WiFi disconnect command failed": "WiFi断开指令失败",
						"Exception during WiFi disconnect": "断开WiFi时发生异常",
						"Failed to get connected SSID": "获取当前WiFi失败",
						"Exception during WiFi connect command": "执行WiFi连接指令时发生异常",
						"Probe failed: ": "连通性探测失败："
					}
					for k, v in translations.items():
						msg = msg.replace(k, v)
					level = record.levelname
					# Filter by UI-selected level
					level_order = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
					min_level = getattr(self.widget.master.master.master.master, "_ui_log_level", logging.INFO)
					if level_order.get(level, 100) < min_level:
						return
					self.widget.configure(state="normal")
					self.widget.insert("end", msg + "\n", (level,))
					self.widget.configure(state="disabled")
					self.widget.see("end")
				except Exception:
					pass
		try:
			ui_handler = TkTextHandler(self.log_text)
			logging.getLogger().addHandler(ui_handler)
		except Exception:
			pass

	def _on_change_log_level(self):
		mapping = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING, "ERROR": logging.ERROR}
		self._ui_log_level = mapping.get(self._log_level_var.get(), logging.INFO)

	def _clear_log_view(self):
		try:
			self.log_text.configure(state="normal")
			self.log_text.delete("1.0", "end")
			self.log_text.configure(state="disabled")
		except Exception:
			pass

	def _decode_best_effort(self, data: bytes) -> str:
		# Try multiple encodings to avoid Chinese garbling from netsh
		for enc in ("utf-8", "gbk", "cp936"):
			try:
				return data.decode(enc)
			except Exception:
				pass
		try:
			return data.decode("mbcs", errors="ignore")
		except Exception:
			return data.decode(errors="ignore")

	def _load_settings(self):
		try:
			if os.path.exists(self.settings_path):
				with open(self.settings_path, "r", encoding="utf-8") as f:
					data = json.load(f)
					if isinstance(data, dict):
						self.settings.update({
							"wifi_ssid": data.get("wifi_ssid", ""),
							"auth_url": data.get("auth_url", "")
						})
		except Exception:
			# Ignore malformed file; keep defaults
			pass

	def _save_settings(self, wifi_ssid: str, auth_url: str) -> bool:
		try:
			# Ensure data directory exists
			os.makedirs(self.data_dir, exist_ok=True)
			data = {"wifi_ssid": wifi_ssid, "auth_url": auth_url}
			with open(self.settings_path, "w", encoding="utf-8") as f:
				json.dump(data, f, ensure_ascii=False, indent=2)
			self.settings.update(data)
			return True
		except Exception:
			return False

	def _normalize_url(self, value: str) -> str:
		value = (value or "").strip()
		if not value:
			return ""
		# If already has scheme, keep
		if value.lower().startswith(("http://", "https://")):
			return value
		# Accept IP/host[:port][/path]
		# Basic pattern for IPv4 or hostname
		pattern = r"^(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?:/.*)?$|^[a-zA-Z0-9.-]+(?::\d+)?(?:/.*)?$"
		if re.match(pattern, value):
			return f"http://{value}"
		return value

	def _open_settings_dialog(self):
		dlg = tk.Toplevel(self)
		dlg.title("设置")
		dlg.transient(self)
		dlg.grab_set()
		dlg.configure(bg="#f5f7fb")

		container = ttk.Frame(dlg, padding=16)
		container.pack(fill="both", expand=True)

		row1 = ttk.Frame(container)
		row1.pack(fill="x", pady=(0, 10))
		label_ssid = ttk.Label(row1, text="WiFi 名称 (SSID)：")
		label_ssid.pack(side="left")
		ssid_var = tk.StringVar(value=self.settings.get("wifi_ssid", ""))
		entry_ssid = ttk.Entry(row1, textvariable=ssid_var, width=36)
		entry_ssid.pack(side="right", fill="x", expand=True)

		row2 = ttk.Frame(container)
		row2.pack(fill="x", pady=(0, 10))
		label_url = ttk.Label(row2, text="认证 URL：")
		label_url.pack(side="left")
		url_var = tk.StringVar(value=self.settings.get("auth_url", ""))
		entry_url = ttk.Entry(row2, textvariable=url_var, width=36)
		entry_url.pack(side="right", fill="x", expand=True)

		btns = ttk.Frame(container)
		btns.pack(fill="x", pady=(8, 0))

		def on_save():
			ssid = ssid_var.get().strip()
			url = self._normalize_url(url_var.get())
			ok = self._save_settings(ssid, url)
			if ok:
				self._toast("设置已保存")
				dlg.destroy()
			else:
				self._toast("保存失败，请检查权限")

		btn_save = ttk.Button(btns, text="保存", style="Primary.TButton", command=on_save)
		btn_cancel = ttk.Button(btns, text="取消", style="Primary.TButton", command=dlg.destroy)
		btn_cancel.pack(side="right")
		btn_save.pack(side="right", padx=(0, 8))

		self.update_idletasks()
		dlg.update_idletasks()
		# Center dialog relative to main window
		x = self.winfo_x() + (self.winfo_width() - dlg.winfo_reqwidth()) // 2
		y = self.winfo_y() + (self.winfo_height() - dlg.winfo_reqheight()) // 2
		dlg.geometry(f"+{x}+{y}")


if __name__ == "__main__":
	enable_high_dpi_scaling()
	app = App()
	app.mainloop()
