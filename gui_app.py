import os
import sys
import re
import warnings
import urllib.parse
import pandas as pd
import numpy as np
import joblib
import tldextract
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

warnings.filterwarnings("ignore")

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    USE_CTK = True
except ImportError:
    USE_CTK = False

# Danh sách tên miền chính thức uy tín
OFFICIAL_LEGITIMATE_DOMAINS = {
    'google.com', 'google.co.vi', 'google.com.vn', 'google.co.uk', 'google.fr', 'google.de',
    'microsoft.com', 'apple.com', 'amazon.com', 'facebook.com', 'github.com',
    'youtube.com', 'wikipedia.org', 'cloudflare.com', 'bing.com', 'yahoo.com',
    'office.com', 'live.com', 'outlook.com', 'linkedin.com', 'twitter.com', 'instagram.com'
}

# Danh sách dịch vụ rút gọn URL
SHORTENING_SERVICES = {
    'bit.ly', 'tinyurl.com', 'tinyurl.vn', 'vnshort.com', 'vnshort.vn', 'vnshort.net', 't.co', 'goo.gl', 'is.gd', 'cli.gs',
    'yfrog.com', 'migre.me', 'ff.im', 'tiny.cc', 'url4.eu', 'twit.ac',
    'su.pr', 'twurl.nl', 'snipurl.com', 'short.to', 'BudURL.com',
    'ping.fm', 'post.ly', 'Just.as', 'bkite.com', 'snipr.com', 'fic.kr',
    'loopt.us', 'to.ly', 'rayurl.com', 'ow.ly', 'sharein.com', 'is.gd',
    'link.zip.net', 'ity.im', 'q.gs', 'is.gd', 'po.st', 'bc.vc',
    'twitthis.com', 'u.to', 'j.mp', 'buzurl.com', 'cutt.ly', 'adf.ly',
    'rb.gy', 'shorturl.at', 's.id', 'vn.short.gy', 'rutgon.me', 'bit.do',
    'v.gd', 't.ly', 'clck.ru'
}

# Từ khóa nhạy cảm
SECURITY_KEYWORDS = [
    'login', 'secure', 'verify', 'account', 'update', 'banking', 
    'signin', 'credential', 'confirm', 'password', 'webscr', 'cmd',
    'security', 'authentication', 'verification', 'wallet', 'admin'
]

# Thương hiệu lớn hay bị giả mạo
TARGETED_BRANDS = [
    'paypal', 'google', 'apple', 'microsoft', 'amazon', 'facebook',
    'netflix', 'skype', 'chase', 'bankofamerica', 'wellsfargo', 'ebay',
    'yahoo', 'instagram', 'linkedin', 'whatsapp', 'twitter', 'dropbox',
    'steam', 'adobe', 'binance', 'coinbase', 'blockchain', 'roblox'
]

FEATURE_COLUMNS = [
    'url_length',
    'host_path_length',
    'subdomain_count',
    'subdomain_abuse',
    'has_ip',
    'abnormal_double_slash',
    'has_at_symbol',
    'is_shortened',
    'has_security_keywords',
    'security_keyword_count',
    'targets_brand',
    'is_official_domain',
    'count_dots',
    'count_hyphens',
    'count_digits'
]

def is_ip_address(hostname):
    if not hostname:
        return 0
    ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    if re.match(ipv4_pattern, hostname):
        return 1
    if re.match(r'^0x[0-9a-fA-F]+', hostname) or re.match(r'^[0-9]+$', hostname):
        return 1
    return 0

