"""
CapCut Motion Studio - Professional Motion Automation Tool
Final v2 — 16:9 기준 포함, Zoom/Pan 독립 2축 제어
"""

import json
import random
import uuid
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from pathlib import Path

# Drag & Drop 지원 (선택적)
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False


# ============================================================
# 1. Motion Engine — Preview와 Export가 공유하는 단일 계산 모듈
# ============================================================

class MotionEngine:
    """Zoom + Pan 독립 축 모션 값 계산 (Preview / Export 공용)"""

    @staticmethod
    def compute_zoom(zoom_type, start_scale, end_scale_min, end_scale_max):
        """Zoom 축 계산 → (start_s, end_s)"""
        if zoom_type == "none":
            return 1.0, 1.0
        elif zoom_type == "zoom_in":
            return start_scale, round(random.uniform(end_scale_min, end_scale_max), 6)
        elif zoom_type == "zoom_out":
            return round(random.uniform(end_scale_min, end_scale_max), 6), start_scale
        elif zoom_type == "zoom_random":
            end_s = round(random.uniform(end_scale_min, end_scale_max), 6)
            if random.random() < 0.5:
                return start_scale, end_s
            else:
                return end_s, start_scale
        return start_scale, round(random.uniform(end_scale_min, end_scale_max), 6)

    @staticmethod
    def compute_pan_axis(pan_type, strength):
        """단일 축(H 또는 V) 계산 → (start_val, end_val)"""
        if pan_type == "none":
            return 0.0, 0.0
        elif pan_type == "positive":      # L→R 또는 T→B
            return -strength, strength
        elif pan_type == "negative":      # R→L 또는 B→T
            return strength, -strength
        elif pan_type == "random":
            return 0.0, round(random.uniform(-strength, strength), 6)
        return 0.0, 0.0

    @staticmethod
    def interpolate(start, end, progress):
        """선형 보간"""
        return start + (end - start) * progress

    @staticmethod
    def ease_in_out(t):
        """Smoothstep ease"""
        return t * t * (3.0 - 2.0 * t)


# ============================================================
# 2. MotionCard — 카드형 선택 위젯
# ============================================================

class MotionCard(tk.Frame):
    """카드형 선택 위젯 (크기 고정)"""

    COLORS = {
        'normal': '#1E1E1E',
        'hover': '#252525',
        'selected': '#3B82F6',
        'border': '#2A2A2A',
        'text': '#F1F1F1'
    }

    def __init__(self, parent, icon, title, value, variable, **kwargs):
        super().__init__(parent, **kwargs)
        self.value = value
        self.variable = variable
        self.is_selected = False

        self.configure(width=90, height=80)
        self.pack_propagate(False)

        self.configure(bg=self.COLORS['normal'],
                       highlightthickness=2,
                       highlightbackground=self.COLORS['border'],
                       cursor='hand2')

        icon_label = tk.Label(self, text=icon, font=('Segoe UI', 18),
                              bg=self.COLORS['normal'], fg=self.COLORS['text'])
        icon_label.pack(pady=(10, 3))

        title_label = tk.Label(self, text=title, font=('Segoe UI', 8, 'bold'),
                               bg=self.COLORS['normal'], fg=self.COLORS['text'])
        title_label.pack()

        for widget in [self, icon_label, title_label]:
            widget.bind('<Button-1>', self.on_click)
            widget.bind('<Enter>', self.on_enter)
            widget.bind('<Leave>', self.on_leave)

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
# 3. AnimatedPreview — 16:9 프레임 기준 모션 프리뷰
# ============================================================

