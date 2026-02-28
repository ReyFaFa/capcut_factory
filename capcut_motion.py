"""
CapCut Motion Studio - Professional Motion Automation Tool
Final v3 — Pan 로직 수정 (0 → 방향), Preview 축소, Drop Zone 확대
"""

import json
import random
import uuid
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from pathlib import Path

# ============================================================
# 0. Drag & Drop 백엔드 감지
# ============================================================

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_BACKEND = "tkinterdnd2"
except ImportError:
    DND_BACKEND = None

if DND_BACKEND is None and sys.platform == "win32":
    try:
        import ctypes
        from ctypes import windll, wintypes, WINFUNCTYPE, cast, POINTER, create_unicode_buffer
        from ctypes.wintypes import HWND, UINT, WPARAM, LPARAM, BOOL, LPWSTR

        _is_64bit = sys.maxsize > 2**32
        LONG_PTR = ctypes.c_longlong if _is_64bit else ctypes.c_long
        WNDPROC = WINFUNCTYPE(LONG_PTR, HWND, UINT, WPARAM, LPARAM)

        GWL_WNDPROC = -4
        WM_DROPFILES = 0x0233
        MAX_PATH = 260

        shell32 = windll.shell32
        shell32.DragAcceptFiles.argtypes = (HWND, BOOL)
        shell32.DragQueryFileW.argtypes = (WPARAM, UINT, LPWSTR, UINT)
        shell32.DragQueryFileW.restype = UINT
        shell32.DragFinish.argtypes = (WPARAM,)

        user32 = windll.user32
        user32.SetWindowLongPtrW.argtypes = (HWND, ctypes.c_int, WNDPROC)
        user32.SetWindowLongPtrW.restype = WNDPROC
        user32.CallWindowProcW.argtypes = (WNDPROC, HWND, UINT, WPARAM, LPARAM)
        user32.CallWindowProcW.restype = LONG_PTR

        DND_BACKEND = "win32_native"
    except Exception:
        DND_BACKEND = None


class Win32DropHandler:
    def __init__(self, tk_root, callback):
        self.root = tk_root
        self.callback = callback
        self._old_proc = None
        self._new_proc = None

    def enable(self):
        self.root.update_idletasks()
        hwnd = int(self.root.frame(), 16)
        self._new_proc = WNDPROC(self._wnd_proc)
        self._old_proc = user32.SetWindowLongPtrW(hwnd, GWL_WNDPROC, self._new_proc)
        shell32.DragAcceptFiles(hwnd, True)

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_DROPFILES:
            self._handle_drop(wparam)
            return 0
        return user32.CallWindowProcW(self._old_proc, hwnd, msg, wparam, lparam)

    def _handle_drop(self, hdrop):
        count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
        files = []
        for i in range(count):
            buf = create_unicode_buffer('', MAX_PATH)
            shell32.DragQueryFileW(hdrop, i, buf, MAX_PATH)
            files.append(buf[:].split('\0', 1)[0])
        shell32.DragFinish(hdrop)
        for f in files:
            if f.lower().endswith('.json'):
                self.root.after(10, self.callback, f)
                return
        self.root.after(10, lambda: messagebox.showwarning(
            "Invalid File", "Only .json files are supported."))


# ============================================================
# 1. Motion Engine — Pan: 0 → 방향값 (양수만)
# ============================================================

class MotionEngine:
    @staticmethod
    def compute_zoom(zoom_type, start_scale, end_scale_min, end_scale_max):
        if zoom_type == "none":
            return 1.0, 1.0
        elif zoom_type == "zoom_in":
            return start_scale, round(random.uniform(end_scale_min, end_scale_max), 6)
        elif zoom_type == "zoom_out":
            return round(random.uniform(end_scale_min, end_scale_max), 6), start_scale
        elif zoom_type == "zoom_random":
            end_s = round(random.uniform(end_scale_min, end_scale_max), 6)
            return (start_scale, end_s) if random.random() < 0.5 else (end_s, start_scale)
        return start_scale, round(random.uniform(end_scale_min, end_scale_max), 6)

    @staticmethod
    def compute_pan_axis(pan_type, strength):
        """
        Pan은 항상 정지(0)에서 시작 → 선택 방향으로 이동
        strength는 양수 절대값만 사용
        """
        if pan_type == "none":
            return 0.0, 0.0
        elif pan_type == "positive":    # L→R (X+) 또는 T→B (Y+)
            return 0.0, round(strength, 6)
        elif pan_type == "negative":    # R→L (X-) 또는 B→T (Y-)
            return 0.0, round(-strength, 6)
        elif pan_type == "random":
            return 0.0, round(random.uniform(-strength, strength), 6)
        return 0.0, 0.0

    @staticmethod
    def interpolate(start, end, progress):
        return start + (end - start) * progress

    @staticmethod
    def ease_in_out(t):
        return t * t * (3.0 - 2.0 * t)


