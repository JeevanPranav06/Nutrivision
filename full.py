import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import base64
import requests
import json
import time
import re
import threading
from tkinter import filedialog
from datetime import datetime, timedelta
import random
import urllib.parse
from io import BytesIO
import os
from dotenv import load_dotenv

# Matplotlib for graphs
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

# --- Configuration ---
load_dotenv()
API_KEY = os.getenv("API_KEY")  # PASTE YOUR API KEY HERE
MODEL_ID = "gemini-flash-latest"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={API_KEY}"

# --- Modern Theme & Colors (Light, Dark) Tuples matching Mockup ---
ctk.set_appearance_mode("Light")  # Default to Light to match image
ctk.set_default_color_theme("green")

# Palette designed to match the uploaded mockup
BG_APP = ("#f4f7f6", "#0f172a")         # Very light gray background / Dark slate
BG_SIDEBAR = ("#ffffff", "#1e293b")     # Pure white sidebar / Slate 800
BG_CARD = ("#ffffff", "#1e293b")        # Pure white cards / Slate 800
BG_CARD_ALT = ("#f8fafc", "#334155")    # Slightly off-white for inner cards

ACCENT_PRIMARY = ("#10b981", "#10b981") # Emerald Green (Main Button Color)
ACCENT_HOVER = ("#059669", "#059669")   # Darker Green
ACCENT_SECONDARY = ("#3b82f6", "#3b82f6")# Blue
ACCENT_WARNING = ("#f59e0b", "#f59e0b") # Yellow/Orange
ACCENT_DANGER = ("#ef4444", "#ef4444")  # Red

TEXT_MAIN = ("#111827", "#f8fafc")      # Near Black / Slate 50
TEXT_MUTED = ("#6b7280", "#94a3b8")     # Gray / Slate 400

# Heatmap Colors (Matches image: light gray to dark green)
HEATMAP_COLORS = [
    ("#ebedf0", "#1e293b"),  # Level 0 (Rest)
    ("#c6e48b", "#064e3b"),  # Level 1 
    ("#7bc96f", "#047857"),  # Level 2 
    ("#239a3b", "#10b981"),  # Level 3 
    ("#196127", "#34d399")   # Level 4 
]

# Fonts
FONT_TITLE = ("Segoe UI", 28, "bold")
FONT_HEADING = ("Segoe UI", 18, "bold")
FONT_SUBHEADING = ("Segoe UI", 14, "bold")
FONT_MAIN = ("Segoe UI", 13)
FONT_SMALL = ("Segoe UI", 11)

# --- Mock Data ---
INDIAN_FOODS = [
    {"name": "Chicken Biryani", "calories": 500, "protein": 29, "carbs": 60, "fats": 18, "serving": "1.5 cups - 350g"},
    {"name": "Masala Dosa", "calories": 350, "protein": 8, "carbs": 50, "fats": 12, "serving": "1 crepe"},
    {"name": "Paneer Butter Masala", "calories": 450, "protein": 15, "carbs": 20, "fats": 35, "serving": "1 bowl"},
    {"name": "Dal Tadka", "calories": 300, "protein": 12, "carbs": 45, "fats": 8, "serving": "1 cup"},
    {"name": "Pasta Bolognese", "calories": 640, "protein": 25, "carbs": 70, "fats": 22, "serving": "1 plate"},
    {"name": "Fruit Salad", "calories": 150, "protein": 2, "carbs": 35, "fats": 1, "serving": "1 bowl"},
    {"name": "Grilled Chicken", "calories": 500, "protein": 45, "carbs": 5, "fats": 15, "serving": "1 breast"},
    {"name": "Oatmeal", "calories": 200, "protein": 6, "carbs": 35, "fats": 4, "serving": "1 bowl"},
]

MOCK_FOOD_LOG = {}
MOCK_EXERCISE_LOG = {}

for i in range(100):  
    date_str = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
    daily_meals = random.sample(INDIAN_FOODS, k=random.randint(2, 4))
    MOCK_FOOD_LOG[date_str] = []
    meal_times = ["09:15 AM", "12:30 PM", "04:30 PM", "07:00 PM"]
    for idx, meal in enumerate(daily_meals):
        meal_copy = meal.copy()
        meal_copy["time"] = meal_times[idx % len(meal_times)]
        MOCK_FOOD_LOG[date_str].append(meal_copy)
        
    if random.random() > 0.3:
        MOCK_EXERCISE_LOG[date_str] = random.choice([1, 2, 3, 4])
    else:
        MOCK_EXERCISE_LOG[date_str] = 0

SUGGESTIONS = [
    {"name": "Morning HIIT", "desc": "High intensity interval training to boost your metabolism and burn calories.", "cal": 280, "time": "25 min", "color": "#e0f2fe", "btn_color": ACCENT_PRIMARY, "icon": "🏃‍♀️"},
    {"name": "Outdoor Running", "desc": "Steady run to improve cardiovascular health and endurance.", "cal": 350, "time": "5 km", "color": "#dcfce7", "btn_color": ACCENT_PRIMARY, "icon": "🏃"},
    {"name": "Evening Yoga", "desc": "Relaxing yoga session to flexibility and reduce stress.", "cal": 120, "time": "20 min", "color": "#f3e8ff", "btn_color": ACCENT_PRIMARY, "icon": "🧘‍♀️"}
]