class AnimatedPreview(tk.Canvas):
    """16:9 프레임 기반 모션 프리뷰 캔버스"""

    def __init__(self, parent, width=340, height=240, **kwargs):
        super().__init__(parent, width=width, height=height,
                         bg='#0D0D0D', highlightthickness=0, **kwargs)

        self.w = width
        self.h = height
        self.cx = width // 2
        self.cy = height // 2

        # 16:9 프레임 크기 (캔버스 내 마진 포함)
        margin = 20
        max_fw = width - margin * 2
        max_fh = height - margin * 2
        if max_fw / max_fh > 16 / 9:
            self.frame_h = max_fh
            self.frame_w = int(max_fh * 16 / 9)
        else:
            self.frame_w = max_fw
            self.frame_h = int(max_fw * 9 / 16)

        self.frame_x1 = self.cx - self.frame_w // 2
        self.frame_y1 = self.cy - self.frame_h // 2
        self.frame_x2 = self.cx + self.frame_w // 2
        self.frame_y2 = self.cy + self.frame_h // 2

        # 애니메이션 상태
        self.animation_duration = 2000
        self.start_time = 0
        self.is_animating = False
        self.update_job = None

        # 모션 파라미터
        self.start_scale = 1.04
        self.end_scale = 1.09
        self.start_x = 0.0
        self.end_x = 0.0
        self.start_y = 0.0
        self.end_y = 0.0

        # 그리기
        self._draw_static()
        self.image_rect = self.create_rectangle(0, 0, 0, 0,
                                                 outline='#3B82F6', width=2, dash=(4, 2))

    def _draw_static(self):
        """정적 요소: 그리드, 프레임, 십자선"""
        # 그리드
        grid_color = '#1a1a1a'
        for x in range(0, self.w, 40):
            self.create_line(x, 0, x, self.h, fill=grid_color)
        for y in range(0, self.h, 40):
            self.create_line(0, y, self.w, y, fill=grid_color)

        # 중앙 십자선
        self.create_line(self.cx, self.frame_y1, self.cx, self.frame_y2,
                         fill='#333333', dash=(2, 2))
        self.create_line(self.frame_x1, self.cy, self.frame_x2, self.cy,
                         fill='#333333', dash=(2, 2))

        # 16:9 외곽 프레임 (항상 고정)
        self.create_rectangle(self.frame_x1, self.frame_y1,
                              self.frame_x2, self.frame_y2,
                              outline='#FFFFFF', width=2)

        # 프레임 라벨
        self.create_text(self.frame_x1 + 6, self.frame_y1 + 4,
                         text="16:9", anchor=tk.NW,
                         fill='#666666', font=('Consolas', 8))

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

        # 이미지 영역 = 프레임 × scale, 중심에서 pan 오프셋
        img_w = self.frame_w * scale
        img_h = self.frame_h * scale
        offset_x = pan_x * self.frame_w
        offset_y = pan_y * self.frame_h

        ix1 = self.cx - img_w / 2 + offset_x
        iy1 = self.cy - img_h / 2 + offset_y
        ix2 = self.cx + img_w / 2 + offset_x
        iy2 = self.cy + img_h / 2 + offset_y

        self.coords(self.image_rect, ix1, iy1, ix2, iy2)

        self.update_job = self.after(16, self._animate)


# ============================================================
# 4. 메인 애플리케이션
# ============================================================

