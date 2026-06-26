import os
import json
import time
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import cv2
import mediapipe as mp

# --- HOTFIX FOR MEDIAPIPE ATTRIBUTE ERROR ---
if not hasattr(mp, 'solutions'):
    try:
        import mediapipe.python.solutions as solutions
        mp.solutions = solutions
    except ImportError:
        pass

import serial
import serial.tools.list_ports
from PIL import Image, ImageTk

# --- SYSTEM CONFIGURATION ---
CONFIG_FILE = "config.json"

# Expanded List of Recognizable Gestures
GESTURES = {
    "NONE": "No Hand (Idle)",
    "FIST": "Fist (Closed Hand)",
    "INDEX": "One Finger (Index)",
    "PEACE": "Peace Sign (V)",
    "THREE": "Three Fingers",
    "FOUR": "Four Fingers",
    "OPEN": "Open Palm (High 5)",
    "THUMB_UP": "Thumbs Up",
    "ROCK": "Rock On Sign",
    "SPIDER": "Spider-Man Sign"
}

# Default mappings for a fresh start
DEFAULT_CONFIG = {
    "NONE": {"name": "Idle Mode", "pin": "ALL", "action": "CLEAR", "interval": ""},
    "FIST": {"name": "Emergency Stop", "pin": "ALL", "action": "CLEAR", "interval": ""},
    "INDEX": {"name": "Red LED Only", "pin": "2", "action": "ON", "interval": ""},
    "PEACE": {"name": "Yellow Blink", "pin": "3", "action": "BLINK", "interval": "300"},
    "THREE": {"name": "Green LED Only", "pin": "4", "action": "ON", "interval": ""},
    "FOUR": {"name": "Unassigned 4", "pin": "ALL", "action": "CLEAR", "interval": ""},
    "OPEN": {"name": "All Lights ON", "pin": "ALL", "action": "ON", "interval": ""},
    "THUMB_UP": {"name": "Confirm / OK", "pin": "4", "action": "BLINK", "interval": "100"},
    "ROCK": {"name": "Party Mode", "pin": "ALL", "action": "BLINK", "interval": "200"},
    "SPIDER": {"name": "Web Shooter", "pin": "2", "action": "BLINK", "interval": "50"}
}

