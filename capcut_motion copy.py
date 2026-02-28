"""
CapCut Motion Studio - Professional Motion Automation Tool
Zoom and Pan as independent variables - Clean architecture
"""

import json
import random
import uuid
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from pathlib import Path


class MotionCard(tk.Frame):
    """카드형 선택 위젯 (크기 고정)"""

    def __init__(self, parent, icon, title, value, variable, **kwargs):
        super().__init__(parent, **kwargs)
        self.value = value
        self.variable = variable
        self.is_selected = False

        # 크기 고정
        self.configure(width=90, height=90)
        self.pack_propagate(False)

        # 색상
        self.colors = {
            'normal': '#1E1E1E',
            'hover': '#252525',
            'selected': '#3B82F6',
            'border': '#2A2A2A',
            'text': '#F1F1F1'
        }

        self.configure(bg=self.colors['normal'],
                      highlightthickness=2,
                      highlightbackground=self.colors['border'],
                      cursor='hand2')

        # 내용
        icon_label = tk.Label(self, text=icon, font=('Segoe UI', 20),
                             bg=self.colors['normal'], fg=self.colors['text'])
        icon_label.pack(pady=(12, 5))

        title_label = tk.Label(self, text=title, font=('Segoe UI', 9, 'bold'),
                              bg=self.colors['normal'], fg=self.colors['text'])
        title_label.pack()

        # 이벤트 바인딩
        for widget in [self, icon_label, title_label]:
            widget.bind('<Button-1>', self.on_click)
            widget.bind('<Enter>', self.on_enter)
            widget.bind('<Leave>', self.on_leave)

        # 초기 선택 상태
        if self.variable.get() == self.value:
            self.select()

    def on_click(self, _=None):
        self.variable.set(self.value)
        for sibling in self.master.winfo_children():
            if isinstance(sibling, MotionCard):
                if sibling.value == self.value:
                    sibling.select()
                else:
                    sibling.deselect()

    def on_enter(self, _=None):
        if not self.is_selected:
            self.configure(bg=self.colors['hover'])
            for child in self.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=self.colors['hover'])

    def on_leave(self, _=None):
        if not self.is_selected:
            self.configure(bg=self.colors['normal'])
            for child in self.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=self.colors['normal'])

    def select(self):
        self.is_selected = True
        self.configure(highlightbackground=self.colors['selected'], highlightthickness=3)

    def deselect(self):
        self.is_selected = False
        self.configure(highlightbackground=self.colors['border'], highlightthickness=2)