class CapCutMotionStudio:
    """CapCut Motion Studio 메인 애플리케이션"""

    COLORS = {
        'bg': '#121212',
        'card': '#1E1E1E',
        'border': '#2A2A2A',
        'primary': '#3B82F6',
        'primary_hover': '#2563EB',
        'text_main': '#F1F1F1',
        'text_secondary': '#9CA3AF',
        'success': '#10B981',
        'warning': '#F59E0B',
        'error': '#EF4444'
    }

    def __init__(self, root):
        self.root = root
        self.root.title("CapCut Motion Studio")
        self.root.geometry("1060x780")
        self.root.resizable(False, False)
        self.root.configure(bg=self.COLORS['bg'])

        self.input_file = None
        self.clip_count = 0
        self.update_timer = None

        self._setup_dnd()
        self._build_ui()

    # ── Drag & Drop ──

    def _setup_dnd(self):
        """Drag & Drop 초기화 (tkinterdnd2 있을 때만)"""
        if HAS_DND:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_drop)

    def _on_drop(self, event):
        """Drag & Drop 이벤트 처리"""
        path = event.data.strip('{}')
        if path.lower().endswith('.json'):
            self._load_file(path)
        else:
            messagebox.showwarning("Invalid File", "Only .json files are supported.")

    # ── UI 빌드 ──

    def _build_ui(self):
        self._build_header()

        main = tk.Frame(self.root, bg=self.COLORS['bg'])
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        # 좌측: 스크롤 가능 설정 영역
        left_outer = tk.Frame(main, bg=self.COLORS['bg'])
        left_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        canvas = tk.Canvas(left_outer, bg=self.COLORS['bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(left_outer, orient=tk.VERTICAL, command=canvas.yview)
        self.left_scroll_frame = tk.Frame(canvas, bg=self.COLORS['bg'])

        self.left_scroll_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        canvas.create_window((0, 0), window=self.left_scroll_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 마우스 휠 바인딩
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all('<MouseWheel>', _on_mousewheel)

        self._build_zoom_section(self.left_scroll_frame)
        self._build_pan_section(self.left_scroll_frame)
        self._build_settings_section(self.left_scroll_frame)

        # 우측: 프리뷰
        right = tk.Frame(main, bg=self.COLORS['bg'], width=380)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right.pack_propagate(False)

        self._build_preview_section(right)

        # 하단: Apply
        self._build_apply_section()

    def _build_header(self):
        header = tk.Frame(self.root, bg=self.COLORS['bg'])
        header.pack(fill=tk.X, padx=20, pady=(20, 12))

        tk.Label(header, text="🎬 CapCut Motion Studio",
                 font=('Segoe UI', 22, 'bold'),
                 bg=self.COLORS['bg'], fg=self.COLORS['text_main']).pack(anchor=tk.W)

        file_row = tk.Frame(header, bg=self.COLORS['bg'])
        file_row.pack(fill=tk.X, pady=(5, 0))

        tk.Label(file_row, text="Project:",
                 font=('Segoe UI', 10),
                 bg=self.COLORS['bg'], fg=self.COLORS['text_secondary']).pack(side=tk.LEFT)

        self.file_label = tk.Label(file_row, text="No file selected  (Drag & Drop .json here)" if HAS_DND else "No file selected",
                                   font=('Segoe UI', 10),
                                   bg=self.COLORS['bg'], fg=self.COLORS['text_secondary'])
        self.file_label.pack(side=tk.LEFT, padx=(5, 10))

        self._make_button(file_row, "Select File", self.select_file,
                          bg=self.COLORS['card'], fg=self.COLORS['text_main'],
                          hover_bg='#252525').pack(side=tk.LEFT)

    # ── Zoom 섹션 ──

    def _build_zoom_section(self, parent):
        inner = self._section(parent, "Zoom")

        row = tk.Frame(inner, bg=self.COLORS['card'])
        row.pack(fill=tk.X, pady=(10, 0))

        self.zoom_var = tk.StringVar(value="zoom_in")

        for icon, title, value in [
            ("⚫", "None", "none"),
            ("🔍", "Zoom In", "zoom_in"),
            ("🔎", "Zoom Out", "zoom_out"),
            ("🎲", "Random", "zoom_random")
        ]:
            MotionCard(row, icon, title, value, self.zoom_var).pack(side=tk.LEFT, padx=(0, 8))

        self.zoom_var.trace_add('write', lambda *_: self._schedule_preview())

    # ── Pan 섹션 (H/V 독립) ──

    def _build_pan_section(self, parent):
        inner = self._section(parent, "Pan")

        # Horizontal
        tk.Label(inner, text="Horizontal", font=('Segoe UI', 10, 'bold'),
                 bg=self.COLORS['card'], fg=self.COLORS['text_secondary']).pack(anchor=tk.W, pady=(8, 5))

        h_row = tk.Frame(inner, bg=self.COLORS['card'])
        h_row.pack(fill=tk.X)

        self.pan_h_var = tk.StringVar(value="random")

        for icon, title, value in [
            ("⚫", "None", "none"),
            ("→", "L→R", "positive"),
            ("←", "R→L", "negative"),
            ("🎲", "Random", "random")
        ]:
            MotionCard(h_row, icon, title, value, self.pan_h_var).pack(side=tk.LEFT, padx=(0, 8))

        # Vertical
        tk.Label(inner, text="Vertical", font=('Segoe UI', 10, 'bold'),
                 bg=self.COLORS['card'], fg=self.COLORS['text_secondary']).pack(anchor=tk.W, pady=(15, 5))

        v_row = tk.Frame(inner, bg=self.COLORS['card'])
        v_row.pack(fill=tk.X)

        self.pan_v_var = tk.StringVar(value="random")

        for icon, title, value in [
            ("⚫", "None", "none"),
            ("↓", "T→B", "positive"),
            ("↑", "B→T", "negative"),
            ("🎲", "Random", "random")
        ]:
            MotionCard(v_row, icon, title, value, self.pan_v_var).pack(side=tk.LEFT, padx=(0, 8))

        self.pan_h_var.trace_add('write', lambda *_: self._schedule_preview())
        self.pan_v_var.trace_add('write', lambda *_: self._schedule_preview())

    # ── Settings 섹션 ──

    def _build_settings_section(self, parent):
        inner = self._section(parent, "Settings")

        # Start Scale
        r1 = tk.Frame(inner, bg=self.COLORS['card'])
        r1.pack(fill=tk.X, pady=(10, 8))
        tk.Label(r1, text="Start Scale", font=('Segoe UI', 11),
                 bg=self.COLORS['card'], fg=self.COLORS['text_main'],
                 width=15, anchor=tk.W).pack(side=tk.LEFT)
        self.start_scale = tk.DoubleVar(value=1.04)
        self._entry(r1, self.start_scale).pack(side=tk.LEFT)

        # End Scale Range
        r2 = tk.Frame(inner, bg=self.COLORS['card'])
        r2.pack(fill=tk.X, pady=(0, 8))
        tk.Label(r2, text="End Scale Range", font=('Segoe UI', 11),
                 bg=self.COLORS['card'], fg=self.COLORS['text_main'],
                 width=15, anchor=tk.W).pack(side=tk.LEFT)
        self.end_scale_min = tk.DoubleVar(value=1.08)
        self._entry(r2, self.end_scale_min).pack(side=tk.LEFT)
        tk.Label(r2, text=" ~ ", font=('Segoe UI', 11),
                 bg=self.COLORS['card'], fg=self.COLORS['text_secondary']).pack(side=tk.LEFT)
        self.end_scale_max = tk.DoubleVar(value=1.10)
        self._entry(r2, self.end_scale_max).pack(side=tk.LEFT)

        # Pan Strength
        r3 = tk.Frame(inner, bg=self.COLORS['card'])
        r3.pack(fill=tk.X)
        tk.Label(r3, text="Pan Strength", font=('Segoe UI', 11),
                 bg=self.COLORS['card'], fg=self.COLORS['text_main'],
                 width=15, anchor=tk.W).pack(side=tk.LEFT)
        self.pan_strength = tk.DoubleVar(value=0.05)
        self._entry(r3, self.pan_strength).pack(side=tk.LEFT)
        tk.Label(r3, text=" ±", font=('Segoe UI', 11),
                 bg=self.COLORS['card'], fg=self.COLORS['text_secondary']).pack(side=tk.LEFT)

    # ── Preview 섹션 ──

    def _build_preview_section(self, parent):
        inner = self._section(parent, "Motion Preview", width=360)
        inner.master.pack(fill=tk.BOTH, expand=True)

        self.preview = AnimatedPreview(inner, width=340, height=220)
        self.preview.pack(pady=(10, 12), padx=5)

        self.info_label = tk.Label(inner, text="",
                                   font=('Consolas', 9),
                                   bg=self.COLORS['card'], fg=self.COLORS['text_secondary'],
                                   justify=tk.LEFT, anchor=tk.NW)
        self.info_label.pack(fill=tk.X, padx=10, pady=(0, 10))

        self._update_preview()

    # ── Apply 섹션 ──

    def _build_apply_section(self):
        section = tk.Frame(self.root, bg=self.COLORS['bg'])
        section.pack(fill=tk.X, padx=20, pady=(5, 15))

        self.apply_btn = self._make_button(
            section, "Apply Random Motion", self.apply_motion,
            bg=self.COLORS['primary'], fg='#FFFFFF',
            hover_bg=self.COLORS['primary_hover'],
            font=('Segoe UI', 13, 'bold'), height=2
        )
        self.apply_btn.pack(fill=tk.X, ipady=6)

        self.status_label = tk.Label(section, text="Select a file to get started",
                                     font=('Segoe UI', 10),
                                     bg=self.COLORS['bg'], fg=self.COLORS['text_secondary'])
        self.status_label.pack(pady=(6, 0))

    # ── 공통 위젯 헬퍼 ──

    def _section(self, parent, title, width=None):
        container = tk.Frame(parent, bg=self.COLORS['bg'])
        container.pack(fill=tk.X, pady=(0, 12))

        tk.Label(container, text=title, font=('Segoe UI', 14, 'bold'),
                 bg=self.COLORS['bg'], fg=self.COLORS['text_main']).pack(anchor=tk.W, pady=(0, 6))

        frame = tk.Frame(container, bg=self.COLORS['card'],
                         highlightthickness=1,
                         highlightbackground=self.COLORS['border'])
        if width:
            frame.configure(width=width)
        frame.pack(fill=tk.X, padx=2, pady=2)

        inner = tk.Frame(frame, bg=self.COLORS['card'])
        inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)
        return inner

    def _entry(self, parent, variable):
        e = tk.Entry(parent, textvariable=variable, font=('Segoe UI', 11),
                     bg='#252525', fg=self.COLORS['text_main'],
                     insertbackground=self.COLORS['text_main'],
                     relief=tk.FLAT, width=8)
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
            original_bg = bg or self.COLORS['card']
            btn.bind('<Enter>', lambda _: btn.config(bg=hover_bg))
            btn.bind('<Leave>', lambda _: btn.config(bg=original_bg))
        return btn

    # ── 프리뷰 로직 ──

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

            zoom_labels = {"none": "None", "zoom_in": "Zoom In", "zoom_out": "Zoom Out", "zoom_random": "Random"}
            pan_labels = {"none": "None", "positive": "+Dir", "negative": "-Dir", "random": "Random"}

            info = (
                f"Zoom : {zoom_labels.get(self.zoom_var.get(), '?')}\n"
                f"Pan H: {pan_labels.get(self.pan_h_var.get(), '?')}   "
                f"Pan V: {pan_labels.get(self.pan_v_var.get(), '?')}\n"
                f"{'─' * 36}\n"
                f"  Start  ──────────────  End\n"
                f"Scale  {start_s:.4f}          {end_s:.4f}\n"
                f"Pan X  {start_x:+.4f}          {end_x:+.4f}\n"
                f"Pan Y  {start_y:+.4f}          {end_y:+.4f}"
            )
            self.info_label.config(text=info)
        except (tk.TclError, ValueError):
            pass

    # ── 파일 로드 ──

    def select_file(self):
        path = filedialog.askopenfilename(
            title="Select draft_content.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            self._load_file(path)

    def _load_file(self, path):
        self.input_file = path
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 유효성 검증
            tracks = data.get("tracks", [])
            if not tracks:
                messagebox.showwarning("Warning", "No 'tracks' found in JSON.")
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
            messagebox.showerror("Error", f"Failed to load file:\n{e}")
            return

        name = os.path.basename(path)
        if len(name) > 40:
            name = name[:37] + "..."

        self.file_label.config(text=name, fg=self.COLORS['text_main'])
        self.status_label.config(text=f"✓ Ready — {self.clip_count} clips detected",
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

            output_file = self.input_file.replace(".json", "_motion.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.status_label.config(text=f"✓ Applied motion to {count} clips",
                                     fg=self.COLORS['success'])
            messagebox.showinfo("Success",
                                f"Motion applied to {count} clips.\n\n"
                                f"Output: {os.path.basename(output_file)}")

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
        """세그먼트에 모션 적용 (MotionEngine 사용 → Preview와 동일 계산)"""
        count = 0
        zoom_type = self.zoom_var.get()
        pan_h_type = self.pan_h_var.get()
        pan_v_type = self.pan_v_var.get()
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

                # MotionEngine으로 계산 (Preview와 동일 함수)
                start_s, end_s = MotionEngine.compute_zoom(zoom_type, ss, emin, emax)
                start_x, end_x = MotionEngine.compute_pan_axis(pan_h_type, ps)
                start_y, end_y = MotionEngine.compute_pan_axis(pan_v_type, ps)

                # clip 기본값 설정
                if "clip" in seg:
                    seg["clip"]["scale"] = {"x": start_s, "y": start_s}
                    seg["clip"]["transform"] = {"x": start_x, "y": start_y}

                # 키프레임 설정
                seg["common_keyframes"] = [
                    self._keyframe("KFTypePositionX", start_x, end_x, duration),
                    self._keyframe("KFTypePositionY", start_y, end_y, duration),
                    self._keyframe("KFTypeScaleX", start_s, end_s, duration),
                ]

                count += 1

        return count

    @staticmethod
    def _keyframe(kf_type, start_val, end_val, duration):
        def _point(time_offset, value):
            return {
                "id": str(uuid.uuid4()).upper(),
                "curveType": "Line",
                "time_offset": time_offset,
                "left_control": {"x": 0.0, "y": 0.0},
                "right_control": {"x": 0.0, "y": 0.0},
                "values": [value],
                "string_value": "",
                "graphID": ""
            }

        return {
            "id": str(uuid.uuid4()).upper(),
            "material_id": "",
            "property_type": kf_type,
            "keyframe_list": [
                _point(0, start_val),
                _point(duration, end_val)
            ]
        }


# ============================================================
# 5. Entry Point
# ============================================================

def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    CapCutMotionStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