# --- API Logic ---
def identify_food(base64_image):
    if not API_KEY:
        return {"error": "API_KEY is empty. Please configure it in the script."}
    prompt_text = (
        "Identify the food in this image. Provide the following details in JSON format only: "
        "name, calories, protein_g, carbs_g, fat_g, and a short description. "
        "If it is Indian cuisine, be specific. Return ONLY the raw JSON object. "
        "Do not include any markdown formatting."
    )
    payload = {"contents": [{"parts": [{"text": prompt_text}, {"inlineData": {"mimeType": "image/jpeg", "data": base64_image}}]}]}
    for attempt in range(3):
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                result = response.json()
                content = result['candidates'][0]['content']['parts'][0]['text']
                clean_json = re.sub(r'^```json\s*|\s*```$', '', content, flags=re.MULTILINE).strip()
                return json.loads(clean_json)
            elif response.status_code in [429, 500, 503, 504]:
                time.sleep((2 ** attempt))
                continue
            else:
                return {"error": f"API Error: {response.status_code}"}
        except Exception as e:
            return {"error": "Connection Error"}
    return {"error": "Model overloaded."}

# --- Main Application GUI ---
class NutriVisionApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NutriVision")
        self.geometry("1280x850")
        self.minsize(1100, 700)
        self.configure(fg_color=BG_APP)
        
        # Main Grid Layout: Sidebar + Main Content Area
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # State Variables
        self.current_view = None
        self.cap = None
        self.camera_active = False
        self.current_frame = None
        self.selected_day = datetime.now().strftime("%Y-%m-%d")
        
        # Build UI Components
        self.build_sidebar()
        
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Header Area (Shared)
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.header_frame.grid_columnconfigure(1, weight=1)

        self.lbl_page_title = ctk.CTkLabel(self.header_frame, text="Scan", font=FONT_TITLE, text_color=TEXT_MAIN)
        self.lbl_page_title.grid(row=0, column=0, sticky="w")
        
        self.lbl_page_desc = ctk.CTkLabel(self.header_frame, text="Scan your meal to detect food items and get nutrition info.", font=FONT_MAIN, text_color=TEXT_MUTED)
        self.lbl_page_desc.grid(row=1, column=0, sticky="w")

        self.header_actions = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.header_actions.grid(row=0, column=1, rowspan=2, sticky="e")

        # Container for different views
        self.views_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.views_container.grid(row=1, column=0, sticky="nsew")
        self.views_container.grid_rowconfigure(0, weight=1)
        self.views_container.grid_columnconfigure(0, weight=1)

        # Dictionary to hold frames
        self.views = {}
        self.build_scan_view()
        self.build_track_view()
        self.build_suggestions_view()
        self.build_settings_view()

        # Start App
        self.switch_view("Scan")
        self.update_camera_feed()

    def get_color(self, color_var):
        if isinstance(color_var, tuple):
            return color_var[1] if ctk.get_appearance_mode() == "Dark" else color_var[0]
        return color_var

    # ==========================================
    #               SIDEBAR
    # ==========================================
    def build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=30, sticky="w")
        ctk.CTkLabel(logo_frame, text="🍃", font=("Arial", 24), text_color=ACCENT_PRIMARY).pack(side="left")
        ctk.CTkLabel(logo_frame, text=" NutriVision", font=FONT_HEADING, text_color=TEXT_MAIN).pack(side="left", padx=5)

        # Nav Buttons
        self.nav_btns = {}
        nav_items = [("Scan", "🔍"), ("Track", "📊"), ("Suggestions", "💡"), ("Settings", "⚙️")]
        
        for i, (name, icon) in enumerate(nav_items):
            btn = ctk.CTkButton(
                self.sidebar, text=f"  {name}", image=None, anchor="w", 
                fg_color="transparent", text_color=TEXT_MUTED, hover_color=BG_CARD_ALT,
                font=FONT_HEADING, corner_radius=10, height=45,
                command=lambda n=name: self.switch_view(n)
            )
            btn.configure(text=f"{icon}   {name}") 
            btn.grid(row=i+1, column=0, padx=15, pady=5, sticky="ew")
            self.nav_btns[name] = btn

    def switch_view(self, view_name):
        # Update button highlights
        for name, btn in self.nav_btns.items():
            if name == view_name:
                btn.configure(fg_color=BG_CARD_ALT, text_color=ACCENT_PRIMARY)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_MUTED)

        # Update Header Texts
        headers = {
            "Scan": "Scan your meal to detect food items and get nutrition information instantly.",
            "Track": "Monitor your nutrition, calories, and macronutrients progress.",
            "Suggestions": "Personalized activity recommendations based on your goals and progress.",
            "Settings": "Manage your application preferences and appearance."
        }
        self.lbl_page_title.configure(text=view_name)
        self.lbl_page_desc.configure(text=headers.get(view_name, ""))

        # Clear specific header actions
        for widget in self.header_actions.winfo_children():
            widget.destroy()

        # Build specific header actions
        if view_name == "Scan":
            ctk.CTkButton(self.header_actions, text="📷 Upload Image", fg_color="transparent", border_width=1, border_color=TEXT_MUTED, text_color=TEXT_MAIN, hover_color=BG_CARD_ALT, command=self.upload_image).pack(side="left", padx=10)
            self.btn_capture = ctk.CTkButton(self.header_actions, text="◎ Capture", fg_color=ACCENT_PRIMARY, hover_color=ACCENT_HOVER, command=self.scan_image)
            self.btn_capture.pack(side="left")
            self.camera_active = True
        else:
            self.camera_active = False

        if view_name == "Track":
            # Add date selector in header
            date_frame = ctk.CTkFrame(self.header_actions, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BG_CARD_ALT)
            date_frame.pack(side="right")
            
            def change_date(delta):
                curr = datetime.strptime(self.selected_day, "%Y-%m-%d")
                new_date = curr + timedelta(days=delta)
                self.selected_day = new_date.strftime("%Y-%m-%d")
                
                if self.selected_day == datetime.now().strftime("%Y-%m-%d"):
                    self.lbl_header_date.configure(text="📅 Today")
                else:
                    self.lbl_header_date.configure(text="📅 " + new_date.strftime("%b %d, %Y"))
                
                self.draw_track_charts()

            ctk.CTkButton(date_frame, text="<", width=30, fg_color="transparent", text_color=TEXT_MAIN, command=lambda: change_date(-1)).pack(side="left")
            self.lbl_header_date = ctk.CTkLabel(date_frame, text="📅 Today", font=FONT_MAIN, text_color=TEXT_MAIN)
            self.lbl_header_date.pack(side="left", padx=10)
            
            if self.selected_day != datetime.now().strftime("%Y-%m-%d"):
                self.lbl_header_date.configure(text="📅 " + datetime.strptime(self.selected_day, "%Y-%m-%d").strftime("%b %d, %Y"))

            ctk.CTkButton(date_frame, text=">", width=30, fg_color="transparent", text_color=TEXT_MAIN, command=lambda: change_date(1)).pack(side="left")
            
            self.after(50, self.draw_track_charts)

        if view_name == "Suggestions":
             ctk.CTkButton(self.header_actions, text="↻ Refresh Suggestions", fg_color="transparent", border_width=1, border_color=TEXT_MUTED, text_color=TEXT_MAIN, hover_color=BG_CARD_ALT).pack(side="right")

        # Hide all, show target
        for name, frame in self.views.items():
            frame.grid_forget()
            
        if view_name in self.views:
            self.views[view_name].grid(row=0, column=0, sticky="nsew")
        self.current_view = view_name

    # ==========================================
    #               SCAN VIEW
    # ==========================================
    def build_scan_view(self):
        frame = ctk.CTkFrame(self.views_container, fg_color="transparent")
        self.views["Scan"] = frame
        frame.grid_rowconfigure(0, weight=3)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=5)
        frame.grid_columnconfigure(1, weight=3)

        # --- Camera Card ---
        cam_card = ctk.CTkFrame(frame, fg_color=BG_CARD, corner_radius=15)
        cam_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        cam_card.grid_rowconfigure(0, weight=1)
        cam_card.grid_columnconfigure(0, weight=1)

        self.camera_label = ctk.CTkLabel(cam_card, text="Camera starting...", text_color=TEXT_MUTED)
        self.camera_label.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.camera_ctk_img = None 
        
        # Live badge overlay
        badge = ctk.CTkLabel(cam_card, text="● Live Camera", fg_color="#1e293b", text_color="white", corner_radius=10, width=100, height=25, font=FONT_SMALL)
        badge.place(x=30, y=30)

        # --- Detection Results Card ---
        self.res_card = ctk.CTkFrame(frame, fg_color=BG_CARD, corner_radius=15)
        self.res_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=(0, 10))
        
        # Header
        r_head = ctk.CTkFrame(self.res_card, fg_color="transparent")
        r_head.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(r_head, text="Detection Results", font=FONT_HEADING, text_color=TEXT_MAIN).pack(side="left")
        self.lbl_verified = ctk.CTkLabel(r_head, text="● Verified", text_color="#10b981", fg_color="#dcfce7", corner_radius=10, width=80, height=25, font=FONT_SMALL)
        
        # Food Info
        info_f = ctk.CTkFrame(self.res_card, fg_color="transparent")
        info_f.pack(fill="x", padx=20)
        self.res_icon = ctk.CTkLabel(info_f, text="🍽️", font=("Arial", 40), width=70, height=70, fg_color=BG_CARD_ALT, corner_radius=35)
        self.res_icon.pack(side="left", padx=(0, 15))
        
        text_f = ctk.CTkFrame(info_f, fg_color="transparent")
        text_f.pack(side="left", fill="x", expand=True)
        self.lbl_res_name = ctk.CTkLabel(text_f, text="Awaiting Scan", font=FONT_HEADING, text_color=TEXT_MAIN)
        self.lbl_res_name.pack(anchor="w")
        self.lbl_res_serv = ctk.CTkLabel(text_f, text="--", font=FONT_MAIN, text_color=TEXT_MUTED)
        self.lbl_res_serv.pack(anchor="w")

        # Calories Block
        cal_f = ctk.CTkFrame(self.res_card, fg_color="transparent")
        cal_f.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(cal_f, text="🔥 Calories", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w")
        self.lbl_res_cal = ctk.CTkLabel(cal_f, text="-- kcal", font=FONT_TITLE, text_color=TEXT_MAIN)
        self.lbl_res_cal.pack(anchor="w")

        # Macros Grid
        mac_f = ctk.CTkFrame(self.res_card, fg_color="transparent")
        mac_f.pack(fill="x", padx=20)
        mac_f.grid_columnconfigure((0,1,2), weight=1)

        self.m_pro = self.create_macro_badge(mac_f, "💧 Protein", "--g", 0)
        self.m_car = self.create_macro_badge(mac_f, "🍞 Carbs", "--g", 1)
        self.m_fat = self.create_macro_badge(mac_f, "🥑 Fats", "--g", 2)

        # Serving Dropdown (Mock)
        serv_f = ctk.CTkFrame(self.res_card, fg_color="transparent")
        serv_f.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(serv_f, text="Serving Size", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w")
        ctk.CTkOptionMenu(serv_f, values=["1 Portion", "100g", "1 Cup"], fg_color=BG_CARD_ALT, text_color=TEXT_MAIN, button_color=BG_CARD_ALT).pack(fill="x", pady=5)

        # Add Button
        self.btn_add_log = ctk.CTkButton(self.res_card, text="Add to Log", fg_color=ACCENT_PRIMARY, hover_color=ACCENT_HOVER, font=FONT_SUBHEADING, height=45, state="disabled", command=self.add_to_log)
        self.btn_add_log.pack(fill="x", padx=20, side="bottom", pady=20)


        # --- Recent Foods Horizontal List ---
        rec_f = ctk.CTkFrame(frame, fg_color="transparent")
        rec_f.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        
        rh = ctk.CTkFrame(rec_f, fg_color="transparent")
        rh.pack(fill="x")
        ctk.CTkLabel(rh, text="Recent Foods", font=FONT_HEADING, text_color=TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(rh, text="View All", font=FONT_SMALL, text_color=ACCENT_PRIMARY).pack(side="right")

        scroll = ctk.CTkScrollableFrame(rec_f, fg_color="transparent", orientation="horizontal", height=100)
        scroll.pack(fill="both", expand=True, pady=10)

        for food in INDIAN_FOODS[:5]:
            self.create_recent_food_card(scroll, food).pack(side="left", padx=(0, 15))

    def create_macro_badge(self, parent, title, value, col):
        f = ctk.CTkFrame(parent, fg_color=BG_CARD_ALT, corner_radius=10)
        f.grid(row=0, column=col, padx=5, sticky="ew")
        ctk.CTkLabel(f, text=title, font=FONT_SMALL, text_color=TEXT_MUTED).pack(pady=(10, 0))
        lbl_val = ctk.CTkLabel(f, text=value, font=FONT_HEADING, text_color=TEXT_MAIN)
        lbl_val.pack(pady=(0, 10))
        return lbl_val

    def create_recent_food_card(self, parent, data):
        f = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12, width=220, height=80)
        f.pack_propagate(False)
        ctk.CTkLabel(f, text="🥘", font=("Arial", 24), fg_color=BG_CARD_ALT, corner_radius=10, width=50, height=50).pack(side="left", padx=10)
        txt = ctk.CTkFrame(f, fg_color="transparent")
        txt.pack(side="left", fill="both", expand=True, pady=15)
        ctk.CTkLabel(txt, text=data['name'], font=FONT_SUBHEADING, text_color=TEXT_MAIN, anchor="w").pack(fill="x")
        ctk.CTkLabel(txt, text=f"{data['calories']} kcal • {data.get('time', '12:30 PM')}", font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w").pack(fill="x")
        return f

    def update_camera_feed(self):
        if self.current_view == "Scan" and self.camera_active:
            if not self.cap:
                self.cap = cv2.VideoCapture(0)
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    self.current_frame = frame
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    
                    cam_width = self.camera_label.winfo_width()
                    cam_height = self.camera_label.winfo_height()
                    if cam_width > 50 and cam_height > 50:
                        img.thumbnail((cam_width, cam_height))
                        
                    self.camera_ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                    self.camera_label.configure(image=self.camera_ctk_img, text="")
        self.after(20, self.update_camera_feed)

    def upload_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if file_path:
            img = cv2.imread(file_path)
            if img is not None:
                self.process_image(img)

    def scan_image(self):
        if self.current_frame is not None:
            self.process_image(self.current_frame)

    def process_image(self, frame):
        self.btn_add_log.configure(state="disabled")
        self.lbl_res_name.configure(text="Analyzing image...", text_color=ACCENT_PRIMARY)
        self.lbl_verified.pack_forget()
        
        # Update header button to show scanning state
        if hasattr(self, 'btn_capture') and self.btn_capture.winfo_exists():
            self.btn_capture.configure(state="disabled", text="Scanning...")

        _, buffer = cv2.imencode('.jpg', frame.copy(), [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        base64_image = base64.b64encode(buffer).decode('utf-8')
        threading.Thread(target=self._api_thread, args=(base64_image,)).start()

    def _api_thread(self, base64_image):
        result = identify_food(base64_image)
        self.after(0, lambda: self._update_ui_with_result(result))

    def _update_ui_with_result(self, result):
        if hasattr(self, 'btn_capture') and self.btn_capture.winfo_exists():
            self.btn_capture.configure(state="normal", text="◎ Capture")
            
        if "error" in result:
            self.lbl_res_name.configure(text="Error", text_color=ACCENT_DANGER)
            self.btn_add_log.configure(text="Add to Log")
        else:
            self.current_food_data = result
            self.lbl_verified.pack(side="right")
            self.lbl_res_name.configure(text=result.get('name', 'Unknown'), text_color=TEXT_MAIN)
            self.lbl_res_cal.configure(text=f"{result.get('calories', '0')} kcal")
            self.lbl_res_serv.configure(text=result.get('description', 'Standard Serving')[:30] + "..")
            
            self.m_pro.configure(text=f"{result.get('protein_g', '0')}g")
            self.m_car.configure(text=f"{result.get('carbs_g', '0')}g")
            self.m_fat.configure(text=f"{result.get('fat_g', '0')}g")
            
            self.btn_add_log.configure(state="normal", text="Add to Log")

    def add_to_log(self):
        if hasattr(self, 'current_food_data'):
            today = datetime.now().strftime("%Y-%m-%d")
            time_now = datetime.now().strftime("%I:%M %p")
            new_entry = {
                "name": self.current_food_data.get('name', 'Unknown Food'),
                "calories": self.current_food_data.get('calories', 0),
                "protein": self.current_food_data.get('protein_g', 0),
                "carbs": self.current_food_data.get('carbs_g', 0),
                "fats": self.current_food_data.get('fat_g', 0),
                "time": time_now
            }
            if today not in MOCK_FOOD_LOG: MOCK_FOOD_LOG[today] = []
            MOCK_FOOD_LOG[today].append(new_entry)
            
            self.btn_add_log.configure(text="✅ Added!", state="disabled")
            self.after(2000, lambda: self.btn_add_log.configure(text="Add to Log", state="normal"))
            self.draw_track_charts()

    # ==========================================
    #               TRACK VIEW
    # ==========================================
    def build_track_view(self):
        frame = ctk.CTkFrame(self.views_container, fg_color="transparent")
        self.views["Track"] = frame
        frame.grid_columnconfigure((0, 1), weight=1)
        frame.grid_rowconfigure(1, weight=1) # Charts row
        
        # --- Top Cards (Today & Macros) ---
        top_grid = ctk.CTkFrame(frame, fg_color="transparent")
        top_grid.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        top_grid.grid_columnconfigure((0, 1), weight=1)

        # 1. Today's Intake
        self.intake_card = ctk.CTkFrame(top_grid, fg_color=BG_CARD, corner_radius=15)
        self.intake_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        c_head = ctk.CTkFrame(self.intake_card, fg_color="transparent")
        c_head.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(c_head, text="Today's Intake", font=FONT_HEADING, text_color=TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(c_head, text="Edit Goal", font=FONT_SMALL, text_color=ACCENT_PRIMARY).pack(side="right")

        content_f = ctk.CTkFrame(self.intake_card, fg_color="transparent")
        content_f.pack(fill="both", expand=True, padx=20)
        
        text_f = ctk.CTkFrame(content_f, fg_color="transparent")
        text_f.pack(side="left", fill="y")
        self.lbl_t_cal = ctk.CTkLabel(text_f, text="1,500 kcal", font=FONT_TITLE, text_color=TEXT_MAIN)
        self.lbl_t_cal.pack(anchor="w")
        ctk.CTkLabel(text_f, text="of 2,200 kcal", font=FONT_MAIN, text_color=TEXT_MUTED).pack(anchor="w")

        # Donut Chart Space
        self.fig_donut = Figure(figsize=(2, 2), facecolor=self.get_color(BG_CARD))
        self.ax_donut = self.fig_donut.add_subplot(111)
        self.canvas_donut = FigureCanvasTkAgg(self.fig_donut, master=content_f)
        self.canvas_donut.get_tk_widget().pack(side="right")

        # 2. Macronutrients
        self.macro_card = ctk.CTkFrame(top_grid, fg_color=BG_CARD, corner_radius=15)
        self.macro_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        m_head = ctk.CTkFrame(self.macro_card, fg_color="transparent")
        m_head.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(m_head, text="Macronutrients", font=FONT_HEADING, text_color=TEXT_MAIN).pack(side="left")

        m_content = ctk.CTkFrame(self.macro_card, fg_color="transparent")
        m_content.pack(fill="both", expand=True)

        self.fig_pie = Figure(figsize=(2.5, 2.5), facecolor=self.get_color(BG_CARD))
        self.ax_pie = self.fig_pie.add_subplot(111)
        self.canvas_pie = FigureCanvasTkAgg(self.fig_pie, master=m_content)
        self.canvas_pie.get_tk_widget().pack(side="left", padx=10)

        # Legend 
        leg_f = ctk.CTkFrame(m_content, fg_color="transparent")
        leg_f.pack(side="left", expand=True, padx=10)
        self.lbl_l_carb = ctk.CTkLabel(leg_f, text="● 55% Carbs", text_color=TEXT_MAIN, font=FONT_MAIN); self.lbl_l_carb.pack(anchor="w")
        self.lbl_l_fat = ctk.CTkLabel(leg_f, text="● 20% Fats", text_color=TEXT_MAIN, font=FONT_MAIN); self.lbl_l_fat.pack(anchor="w")
        self.lbl_l_pro = ctk.CTkLabel(leg_f, text="● 25% Protein", text_color=TEXT_MAIN, font=FONT_MAIN); self.lbl_l_pro.pack(anchor="w")

        # --- Middle: Weekly Bar Chart ---
        self.bar_card = ctk.CTkFrame(frame, fg_color=BG_CARD, corner_radius=15)
        self.bar_card.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=10)
        
        b_head = ctk.CTkFrame(self.bar_card, fg_color="transparent")
        b_head.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(b_head, text="Weekly Calorie Intake", font=FONT_HEADING, text_color=TEXT_MAIN).pack(side="left")

        self.fig_bar = Figure(figsize=(8, 3), facecolor=self.get_color(BG_CARD))
        self.ax_bar = self.fig_bar.add_subplot(111)
        self.canvas_bar = FigureCanvasTkAgg(self.fig_bar, master=self.bar_card)
        self.canvas_bar.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Connect click event to bar chart
        self.fig_bar.canvas.mpl_connect('button_press_event', self.on_bar_click)

        # --- Bottom: Recent Meals ---
        rec_f = ctk.CTkFrame(frame, fg_color="transparent")
        rec_f.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        
        rh = ctk.CTkFrame(rec_f, fg_color="transparent")
        rh.pack(fill="x")
        ctk.CTkLabel(rh, text="Meals Logged", font=FONT_HEADING, text_color=TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(rh, text="View All", font=FONT_SMALL, text_color=ACCENT_PRIMARY).pack(side="right")

        self.meals_scroll = ctk.CTkScrollableFrame(rec_f, fg_color="transparent", orientation="horizontal", height=100)
        self.meals_scroll.pack(fill="both", expand=True, pady=10)

    def on_bar_click(self, event):
        if event.inaxes == self.ax_bar and event.xdata is not None:
            day_idx = int(round(event.xdata))
            if 0 <= day_idx <= 6:
                selected_dt = datetime.strptime(self.selected_day, "%Y-%m-%d")
                start_of_week = selected_dt - timedelta(days=selected_dt.weekday())
                new_date = start_of_week + timedelta(days=day_idx)
                
                self.selected_day = new_date.strftime("%Y-%m-%d")
                
                # Update header label dynamically if present
                if hasattr(self, 'lbl_header_date'):
                    if self.selected_day == datetime.now().strftime("%Y-%m-%d"):
                        self.lbl_header_date.configure(text="📅 Today")
                    else:
                        self.lbl_header_date.configure(text="📅 " + new_date.strftime("%b %d, %Y"))
                        
                self.draw_track_charts()

    def draw_track_charts(self):
        bg = self.get_color(BG_CARD)
        text_color = self.get_color(TEXT_MUTED)
        
        # 1. Donut
        self.fig_donut.set_facecolor(bg)
        self.ax_donut.clear()
        today_cals = sum(float(m.get('calories', 0)) for m in MOCK_FOOD_LOG.get(self.selected_day, []))
        goal = 2200
        pct = min(today_cals / goal, 1.0)
        
        self.lbl_t_cal.configure(text=f"{int(today_cals):,} kcal")
        
        wedges, _ = self.ax_donut.pie([pct, 1-pct], colors=[self.get_color(ACCENT_PRIMARY), self.get_color(BG_CARD_ALT)], startangle=90, counterclock=False, wedgeprops=dict(width=0.3, edgecolor=bg))
        self.ax_donut.text(0, 0, f"{int(pct*100)}%", ha='center', va='center', fontsize=12, fontweight='bold', color=self.get_color(ACCENT_PRIMARY))
        self.canvas_donut.draw()

        # 2. Pie Chart Macros
        self.fig_pie.set_facecolor(bg)
        self.ax_pie.clear()
        tc, tf, tp = 1, 1, 1
        for m in MOCK_FOOD_LOG.get(self.selected_day, []):
            tc += float(m.get('carbs', 0)); tf += float(m.get('fats', 0)); tp += float(m.get('protein', 0))
            
        colors = ["#3b82f6", "#f59e0b", "#f43f5e"] # Blue, Yellow, Red matching image
        self.ax_pie.pie([tc, tf, tp], colors=colors, startangle=90)
        self.canvas_pie.draw()
        
        total = tc+tf+tp
        self.lbl_l_carb.configure(text=f"● {int(tc/total*100)}% Carbs", text_color=colors[0])
        self.lbl_l_fat.configure(text=f"● {int(tf/total*100)}% Fats", text_color=colors[1])
        self.lbl_l_pro.configure(text=f"● {int(tp/total*100)}% Protein", text_color=colors[2])

        # 3. Bar Chart
        self.fig_bar.set_facecolor(bg)
        self.ax_bar.clear()
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        cals = []
        bar_colors = []
        
        selected_dt = datetime.strptime(self.selected_day, "%Y-%m-%d")
        start_of_week = selected_dt - timedelta(days=selected_dt.weekday())
        
        for i in range(7):
            d_dt = start_of_week + timedelta(days=i)
            d_str = d_dt.strftime("%Y-%m-%d")
            c = sum(float(m.get('calories', 0)) for m in MOCK_FOOD_LOG.get(d_str, []))
            cals.append(c)
            
            # Highlight selected day dynamically
            if d_str == self.selected_day:
                bar_colors.append(self.get_color(ACCENT_WARNING))
            else:
                bar_colors.append(self.get_color(ACCENT_SECONDARY))

        self.ax_bar.bar(days, cals, color=bar_colors, width=0.4, edgecolor='none')
        self.ax_bar.tick_params(colors=text_color, bottom=False, left=False)
        for spine in self.ax_bar.spines.values(): spine.set_visible(False)
        self.ax_bar.grid(axis='y', linestyle='-', alpha=0.1)
        self.canvas_bar.draw()

        # Update Meals
        for w in self.meals_scroll.winfo_children(): w.destroy()
        meals = MOCK_FOOD_LOG.get(self.selected_day, [])
        if not meals:
             ctk.CTkLabel(self.meals_scroll, text="No meals logged for this day.", font=FONT_MAIN, text_color=TEXT_MUTED).pack(pady=20, padx=20)
        else:
            for m in meals:
                self.create_recent_food_card(self.meals_scroll, m).pack(side="left", padx=(0, 15))


    # ==========================================
    #            SUGGESTIONS VIEW
    # ==========================================
    def build_suggestions_view(self):
        frame = ctk.CTkFrame(self.views_container, fg_color="transparent")
        self.views["Suggestions"] = frame
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # --- Top: Smart Recommendations ---
        ctk.CTkLabel(frame, text="Smart Recommendations", font=FONT_HEADING, text_color=TEXT_MAIN).grid(row=0, column=0, sticky="w", pady=(0, 15))
        
        rec_frame = ctk.CTkFrame(frame, fg_color="transparent")
        rec_frame.grid(row=1, column=0, sticky="nsew")
        rec_frame.grid_columnconfigure((0,1,2), weight=1)

        for i, sug in enumerate(SUGGESTIONS):
            card = ctk.CTkFrame(rec_frame, fg_color=BG_CARD, corner_radius=15)
            card.grid(row=0, column=i, sticky="nsew", padx=10)
            card.pack_propagate(False)
            
            # Top Graphic Area
            g_frame = ctk.CTkFrame(card, fg_color=sug['color'], height=120, corner_radius=15)
            g_frame.pack(fill="x", padx=10, pady=10)
            ctk.CTkLabel(g_frame, text=sug['icon'], font=("Arial", 60)).place(relx=0.5, rely=0.5, anchor="center")

            # Info
            i_frame = ctk.CTkFrame(card, fg_color="transparent")
            i_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            ctk.CTkLabel(i_frame, text=sug['name'], font=FONT_HEADING, text_color=TEXT_MAIN).pack(anchor="w")
            ctk.CTkLabel(i_frame, text=sug['desc'], font=FONT_MAIN, text_color=TEXT_MUTED, wraplength=250, justify="left").pack(anchor="w", pady=(5, 15))
            
            # Stats
            s_frame = ctk.CTkFrame(i_frame, fg_color="transparent")
            s_frame.pack(fill="x", pady=10)
            ctk.CTkLabel(s_frame, text=f"🔥 {sug['cal']} kcal", font=FONT_SUBHEADING, text_color=TEXT_MAIN).pack(side="left")
            ctk.CTkLabel(s_frame, text=f"⏱️ {sug['time']}", font=FONT_SUBHEADING, text_color=TEXT_MAIN).pack(side="left", padx=20)

            # Button 
            btn = ctk.CTkButton(card, text="Start Session", fg_color=sug['btn_color'], hover_color=ACCENT_HOVER, font=FONT_SUBHEADING, height=40, command=lambda s=sug: self.start_session(s))
            if i > 0: btn.configure(fg_color="transparent", border_width=1, border_color=ACCENT_PRIMARY, text_color=ACCENT_PRIMARY)
            btn.pack(fill="x", padx=20, pady=20, side="bottom")

        # --- Bottom: Monthly Heatmap ---
        heat_card = ctk.CTkFrame(frame, fg_color=BG_CARD, corner_radius=15)
        heat_card.grid(row=2, column=0, sticky="nsew", pady=(20, 0))
        
        h_head = ctk.CTkFrame(heat_card, fg_color="transparent")
        h_head.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(h_head, text="Monthly Activity Heat Map", font=FONT_HEADING, text_color=TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(h_head, text="< October 2023 >", font=FONT_MAIN, text_color=TEXT_MUTED).pack(side="right")

        # Grid container
        grid_f = ctk.CTkFrame(heat_card, fg_color="transparent")
        grid_f.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Side stats
        stat_f = ctk.CTkFrame(grid_f, fg_color="transparent", width=150)
        stat_f.pack(side="right", fill="y", padx=(20, 0))
        ctk.CTkLabel(stat_f, text="This Month", font=FONT_SUBHEADING, text_color=TEXT_MAIN).pack(anchor="w", pady=(0,10))
        
        def add_stat(icon, val, sub):
            f = ctk.CTkFrame(stat_f, fg_color="transparent"); f.pack(fill="x", pady=5)
            ctk.CTkLabel(f, text=icon, font=("Arial", 20)).pack(side="left")
            t_f = ctk.CTkFrame(f, fg_color="transparent"); t_f.pack(side="left", padx=10)
            ctk.CTkLabel(t_f, text=val, font=FONT_SUBHEADING, text_color=TEXT_MAIN).pack(anchor="w")
            ctk.CTkLabel(t_f, text=sub, font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w")
            
        add_stat("📅", "12", "sessions")
        add_stat("🔥", "3,240", "kcal Burned")
        add_stat("🏃", "18.4", "km Tracked")

        # Heatmap blocks
        map_f = ctk.CTkFrame(grid_f, fg_color="transparent")
        map_f.pack(side="left", fill="both", expand=True)

        days = ['Mon', 'Wed', 'Fri', 'Sun']
        for i, d in enumerate(days):
            ctk.CTkLabel(map_f, text=d, font=FONT_SMALL, text_color=TEXT_MUTED).grid(row=i*2, column=0, padx=(0, 10))

        # Build horizontal heatmap 
        for col in range(1, 32):
            ctk.CTkLabel(map_f, text=str(col), font=FONT_SMALL, text_color=TEXT_MUTED).grid(row=8, column=col, pady=(5,0))
            for row in range(7):
                intensity = random.choice([0, 0, 1, 2, 3, 4])
                color = self.get_color(HEATMAP_COLORS[intensity])
                # Small rounded squares
                box = ctk.CTkFrame(map_f, width=16, height=16, fg_color=color, corner_radius=3)
                box.grid(row=row, column=col, padx=2, pady=2)

        # Legend
        leg_f = ctk.CTkFrame(heat_card, fg_color="transparent")
        leg_f.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(leg_f, text="Less Activity", font=FONT_SMALL, text_color=TEXT_MUTED).pack(side="left", padx=5)
        for i in range(5):
             ctk.CTkFrame(leg_f, width=12, height=12, fg_color=self.get_color(HEATMAP_COLORS[i]), corner_radius=2).pack(side="left", padx=2)
        ctk.CTkLabel(leg_f, text="More Activity", font=FONT_SMALL, text_color=TEXT_MUTED).pack(side="left", padx=5)

    def start_session(self, sug):
        # Create Toplevel popup window for the timer
        timer_win = ctk.CTkToplevel(self)
        timer_win.title(f"Active Session: {sug['name']}")
        timer_win.geometry("400x300")
        timer_win.attributes("-topmost", True)
        timer_win.configure(fg_color=self.get_color(BG_CARD))

        # Extract minutes from string (e.g., "25 min" -> 25)
        match = re.search(r'\d+', sug['time'])
        minutes = int(match.group()) if match else 10
        total_seconds = minutes * 60

        lbl_title = ctk.CTkLabel(timer_win, text=f"{sug['icon']} {sug['name']}", font=("Segoe UI", 24, "bold"), text_color=self.get_color(TEXT_MAIN))
        lbl_title.pack(pady=(40, 10))

        lbl_time = ctk.CTkLabel(timer_win, text=f"{minutes:02d}:00", font=("Segoe UI", 48, "bold"), text_color=self.get_color(ACCENT_PRIMARY))
        lbl_time.pack(pady=20)

        def update_timer(left):
            if not timer_win.winfo_exists(): return
            if left >= 0:
                mins, secs = divmod(left, 60)
                lbl_time.configure(text=f"{mins:02d}:{secs:02d}")
                timer_win.after(1000, update_timer, left - 1)
            else:
                lbl_time.configure(text="00:00", text_color=self.get_color(ACCENT_SUCCESS))
                ctk.CTkLabel(timer_win, text="Session Complete! Great Job!", font=("Segoe UI", 16, "bold"), text_color=self.get_color(ACCENT_SUCCESS)).pack(pady=10)

        # Begin countdown
        update_timer(total_seconds)

    # ==========================================
    #               SETTINGS VIEW
    # ==========================================
    def build_settings_view(self):
        frame = ctk.CTkFrame(self.views_container, fg_color="transparent")
        self.views["Settings"] = frame
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(frame, fg_color=BG_CARD, corner_radius=15)
        card.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        ctk.CTkLabel(card, text="Appearance Settings", font=FONT_HEADING, text_color=TEXT_MAIN).pack(pady=(40, 10))

        self.appearance_menu = ctk.CTkOptionMenu(
            card, values=["Light", "Dark", "System"],
            command=self.change_appearance_mode_event,
            fg_color=BG_CARD_ALT, text_color=TEXT_MAIN, button_color=ACCENT_PRIMARY,
            font=FONT_MAIN, width=200, height=40, corner_radius=10
        )
        self.appearance_menu.pack(pady=10)
        self.appearance_menu.set("Light")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)
        # Redraw charts and colors dynamically
        if self.current_view == "Track":
            self.draw_track_charts()
        # Force a total refresh of the view to apply tuple colors to custom components
        self.switch_view(self.current_view)

    def on_closing(self):
        self.camera_active = False
        if self.cap:
            self.cap.release()
        self.destroy()

if __name__ == "__main__":
    app = NutriVisionApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()