# --- MAIN APPLICATION CLASS ---
class NexusApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Window Setup
        self.title("LED Gesture Controller")
        self.geometry("1300x750")
        self.minsize(1100, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # System Variables
        self.config_data = self.load_config()
        self.serial_conn = None
        self.camera_active = False
        self.cap = None
        self.current_active_gesture = ""  # Keeps track so we don't spam the Arduino

        # MediaPipe Setup
        try:
            self.mp_hands = mp.solutions.hands
            self.mp_draw = mp.solutions.drawing_utils
        except AttributeError:
            from mediapipe.python.solutions import hands as mp_hands
            from mediapipe.python.solutions import drawing_utils as mp_draw
            self.mp_hands = mp_hands
            self.mp_draw = mp_draw
            
        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
        self.tip_ids = [4, 8, 12, 16, 20] # Thumb, Index, Middle, Ring, Pinky

        self.build_ui()
        self.update_port_list()

    # --- UI BUILDING ---
    def build_ui(self):
        # Configure Grid: 3 Columns (Controls, Camera, Rules)
        self.grid_columnconfigure(0, weight=0, minsize=300)
        self.grid_columnconfigure(1, weight=1) # Camera takes up remaining space
        self.grid_columnconfigure(2, weight=0, minsize=450)
        self.grid_rowconfigure(0, weight=1)

        # ========================================================
        # COLUMN 0: SYSTEM CONTROLS
        # ========================================================
        self.sidebar = ctk.CTkFrame(self, corner_radius=0, fg_color="#1a1a1a")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="LED GESTURE\nCONTROLLER", font=ctk.CTkFont(size=26, weight="bold", slant="italic"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(40, 20))

        # Hardware Connection
        self.conn_frame = ctk.CTkFrame(self.sidebar, fg_color="#2b2b2b", corner_radius=10)
        self.conn_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.conn_frame, text="Hardware Link", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 0))
        
        self.port_var = tk.StringVar(value="Select Port")
        self.port_dropdown = ctk.CTkOptionMenu(self.conn_frame, variable=self.port_var, values=["Searching..."])
        self.port_dropdown.pack(padx=20, pady=(10, 5), fill="x")
        
        self.connect_btn = ctk.CTkButton(self.conn_frame, text="Connect Hardware", command=self.toggle_connection)
        self.connect_btn.pack(padx=20, pady=(5, 15), fill="x")

        # Camera Controls
        self.cam_frame = ctk.CTkFrame(self.sidebar, fg_color="#2b2b2b", corner_radius=10)
        self.cam_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.cam_frame, text="Vision System", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 0))
        self.cam_btn = ctk.CTkButton(self.cam_frame, text="Start Camera Feed", command=self.toggle_camera, height=40)
        self.cam_btn.pack(padx=20, pady=(10, 15), fill="x")

        # Status Display
        self.status_var = tk.StringVar(value="OFFLINE")
        self.status_label = ctk.CTkLabel(self.sidebar, textvariable=self.status_var, font=ctk.CTkFont(size=14, weight="bold"), text_color="#e74c3c")
        self.status_label.grid(row=3, column=0, pady=20)


        # ========================================================
        # COLUMN 1: LIVE MONITOR (CAMERA)
        # ========================================================
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#101010")
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.video_label = tk.Label(self.main_frame, bg="#000000", text="CAMERA OFFLINE", fg="#444444", font=("Arial", 24, "bold"))
        self.video_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")


        # ========================================================
        # COLUMN 2: RULES MANAGER
        # ========================================================
        self.rules_frame = ctk.CTkScrollableFrame(self, width=450, corner_radius=0, fg_color="#1a1a1a")
        self.rules_frame.grid(row=0, column=2, sticky="nsew")

        title_frame = ctk.CTkFrame(self.rules_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(20, 10), padx=20)
        
        ctk.CTkLabel(title_frame, text="Mapping Dashboard", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        ctk.CTkButton(title_frame, text="Save Config", width=100, command=self.save_config, fg_color="#27ae60", hover_color="#2ecc71").pack(side="right")

        self.rule_vars = {} # Store Tkinter variables

        # Build dynamic rows based on GESTURES dictionary
        for gesture_id, description in GESTURES.items():
            row_frame = ctk.CTkFrame(self.rules_frame, fg_color="#2b2b2b", corner_radius=8)
            row_frame.pack(fill="x", padx=10, pady=5)
            
            rule = self.config_data.get(gesture_id, {"name": "", "pin": "ALL", "action": "CLEAR", "interval": ""})
            
            # Header line (Gesture Name)
            ctk.CTkLabel(row_frame, text=description, font=ctk.CTkFont(weight="bold", size=13), text_color="#1abc9c").grid(row=0, column=0, columnspan=4, padx=10, pady=(5,0), sticky="w")
            
            # Form elements
            name_var = tk.StringVar(value=rule["name"])
            name_entry = ctk.CTkEntry(row_frame, textvariable=name_var, width=130, placeholder_text="Alias (e.g. Stop)")
            name_entry.grid(row=1, column=0, padx=5, pady=(5, 10))
            
            pin_var = tk.StringVar(value=rule["pin"])
            pin_opts = ["ALL"] + [str(i) for i in range(2, 14)]
            pin_menu = ctk.CTkOptionMenu(row_frame, variable=pin_var, values=pin_opts, width=60)
            pin_menu.grid(row=1, column=1, padx=5, pady=(5, 10))
            
            action_var = tk.StringVar(value=rule["action"])
            action_opts = ["ON", "OFF", "BLINK", "CLEAR"]
            action_menu = ctk.CTkOptionMenu(row_frame, variable=action_var, values=action_opts, width=80)
            action_menu.grid(row=1, column=2, padx=5, pady=(5, 10))
            
            int_var = tk.StringVar(value=rule["interval"])
            int_entry = ctk.CTkEntry(row_frame, textvariable=int_var, width=50, placeholder_text="ms")
            int_entry.grid(row=1, column=3, padx=5, pady=(5, 10))

            self.rule_vars[gesture_id] = {"name": name_var, "pin": pin_var, "action": action_var, "interval": int_var}

    # --- CONFIGURATION LOGIC ---
    def load_config(self):
        loaded = DEFAULT_CONFIG.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    user_config = json.load(f)
                    for k, v in user_config.items():
                        if k in loaded: # Map only recognized keys
                            loaded[k] = v
            except Exception:
                pass
        return loaded

    def save_config(self):
        for g_id, vars_dict in self.rule_vars.items():
            self.config_data[g_id] = {
                "name": vars_dict["name"].get(),
                "pin": vars_dict["pin"].get(),
                "action": vars_dict["action"].get(),
                "interval": vars_dict["interval"].get()
            }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config_data, f, indent=4)
        messagebox.showinfo("Saved", "Hardware configurations successfully saved!")

    # --- SERIAL HARDWARE LOGIC ---
    def update_port_list(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if ports:
            self.port_dropdown.configure(values=ports)
            if self.port_var.get() == "Searching..." or self.port_var.get() == "No Ports Found":
                self.port_var.set(ports[0])
        else:
            self.port_dropdown.configure(values=["No Ports Found"])
            self.port_var.set("No Ports Found")
        self.after(5000, self.update_port_list)

    def toggle_connection(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.serial_conn = None
            self.connect_btn.configure(text="Connect Hardware", fg_color=["#3B8ED0", "#1F6AA5"])
            self.update_status()
        else:
            port = self.port_var.get()
            if port and "Found" not in port and "Select" not in port:
                try:
                    self.serial_conn = serial.Serial(port, 9600, timeout=1)
                    time.sleep(1.5)
                    self.connect_btn.configure(text="Disconnect Hardware", fg_color="#e74c3c", hover_color="#c0392b")
                    self.send_to_arduino("CLEAR")
                    self.update_status()
                except Exception as e:
                    messagebox.showerror("Connection Error", f"Could not connect to {port}.\n{e}")

    def send_to_arduino(self, command):
        if self.serial_conn and self.serial_conn.is_open:
            try:
                packet = f"{command}\n"
                self.serial_conn.write(packet.encode('utf-8'))
                print(f"HW >> {packet.strip()}")
            except Exception as e:
                print(f"Serial Error: {e}")

    def update_status(self):
        cam = "ON" if self.camera_active else "OFF"
        if self.serial_conn and self.serial_conn.is_open:
            ser = f"CONNECTED ({self.port_var.get()})"
            color = "#2ecc71"
        else:
            ser = "DISCONNECTED"
            color = "#e74c3c"
        self.status_var.set(f"CAM: {cam} | HW: {ser}")
        self.status_label.configure(text_color=color)

    # --- COMPUTER VISION LOGIC ---
    def toggle_camera(self):
        if self.camera_active:
            self.camera_active = False
            self.cam_btn.configure(text="Start Camera Feed", fg_color=["#3B8ED0", "#1F6AA5"])
            if self.cap:
                self.cap.release()
            self.video_label.configure(image='', text="CAMERA OFFLINE", bg="#000000")
            self.update_status()
            self.process_gesture("NONE", None) # Turn off LEDs when camera closes
        else:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("Camera Error", "Could not access webcam.")
                return
            self.camera_active = True
            self.cam_btn.configure(text="Stop Camera Feed", fg_color="#e74c3c", hover_color="#c0392b")
            self.update_status()
            self.video_loop()

    def process_gesture(self, gesture_id, frame):
        # Update UI text on the frame
        if frame is not None:
            rule_name = self.config_data.get(gesture_id, {}).get("name", "Unknown Pose")
            if gesture_id == "UNKNOWN": rule_name = "Unrecognized"
            cv2.putText(frame, f'Active: {rule_name}', (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (26, 188, 156), 3)

        # Only trigger hardware if the state has changed (prevents spamming)
        if gesture_id != self.current_active_gesture:
            self.current_active_gesture = gesture_id
            
            # If the gesture is completely unknown, safely clear the LEDs
            if gesture_id == "UNKNOWN":
                self.send_to_arduino("CLEAR")
                return

            rule = self.config_data.get(gesture_id)
            if rule:
                action = rule["action"]
                pin = rule["pin"]
                interval = rule["interval"]

                if action == "CLEAR":
                    self.send_to_arduino("CLEAR")
                
                elif action == "ON":
                    if pin == "ALL":
                        # Turn on primary pins to prevent serial flooding
                        for i in range(2, 6): self.send_to_arduino(f"ON:{i}")
                    else:
                        self.send_to_arduino(f"ON:{pin}")
                
                elif action == "OFF":
                    if pin == "ALL":
                        self.send_to_arduino("CLEAR")
                    else:
                        self.send_to_arduino(f"OFF:{pin}")
                
                elif action == "BLINK":
                    interval = interval if interval.isdigit() else "500"
                    if pin == "ALL":
                         for i in range(2, 6): self.send_to_arduino(f"BLINK:{i}:{interval}")
                    else:
                        self.send_to_arduino(f"BLINK:{pin}:{interval}")

    def video_loop(self):
        if not self.camera_active:
            return

        success, frame = self.cap.read()
        if success:
            frame = cv2.flip(frame, 1) # Mirror image
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)

            detected_gesture = "NONE"

            if results.multi_hand_landmarks:
                for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    
                    # Figure out if physical hand is Left or Right (needed for thumb accuracy)
                    is_right_hand = True
                    if results.multi_handedness:
                        label = results.multi_handedness[idx].classification[0].label
                        # Because we flipped the frame earlier, "Left" actually means physical Right hand
                        is_right_hand = (label == "Left")

                    fingers = []
                    
                    # 1. Thumb Exception (X-axis check)
                    if is_right_hand:
                        thumb_open = hand_landmarks.landmark[self.tip_ids[0]].x > hand_landmarks.landmark[self.tip_ids[0] - 1].x
                    else:
                        thumb_open = hand_landmarks.landmark[self.tip_ids[0]].x < hand_landmarks.landmark[self.tip_ids[0] - 1].x
                    fingers.append(1 if thumb_open else 0)

                    # 2. Four Fingers (Y-axis check)
                    for id in range(1, 5):
                        if hand_landmarks.landmark[self.tip_ids[id]].y < hand_landmarks.landmark[self.tip_ids[id] - 2].y:
                            fingers.append(1)
                        else:
                            fingers.append(0)

                    # MATCH FINGER ARRAY TO SPECIFIC POSES
                    if fingers == [0,0,0,0,0]: detected_gesture = "FIST"
                    elif fingers == [0,1,0,0,0]: detected_gesture = "INDEX"
                    elif fingers == [0,1,1,0,0]: detected_gesture = "PEACE"
                    elif fingers == [0,1,1,1,0]: detected_gesture = "THREE"
                    elif fingers == [0,1,1,1,1]: detected_gesture = "FOUR"
                    elif fingers == [1,1,1,1,1]: detected_gesture = "OPEN"
                    elif fingers == [1,0,0,0,0]: detected_gesture = "THUMB_UP"
                    elif fingers == [0,1,0,0,1]: detected_gesture = "ROCK"
                    elif fingers == [1,1,0,0,1]: detected_gesture = "SPIDER"
                    else: detected_gesture = "UNKNOWN"
                    
            # Fire command based on current state
            self.process_gesture(detected_gesture, frame)

            # Update Canvas
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            img_tk = ImageTk.PhotoImage(image=img_pil)
            self.video_label.imgtk = img_tk
            self.video_label.configure(image=img_tk, bg="#000000")

        self.after(15, self.video_loop)

# --- RUN APP ---
if __name__ == "__main__":
    app = NexusApp()
    app.protocol("WM_DELETE_WINDOW", lambda: (app.cap.release() if app.cap else None, app.destroy()))
    app.mainloop()