def unshorten_single(url, timeout=2.5):
    if not isinstance(url, str) or not url.strip():
        return url, False
    url_str = url.strip()
    url_lower = url_str.lower()
    
    url_for_parse = url_str if (url_lower.startswith('http://') or url_lower.startswith('https://')) else 'http://' + url_str
    try:
        parsed = urllib.parse.urlparse(url_for_parse)
        path = parsed.path
        ext = tldextract.extract(url_for_parse)
        registered_domain = getattr(ext, 'top_domain_under_public_suffix', getattr(ext, 'registered_domain', ''))
        domain_name = ext.domain
        suffix = ext.suffix
        full_domain = f"{domain_name}.{suffix}".lower() if suffix else domain_name.lower()
    except Exception:
        path = ""
        registered_domain = ""
        full_domain = ""
        
    is_shortener_domain = (full_domain in SHORTENING_SERVICES or registered_domain.lower() in SHORTENING_SERVICES)
    looks_like_shortener_path = (len(path.strip('/')) > 0 and len(path.strip('/')) <= 20 and '.' not in path)
    
    if not (is_shortener_domain or looks_like_shortener_path):
        return url_str, False

    curr_url = url_str
    expanded = False
    
    try:
        url_req = curr_url if (curr_url.lower().startswith('http://') or curr_url.lower().startswith('https://')) else 'http://' + curr_url
        import requests
        resp = requests.head(url_req, allow_redirects=True, timeout=timeout, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        if resp.url and resp.url.strip().rstrip('/') != curr_url.strip().rstrip('/'):
            curr_url = resp.url.strip()
            expanded = True
    except Exception:
        try:
            url_req = curr_url if (curr_url.lower().startswith('http://') or curr_url.lower().startswith('https://')) else 'http://' + curr_url
            import requests
            resp = requests.get(url_req, allow_redirects=True, stream=True, timeout=timeout, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            if resp.url and resp.url.strip().rstrip('/') != curr_url.strip().rstrip('/'):
                curr_url = resp.url.strip()
                expanded = True
        except Exception:
            pass
            
    if not expanded:
        try:
            url_req = curr_url if (curr_url.lower().startswith('http://') or curr_url.lower().startswith('https://')) else 'http://' + curr_url
            import urllib.request
            req = urllib.request.Request(url_req, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                next_u = r.geturl()
                if next_u and next_u.strip().rstrip('/') != curr_url.strip().rstrip('/'):
                    curr_url = next_u.strip()
                    expanded = True
        except Exception:
            pass

    return curr_url, expanded

def unshorten_url(url, timeout=2.5, max_chain=3):
    curr = url
    any_expanded = False
    for _ in range(max_chain):
        next_u, exp = unshorten_single(curr, timeout=timeout)
        if exp:
            curr = next_u
            any_expanded = True
        else:
            break
    return curr, any_expanded

def extract_features(url, auto_unshorten=True):
    if not url or not isinstance(url, str):
        url = ""

    original_url = url.strip()
    target_url = original_url
    unshortened_url = None
    was_shortened = 0

    if auto_unshorten and original_url:
        expanded_url, is_exp = unshorten_url(original_url, timeout=2.5)
        if is_exp:
            target_url = expanded_url
            unshortened_url = expanded_url
            was_shortened = 1
        else:
            url_for_parse_init = original_url if (original_url.lower().startswith('http://') or original_url.lower().startswith('https://')) else 'http://' + original_url
            try:
                ext_i = tldextract.extract(url_for_parse_init)
                reg_dom_i = getattr(ext_i, 'top_domain_under_public_suffix', getattr(ext_i, 'registered_domain', ''))
                full_dom_i = f"{ext_i.domain}.{ext_i.suffix}".lower() if ext_i.suffix else ext_i.domain.lower()
                if full_dom_i in SHORTENING_SERVICES or reg_dom_i.lower() in SHORTENING_SERVICES:
                    was_shortened = 1
            except Exception:
                pass

    url_str = target_url
    url_lower = url_str.lower()

    url_for_parse = url_str
    if not (url_lower.startswith('http://') or url_lower.startswith('https://')):
        url_for_parse = 'http://' + url_str

    parsed = None
    try:
        parsed = urllib.parse.urlparse(url_for_parse)
        hostname = parsed.netloc or parsed.path.split('/')[0]
    except Exception:
        hostname = url_str.split('/')[0]

    try:
        ext = tldextract.extract(url_for_parse)
        subdomain = ext.subdomain
        registered_domain = getattr(ext, 'top_domain_under_public_suffix', getattr(ext, 'registered_domain', ''))
        domain_name = ext.domain
        suffix = ext.suffix
    except Exception:
        subdomain = ""
        registered_domain = ""
        domain_name = ""
        suffix = ""

    url_unquoted = urllib.parse.unquote(url_str)
    url_length = len(url_unquoted)

    if subdomain:
        subdomain_parts = [p for p in subdomain.split('.') if p]
        subdomain_count = len(subdomain_parts)
    else:
        subdomain_count = 0
    
    subdomain_abuse = 1 if subdomain_count > 3 else 0
    has_ip = is_ip_address(hostname.split(':')[0])

    last_double_slash = url_lower.rfind('//')
    abnormal_double_slash = 1 if last_double_slash > 7 else 0
    has_at_symbol = 1 if '@' in url_str else 0

    full_domain = f"{domain_name}.{suffix}".lower() if suffix else domain_name.lower()
    is_shortened = 1 if (was_shortened or full_domain in SHORTENING_SERVICES or registered_domain.lower() in SHORTENING_SERVICES) else 0

    security_keyword_count = sum(1 for kw in SECURITY_KEYWORDS if kw in url_lower)
    has_security_keywords = 1 if security_keyword_count > 0 else 0

    OFFICIAL_TRUSTED_SUFFIXES = {'gov.vn', 'gov', 'edu.vn', 'edu', 'chinhphu.vn'}
    is_official_domain = 1 if (registered_domain.lower() in OFFICIAL_LEGITIMATE_DOMAINS or suffix.lower() in OFFICIAL_TRUSTED_SUFFIXES) else 0
    targets_brand = 0

    if not is_official_domain:
        for brand in TARGETED_BRANDS:
            if brand in url_lower:
                if domain_name.lower() != brand:
                    targets_brand = 1
                    break

    host_path = (parsed.netloc + parsed.path) if (parsed is not None and hasattr(parsed, 'netloc') and parsed.netloc) else url_unquoted.split('?')[0]
    host_path_length = len(host_path)

    count_dots = url_str.count('.')
    count_hyphens = url_str.count('-')
    count_digits = sum(c.isdigit() for c in url_unquoted)

    res = {
        'url_length': url_length,
        'host_path_length': host_path_length,
        'subdomain_count': subdomain_count,
        'subdomain_abuse': subdomain_abuse,
        'has_ip': has_ip,
        'abnormal_double_slash': abnormal_double_slash,
        'has_at_symbol': has_at_symbol,
        'is_shortened': is_shortened,
        'has_security_keywords': has_security_keywords,
        'security_keyword_count': security_keyword_count,
        'targets_brand': targets_brand,
        'is_official_domain': is_official_domain,
        'count_dots': count_dots,
        'count_hyphens': count_hyphens,
        'count_digits': count_digits
    }
    if unshortened_url:
        res['unshortened_url'] = unshortened_url

    return res

class PhishingDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Phishing URL Detector - Học máy cho bảo mật")
        self.root.geometry("1050x780")
        self.root.resizable(True, True)

        self.models_dir = "models"
        self.models = {}
        self.scaler = None
        self.batch_df_result = None
        self.load_models()

        self.setup_ui()

    def load_models(self):
        scaler_path = os.path.join(self.models_dir, "scaler.joblib")
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)

        model_files = {
            "Random Forest": "random_forest.joblib",
            "XGBoost": "xgboost.joblib",
            "SVM": "support_vector_machine_svm.joblib"
        }

        for name, filename in model_files.items():
            path = os.path.join(self.models_dir, filename)
            if os.path.exists(path):
                try:
                    self.models[name] = joblib.load(path)
                except Exception as e:
                    print(f"Lỗi tải mô hình {name}: {e}")

    def setup_ui(self):
        if USE_CTK:
            self.setup_ctk_ui()
        else:
            self.setup_standard_ui()

    def setup_ctk_ui(self):
        # Header Frame
        header_frame = ctk.CTkFrame(self.root, corner_radius=10, fg_color="#1f2937")
        header_frame.pack(fill="x", padx=15, pady=(15, 10))

        title_label = ctk.CTkLabel(
            header_frame, 
            text=" HỆ THỐNG TỰ ĐỘNG NHẬN DIỆN & PHÂN LOẠI PHISHING URL", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#60a5fa"
        )
        title_label.pack(pady=8)

        subtitle_label = ctk.CTkLabel(
            header_frame, 
            text="Đồ án Học máy cho bảo mật | Sử dụng 3 thuật toán: Random Forest, SVM & XGBoost", 
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af"
        )
        subtitle_label.pack(pady=(0, 8))

        # Tabview navigation
        self.tabview = ctk.CTkTabview(self.root, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.tab_single = self.tabview.add("🔍 Kiểm tra URL Đơn lẻ")
        self.tab_batch = self.tabview.add("📁 Kiểm tra Hàng loạt (File CSV/Excel)")

        self.setup_tab_single()
        self.setup_tab_batch()

    def setup_tab_single(self):
        input_frame = ctk.CTkFrame(self.tab_single, corner_radius=10)
        input_frame.pack(fill="x", padx=10, pady=10)

        url_label = ctk.CTkLabel(input_frame, text="Nhập đường link (URL) cần kiểm tra:", font=ctk.CTkFont(size=14, weight="bold"))
        url_label.pack(anchor="w", padx=15, pady=(10, 5))

        entry_container = ctk.CTkFrame(input_frame, fg_color="transparent")
        entry_container.pack(fill="x", padx=15, pady=(0, 10))

        self.url_entry = ctk.CTkEntry(
            entry_container, 
            placeholder_text="Ví dụ: http://192.168.1.1/paypal/login.php hoặc https://google.com",
            font=ctk.CTkFont(size=13),
            height=40
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_analyze = ctk.CTkButton(
            entry_container, 
            text="🔍 KIỂM TRA URL", 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=40,
            command=self.analyze_url
        )
        btn_analyze.pack(side="right")

        sample_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        sample_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        lbl_samples = ctk.CTkLabel(sample_frame, text="URL Mẫu kiểm thử nhanh:", font=ctk.CTkFont(size=12), text_color="#9ca3af")
        lbl_samples.pack(side="left", padx=(0, 10))

        samples = [
            ("Phishing IP Mẫu", "http://192.168.1.1/paypal.com/cgi-bin/webscr/login.php"),
            ("Phishing Shortener", "https://bit.ly/3xYz12_paypal_secure_update"),
            ("Google Translate", "https://translate.google.com/?sl=vi&tl=en&text=nh%E1%BA%ADn%20di%E1%BB%87n%20url%20l%E1%BB%ABa%20%C4%91%E1%BA%A3o&op=translate"),
            ("Legitimate Good", "https://google.com")
        ]

        for label, url in samples:
            btn = ctk.CTkButton(
                sample_frame, 
                text=label, 
                font=ctk.CTkFont(size=11), 
                fg_color="#374151", 
                hover_color="#4b5563",
                height=26,
                command=lambda u=url: self.set_sample_url(u)
            )
            btn.pack(side="left", padx=5)

        content_frame = ctk.CTkFrame(self.tab_single, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left_panel = ctk.CTkFrame(content_frame, corner_radius=10)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        feat_title = ctk.CTkLabel(left_panel, text="📊 Phân tích 8 Nhóm Đặc trưng URL", font=ctk.CTkFont(size=15, weight="bold"), text_color="#38bdf8")
        feat_title.pack(anchor="w", padx=15, pady=10)

        self.features_text = ctk.CTkTextbox(left_panel, font=ctk.CTkFont(family="Consolas", size=12), activate_scrollbars=True)
        self.features_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.features_text.insert("1.0", "Hãy nhập URL và bấm 'KIỂM TRA URL' để xem chi tiết các đặc trưng trích xuất.")

        right_panel = ctk.CTkFrame(content_frame, corner_radius=10)
        right_panel.pack(side="right", fill="both", expand=True)

        res_title = ctk.CTkLabel(right_panel, text="🤖 Kết quả Dự đoán 3 Mô hình ML", font=ctk.CTkFont(size=15, weight="bold"), text_color="#38bdf8")
        res_title.pack(anchor="w", padx=15, pady=10)

        self.alert_banner = ctk.CTkFrame(right_panel, fg_color="#374151", corner_radius=8)
        self.alert_banner.pack(fill="x", padx=15, pady=(0, 15))

        self.alert_label = ctk.CTkLabel(
            self.alert_banner, 
            text="CHƯA KIỂM TRA", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#9ca3af"
        )
        self.alert_label.pack(pady=15)

        self.results_text = ctk.CTkTextbox(right_panel, font=ctk.CTkFont(size=13), activate_scrollbars=True)
        self.results_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.results_text.insert("1.0", "Thông số dự đoán chi tiết của Random Forest, XGBoost và SVM sẽ xuất hiện tại đây.")

    def setup_tab_batch(self):
        batch_input_frame = ctk.CTkFrame(self.tab_batch, corner_radius=10)
        batch_input_frame.pack(fill="x", padx=10, pady=10)

        lbl_instruct = ctk.CTkLabel(
            batch_input_frame, 
            text="Tải lên tệp CSV hoặc Excel (File gồm 1 cột chứa danh sách các URL):", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl_instruct.pack(anchor="w", padx=15, pady=(10, 5))

        file_container = ctk.CTkFrame(batch_input_frame, fg_color="transparent")
        file_container.pack(fill="x", padx=15, pady=(0, 10))

        self.batch_file_entry = ctk.CTkEntry(
            file_container, 
            placeholder_text="Đường dẫn tệp CSV hoặc Excel...", 
            font=ctk.CTkFont(size=13),
            height=40
        )
        self.batch_file_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_browse = ctk.CTkButton(
            file_container, 
            text="📁 Chọn Tệp", 
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#4b5563",
            hover_color="#374151",
            height=40,
            command=self.browse_batch_file
        )
        btn_browse.pack(side="left", padx=(0, 10))

        btn_run_batch = ctk.CTkButton(
            file_container, 
            text="⚡ KIỂM TRA HÀNG LOẠT", 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=40,
            command=self.run_batch_prediction
        )
        btn_run_batch.pack(side="right")

        # Progress bar & Status
        self.progress_frame = ctk.CTkFrame(batch_input_frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.batch_status_lbl = ctk.CTkLabel(self.progress_frame, text="Sẵn sàng xử lý tệp.", font=ctk.CTkFont(size=12), text_color="#9ca3af")
        self.batch_status_lbl.pack(anchor="w")

        self.progressbar = ctk.CTkProgressBar(self.progress_frame)
        self.progressbar.pack(fill="x", pady=(3, 0))
        self.progressbar.set(0)

        # Summary Cards Frame
        summary_frame = ctk.CTkFrame(self.tab_batch, fg_color="transparent")
        summary_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.card_total = ctk.CTkFrame(summary_frame, corner_radius=8, fg_color="#374151")
        self.card_total.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.lbl_card_total = ctk.CTkLabel(self.card_total, text="Tổng URL: 0", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_card_total.pack(pady=10)

        self.card_phish = ctk.CTkFrame(summary_frame, corner_radius=8, fg_color="#991b1b")
        self.card_phish.pack(side="left", fill="both", expand=True, padx=5)
        self.lbl_card_phish = ctk.CTkLabel(self.card_phish, text="🚨 Phishing: 0", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff")
        self.lbl_card_phish.pack(pady=10)

        self.card_safe = ctk.CTkFrame(summary_frame, corner_radius=8, fg_color="#166534")
        self.card_safe.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.lbl_card_safe = ctk.CTkLabel(self.card_safe, text="✅ An toàn: 0", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff")
        self.lbl_card_safe.pack(pady=10)

        # Results Table Display Frame
        table_frame = ctk.CTkFrame(self.tab_batch, corner_radius=10)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        tbl_top_bar = ctk.CTkFrame(table_frame, fg_color="transparent")
        tbl_top_bar.pack(fill="x", padx=15, pady=10)

        lbl_tbl_title = ctk.CTkLabel(tbl_top_bar, text="📋 Bảng Kết quả Phân loại Chi tiết", font=ctk.CTkFont(size=15, weight="bold"), text_color="#38bdf8")
        lbl_tbl_title.pack(side="left")

        self.btn_export = ctk.CTkButton(
            tbl_top_bar, 
            text="💾 Xuất Kết Quả File (CSV/Excel)", 
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#16a34a",
            hover_color="#15803d",
            state="disabled",
            command=self.export_batch_results
        )
        self.btn_export.pack(side="right")

        self.batch_textbox = ctk.CTkTextbox(table_frame, font=ctk.CTkFont(family="Consolas", size=12), activate_scrollbars=True)
        self.batch_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.batch_textbox.insert("1.0", "Chọn tệp CSV/Excel và bấm 'KIỂM TRA HÀNG LOẠT' để hiển thị bảng kết quả phân loại.")

    def setup_standard_ui(self):
        self.root.geometry("900x650")
        lbl = tk.Label(self.root, text="HỆ THỐNG NHẬN DIỆN PHISHING URL", font=("Arial", 16, "bold"))
        lbl.pack(pady=10)
        
        frame_input = tk.Frame(self.root)
        frame_input.pack(pady=10, fill="x", padx=20)
        
        tk.Label(frame_input, text="Nhập URL:").pack(side="left")
        self.url_entry = tk.Entry(frame_input, width=60)
        self.url_entry.pack(side="left", padx=10)
        
        btn = tk.Button(frame_input, text="Kiểm tra", command=self.analyze_url, bg="#2563eb", fg="white")
        btn.pack(side="left")
        
        frame_content = tk.Frame(self.root)
        frame_content.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.features_text = tk.Text(frame_content, width=50)
        self.features_text.pack(side="left", fill="both", expand=True, padx=5)
        
        self.results_text = tk.Text(frame_content, width=50)
        self.results_text.pack(side="right", fill="both", expand=True, padx=5)

    def set_sample_url(self, url):
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, url)
        self.analyze_url()

    def analyze_url(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập đường link URL cần kiểm tra!")
            return

        feats = extract_features(url)

        feat_str = f"=== BẢNG TRÍCH XUẤT ĐẶC TRƯNG URL ===\n"
        feat_str += f"URL Gốc: {url}\n"
        if feats.get('unshortened_url'):
            feat_str += f"🔗 URL Đích (Giải mã Unshorten): {feats['unshortened_url']}\n"
        feat_str += f"----------------------------------------\n"
        feat_str += f"1. Độ dài URL (Unquoted)     : {feats['url_length']} ký tự (Host+Path: {feats['host_path_length']})\n"
        feat_str += f"2. Số lượng Sub-domains       : {feats['subdomain_count']} (Lạm dụng >3: {'CÓ ⚠️' if feats['subdomain_abuse'] else 'Không'})\n"
        feat_str += f"3. Sử dụng IP trực tiếp      : {'CÓ ⚠️ (Địa chỉ IP)' if feats['has_ip'] else 'Không (Domain chuẩn)'}\n"
        feat_str += f"4. Vị trí // bất thường      : {'CÓ ⚠️' if feats['abnormal_double_slash'] else 'Không'}\n"
        feat_str += f"5. Sử dụng ký tự '@'         : {'CÓ ⚠️' if feats['has_at_symbol'] else 'Không'}\n"
        feat_str += f"6. Liên kết rút gọn          : {'CÓ ⚠️ (Shortener)' if feats['is_shortened'] else 'Không'}\n"
        feat_str += f"7. Từ khóa bảo mật nhạy cảm  : {feats['security_keyword_count']} từ ({'CÓ ⚠️' if feats['has_security_keywords'] else 'Không'})\n"
        feat_str += f"8. Mạo danh thương hiệu lớn  : {'CÓ ⚠️ (Brand Spoofing)' if feats['targets_brand'] else 'Không'}\n"
        feat_str += f"9. Tên miền uy tín chính chủ : {'CÓ ✅ (Official Domain)' if feats['is_official_domain'] else 'Không'}\n"
        feat_str += f"----------------------------------------\n"
        feat_str += f"Số dấu chấm (.): {feats['count_dots']} | Số gạch ngang (-): {feats['count_hyphens']} | Số chữ số: {feats['count_digits']}\n"

        self.features_text.delete("1.0", "end")
        self.features_text.insert("1.0", feat_str)

        input_df = pd.DataFrame([feats])[FEATURE_COLUMNS]

        if not self.models:
            res_str = "⚠️ CẢNH BÁO: Chưa tìm thấy file mô hình đã huấn luyện trong thư mục 'models/'.\n\nVui lòng chạy notebook trước để huấn luyện và xuất file mô hình (.joblib)."
            if USE_CTK:
                self.results_text.delete("1.0", "end")
                self.results_text.insert("1.0", res_str)
                self.alert_label.configure(text="CHƯA HUẤN LUYỆN MÔ HÌNH", text_color="#f59e0b")
                self.alert_banner.configure(fg_color="#78350f")
            return

        predictions = {}
        probabilities = {}
        phishing_votes = 0

        for name, model in self.models.items():
            try:
                if name == "SVM" and self.scaler is not None:
                    input_scaled = self.scaler.transform(input_df)
                    pred = model.predict(input_scaled)[0]
                    prob = model.predict_proba(input_scaled)[0][1]
                else:
                    pred = model.predict(input_df)[0]
                    prob = model.predict_proba(input_df)[0][1]

                predictions[name] = pred
                probabilities[name] = prob
                if pred == 1:
                    phishing_votes += 1
            except Exception as e:
                predictions[name] = None
                probabilities[name] = 0.0

        # Mô hình quyết định chính: Random Forest (Accuracy 83.60% cao nhất)
        rf_pred = predictions.get("Random Forest")
        rf_prob = probabilities.get("Random Forest", 0.0)

        if rf_pred is not None:
            is_phishing = (rf_pred == 1)
            main_prob = rf_prob
        else:
            total_models = len(predictions)
            avg_prob = sum(probabilities.values()) / total_models if total_models > 0 else 0
            is_phishing = (phishing_votes >= (total_models / 2))
            main_prob = avg_prob

        if feats['is_official_domain'] == 1 and feats['has_ip'] == 0 and feats['is_shortened'] == 0 and feats['abnormal_double_slash'] == 0 and feats['subdomain_abuse'] == 0 and feats['has_at_symbol'] == 0 and feats['targets_brand'] == 0:
            is_phishing = False
            main_prob = min(main_prob, 0.05)

        if USE_CTK:
            if is_phishing:
                self.alert_label.configure(text=f"🚨 CẢNH BÁO: PHISHING URL (Random Forest: {main_prob*100:.1f}% Rủi ro)", text_color="#ffffff")
                self.alert_banner.configure(fg_color="#dc2626")
            else:
                self.alert_label.configure(text=f"✅ LIÊN KẾT AN TOÀN (Random Forest: {(1-main_prob)*100:.1f}% Tin cậy)", text_color="#ffffff")
                self.alert_banner.configure(fg_color="#16a34a")

        res_str = "=== KẾT QUẢ ĐÁNH GIÁ 3 MÔ HÌNH ===\n"
        res_str += "⭐ (Mô hình Random Forest - Accuracy 83.60% - làm căn cứ quyết định chính)\n\n"
        for name in ["Random Forest", "XGBoost", "SVM"]:
            if name in predictions and predictions[name] is not None:
                pred = predictions[name]
                prob = probabilities[name]
                status = "🔴 PHISHING (Lừa đảo)" if pred == 1 else "🟢 BENIGN (An toàn)"
                tag = " ⭐ [Mô hình chính]" if name == "Random Forest" else ""
                res_str += f"► Mô hình {name}{tag}:\n"
                res_str += f"   - Dự đoán : {status}\n"
                res_str += f"   - Tỷ lệ Phishing: {prob*100:.2f}%\n\n"

        res_str += "----------------------------------------\n"
        res_str += "📌 ĐÁNH GIÁ YẾU TỐ RỦI RO PHÁT HIỆN:\n"
        risk_factors = []
        if feats.get('unshortened_url'):
            risk_factors.append(f"- 🔗 Đã giải mã Link Rút gọn thành URL Đích: '{feats['unshortened_url']}'.")
        if feats['has_ip']: risk_factors.append("- URL sử dụng IP trực tiếp thay vì tên miền chuẩn.")
        if feats['subdomain_abuse']: risk_factors.append("- URL chứa quá nhiều Sub-domains (> 3 cấp).")
        if feats['is_shortened']: risk_factors.append("- Sử dụng dịch vụ rút gọn liên kết nhằm che giấu đích đến.")
        if feats['targets_brand']: risk_factors.append("- Phát hiện dấu hiệu giả mạo thương hiệu lớn.")
        if feats['has_security_keywords']: risk_factors.append("- Chứa các từ khóa nhạy cảm liên quan đến tài khoản/bảo mật.")
        if feats['has_at_symbol']: risk_factors.append("- Sử dụng ký tự '@' để đánh lừa trình duyệt.")
        if feats['abnormal_double_slash']: risk_factors.append("- Chứa dấu '//' tại vị trí bất thường.")

        if risk_factors:
            res_str += "\n".join(risk_factors)
        else:
            res_str += "- Không phát hiện yếu tố rủi ro bất thường cấu trúc từ URL này."

        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", res_str)

    # --- BATCH PREDICTION LOGIC ---
    def browse_batch_file(self):
        file_path = filedialog.askopenfilename(
            title="Chọn Tệp CSV, Excel hoặc ZIP",
            filetypes=[
                ("Tệp Dữ liệu (CSV, Excel, ZIP)", "*.csv *.xlsx *.xls *.zip"),
                ("Tệp ZIP", "*.zip"),
                ("Tệp CSV", "*.csv"),
                ("Tệp Excel", "*.xlsx *.xls")
            ]
        )
        if file_path:
            self.batch_file_full_path = file_path
            self.batch_file_entry.delete(0, "end")
            self.batch_file_entry.insert(0, os.path.basename(file_path))

    def run_batch_prediction(self):
        file_path = getattr(self, 'batch_file_full_path', None) or self.batch_file_entry.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn tệp CSV, Excel hoặc ZIP hợp lệ!")
            return

        if not self.models:
            messagebox.showerror("Lỗi", "Chưa tìm thấy mô hình đã huấn luyện trong thư mục 'models/'!")
            return

        threading.Thread(target=self._process_batch_file_thread, args=(file_path,), daemon=True).start()

    def _process_batch_file_thread(self, file_path):
        try:
            self.batch_status_lbl.configure(text="Đang đọc tệp dữ liệu...", text_color="#60a5fa")
            self.progressbar.set(0.1)

            ext = os.path.splitext(file_path)[1].lower()
            df_input = None

            if ext in ['.csv', '.zip'] or file_path.endswith('.zip'):
                try:
                    df_temp = pd.read_csv(file_path, header=None)
                    first_val = str(df_temp.iloc[0, 0]).strip().lower()
                    if first_val.startswith(('http', 'www', 'ftp')) or '.' in first_val or '192.' in first_val:
                        df_input = df_temp
                    else:
                        df_input = pd.read_csv(file_path)
                except Exception:
                    df_input = pd.read_csv(file_path)
            elif ext in ['.xlsx', '.xls']:
                try:
                    df_temp = pd.read_excel(file_path, header=None)
                    first_val = str(df_temp.iloc[0, 0]).strip().lower()
                    if first_val.startswith(('http', 'www', 'ftp')) or '.' in first_val or '192.' in first_val:
                        df_input = df_temp
                    else:
                        df_input = pd.read_excel(file_path)
                except Exception as ex_err:
                    print(f"Lỗi read_excel: {ex_err}")
                    df_input = pd.read_excel(file_path)
            else:
                messagebox.showerror("Lỗi", "Định dạng tệp không được hỗ trợ!")
                return

            if df_input is None or df_input.empty:
                messagebox.showwarning("Cảnh báo", "Tệp dữ liệu rỗng!")
                return

            url_col = None
            for col in df_input.columns:
                if 'url' in str(col).lower() or 'link' in str(col).lower():
                    url_col = col
                    break
            if url_col is None:
                url_col = df_input.columns[0]

            raw_urls = df_input[url_col].astype(str).tolist()
            valid_urls = []
            for u in raw_urls:
                u_str = str(u).strip()
                if u_str and u_str.lower() not in ['nan', 'none', 'null', 'url', 'link']:
                    valid_urls.append(u_str)

            total = len(valid_urls)
            if total == 0:
                messagebox.showwarning("Cảnh báo", "Không tìm thấy danh sách URL hợp lệ trong tệp!")
                return

            self.batch_status_lbl.configure(text=f"Đang trích xuất đặc trưng {total} URLs...", text_color="#60a5fa")
            self.progressbar.set(0.3)

            # Trích xuất đặc trưng hàng loạt
            features_list = [extract_features(u) for u in valid_urls]
            df_features = pd.DataFrame(features_list)[FEATURE_COLUMNS]

            self.batch_status_lbl.configure(text=f"Đang chạy 3 mô hình học máy trên {total} URLs...", text_color="#60a5fa")
            self.progressbar.set(0.6)

            rf = self.models.get("Random Forest")
            xgb_m = self.models.get("XGBoost")
            svm_m = self.models.get("SVM")

            probs_rf = rf.predict_proba(df_features)[:, 1] if rf else np.zeros(total)
            probs_xgb = xgb_m.predict_proba(df_features)[:, 1] if xgb_m else np.zeros(total)

            if svm_m and self.scaler:
                scaled_feats = self.scaler.transform(df_features)
                probs_svm = svm_m.predict_proba(scaled_feats)[:, 1]
            else:
                probs_svm = np.zeros(total)

            results = []
            phish_count = 0
            safe_count = 0

            for idx in range(total):
                u_str = valid_urls[idx]
                feats = features_list[idx]

                p_rf = probs_rf[idx]
                p_xgb = probs_xgb[idx]
                p_svm = probs_svm[idx]

                # Primary Decision Engine: Random Forest (Accuracy 83.60%)
                if rf:
                    main_prob = p_rf
                    is_phish = (p_rf >= 0.5)
                else:
                    main_prob = (p_rf + p_xgb + p_svm) / 3.0
                    votes = (1 if p_rf >= 0.5 else 0) + (1 if p_xgb >= 0.5 else 0) + (1 if p_svm >= 0.5 else 0)
                    is_phish = (votes >= 2)

                # Official Whitelist Check
                if feats['is_official_domain'] == 1 and feats['has_ip'] == 0 and feats['is_shortened'] == 0 and feats['abnormal_double_slash'] == 0 and feats['subdomain_abuse'] == 0 and feats['has_at_symbol'] == 0 and feats['targets_brand'] == 0:
                    is_phish = False
                    main_prob = min(main_prob, 0.05)

                if is_phish:
                    phish_count += 1
                    status_str = "🔴 PHISHING (Lừa đảo)"
                else:
                    safe_count += 1
                    status_str = "🟢 BENIGN (An toàn)"

                results.append({
                    "STT": idx + 1,
                    "URL": u_str,
                    "Kết luận (RF Main)": status_str,
                    "Rủi ro Phishing (RF %)": f"{main_prob*100:.2f}%",
                    "RF Prob (%)": f"{p_rf*100:.1f}%",
                    "XGB Prob (%)": f"{p_xgb*100:.1f}%",
                    "SVM Prob (%)": f"{p_svm*100:.1f}%"
                })

            self.progressbar.set(1.0)
            self.batch_df_result = pd.DataFrame(results)

            # Cập nhật GUI kết quả
            self.lbl_card_total.configure(text=f"Tổng URL: {len(results):,}")
            self.lbl_card_phish.configure(text=f"🚨 Phishing: {phish_count:,}")
            self.lbl_card_safe.configure(text=f"✅ An toàn: {safe_count:,}")

            PREVIEW_LIMIT = 1000
            res_tbl_str = f"=== BẢNG TỔNG HỢP DỰ ĐOÁN HÀNG LOẠT ({len(results):,} URLs) ===\n"
            res_tbl_str += f"Tỷ lệ phát hiện: Phishing (Lừa đảo) = {phish_count:,} | Benign (An toàn) = {safe_count:,}\n"
            res_tbl_str += "="*75 + "\n"
            if len(results) > PREVIEW_LIMIT:
                res_tbl_str += f"📌 Ghi chú: Đã xử lý thành công {len(results):,} URLs. Đang hiển thị xem trước {PREVIEW_LIMIT:,} dòng đầu tiên trên màn hình để ứng dụng hoạt động siêu mượt.\n"
                res_tbl_str += f"📌 Bấm nút 'Xuất Kết Quả File (CSV/Excel)' phía trên để lưu đầy đủ {len(results):,} dòng kết quả.\n"
            res_tbl_str += "="*75 + "\n\n"

            for r in results[:PREVIEW_LIMIT]:
                res_tbl_str += f"[{r['STT']}] {r['Kết luận']} | Risk: {r['Tỷ lệ Phishing (%)']} | URL: {r['URL']}\n"

            self.batch_textbox.delete("1.0", "end")
            self.batch_textbox.insert("1.0", res_tbl_str)
            self.btn_export.configure(state="normal")

            self.batch_status_lbl.configure(text=f"✓ Xử lý hoàn tất {len(results):,} URLs!", text_color="#22c55e")
            messagebox.showinfo("Thành công", f"Đã hoàn tất phân loại {len(results):,} URLs!\n- Phishing (Lừa đảo): {phish_count:,}\n- Benign (An toàn): {safe_count:,}\n\nBấm 'Xuất Kết Quả File' để lưu toàn bộ dữ liệu.")

        except ImportError as imp_err:
            self.batch_status_lbl.configure(text="Lỗi: Thiếu thư viện openpyxl", text_color="#ef4444")
            messagebox.showerror("Lỗi Thư viện", "Để đọc tệp Excel (.xlsx), vui lòng cài đặt openpyxl bằng lệnh:\npip install openpyxl\nhoặc chuyển tệp sang định dạng CSV.")
        except Exception as e:
            self.batch_status_lbl.configure(text=f"Lỗi: {e}", text_color="#ef4444")
            messagebox.showerror("Lỗi", f"Không thể xử lý tệp: {e}")

    def export_batch_results(self):
        if self.batch_df_result is None or self.batch_df_result.empty:
            messagebox.showwarning("Cảnh báo", "Không có dữ liệu kết quả để xuất!")
            return

        file_path = filedialog.asksaveasfilename(
            title="Lưu Kết Quả Phân Loại",
            defaultextension=".csv",
            filetypes=[
                ("CSV File (Khuyên dùng cho tệp lớn)", "*.csv"),
                ("Excel File", "*.xlsx")
            ]
        )
        if file_path:
            threading.Thread(target=self._export_thread, args=(file_path,), daemon=True).start()

    def _export_thread(self, file_path):
        try:
            self.btn_export.configure(state="disabled", text="⏳ Đang xuất tệp...")
            self.batch_status_lbl.configure(text=f"Đang xuất {len(self.batch_df_result):,} dòng ra {os.path.basename(file_path)}...", text_color="#60a5fa")
            
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.csv':
                self.batch_df_result.to_csv(file_path, index=False, encoding='utf-8-sig')
            elif ext in ['.xlsx', '.xls']:
                self.batch_df_result.to_excel(file_path, index=False)

            self.batch_status_lbl.configure(text=f"✓ Đã xuất thành công {len(self.batch_df_result):,} dòng!", text_color="#22c55e")
            messagebox.showinfo("Thành công", f"Đã xuất thành công {len(self.batch_df_result):,} dòng ra tệp:\n{file_path}")
        except Exception as e:
            self.batch_status_lbl.configure(text=f"Lỗi xuất tệp: {e}", text_color="#ef4444")
            messagebox.showerror("Lỗi", f"Không thể xuất tệp: {e}")
        finally:
            self.btn_export.configure(state="normal", text="💾 Xuất Kết Quả File (CSV/Excel)")

def main():
    if USE_CTK:
        root = ctk.CTk()
    else:
        root = tk.Tk()
    app = PhishingDetectorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