# ============================================================
# 2. MotionCard
# ============================================================

class MotionCard(tk.Frame):
    COLORS = {
        'normal': '#1E1E1E', 'hover': '#252525',
        'selected': '#3B82F6', 'border': '#2A2A2A', 'text': '#F1F1F1'
    }

    def __init__(self, parent, icon, title, value, variable, **kwargs):
        super().__init__(parent, **kwargs)
        self.value = value
        self.variable = variable
        self.is_selected = False

        self.configure(width=85, height=62)
        self.pack_propagate(False)
        self.configure(bg=self.COLORS['normal'],
                       highlightthickness=2,
                       highlightbackground=self.COLORS['border'],
                       cursor='hand2')

        icon_label = tk.Label(self, text=icon, font=('Segoe UI', 14),
                              bg=self.COLORS['normal'], fg=self.COLORS['text'])
        icon_label.pack(pady=(6, 1))

        title_label = tk.Label(self, text=title, font=('Segoe UI', 8, 'bold'),
                               bg=self.COLORS['normal'], fg=self.COLORS['text'])
        title_label.pack()

        for w in [self, icon_label, title_label]:
            w.bind('<Button-1>', self.on_click)
            w.bind('<Enter>', self.on_enter)
            w.bind('<Leave>', self.on_leave)

        if self.variable.get() == self.value:
            self.select()

    def on_click(self, _=None):
        self.variable.set(self.value)
        for sibling in self.master.winfo_children():
            if isinstance(sibling, MotionCard):
                sibling.select() if sibling.value == self.value else sibling.deselect()

    def on_enter(self, _=None):
        if not self.is_selected:
            self._set_bg(self.COLORS['hover'])

    def on_leave(self, _=None):
        if not self.is_selected:
            self._set_bg(self.COLORS['normal'])

    def _set_bg(self, color):
        self.configure(bg=color)
        for child in self.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(bg=color)

    def select(self):
        self.is_selected = True
        self.configure(highlightbackground=self.COLORS['selected'], highlightthickness=3)

    def deselect(self):
        self.is_selected = False
        self.configure(highlightbackground=self.COLORS['border'], highlightthickness=2)


# ============================================================
# 3. AnimatedPreview — 프레임/이미지 75% 축소
# ============================================================

