#  Identify Phishing URLs

> **Đồ án môn học:** Học máy cho bảo mật (Machine Learning for Cybersecurity)  
> **Repository GitHub:** [https://github.com/Nguyn050719/Identify_phishing_URLs](https://github.com/Nguyn050719/Identify_phishing_URLs)

---

## 📌 Giới thiệu Đề tài

Trong bối cảnh an ninh mạng ngày càng phức tạp, các đường liên kết lừa đảo (**Phishing URLs**) là phương thức hàng đầu được kẻ tấn công sử dụng để đánh cắp thông tin tài khoản, mật khẩu và dữ liệu nhạy cảm của người dùng.

Dự án xây dựng một **Hệ thống Phân loại Phishing URL tự động dựa trên Học máy (Machine Learning)** với bộ dữ liệu gần **550,000 liên kết**. Hệ thống sử dụng 3 thuật toán phổ biến là **Random Forest**, **XGBoost** và **Support Vector Machine (SVM)** kết hợp cùng quy tắc trích xuất **15 đặc trưng cấu trúc URL** và bộ lọc **Tên miền Chính chủ Uy tín (Official Domain Whitelist)**.

---

## Tính năng 

1. **🔍 Kiểm tra URL Đơn lẻ (Single URL Inference):**
   - Phân tích trực quan 15 nhóm đặc trưng kỹ thuật của URL thời gian thực.
   - Kết hợp vote đồng thuận xác suất từ 3 thuật toán ML và hiển thị mức độ rủi ro kèm màu sắc trực quan (Đỏ: Phishing / Xanh: An toàn).


2. **Kiểm tra Hàng loạt từ File CSV / Excel (Batch File Processing):**
   - Tải lên tệp CSV hoặc Excel (`.csv`, `.xlsx`, `.xls`) chứa danh sách URL (gồm 1 cột URL).
   - **Thuật toán Xử lý Lô Vector hóa (Vectorized Batch Processing):** Đạt tốc độ cực nhanh, phân loại **1,000 URLs chỉ trong 2 giây** và hỗ trợ các tệp dữ liệu lớn (**300,000+ dòng**).
   - **Giao diện không bị đơ/lag:** Sử dụng chế độ **Smart Preview 1,000 dòng** kết hợp **Xuất file Ngầm bất đồng bộ (Async Export)** giúp phần mềm luôn chạy siêu mượt.
   - Bấm nút xuất báo cáo chi tiết ra file CSV hoặc Excel.

3. **Báo cáo Jupyter Notebook Tự chứa (`notebooks/Phishing_URL_Classification.ipynb`):**
   - Độc lập 100%, chứa mã nguồn tiền xử lý, huấn luyện mô hình, vẽ 6 biểu đồ báo cáo và kiểm thử trực tuyến.

---

##Bộ 15 Nhóm Đặc trưng Trích xuất từ URL

| STT | Tên Đặc trưng (`Feature`) | Mô tả chi tiết |
| :---: | :--- | :--- |
| 1 | `url_length` | Tổng độ dài toàn bộ chuỗi URL (sau khi Unquote UTF-8). |
| 2 | `host_path_length` | Độ dài riêng phần Tên miền & Đường dẫn (loại bỏ nhiễu từ tham số tìm kiếm). |
| 3 | `subdomain_count` | Số lượng Sub-domains có trong URL. |
| 4 | `subdomain_abuse` | Cảnh báo lạm dụng quá nhiều Sub-domains (> 3 cấp). |
| 5 | `has_ip` | URL sử dụng trực tiếp địa chỉ IP (IPv4 / Hex) thay vì tên miền chuẩn. |
| 6 | `abnormal_double_slash` | Xuất hiện ký tự `//` bất thường tại vị trí khác sau giao thức `http(s)://`. |
| 7 | `has_at_symbol` | Sử dụng ký tự `@` nhằm đánh lừa trình duyệt bỏ qua hostname thực. |
| 8 | `is_shortened` | Sử dụng các dịch vụ rút gọn liên kết (như *bit.ly*, *tinyurl.com*, *t.co*...). |
| 9 | `has_security_keywords` | Kiểm tra sự xuất hiện của các từ khóa nhạy cảm (`login`, `banking`, `verify`...). |
| 10 | `security_keyword_count` | Số lượng từ khóa bảo mật xuất hiện trong URL. |
| 11 | `targets_brand` | Phát hiện dấu hiệu mạo danh các thương hiệu lớn (*PayPal*, *Apple*, *Amazon*...). |
| 12 | `is_official_domain` | Xác nhận tên miền chính chủ thuộc danh sách uy tín toàn cầu. |
| 13 | `count_dots` | Số lượng dấu chấm (`.`) có trong URL. |
| 14 | `count_hyphens` | Số lượng dấu gạch ngang (`-`) có trong URL. |
| 15 | `count_digits` | Số lượng chữ số xuất hiện trong chuỗi URL. |

---

## Kết quả Đánh giá Mô hình Học máy

Các mô hình được huấn luyện và đánh giá trên bộ dữ liệu **549,346 URLs** (phần chia Train/Test: 80/20):

| Thuật toán Học máy | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Thời gian Huấn luyện |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
|  **Random Forest** | **83.60%** | **80.50%** | **55.95%** | **66.02%** | **87.35%** | 7.84 giây |
|  **XGBoost** | **83.24%** | **79.25%** | **55.72%** | **65.44%** | **86.72%** | 1.47 giây |
|  **Support Vector Machine (SVM)** | **77.55%** | **77.15%** | **30.06%** | **43.26%** | **73.39%** | 4.75 giây |

---

##  Cấu trúc Thư mục Dự án

```text
Identify_phishing_URLs/
├── .gitignore                 # Bỏ qua bytecode __pycache__ và venv
├── README.md                  # Tài liệu hướng dẫn đồ án
├── requirements.txt           # Danh sách các thư viện cần thiết
├── gui_app.py                 # Ứng dụng Desktop GUI độc lập 100%
├── data/
│   ├── raw/                   # phishing_site_urls.csv (Dataset gốc)
│   ├── processed/             # features_extracted.csv (Dataset 15 đặc trưng)
│   ├── url_dataset_1000.xlsx  # File mẫu kiểm thử 1,000 URLs
│   └── url_dataset_300000_row.csv # File mẫu kiểm thử 300,000 URLs
├── models/                    # Bộ mô hình học máy đã huấn luyện (.joblib)
│   ├── random_forest.joblib
│   ├── xgboost.joblib
│   ├── support_vector_machine_svm.joblib
│   └── scaler.joblib
├── notebooks/                 # Jupyter Notebook báo cáo thuyết minh
│   └── Phishing_URL_Classification.ipynb
└── reports/figures/           # 6 Biểu đồ trực quan hóa báo cáo đồ án
    ├── label_distribution.png
    ├── feature_correlation_heatmap.png
    ├── confusion_matrices.png
    ├── roc_curves_comparison.png
    ├── metrics_comparison.png
    └── feature_importance.png
```

---

##  Hướng dẫn Cài đặt & Khởi chạy

### 1. Yêu cầu Hệ thống
- Python 3.10 trở lên.
- Hệ điều hành: Windows / macOS / Linux.

### 2. Cài đặt Môi trường
Mở Terminal / PowerShell tại thư mục dự án và thực hiện các lệnh sau:

```bash
# 1. Tạo môi trường ảo Python
python -m venv venv

# 2. Kích hoạt môi trường ảo
# Trên Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Trên macOS/Linux:
source venv/bin/activate

# 3. Cài đặt toàn bộ thư viện phụ thuộc
pip install -r requirements.txt
```

### 3. Khởi chạy Ứng dụng Desktop App GUI
```bash
python gui_app.py
```

### 4. Mở Jupyter Notebook để xem Báo cáo & Đồ họa
```bash
jupyter notebook notebooks/Phishing_URL_Classification.ipynb
```