class AnimatedPreview(tk.Canvas):
    """움직이는 모션 프리뷰 캔버스"""

    def __init__(self, parent, width=320, height=200, **kwargs):
        super().__init__(parent, width=width, height=height,
                        bg='#0D0D0D', highlightthickness=0, **kwargs)

        self.width = width
        self.height = height
        self.center_x = width // 2
        self.center_y = height // 2

        # 애니메이션 설정
        self.animation_duration = 1500  # 1.5초
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

        # 사각형 생성
        self.box_size = 60
        self.box = self.create_rectangle(
            self.center_x - self.box_size // 2,
            self.center_y - self.box_size // 2,
            self.center_x + self.box_size // 2,
            self.center_y + self.box_size // 2,
            fill='#3B82F6', outline='#60A5FA', width=2
        )

        # 그리드 라인
        self.create_grid()

    def create_grid(self):
        """그리드 생성"""
        grid_color = '#1a1a1a'
        for x in range(0, self.width, 40):
            self.create_line(x, 0, x, self.height, fill=grid_color, width=1)
        for y in range(0, self.height, 40):
            self.create_line(0, y, self.width, y, fill=grid_color, width=1)
        self.create_line(self.center_x, 0, self.center_x, self.height,
                        fill='#2a2a2a', width=1, dash=(2, 2))
        self.create_line(0, self.center_y, self.width, self.center_y,
                        fill='#2a2a2a', width=1, dash=(2, 2))

    def set_motion(self, start_scale, end_scale, start_x, end_x, start_y, end_y):
        """모션 파라미터 설정"""
        self.start_scale = start_scale
        self.end_scale = end_scale
        self.start_x = start_x
        self.end_x = end_x
        self.start_y = start_y
        self.end_y = end_y

    def start_animation(self):
        """애니메이션 시작"""
        if self.update_job:
            self.after_cancel(self.update_job)

        self.start_time = self.tk.call('clock', 'milliseconds')
        self.is_animating = True
        self.animate()

    def animate(self):
        """애니메이션 루프"""
        if not self.is_animating:
            return

        current_time = self.tk.call('clock', 'milliseconds')
        elapsed = current_time - self.start_time

        # 루프
        progress = (elapsed % self.animation_duration) / self.animation_duration

        # Ease-in-out
        t = progress
        ease = t * t * (3.0 - 2.0 * t)

        # 값 계산
        current_scale = self.start_scale + (self.end_scale - self.start_scale) * ease
        current_x = self.start_x + (self.end_x - self.start_x) * ease
        current_y = self.start_y + (self.end_y - self.start_y) * ease

        # 위치 계산 (화면 비율로 변환)
        offset_x = current_x * self.width
        offset_y = current_y * self.height

        # 크기 계산
        size = self.box_size * current_scale

        # 사각형 업데이트
        self.coords(self.box,
                   self.center_x - size // 2 + offset_x,
                   self.center_y - size // 2 + offset_y,
                   self.center_x + size // 2 + offset_x,
                   self.center_y + size // 2 + offset_y)

        # 60fps
        self.update_job = self.after(16, self.animate)

    def stop_animation(self):
        """애니메이션 중지"""
        self.is_animating = False
        if self.update_job:
            self.after_cancel(self.update_job)
            self.update_job = None


class CapCutMotionStudio:
    """CapCut Motion Studio 메인 애플리케이션"""

    def __init__(self, root):
        self.root = root
        self.root.title("CapCut Motion Studio")
        self.root.geometry("1000x720")
        self.root.resizable(False, False)

        # 색상 시스템
        self.colors = {
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

        self.root.configure(bg=self.colors['bg'])

        self.input_file = None
        self.clip_count = 0
        self.update_timer = None

        self.setup_ui()

    def setup_ui(self):
        """UI 구성"""
        # 상단 헤더
        self.create_header()

        # 메인 컨테이너
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # 좌측: 설정 영역
        left_frame = tk.Frame(main_container, bg=self.colors['bg'])
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.create_zoom_type_section(left_frame)
        self.create_pan_type_section(left_frame)
        self.create_settings_section(left_frame)

        # 우측: 프리뷰 영역
        right_frame = tk.Frame(main_container, bg=self.colors['bg'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))

        self.create_preview_section(right_frame)

        # 하단: Apply 버튼
        self.create_apply_section()

    def create_header(self):
        """상단 헤더"""
        header = tk.Frame(self.root, bg=self.colors['bg'])
        header.pack(fill=tk.X, padx=20, pady=(20, 15))

        title = tk.Label(header, text="🎬 CapCut Motion Studio",
                        font=('Segoe UI', 22, 'bold'),
                        bg=self.colors['bg'], fg=self.colors['text_main'])
        title.pack(anchor=tk.W)

        file_frame = tk.Frame(header, bg=self.colors['bg'])
        file_frame.pack(fill=tk.X, pady=(5, 0))

        tk.Label(file_frame, text="Project:",
                font=('Segoe UI', 10),
                bg=self.colors['bg'], fg=self.colors['text_secondary']).pack(side=tk.LEFT)

        self.file_label = tk.Label(file_frame, text="No file selected",
                                   font=('Segoe UI', 10),
                                   bg=self.colors['bg'], fg=self.colors['text_secondary'])
        self.file_label.pack(side=tk.LEFT, padx=(5, 10))

        self.create_button(file_frame, "Select File", self.select_file,
                          bg=self.colors['card'], fg=self.colors['text_main'],
                          hover_bg='#252525').pack(side=tk.LEFT)

    def create_zoom_type_section(self, parent):
        """Zoom Type 섹션"""
        section = self.create_section_frame(parent, "Zoom")

        cards_frame = tk.Frame(section, bg=self.colors['card'])
        cards_frame.pack(fill=tk.X, pady=(10, 0))

        self.zoom_var = tk.StringVar(value="zoom_in")

        zoom_types = [
            ("⚫", "None", "none"),
            ("🔍", "Zoom In", "zoom_in"),
            ("🔎", "Zoom Out", "zoom_out"),
            ("🎲", "Random", "zoom_random")
        ]

        for icon, title, value in zoom_types:
            card = MotionCard(cards_frame, icon, title, value, self.zoom_var)
            card.pack(side=tk.LEFT, padx=(0, 8))

        self.zoom_var.trace('w', lambda *args: self.schedule_preview_update())

    def create_pan_type_section(self, parent):
        """Pan Type 섹션"""
        section = self.create_section_frame(parent, "Pan")

        cards_frame = tk.Frame(section, bg=self.colors['card'])
        cards_frame.pack(fill=tk.X, pady=(10, 0))

        self.pan_var = tk.StringVar(value="random")

        # 첫 번째 줄
        row1 = tk.Frame(cards_frame, bg=self.colors['card'])
        row1.pack(pady=(0, 8))

        pan_types_row1 = [
            ("⚫", "None", "none"),
            ("→", "L→R", "left_right"),
            ("←", "R→L", "right_left"),
            ("🎲", "Random", "random")
        ]

        for icon, title, value in pan_types_row1:
            card = MotionCard(row1, icon, title, value, self.pan_var)
            card.pack(side=tk.LEFT, padx=(0, 8))

        # 두 번째 줄
        row2 = tk.Frame(cards_frame, bg=self.colors['card'])
        row2.pack()

        pan_types_row2 = [
            ("↓", "T→B", "top_bottom"),
            ("↑", "B→T", "bottom_top"),
            ("", "", ""),  # 빈 공간
            ("", "", "")   # 빈 공간
        ]

        for icon, title, value in pan_types_row2:
            if value:  # 빈 공간이 아니면
                card = MotionCard(row2, icon, title, value, self.pan_var)
                card.pack(side=tk.LEFT, padx=(0, 8))
            else:  # 빈 공간
                spacer = tk.Frame(row2, width=90, height=90, bg=self.colors['card'])
                spacer.pack(side=tk.LEFT, padx=(0, 8))

        self.pan_var.trace('w', lambda *args: self.schedule_preview_update())

    def create_settings_section(self, parent):
        """Settings 섹션 (Zoom + Pan 통합)"""
        section = self.create_section_frame(parent, "Settings")

        # Start Scale
        row1 = tk.Frame(section, bg=self.colors['card'])
        row1.pack(fill=tk.X, pady=(10, 8))

        tk.Label(row1, text="Start Scale",
                font=('Segoe UI', 11),
                bg=self.colors['card'], fg=self.colors['text_main'],
                width=15, anchor=tk.W).pack(side=tk.LEFT)

        self.start_scale = tk.DoubleVar(value=1.04)
        entry = self.create_entry(row1, self.start_scale)
        entry.pack(side=tk.LEFT)

        tk.Label(row1, text="%",
                font=('Segoe UI', 11),
                bg=self.colors['card'], fg=self.colors['text_secondary']).pack(side=tk.LEFT, padx=(3, 0))

        # End Scale Range
        row2 = tk.Frame(section, bg=self.colors['card'])
        row2.pack(fill=tk.X, pady=(0, 8))

        tk.Label(row2, text="End Scale Range",
                font=('Segoe UI', 11),
                bg=self.colors['card'], fg=self.colors['text_main'],
                width=15, anchor=tk.W).pack(side=tk.LEFT)

        self.end_scale_min = tk.DoubleVar(value=1.08)
        entry_min = self.create_entry(row2, self.end_scale_min)
        entry_min.pack(side=tk.LEFT)

        tk.Label(row2, text="%  ~",
                font=('Segoe UI', 11),
                bg=self.colors['card'], fg=self.colors['text_secondary']).pack(side=tk.LEFT, padx=(3, 8))

        self.end_scale_max = tk.DoubleVar(value=1.10)
        entry_max = self.create_entry(row2, self.end_scale_max)
        entry_max.pack(side=tk.LEFT)

        tk.Label(row2, text="%",
                font=('Segoe UI', 11),
                bg=self.colors['card'], fg=self.colors['text_secondary']).pack(side=tk.LEFT, padx=(3, 0))

        # Pan Strength
        row3 = tk.Frame(section, bg=self.colors['card'])
        row3.pack(fill=tk.X)

        tk.Label(row3, text="Pan Strength",
                font=('Segoe UI', 11),
                bg=self.colors['card'], fg=self.colors['text_main'],
                width=15, anchor=tk.W).pack(side=tk.LEFT)

        self.move_range = tk.DoubleVar(value=0.05)
        entry = self.create_entry(row3, self.move_range)
        entry.pack(side=tk.LEFT)

        tk.Label(row3, text="±",
                font=('Segoe UI', 11),
                bg=self.colors['card'], fg=self.colors['text_secondary']).pack(side=tk.LEFT, padx=(3, 0))

    def create_entry(self, parent, variable):
        """입력 필드 생성"""
        entry = tk.Entry(parent, textvariable=variable,
                        font=('Segoe UI', 11),
                        bg='#252525', fg=self.colors['text_main'],
                        insertbackground=self.colors['text_main'],
                        relief=tk.FLAT, width=8)
        entry.bind('<KeyRelease>', lambda e: self.schedule_preview_update())
        return entry

    def create_preview_section(self, parent):
        """프리뷰 섹션"""
        section = self.create_section_frame(parent, "Motion Preview", width=340)
        section.pack(fill=tk.BOTH, expand=True)

        # 애니메이션 캔버스
        self.preview_canvas = AnimatedPreview(section, width=320, height=200)
        self.preview_canvas.pack(pady=(10, 15), padx=10)

        # 값 표시
        self.preview_info = tk.Frame(section, bg=self.colors['card'])
        self.preview_info.pack(fill=tk.X, padx=10)

        self.info_label = tk.Label(self.preview_info, text="",
                                   font=('Consolas', 10),
                                   bg=self.colors['card'], fg=self.colors['text_secondary'],
                                   justify=tk.LEFT)
        self.info_label.pack(pady=10, padx=10)

        # 초기 프리뷰
        self.update_preview()

    def schedule_preview_update(self):
        """0.3초 딜레이 후 프리뷰 업데이트"""
        if self.update_timer:
            self.root.after_cancel(self.update_timer)
        self.update_timer = self.root.after(300, self.update_preview)

    def update_preview(self):
        """프리뷰 업데이트 (Zoom + Pan 독립 변수)"""
        try:
            # Settings 값
            start_scale = self.start_scale.get()
            end_min = self.end_scale_min.get()
            end_max = self.end_scale_max.get()
            pan_strength = self.move_range.get()

            # Zoom 타입
            zoom_type = self.zoom_var.get()
            if zoom_type == "none":
                start_s, end_s = 1.0, 1.0
            elif zoom_type == "zoom_in":
                start_s = start_scale
                end_s = random.uniform(end_min, end_max)
            elif zoom_type == "zoom_out":
                start_s = random.uniform(end_min, end_max)
                end_s = start_scale
            elif zoom_type == "zoom_random":
                if random.random() < 0.5:
                    start_s, end_s = start_scale, random.uniform(end_min, end_max)
                else:
                    start_s, end_s = random.uniform(end_min, end_max), start_scale
            else:
                start_s, end_s = start_scale, random.uniform(end_min, end_max)

            # Pan 타입
            pan_type = self.pan_var.get()
            if pan_type == "none":
                start_x, end_x = 0.0, 0.0
                start_y, end_y = 0.0, 0.0
            elif pan_type == "left_right":
                start_x, end_x = -pan_strength, pan_strength
                start_y, end_y = 0.0, 0.0
            elif pan_type == "right_left":
                start_x, end_x = pan_strength, -pan_strength
                start_y, end_y = 0.0, 0.0
            elif pan_type == "top_bottom":
                start_x, end_x = 0.0, 0.0
                start_y, end_y = -pan_strength, pan_strength
            elif pan_type == "bottom_top":
                start_x, end_x = 0.0, 0.0
                start_y, end_y = pan_strength, -pan_strength
            elif pan_type == "random":
                start_x, end_x = 0.0, random.uniform(-pan_strength, pan_strength)
                start_y, end_y = 0.0, random.uniform(-pan_strength, pan_strength)
            else:
                start_x, end_x = 0.0, 0.0
                start_y, end_y = 0.0, 0.0

            # 애니메이션 설정
            self.preview_canvas.set_motion(start_s, end_s, start_x, end_x, start_y, end_y)
            self.preview_canvas.start_animation()

            # 텍스트 업데이트
            zoom_name = {"none": "None", "zoom_in": "Zoom In", "zoom_out": "Zoom Out", "zoom_random": "Random"}
            pan_name = {"none": "None", "left_right": "L→R", "right_left": "R→L",
                       "top_bottom": "T→B", "bottom_top": "B→T", "random": "Random"}

            info_text = f"Zoom: {zoom_name.get(zoom_type, zoom_type)}\n"
            info_text += f"Pan: {pan_name.get(pan_type, pan_type)}\n\n"
            info_text += f"Start ──────────── End\n"
            info_text += f"Scale: {start_s:.2f} → {end_s:.2f}\n"
            info_text += f"Pan X: {start_x:+.3f} → {end_x:+.3f}\n"
            info_text += f"Pan Y: {start_y:+.3f} → {end_y:+.3f}"

            self.info_label.config(text=info_text)

        except:
            pass

    def create_apply_section(self):
        """하단 Apply 버튼"""
        section = tk.Frame(self.root, bg=self.colors['bg'])
        section.pack(fill=tk.X, padx=20, pady=(0, 20))

        self.apply_btn = self.create_button(
            section,
            f"Apply Motion to {self.clip_count} Clips" if self.clip_count > 0 else "Apply Random Motion",
            self.apply_motion,
            bg=self.colors['primary'],
            fg='#FFFFFF',
            hover_bg=self.colors['primary_hover'],
            font=('Segoe UI', 13, 'bold'),
            height=2
        )
        self.apply_btn.pack(fill=tk.X, ipady=8)

        self.status_label = tk.Label(section, text="Select a file to get started",
                                     font=('Segoe UI', 10),
                                     bg=self.colors['bg'], fg=self.colors['text_secondary'])
        self.status_label.pack(pady=(8, 0))

    def create_section_frame(self, parent, title, width=None):
        """섹션 프레임"""
        container = tk.Frame(parent, bg=self.colors['bg'])
        container.pack(fill=tk.X, pady=(0, 15))

        tk.Label(container, text=title,
                font=('Segoe UI', 16, 'bold'),
                bg=self.colors['bg'], fg=self.colors['text_main']).pack(anchor=tk.W, pady=(0, 8))

        frame = tk.Frame(container, bg=self.colors['card'],
                        highlightthickness=1,
                        highlightbackground=self.colors['border'])
        if width:
            frame.configure(width=width)
        frame.pack(fill=tk.X, padx=2, pady=2)

        inner = tk.Frame(frame, bg=self.colors['card'])
        inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        return inner

    def create_button(self, parent, text, command, bg=None, fg=None,
                     hover_bg=None, font=None, height=1):
        """커스텀 버튼"""
        if not font:
            font = ('Segoe UI', 10)

        btn = tk.Button(parent, text=text, command=command,
                       font=font, bg=bg or self.colors['card'],
                       fg=fg or self.colors['text_main'],
                       relief=tk.FLAT, cursor='hand2',
                       activebackground=hover_bg or bg or self.colors['card'],
                       activeforeground=fg or self.colors['text_main'],
                       height=height, bd=0)

        if hover_bg:
            btn.bind('<Enter>', lambda e: btn.config(bg=hover_bg))
            btn.bind('<Leave>', lambda e: btn.config(bg=bg))

        return btn

    def select_file(self):
        """파일 선택"""
        filename = filedialog.askopenfilename(
            title="Select draft_content.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.input_file = filename

            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                count = 0
                for track in data.get("tracks", []):
                    if track.get("type") == "video":
                        count += len(track.get("segments", []))
                self.clip_count = count
            except:
                self.clip_count = 0

            display_name = os.path.basename(filename)
            if len(display_name) > 40:
                display_name = display_name[:37] + "..."

            self.file_label.config(text=display_name, fg=self.colors['text_main'])
            self.status_label.config(text=f"✓ Ready to process {self.clip_count} clips",
                                   fg=self.colors['success'])

            self.apply_btn.config(text=f"Apply Motion to {self.clip_count} Clips")

    def apply_motion(self):
        """모션 적용"""
        if not self.input_file:
            messagebox.showerror("Error", "Please select a file first")
            return

        try:
            self.status_label.config(text="⏳ Processing...", fg=self.colors['warning'])
            self.root.update()

            self.create_backup()

            with open(self.input_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            count = self.process_segments(data)

            output_file = self.input_file.replace(".json", "_motion.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.status_label.config(text=f"✓ Successfully applied motion to {count} clips",
                                   fg=self.colors['success'])

            messagebox.showinfo(
                "Success",
                f"🎉 Motion applied successfully!\n\n"
                f"Processed clips: {count}\n"
                f"Output file: {os.path.basename(output_file)}"
            )

        except Exception as e:
            self.status_label.config(text="✗ Error occurred", fg=self.colors['error'])
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")

    def create_backup(self):
        """백업 생성"""
        backup_dir = Path(self.input_file).parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"draft_backup_{timestamp}.json"
        backup_path = backup_dir / backup_name

        with open(self.input_file, "r", encoding="utf-8") as src:
            with open(backup_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())

    def process_segments(self, data):
        """세그먼트 처리 (Zoom + Pan 독립)"""
        count = 0
        zoom_type = self.zoom_var.get()
        pan_type = self.pan_var.get()

        for track in data.get("tracks", []):
            if track.get("type") != "video":
                continue

            for seg in track.get("segments", []):
                duration = seg.get("target_timerange", {}).get("duration", 0)
                if duration == 0:
                    continue

                values = self.get_motion_values(zoom_type, pan_type)

                if "clip" in seg:
                    seg["clip"]["scale"] = {
                        "x": values["end_scale"],
                        "y": values["end_scale"]
                    }
                    seg["clip"]["transform"] = {
                        "x": values["end_x"],
                        "y": values["end_y"]
                    }

                seg["common_keyframes"] = [
                    self.build_keyframe("KFTypePositionX", values["start_x"], values["end_x"], duration),
                    self.build_keyframe("KFTypePositionY", values["start_y"], values["end_y"], duration),
                    self.build_keyframe("KFTypeScaleX", values["start_scale"], values["end_scale"], duration)
                ]

                count += 1

        return count

    def get_motion_values(self, zoom_type, pan_type):
        """Zoom + Pan 독립 변수로 값 계산"""
        start_scale = self.start_scale.get()
        end_scale_min = self.end_scale_min.get()
        end_scale_max = self.end_scale_max.get()
        pan_strength = self.move_range.get()

        # Zoom 계산
        if zoom_type == "none":
            start_s, end_s = 1.0, 1.0
        elif zoom_type == "zoom_in":
            start_s = start_scale
            end_s = round(random.uniform(end_scale_min, end_scale_max), 6)
        elif zoom_type == "zoom_out":
            start_s = round(random.uniform(end_scale_min, end_scale_max), 6)
            end_s = start_scale
        elif zoom_type == "zoom_random":
            end_s = round(random.uniform(end_scale_min, end_scale_max), 6)
            if random.random() < 0.5:
                start_s = start_scale
            else:
                start_s, end_s = end_s, start_scale
        else:
            start_s = start_scale
            end_s = round(random.uniform(end_scale_min, end_scale_max), 6)

        # Pan 계산
        if pan_type == "none":
            start_x, end_x = 0.0, 0.0
            start_y, end_y = 0.0, 0.0
        elif pan_type == "left_right":
            start_x, end_x = -pan_strength, pan_strength
            start_y, end_y = 0.0, 0.0
        elif pan_type == "right_left":
            start_x, end_x = pan_strength, -pan_strength
            start_y, end_y = 0.0, 0.0
        elif pan_type == "top_bottom":
            start_x, end_x = 0.0, 0.0
            start_y, end_y = -pan_strength, pan_strength
        elif pan_type == "bottom_top":
            start_x, end_x = 0.0, 0.0
            start_y, end_y = pan_strength, -pan_strength
        elif pan_type == "random":
            start_x, end_x = 0.0, round(random.uniform(-pan_strength, pan_strength), 6)
            start_y, end_y = 0.0, round(random.uniform(-pan_strength, pan_strength), 6)
        else:
            start_x, end_x = 0.0, 0.0
            start_y, end_y = 0.0, 0.0

        return {
            "start_scale": start_s,
            "end_scale": end_s,
            "start_x": start_x,
            "end_x": end_x,
            "start_y": start_y,
            "end_y": end_y
        }

    def build_keyframe(self, kf_type, start_value, end_value, duration):
        """키프레임 생성"""
        return {
            "id": str(uuid.uuid4()).upper(),
            "material_id": "",
            "property_type": kf_type,
            "keyframe_list": [
                {
                    "id": str(uuid.uuid4()).upper(),
                    "curveType": "Line",
                    "time_offset": 0,
                    "left_control": {"x": 0.0, "y": 0.0},
                    "right_control": {"x": 0.0, "y": 0.0},
                    "values": [start_value],
                    "string_value": "",
                    "graphID": ""
                },
                {
                    "id": str(uuid.uuid4()).upper(),
                    "curveType": "Line",
                    "time_offset": duration,
                    "left_control": {"x": 0.0, "y": 0.0},
                    "right_control": {"x": 0.0, "y": 0.0},
                    "values": [end_value],
                    "string_value": "",
                    "graphID": ""
                }
            ]
        }


def main():
    root = tk.Tk()
    app = CapCutMotionStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