class AnimatedPreview(tk.Canvas):
    # 프레임을 캔버스 대비 작게 표시하여 움직임 여백 확보
    FRAME_RATIO = 0.55  # 캔버스 대비 프레임 비율 (기존 ~0.75 → 0.55)

    def __init__(self, parent, width=330, height=200, **kwargs):
        super().__init__(parent, width=width, height=height,
                         bg='#0D0D0D', highlightthickness=0, **kwargs)

        self.w = width
        self.h = height
        self.cx = width // 2
        self.cy = height // 2

        # 16:9 프레임 — 캔버스 대비 FRAME_RATIO 크기
        target_w = int(width * self.FRAME_RATIO)
        target_h = int(height * self.FRAME_RATIO)

        if target_w / target_h > 16 / 9:
            self.frame_h = target_h
            self.frame_w = int(target_h * 16 / 9)
        else:
            self.frame_w = target_w
            self.frame_h = int(target_w * 9 / 16)

        self.frame_x1 = self.cx - self.frame_w // 2
        self.frame_y1 = self.cy - self.frame_h // 2
        self.frame_x2 = self.cx + self.frame_w // 2
        self.frame_y2 = self.cy + self.frame_h // 2

        self.animation_duration = 2000
        self.start_time = 0
        self.is_animating = False
        self.update_job = None

        self.start_scale = 1.04
        self.end_scale = 1.09
        self.start_x = 0.0
        self.end_x = 0.0
        self.start_y = 0.0
        self.end_y = 0.0

        self._draw_static()
        self.image_rect = self.create_rectangle(0, 0, 0, 0,
                                                 outline='#3B82F6', width=2, dash=(4, 2))

    def _draw_static(self):
        grid_color = '#1a1a1a'
        for x in range(0, self.w, 40):
            self.create_line(x, 0, x, self.h, fill=grid_color)
        for y in range(0, self.h, 40):
            self.create_line(0, y, self.w, y, fill=grid_color)
        # 십자선 (프레임 내부만)
        self.create_line(self.cx, self.frame_y1, self.cx, self.frame_y2,
                         fill='#333333', dash=(2, 2))
        self.create_line(self.frame_x1, self.cy, self.frame_x2, self.cy,
                         fill='#333333', dash=(2, 2))
        # 16:9 프레임
        self.create_rectangle(self.frame_x1, self.frame_y1,
                              self.frame_x2, self.frame_y2,
                              outline='#FFFFFF', width=2)
        self.create_text(self.frame_x1 + 5, self.frame_y1 + 3,
                         text="16:9", anchor=tk.NW,
                         fill='#555555', font=('Consolas', 7))

    def set_motion(self, start_scale, end_scale, start_x, end_x, start_y, end_y):
        self.start_scale = start_scale
        self.end_scale = end_scale
        self.start_x = start_x
        self.end_x = end_x
        self.start_y = start_y
        self.end_y = end_y

    def start_animation(self):
        if self.update_job:
            self.after_cancel(self.update_job)
        self.start_time = self._now()
        self.is_animating = True
        self._animate()

    def stop_animation(self):
        self.is_animating = False
        if self.update_job:
            self.after_cancel(self.update_job)
            self.update_job = None

    def _now(self):
        return int(self.tk.call('clock', 'milliseconds'))

    def _animate(self):
        if not self.is_animating:
            return
        elapsed = self._now() - self.start_time
        progress = (elapsed % self.animation_duration) / self.animation_duration
        t = MotionEngine.ease_in_out(progress)

        scale = MotionEngine.interpolate(self.start_scale, self.end_scale, t)
        pan_x = MotionEngine.interpolate(self.start_x, self.end_x, t)
        pan_y = MotionEngine.interpolate(self.start_y, self.end_y, t)

        img_w = self.frame_w * scale
        img_h = self.frame_h * scale
        offset_x = pan_x * self.frame_w
        offset_y = pan_y * self.frame_h

        self.coords(self.image_rect,
                    self.cx - img_w / 2 + offset_x,
                    self.cy - img_h / 2 + offset_y,
                    self.cx + img_w / 2 + offset_x,
                    self.cy + img_h / 2 + offset_y)
        self.update_job = self.after(16, self._animate)


# ============================================================
# 4. 메인 애플리케이션
# ============================================================

class CapCutMotionStudio:
    COLORS = {
        'bg': '#121212', 'card': '#1E1E1E', 'border': '#2A2A2A',
        'primary': '#3B82F6', 'primary_hover': '#2563EB',
        'text_main': '#F1F1F1', 'text_secondary': '#9CA3AF',
        'success': '#10B981', 'warning': '#F59E0B', 'error': '#EF4444',
        'drop_zone': '#1A1A2E', 'drop_zone_border': '#3B82F6',
        'drop_zone_hover': '#1E2A4A'
    }

    def __init__(self, root):
        self.root = root
        self.root.title("CapCut Motion Studio")
        self.root.geometry("1060x720")
        self.root.resizable(False, False)
        self.root.configure(bg=self.COLORS['bg'])

        self.input_file = None
        self.clip_count = 0
        self.update_timer = None
        self.win32_drop_handler = None

        self._build_ui()
        self._init_drag_and_drop()

    # ── Drag & Drop ──

    def _init_drag_and_drop(self):
        if DND_BACKEND == "tkinterdnd2":
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_dnd_drop)
        elif DND_BACKEND == "win32_native":
            self.win32_drop_handler = Win32DropHandler(self.root, self._load_file)
            self.win32_drop_handler.enable()

    def _on_dnd_drop(self, event):
        path = event.data.strip('{}')
        if path.lower().endswith('.json'):
            self._load_file(path)
        else:
            messagebox.showwarning("Invalid File", "Only .json files are supported.")

    # ── UI 빌드 ──

    def _build_ui(self):
        self._build_header()

        main = tk.Frame(self.root, bg=self.COLORS['bg'])
        main.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))

        # 좌측
        left = tk.Frame(main, bg=self.COLORS['bg'])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self._build_zoom_section(left)
        self._build_pan_section(left)
        self._build_settings_section(left)

        # 우측
        right = tk.Frame(main, bg=self.COLORS['bg'], width=370)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(8, 0))
        right.pack_propagate(False)

        self._build_preview_section(right)

        # 하단
        self._build_apply_section()

    def _build_header(self):
        header = tk.Frame(self.root, bg=self.COLORS['bg'])
        header.pack(fill=tk.X, padx=16, pady=(14, 8))

        tk.Label(header, text="🎬 CapCut Motion Studio",
                 font=('Segoe UI', 18, 'bold'),
                 bg=self.COLORS['bg'], fg=self.COLORS['text_main']).pack(anchor=tk.W)

        # Drop Zone — 넓게
        self.drop_zone = tk.Frame(header,
                                   bg=self.COLORS['drop_zone'],
                                   highlightthickness=2,
                                   highlightbackground=self.COLORS['drop_zone_border'],
                                   cursor='hand2')
        self.drop_zone.pack(fill=tk.X, pady=(8, 0), ipady=10)

        self.drop_label = tk.Label(self.drop_zone,
                                    text="📂  Drag & Drop .json file here  or  Click to browse",
                                    font=('Segoe UI', 10),
                                    bg=self.COLORS['drop_zone'],
                                    fg=self.COLORS['text_secondary'])
        self.drop_label.pack()

        self.file_label = tk.Label(self.drop_zone, text="",
                                   font=('Segoe UI', 10, 'bold'),
                                   bg=self.COLORS['drop_zone'],
                                   fg=self.COLORS['text_main'])
        self.file_label.pack()

        for w in [self.drop_zone, self.drop_label, self.file_label]:
            w.bind('<Button-1>', lambda _: self.select_file())
            w.bind('<Enter>', self._drop_hover_in)
            w.bind('<Leave>', self._drop_hover_out)

    def _drop_hover_in(self, _=None):
        for w in [self.drop_zone, self.drop_label, self.file_label]:
            w.config(bg=self.COLORS['drop_zone_hover'])

    def _drop_hover_out(self, _=None):
        for w in [self.drop_zone, self.drop_label, self.file_label]:
            w.config(bg=self.COLORS['drop_zone'])

    # ── Zoom ──

    def _build_zoom_section(self, parent):
        inner = self._section(parent, "Zoom")
        row = tk.Frame(inner, bg=self.COLORS['card'])
        row.pack(fill=tk.X, pady=(4, 0))

        self.zoom_var = tk.StringVar(value="zoom_in")
        for icon, title, value in [
            ("⚫", "None", "none"), ("🔍", "In", "zoom_in"),
            ("🔎", "Out", "zoom_out"), ("🎲", "Random", "zoom_random")
        ]:
            MotionCard(row, icon, title, value, self.zoom_var).pack(side=tk.LEFT, padx=(0, 6))
        self.zoom_var.trace_add('write', lambda *_: self._schedule_preview())

    # ── Pan (H/V 독립) ──

    def _build_pan_section(self, parent):
        inner = self._section(parent, "Pan")

        # Horizontal
        h_header = tk.Frame(inner, bg=self.COLORS['card'])
        h_header.pack(fill=tk.X, pady=(2, 3))
        tk.Label(h_header, text="H", font=('Segoe UI', 9, 'bold'),
                 bg=self.COLORS['card'], fg=self.COLORS['text_secondary'],
                 width=3).pack(side=tk.LEFT)
        h_row = tk.Frame(h_header, bg=self.COLORS['card'])
        h_row.pack(side=tk.LEFT)

        self.pan_h_var = tk.StringVar(value="random")
        for icon, title, value in [
            ("⚫", "None", "none"), ("→", "L→R", "positive"),
            ("←", "R→L", "negative"), ("🎲", "Rand", "random")
        ]:
            MotionCard(h_row, icon, title, value, self.pan_h_var).pack(side=tk.LEFT, padx=(0, 6))

        # Vertical
        v_header = tk.Frame(inner, bg=self.COLORS['card'])
        v_header.pack(fill=tk.X, pady=(6, 0))
        tk.Label(v_header, text="V", font=('Segoe UI', 9, 'bold'),
                 bg=self.COLORS['card'], fg=self.COLORS['text_secondary'],
                 width=3).pack(side=tk.LEFT)
        v_row = tk.Frame(v_header, bg=self.COLORS['card'])
        v_row.pack(side=tk.LEFT)

        self.pan_v_var = tk.StringVar(value="random")
        for icon, title, value in [
            ("⚫", "None", "none"), ("↓", "T→B", "positive"),
            ("↑", "B→T", "negative"), ("🎲", "Rand", "random")
        ]:
            MotionCard(v_row, icon, title, value, self.pan_v_var).pack(side=tk.LEFT, padx=(0, 6))

        self.pan_h_var.trace_add('write', lambda *_: self._schedule_preview())
        self.pan_v_var.trace_add('write', lambda *_: self._schedule_preview())

    # ── Settings ──

    def _build_settings_section(self, parent):
        inner = self._section(parent, "Settings")

        rows = [
            ("Start Scale", "start_scale", 1.04, None, None),
            ("End Scale", "end_scale_min", 1.08, "end_scale_max", 1.10),
            ("Pan Strength", "pan_strength", 0.05, None, None),
        ]

        for i, (label, v1n, v1v, v2n, v2v) in enumerate(rows):
            row = tk.Frame(inner, bg=self.COLORS['card'])
            row.pack(fill=tk.X, pady=(4 if i == 0 else 0, 4))

            tk.Label(row, text=label, font=('Segoe UI', 10),
                     bg=self.COLORS['card'], fg=self.COLORS['text_main'],
                     width=14, anchor=tk.W).pack(side=tk.LEFT)

            v1 = tk.DoubleVar(value=v1v)
            setattr(self, v1n, v1)
            self._entry(row, v1).pack(side=tk.LEFT)

            if v2n:
                tk.Label(row, text=" ~ ", font=('Segoe UI', 10),
                         bg=self.COLORS['card'], fg=self.COLORS['text_secondary']).pack(side=tk.LEFT)
                v2 = tk.DoubleVar(value=v2v)
                setattr(self, v2n, v2)
                self._entry(row, v2).pack(side=tk.LEFT)
            elif "pan" in v1n:
                tk.Label(row, text=" ±", font=('Segoe UI', 10),
                         bg=self.COLORS['card'], fg=self.COLORS['text_secondary']).pack(side=tk.LEFT)

    # ── Preview ──

    def _build_preview_section(self, parent):
        inner = self._section(parent, "Motion Preview", width=355)
        inner.master.pack(fill=tk.BOTH, expand=True)

        self.preview = AnimatedPreview(inner, width=330, height=200)
        self.preview.pack(pady=(6, 8), padx=5)

        self.info_label = tk.Label(inner, text="",
                                   font=('Consolas', 9),
                                   bg=self.COLORS['card'], fg=self.COLORS['text_secondary'],
                                   justify=tk.LEFT, anchor=tk.NW)
        self.info_label.pack(fill=tk.X, padx=8, pady=(0, 6))
        self._update_preview()

    # ── Apply ──

    def _build_apply_section(self):
        section = tk.Frame(self.root, bg=self.COLORS['bg'])
        section.pack(fill=tk.X, padx=16, pady=(4, 12))

        self.apply_btn = self._make_button(
            section, "Apply Random Motion", self.apply_motion,
            bg=self.COLORS['primary'], fg='#FFFFFF',
            hover_bg=self.COLORS['primary_hover'],
            font=('Segoe UI', 12, 'bold'), height=1)
        self.apply_btn.pack(fill=tk.X, ipady=6)

        self.status_label = tk.Label(section, text="",
                                     font=('Segoe UI', 9),
                                     bg=self.COLORS['bg'], fg=self.COLORS['text_secondary'])
        self.status_label.pack(pady=(4, 0))

        backend_labels = {
            "tkinterdnd2": "DnD: tkinterdnd2",
            "win32_native": "DnD: Windows Native",
            None: "DnD unavailable — pip install tkinterdnd2"
        }
        self.status_label.config(text=backend_labels.get(DND_BACKEND, ""))

    # ── 공통 헬퍼 ──

    def _section(self, parent, title, width=None):
        container = tk.Frame(parent, bg=self.COLORS['bg'])
        container.pack(fill=tk.X, pady=(0, 6))
        tk.Label(container, text=title, font=('Segoe UI', 12, 'bold'),
                 bg=self.COLORS['bg'], fg=self.COLORS['text_main']).pack(anchor=tk.W, pady=(0, 3))
        frame = tk.Frame(container, bg=self.COLORS['card'],
                         highlightthickness=1,
                         highlightbackground=self.COLORS['border'])
        if width:
            frame.configure(width=width)
        frame.pack(fill=tk.X)
        inner = tk.Frame(frame, bg=self.COLORS['card'])
        inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        return inner

    def _entry(self, parent, variable):
        e = tk.Entry(parent, textvariable=variable, font=('Segoe UI', 10),
                     bg='#252525', fg=self.COLORS['text_main'],
                     insertbackground=self.COLORS['text_main'],
                     relief=tk.FLAT, width=7)
        e.bind('<KeyRelease>', lambda _: self._schedule_preview())
        return e

    def _make_button(self, parent, text, command, bg=None, fg=None,
                     hover_bg=None, font=None, height=1):
        if not font:
            font = ('Segoe UI', 10)
        btn = tk.Button(parent, text=text, command=command,
                        font=font, bg=bg or self.COLORS['card'],
                        fg=fg or self.COLORS['text_main'],
                        relief=tk.FLAT, cursor='hand2',
                        activebackground=hover_bg or bg,
                        activeforeground=fg or self.COLORS['text_main'],
                        height=height, bd=0)
        if hover_bg:
            orig = bg or self.COLORS['card']
            btn.bind('<Enter>', lambda _: btn.config(bg=hover_bg))
            btn.bind('<Leave>', lambda _: btn.config(bg=orig))
        return btn

    # ── 프리뷰 ──

    def _schedule_preview(self):
        if self.update_timer:
            self.root.after_cancel(self.update_timer)
        self.update_timer = self.root.after(300, self._update_preview)

    def _update_preview(self):
        try:
            ss = self.start_scale.get()
            emin = self.end_scale_min.get()
            emax = self.end_scale_max.get()
            ps = self.pan_strength.get()

            start_s, end_s = MotionEngine.compute_zoom(self.zoom_var.get(), ss, emin, emax)
            start_x, end_x = MotionEngine.compute_pan_axis(self.pan_h_var.get(), ps)
            start_y, end_y = MotionEngine.compute_pan_axis(self.pan_v_var.get(), ps)

            self.preview.set_motion(start_s, end_s, start_x, end_x, start_y, end_y)
            self.preview.start_animation()

            zoom_labels = {"none": "None", "zoom_in": "Zoom In",
                           "zoom_out": "Zoom Out", "zoom_random": "Random"}
            pan_labels = {"none": "None", "positive": "+Dir",
                          "negative": "-Dir", "random": "Random"}

            info = (
                f"Zoom: {zoom_labels.get(self.zoom_var.get(), '?')}  "
                f"Pan H: {pan_labels.get(self.pan_h_var.get(), '?')}  "
                f"V: {pan_labels.get(self.pan_v_var.get(), '?')}\n"
                f"{'─' * 40}\n"
                f"         Start          End\n"
                f"Scale    {start_s:.4f}        {end_s:.4f}\n"
                f"Pan X    {start_x:+.4f}        {end_x:+.4f}\n"
                f"Pan Y    {start_y:+.4f}        {end_y:+.4f}"
            )
            self.info_label.config(text=info)
        except (tk.TclError, ValueError):
            pass

    # ── 파일 ──

    def select_file(self):
        path = filedialog.askopenfilename(
            title="Select draft_content.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if path:
            self._load_file(path)

    def _load_file(self, path):
        if not path.lower().endswith('.json'):
            messagebox.showwarning("Invalid File", "Only .json files are supported.")
            return
        self.input_file = path
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tracks = data.get("tracks", [])
            if not tracks:
                messagebox.showwarning("Warning", "No 'tracks' found.")
                return
            count = 0
            has_video = False
            for track in tracks:
                if track.get("type") == "video":
                    has_video = True
                    count += len(track.get("segments", []))
            if not has_video:
                messagebox.showwarning("Warning", "No video tracks found.")
                return
            self.clip_count = count
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load:\n{e}")
            return

        name = os.path.basename(path)
        if len(name) > 45:
            name = name[:42] + "..."

        self.drop_label.config(text="📄 File loaded:")
        self.file_label.config(text=f"{name}  ({self.clip_count} clips)")
        self.status_label.config(text=f"✓ Ready — {self.clip_count} clips",
                                 fg=self.COLORS['success'])
        self.apply_btn.config(text=f"Apply Motion to {self.clip_count} Clips")

    # ── 모션 적용 ──

    def apply_motion(self):
        if not self.input_file:
            messagebox.showerror("Error", "Please select a file first.")
            return
        try:
            self.status_label.config(text="⏳ Processing...", fg=self.COLORS['warning'])
            self.root.update()
            self._create_backup()

            with open(self.input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = self._process_segments(data)

            with open(self.input_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.status_label.config(text=f"✓ Applied to {count} clips",
                                     fg=self.COLORS['success'])
            messagebox.showinfo("Success",
                                f"Motion applied to {count} clips.\n"
                                f"Backup saved in backups/ folder.")
        except Exception as e:
            self.status_label.config(text="✗ Error", fg=self.COLORS['error'])
            messagebox.showerror("Error", str(e))

    def _create_backup(self):
        backup_dir = Path(self.input_file).parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = backup_dir / f"draft_backup_{ts}.json"
        with open(self.input_file, "r", encoding="utf-8") as s:
            with open(dst, "w", encoding="utf-8") as d:
                d.write(s.read())

    def _process_segments(self, data):
        count = 0
        zt = self.zoom_var.get()
        ph = self.pan_h_var.get()
        pv = self.pan_v_var.get()
        ss = self.start_scale.get()
        emin = self.end_scale_min.get()
        emax = self.end_scale_max.get()
        ps = self.pan_strength.get()

        for track in data.get("tracks", []):
            if track.get("type") != "video":
                continue
            for seg in track.get("segments", []):
                duration = seg.get("target_timerange", {}).get("duration", 0)
                if duration == 0:
                    continue

                s_s, e_s = MotionEngine.compute_zoom(zt, ss, emin, emax)
                s_x, e_x = MotionEngine.compute_pan_axis(ph, ps)
                s_y, e_y = MotionEngine.compute_pan_axis(pv, ps)

                if "clip" in seg:
                    seg["clip"]["scale"] = {"x": s_s, "y": s_s}
                    seg["clip"]["transform"] = {"x": s_x, "y": s_y}

                seg["common_keyframes"] = [
                    self._kf("KFTypePositionX", s_x, e_x, duration),
                    self._kf("KFTypePositionY", s_y, e_y, duration),
                    self._kf("KFTypeScaleX", s_s, e_s, duration),
                ]
                count += 1
        return count

    @staticmethod
    def _kf(kf_type, start_val, end_val, duration):
        def pt(t, v):
            return {
                "id": str(uuid.uuid4()).upper(),
                "curveType": "Line",
                "time_offset": t,
                "left_control": {"x": 0.0, "y": 0.0},
                "right_control": {"x": 0.0, "y": 0.0},
                "values": [v],
                "string_value": "",
                "graphID": ""
            }
        return {
            "id": str(uuid.uuid4()).upper(),
            "material_id": "",
            "property_type": kf_type,
            "keyframe_list": [pt(0, start_val), pt(duration, end_val)]
        }


# ============================================================
# 5. Entry Point
# ============================================================

def main():
    root = TkinterDnD.Tk() if DND_BACKEND == "tkinterdnd2" else tk.Tk()
    CapCutMotionStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
