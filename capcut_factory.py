"""
CapCut Factory - Unified Image Matching + Motion Automation Tool
Tab-based integration: Tab 1 (Image Matching) + Tab 2 (Motion Application)
"""

import json
import random
import uuid
import os
import sys
import re
import copy
import unicodedata
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from pathlib import Path

# ============================================================
# 0. Drag & Drop Backend Detection
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
        try:
            count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
            files = []
            for i in range(count):
                buf = create_unicode_buffer('', MAX_PATH)
                shell32.DragQueryFileW(hdrop, i, buf, MAX_PATH)
                path = buf[:].split('\0', 1)[0]
                if path:
                    files.append(path)
            shell32.DragFinish(hdrop)
            if files:
                # Use after to move callback execution out of the window procedure context
                self.root.after(10, self.callback, files[0])
        except Exception as e:
            print(f"Error handling drop: {e}")
            try:
                shell32.DragFinish(hdrop)
            except:
                pass


# ============================================================
# 1. Motion Engine (Reused from capcut_motion.py)
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
        if pan_type == "none":
            return 0.0, 0.0
        elif pan_type == "positive":
            return 0.0, round(strength, 6)
        elif pan_type == "negative":
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
# 2. Image Matching Engine
# ============================================================

class SubtitleExtractor:
    """Extract subtitle data from draft_content.json"""

    @staticmethod
    def extract(draft_data):
        subtitles = []
        materials_texts = draft_data.get("materials", {}).get("texts", [])

        # Build material_id -> text mapping
        text_map = {}
        for text_item in materials_texts:
            mat_id = text_item.get("id", "")
            raw_content = text_item.get("content", "")
            text = SubtitleExtractor._parse_text_content(raw_content)
            if text:
                text_map[mat_id] = {"text": text, "raw": raw_content}

        # Find text track segments for timing info
        tracks = draft_data.get("tracks", [])
        idx = 0
        for t_idx, track in enumerate(tracks):
            if track.get("type") != "text":
                continue
            for s_idx, seg in enumerate(track.get("segments", [])):
                mat_id = seg.get("material_id", "")
                timerange = seg.get("target_timerange", {})
                start = timerange.get("start", 0)
                duration = timerange.get("duration", 0)

                text_info = text_map.get(mat_id, {})
                text = text_info.get("text", "")
                if not text:
                    continue

                subtitles.append({
                    "index": idx,
                    "srt_index": idx + 1,  # 1-based SRT subtitle index
                    "material_id": mat_id,
                    "text": text,
                    "start": start,
                    "duration": duration,
                    "track_index": t_idx,
                    "segment_index": s_idx,
                })
                idx += 1

        subtitles.sort(key=lambda s: s["start"])
        # Re-assign srt_index after sorting by time (1-based)
        for i, sub in enumerate(subtitles):
            sub["srt_index"] = i + 1
        return subtitles

    @staticmethod
    def _parse_text_content(content_str):
        """Parse CapCut text content field - may be plain text or JSON"""
        if not content_str:
            return ""
        try:
            content = json.loads(content_str)
            if isinstance(content, dict):
                # Try common CapCut text structures
                if "text" in content:
                    return content["text"]
                if "texts" in content:
                    return " ".join(t.get("text", "") for t in content["texts"])
                # Nested styles structure
                if "styles" in content and "text" in content:
                    return content["text"]
            return str(content)
        except (json.JSONDecodeError, TypeError):
            return content_str.strip()


class ImageIndexer:
    """Scan image folder and index by extracted text"""

    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif'}

    # Prefix pattern: digits/Scene prefix + separator
    PREFIX_PATTERN = re.compile(
        r'^(?:Scene\s*\d+|EP\d+_S\d+|\d{1,4})\s*[_\-.\s]+',
        re.IGNORECASE
    )

    # Korean text extraction: match consecutive Korean syllables/jamo + spaces
    KOREAN_PATTERN = re.compile(r'[\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F]+')

    @staticmethod
    def index(folder_path):
        images = {}
        if not os.path.isdir(folder_path):
            return images

        for filename in os.listdir(folder_path):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ImageIndexer.SUPPORTED_EXTENSIONS:
                continue

            raw_name = os.path.splitext(filename)[0]
            text = ImageIndexer._extract_text(raw_name)
            scene_number = ImageIndexer._extract_number(raw_name)
            korean_text = ImageIndexer._extract_korean_text(raw_name)
            normalized = TextMatcher.normalize(text)
            korean_normalized = TextMatcher.normalize(korean_text)

            # Use raw_name as unique key to preserve duplicate scene numbers
            full_path = os.path.join(folder_path, filename)
            images[raw_name] = {
                "filename": filename,
                "path": full_path,
                "raw_name": raw_name,
                "text": text,
                "korean_text": korean_text,
                "scene_number": scene_number,
                "normalized": normalized,
                "korean_normalized": korean_normalized,
            }
        return images

    @staticmethod
    def _extract_text(raw_name):
        """Remove prefix pattern from filename to get subtitle text"""
        text = ImageIndexer.PREFIX_PATTERN.sub('', raw_name)
        # Replace underscores with spaces
        text = text.replace('_', ' ').strip()
        return text

    @staticmethod
    def _extract_korean_text(raw_name):
        """Extract only Korean text from filename (ignoring English tags like MCR, medium_shot etc)"""
        # Replace underscores with spaces first
        name_spaced = raw_name.replace('_', ' ')
        # Find all Korean character sequences
        korean_parts = ImageIndexer.KOREAN_PATTERN.findall(name_spaced)
        if korean_parts:
            return ' '.join(korean_parts)
        return ""

    @staticmethod
    def _extract_number(raw_name):
        """Extract the scene sequence number from the prefix"""
        match = re.search(r'^(?:Scene\s*(\d+)|EP\d+_S(\d+)|(\d{1,4}))\s*[_.\-\s]*', raw_name, re.IGNORECASE)
        if match:
            for g in match.groups():
                if g is not None:
                    return int(g)
        return None


class TextMatcher:
    """Match subtitles to images using text normalization"""

    # Punctuation to strip
    PUNCT = re.compile(r'[.,!?;:\'\"()\[\]{}<>~@#$%^&*+=|\\/-]')
    WHITESPACE = re.compile(r'\s+')

    @staticmethod
    def normalize(text):
        if not text:
            return ""
        text = unicodedata.normalize('NFC', text)
        text = TextMatcher.PUNCT.sub('', text)
        text = TextMatcher.WHITESPACE.sub('', text)
        text = text.lower().strip()
        return text

    @staticmethod
    def match(subtitles, image_index, match_mode="script"):
        """Match subtitles to images.
        match_mode:
          'srt_index' (Type A) = Index-only matching (ignores text)
          'script'    (Type B) = Subtitle-only matching (ignores index during initial match, followed by gap filling)
        """
        results = []
        used_images = set()

        if match_mode == "srt_index":
            # --- Mode A: Index-only matching ---
            for i, sub in enumerate(subtitles):
                seq = i + 1
                srt_idx = sub.get("srt_index", seq)
                
                matched_images = []
                for img_key, img_data in image_index.items():
                    if img_data.get("scene_number") == srt_idx:
                        matched_images.append(img_data)
                        used_images.add(img_key)
                
                primary_image = matched_images[0] if matched_images else None
                results.append({
                    "index": sub["index"],
                    "seq": seq,
                    "srt_index": srt_idx,
                    "subtitle": sub,
                    "image": primary_image,
                    "images": matched_images,
                    "status": "matched" if primary_image else "unmatched",
                    "match_type": "index_match" if primary_image else "none",
                })
            return results

        else:
            # --- Mode B: Subtitle-only matching + Gap Filling ---
            # 1. Initial text matching
            for i, sub in enumerate(subtitles):
                seq = i + 1
                sub_norm = TextMatcher.normalize(sub["text"])
                scored = []

                for img_key, img_data in image_index.items():
                    if img_key in used_images: continue
                    img_norm = img_data.get("normalized", "")
                    img_korean = img_data.get("korean_normalized", "")
                    target_text = img_korean if img_korean else img_norm
                    
                    score = 0
                    if sub_norm and target_text:
                        if sub_norm == target_text:
                            score = 1000
                        elif sub_norm in target_text or target_text in sub_norm:
                            score = 100 + min(len(sub_norm), len(target_text)) * 10
                    
                    if score > 0:
                        scored.append((score, img_key, img_data))

                scored.sort(key=lambda x: x[0], reverse=True)
                matched_images = []
                best_match_type = "none"
                if scored:
                    best_score = scored[0][0]
                    best_match_type = "exact_text" if best_score >= 1000 else "contains_text"
                    for sc, key, data in scored:
                        if sc >= best_score - 50:
                            matched_images.append(data)
                            used_images.add(key)
                        else: break

                results.append({
                    "index": sub["index"],
                    "seq": seq,
                    "subtitle": sub,
                    "image": matched_images[0] if matched_images else None,
                    "images": matched_images,
                    "status": "matched" if matched_images else "unmatched",
                    "match_type": best_match_type,
                })

            # 2. Gap Filling (Type B only): 배치되지 않은 항목 앞뒤를 확인하여 채우기
            for i in range(len(results)):
                if results[i]["status"] == "unmatched":
                    # 이전/다음 매칭된 결과 찾기
                    prev_match = None
                    for pi in range(i - 1, -1, -1):
                        if results[pi]["status"] == "matched":
                            prev_match = results[pi]["image"]
                            break
                    
                    next_match = None
                    for ni in range(i + 1, len(results)):
                        if results[ni]["status"] == "matched":
                            next_match = results[ni]["image"]
                            break
                    
                    # 주변에 매칭된 이미지가 있다면 가장 가까운 것을 사용 (보통 이전 것 유지)
                    filler = prev_match or next_match
                    if filler:
                        results[i]["image"] = filler
                        results[i]["images"] = [filler]
                        results[i]["status"] = "matched"
                        results[i]["match_type"] = "gap_filled"

            return results


class DraftGenerator:
    """Generate modified draft_content.json with matched images on timeline"""

    @staticmethod
    def generate(draft_data, match_results, image_folder):
        data = copy.deepcopy(draft_data)

        # Find template material from existing videos
        template_mat = DraftGenerator._find_template_material(data)
        if not template_mat:
            raise ValueError("No template image found in materials.videos. "
                             "CapCut project must contain at least one image.")
        
        # Find template segment for robust structure
        template_seg = DraftGenerator._find_template_segment(data)

        # Register ALL matched images as materials (1:N support)
        new_materials = []
        for result in match_results:
            images = result.get("images", [])
            if result["status"] not in ("matched", "manual"):
                if result.get("image"):
                    images = [result["image"]]
                else:
                    continue
            if not images:
                continue

            mat_ids = []
            for img in images:
                mat = DraftGenerator._create_material(
                    template_mat, img["path"], img["filename"])
                new_materials.append(mat)
                mat_ids.append(mat["id"])
            result["_material_ids"] = mat_ids

        # Add to materials.videos
        if "materials" not in data:
            data["materials"] = {}
        if "videos" not in data["materials"]:
            data["materials"]["videos"] = []
        data["materials"]["videos"].extend(new_materials)

        # Build video segments per track layer
        track_layers = {}  # layer_index -> list of segments
        for result in match_results:
            mat_ids = result.get("_material_ids", [])
            if not mat_ids:
                continue
            for layer_idx, mat_id in enumerate(mat_ids):
                seg = DraftGenerator._create_segment(
                    mat_id,
                    result["subtitle"]["start"],
                    result["subtitle"]["duration"],
                    template_seg
                )
                if layer_idx not in track_layers:
                    track_layers[layer_idx] = []
                track_layers[layer_idx].append(seg)

        # Process each track layer
        for layer_idx in sorted(track_layers.keys()):
            segments = track_layers[layer_idx]
            segments.sort(key=lambda s: s["target_timerange"]["start"])
            DraftGenerator._fill_gaps(segments)

            # Find existing video track or create new one
            video_tracks = [t for t in data.get("tracks", []) if t.get("type") == "video"]

            if layer_idx < len(video_tracks):
                video_tracks[layer_idx]["segments"] = segments
            else:
                new_track = {
                    "attribute": 0,
                    "flag": 0,
                    "frozen": False,
                    "id": str(uuid.uuid4()).upper(),
                    "segments": segments,
                    "type": "video"
                }
                data["tracks"].append(new_track)

        return data

    @staticmethod
    def _find_template_material(data):
        videos = data.get("materials", {}).get("videos", [])
        for v in videos:
            if v.get("path") or v.get("material_name"):
                return v
        return None

    @staticmethod
    def _find_template_segment(data):
        tracks = data.get("tracks", [])
        for t in tracks:
            if t.get("type") == "video" and t.get("segments"):
                return t["segments"][0]
        return None

    @staticmethod
    def _create_material(template, image_path, filename):
        mat = copy.deepcopy(template)
        mat["id"] = str(uuid.uuid4()).upper()
        mat["path"] = image_path.replace("/", "\\")
        mat["material_name"] = filename
        mat["category_name"] = "local"
        mat["type"] = "photo" if ".png" in filename.lower() or ".jpg" in filename.lower() else mat.get("type", 0)
        return mat

    @staticmethod
    def _create_segment(material_id, start, duration, template=None):
        if template:
            seg = copy.deepcopy(template)
            seg["id"] = str(uuid.uuid4()).upper()
            seg["material_id"] = material_id
            seg["source_timerange"] = {"start": 0, "duration": duration}
            seg["target_timerange"] = {"start": start, "duration": duration}
            seg["render_timerange"] = {"start": 0, "duration": 0}
            if "extra_material_refs" not in seg:
                seg["extra_material_refs"] = []
            return seg
        
        # Fallback if no template found (should not happen in healthy project)
        return {
            "id": str(uuid.uuid4()).upper(),
            "material_id": material_id,
            "source_timerange": {"start": 0, "duration": duration},
            "target_timerange": {"start": start, "duration": duration},
            "render_timerange": {"start": 0, "duration": 0},
            "visible": True,
            "speed": 1.0,
            "volume": 1.0,
            "clip": {
                "scale": {"x": 1.0, "y": 1.0},
                "rotation": 0.0,
                "transform": {"x": 0.0, "y": 0.0},
                "flip": {"vertical": False, "horizontal": False}
            },
            "extra_material_refs": [],
            "render_index": 0,
            "track_render_index": 0,
            "source": "segmentsourcenormal"
        }

    @staticmethod
    def _fill_gaps(segments):
        for i in range(len(segments) - 1):
            current = segments[i]["target_timerange"]
            next_start = segments[i + 1]["target_timerange"]["start"]
            gap = next_start - (current["start"] + current["duration"])
            if gap > 0:
                current["duration"] += gap
                segments[i]["source_timerange"]["duration"] = current["duration"]


# ============================================================
# 3. Shared UI Widgets
# ============================================================

COLORS = {
    # Stitch Design System - Navy Dark Theme
    'bg': '#0F172A',                    # background-dark
    'card': '#1E293B',                  # surface-dark
    'border': '#1C2536',                # subtle border (white/5 equivalent)
    'primary': '#3B82F6',               # accent blue
    'primary_hover': '#2563EB',         # blue-600
    'primary_light': '#60A5FA',         # lightBlue accent
    'text_main': '#F1F5F9',             # slate-100
    'text_secondary': '#64748B',        # slate-500
    'text_muted': '#475569',            # slate-600
    'success': '#10B981',               # green
    'warning': '#F59E0B',               # amber
    'error': '#EF4444',                 # red
    'accent_cyan': '#00D1B2',           # motion end values
    'drop_zone': '#0F172A',             # same as bg (glass effect)
    'drop_zone_border': '#334155',      # slate-700 dashed border
    'drop_zone_hover': '#1E293B',       # surface on hover
    'glass': '#1E293B',                 # glass panel bg (rgba(30,41,59,0.4))
    'glass_border': '#1C2536',          # glass border
    'slate_800': '#1E293B',             # slate-800
    'surface_motion': '#1A1D23',        # motion tab surface
    'bg_motion': '#0F1115',             # motion tab background
}


class DropZone(tk.Frame):
    """Reusable drag & drop zone - Stitch glass design with circular icon"""

    def __init__(self, parent, label, description, mode="file",
                 file_types=None, on_select=None, icon_text=None, **kwargs):
        super().__init__(parent, bg=COLORS['bg'], **kwargs)
        self.mode = mode
        self.file_types = file_types or [("All files", "*.*")]
        self.on_select = on_select
        self.selected_path = None
        self._icon_text = icon_text or ("+" if mode == "file" else "+")
        self._drop_bg = COLORS['glass']
        self._drop_border = COLORS['drop_zone_border']

        # Drop area - glass panel with dashed border feel
        self.drop_frame = tk.Frame(self, bg=self._drop_bg,
                                    highlightthickness=2,
                                    highlightbackground=self._drop_border,
                                    cursor='hand2')
        self.drop_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Inner content centered
        self.inner = tk.Frame(self.drop_frame, bg=self._drop_bg)
        self.inner.pack(expand=True, fill=tk.BOTH)

        # Circular icon background
        self.icon_circle = tk.Frame(self.inner, bg=COLORS['bg'],
                                     width=48, height=48)
        self.icon_circle.pack(pady=(16, 6))
        self.icon_circle.pack_propagate(False)

        self.icon_label = tk.Label(
            self.icon_circle, text=self._icon_text,
            font=('Segoe UI', 16, 'bold'),
            bg=COLORS['bg'], fg=COLORS['primary'])
        self.icon_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Main text
        self.title_label = tk.Label(
            self.inner, text=f"Drop {('folder' if mode == 'folder' else 'file')} here",
            font=('Segoe UI', 10, 'bold'),
            bg=self._drop_bg, fg=COLORS['text_main'])
        self.title_label.pack(pady=(0, 2))

        # Description
        self.desc_label = tk.Label(
            self.inner, text=description,
            font=('Segoe UI', 8),
            bg=self._drop_bg, fg=COLORS['text_secondary'])
        self.desc_label.pack(pady=(0, 16))

        # Status (hidden until loaded) - replaces drop content
        self.status_frame = tk.Frame(self.drop_frame, bg=self._drop_bg)

        self.loaded_icon = tk.Label(
            self.status_frame, text="V",
            font=('Segoe UI', 12, 'bold'),
            bg=self._drop_bg, fg=COLORS['success'])
        self.loaded_icon.pack(pady=(12, 4))

        self.path_label = tk.Label(
            self.status_frame, text="",
            font=('Segoe UI', 9, 'bold'),
            bg=self._drop_bg, fg=COLORS['text_main'])
        self.path_label.pack(pady=(0, 4))

        self.delete_btn = tk.Button(
            self.status_frame, text="Remove",
            font=('Segoe UI', 8), bg=COLORS['error'], fg='#FFFFFF',
            relief=tk.FLAT, cursor='hand2', padx=10, pady=2,
            command=self._reset)
        self.delete_btn.pack(pady=(0, 12))

        # Bind clicks to all inner widgets
        for w in [self.drop_frame, self.inner, self.icon_circle,
                   self.icon_label, self.title_label, self.desc_label]:
            w.bind('<Button-1>', lambda _: self._browse())
            w.bind('<Enter>', self._hover_in)
            w.bind('<Leave>', self._hover_out)

    def _browse(self):
        if self.mode == "folder":
            path = filedialog.askdirectory(title="Select Folder")
        else:
            path = filedialog.askopenfilename(
                title="Select File", filetypes=self.file_types)
        if path:
            self.set_path(path)

    def set_path(self, path):
        self.selected_path = path
        name = os.path.basename(path)
        if len(name) > 40:
            name = name[:37] + "..."
        self.path_label.config(text=name)

        self.inner.pack_forget()
        self.status_frame.pack(expand=True, fill=tk.BOTH)
        self.drop_frame.configure(highlightbackground=COLORS['success'])

        if self.on_select:
            self.on_select(path)

    def _reset(self):
        self.selected_path = None
        self.status_frame.pack_forget()
        self.inner.pack(expand=True, fill=tk.BOTH)
        self.drop_frame.configure(highlightbackground=self._drop_border)

    def _hover_in(self, _=None):
        if not self.selected_path:
            self.drop_frame.configure(highlightbackground=COLORS['primary'])
            for w in [self.drop_frame, self.inner, self.icon_circle,
                       self.title_label, self.desc_label]:
                try:
                    w.config(bg=COLORS['drop_zone_hover'])
                except tk.TclError:
                    pass
            self.icon_label.config(bg=COLORS['drop_zone_hover'])

    def _hover_out(self, _=None):
        if not self.selected_path:
            self.drop_frame.configure(highlightbackground=self._drop_border)
            for w in [self.drop_frame, self.inner, self.icon_circle,
                       self.title_label, self.desc_label]:
                try:
                    w.config(bg=self._drop_bg)
                except tk.TclError:
                    pass
            self.icon_label.config(bg=COLORS['bg'])


class MatchingTable(tk.Frame):
    """Treeview-based matching results - High performance for 1000+ rows"""

    def __init__(self, parent, all_images=None, **kwargs):
        super().__init__(parent, bg=COLORS['glass'],
                         highlightthickness=1,
                         highlightbackground=COLORS['glass_border'], **kwargs)
        self.match_results = []
        self.all_images = all_images or {}
        self._filtered_results = []  # currently displayed items (index -> result)
        self._img_names_cache = ["(unmatched)"]

        # Header bar (dark top)
        self.header = tk.Frame(self, bg='#0F172D')
        self.header.pack(fill=tk.X)
        header_inner = tk.Frame(self.header, bg='#0F172D')
        header_inner.pack(fill=tk.X, padx=12, pady=8)

        self.summary_label = tk.Label(
            header_inner, text="Matching Results",
            font=('Segoe UI', 11, 'bold'),
            bg='#0F172D', fg=COLORS['text_main'])
        self.summary_label.pack(side=tk.LEFT)

        self.badge_label = tk.Label(self.header, text="0 MATCHES",
                                    font=('Segoe UI', 9, 'bold'),
                                    bg=COLORS['border'], fg=COLORS['text_main'],
                                    padx=8, pady=2)
        self.badge_label.pack(side=tk.LEFT, padx=10)

        # Filter: Matched / Unmatched / All
        self.filter_var = tk.StringVar(value="Matched Only")
        self.filter_combo = ttk.Combobox(self.header, textvariable=self.filter_var,
                                         values=["Matched Only", "Unmatched Only", "All"],
                                         state="readonly", width=15, font=('Segoe UI', 8))
        self.filter_combo.pack(side=tk.RIGHT, padx=10)
        self.filter_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        self.clear_btn = tk.Button(
            header_inner, text="Clear Workspace",
            font=('Segoe UI', 8, 'bold'),
            bg='#0F172D', fg=COLORS['text_secondary'],
            activebackground='#0F172D', activeforeground=COLORS['error'],
            relief=tk.FLAT, cursor='hand2',
            command=self._clear_all)
        self.clear_btn.pack(side=tk.RIGHT)

        # --- Treeview (high-performance native widget) ---
        style = ttk.Style()
        style.configure("Match.Treeview",
                         background=COLORS['bg'],
                         foreground=COLORS['text_main'],
                         fieldbackground=COLORS['bg'],
                         font=('Segoe UI', 11),
                         rowheight=32)
        style.configure("Match.Treeview.Heading",
                         background=COLORS['border'],
                         foreground=COLORS['text_secondary'],
                         font=('Segoe UI', 11, 'bold'))
        style.map("Match.Treeview",
                   background=[('selected', COLORS['primary'])],
                   foreground=[('selected', '#FFFFFF')])

        tree_frame = tk.Frame(self, bg=COLORS['bg'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 4))

        self.tree = ttk.Treeview(tree_frame, style="Match.Treeview",
                                  columns=("idx", "subtitle", "image", "status"),
                                  show="headings", selectmode="browse")

        self.tree.heading("idx", text="#", anchor=tk.W)
        self.tree.heading("subtitle", text="Subtitle", anchor=tk.W)
        self.tree.heading("image", text="Image", anchor=tk.W)
        self.tree.heading("status", text="Status", anchor=tk.CENTER)

        self.tree.column("idx", width=50, minwidth=40, stretch=False)
        self.tree.column("subtitle", width=350, minwidth=200, stretch=True)
        self.tree.column("image", width=400, minwidth=200, stretch=True)
        self.tree.column("status", width=70, minwidth=50, stretch=False)

        # Tag-based coloring (much faster than per-widget)
        self.tree.tag_configure("matched",
                                 foreground=COLORS['success'])
        self.tree.tag_configure("unmatched",
                                 foreground=COLORS['error'])

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Double-click to manually assign image (unmatched rows)
        self.tree.bind("<Double-1>", self._on_double_click)

        # Status bar for empty / info
        self.status_frame = tk.Frame(self, bg=COLORS['bg'])
        self.status_msg = tk.Label(self.status_frame, text="",
                                    font=('Segoe UI', 11),
                                    bg=COLORS['bg'], fg=COLORS['text_secondary'])
        self.status_msg.pack(pady=10)

    def _on_filter_changed(self, event=None):
        if hasattr(self, 'match_results') and self.match_results:
            self.update_results(self.match_results, filter_state=self.filter_var.get())

    def update_results(self, results, all_images=None, filter_state=None):
        self.match_results = results
        if filter_state is not None:
            self.filter_var.set(filter_state)

        current_filter = self.filter_var.get()
        if all_images:
            self.all_images = all_images
            self._img_names_cache = ["(unmatched)"] + [
                v["filename"] for v in all_images.values()
            ]

        # Filter
        if current_filter == "Matched Only":
            self._filtered_results = [r for r in results if r["status"] in ("matched", "manual")]
        elif current_filter == "Unmatched Only":
            self._filtered_results = [r for r in results if r["status"] not in ("matched", "manual")]
        else:
            self._filtered_results = results[:]

        # Stats
        matched = sum(1 for r in results if r["status"] in ("matched", "manual"))
        unmatched_count = len(results) - matched

        status_text = f"{matched} MATCHED | {unmatched_count} UNMATCHED"
        if current_filter != "All":
            status_text += f" (Showing {current_filter})"
        self.badge_label.config(text=status_text)

        # Clear treeview
        self.tree.delete(*self.tree.get_children())
        self.status_frame.pack_forget()

        if not self._filtered_results:
            if unmatched_count == 0 and current_filter != "Unmatched Only":
                self.status_msg.config(text="✨ All items matched perfectly!",
                                        fg=COLORS['success'])
            else:
                self.status_msg.config(text=f"No results for: {current_filter}",
                                        fg=COLORS['text_secondary'])
            self.status_frame.pack(fill=tk.X, pady=20)
            return

        # Insert ALL rows instantly (Treeview handles virtualization natively)
        for r in self._filtered_results:
            is_matched = r["status"] in ("matched", "manual")
            idx_text = str(r["index"] + 1)
            sub_text = r["subtitle"]["text"]

            images = r.get("images", [])
            if not images and r.get("image"):
                images = [r["image"]]
            if images:
                first_name = images[0]["filename"]
                img_text = f"{first_name} (+{len(images)-1})" if len(images) > 1 else first_name
            else:
                img_text = "(unmatched)"

            status_text = "OK" if is_matched else "NEED"
            tag = "matched" if is_matched else "unmatched"

            self.tree.insert("", tk.END,
                              values=(idx_text, sub_text, img_text, status_text),
                              tags=(tag,))

    def _on_double_click(self, event):
        """Double-click on unmatched row to assign image manually"""
        item = self.tree.focus()
        if not item:
            return

        values = self.tree.item(item, "values")
        tags = self.tree.item(item, "tags")
        if "matched" in tags:
            return  # already matched, ignore

        idx_text = values[0]

        # Find matching result
        target_result = None
        for r in self.match_results:
            if str(r["index"] + 1) == idx_text:
                target_result = r
                break

        if not target_result:
            return

        # Show a selection dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Assign Image to #{idx_text}")
        dialog.geometry("500x400")
        dialog.configure(bg=COLORS['bg'])
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        tk.Label(dialog, text=f"Subtitle: {target_result['subtitle']['text']}",
                 font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['bg'], fg=COLORS['text_main'],
                 wraplength=480).pack(padx=10, pady=(10, 5), anchor=tk.W)

        tk.Label(dialog, text="Select an image:",
                 font=('Segoe UI', 9),
                 bg=COLORS['bg'], fg=COLORS['text_secondary']).pack(padx=10, anchor=tk.W)

        list_frame = tk.Frame(dialog, bg=COLORS['bg'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        listbox = tk.Listbox(list_frame, font=('Segoe UI', 10),
                              bg=COLORS['card'], fg=COLORS['text_main'],
                              selectbackground=COLORS['primary'],
                              selectforeground='#FFFFFF',
                              relief=tk.FLAT)

        lb_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=lb_scroll.set)

        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lb_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        img_names = [v["filename"] for v in self.all_images.values()]
        for name in img_names:
            listbox.insert(tk.END, name)

        def apply_selection():
            sel = listbox.curselection()
            if not sel:
                dialog.destroy()
                return
            selected_name = img_names[sel[0]]
            for img_data in self.all_images.values():
                if img_data["filename"] == selected_name:
                    target_result["image"] = img_data
                    target_result["images"] = [img_data]
                    target_result["status"] = "manual"
                    target_result["match_type"] = "manual"
                    break
            dialog.destroy()
            self._refresh_summary()
            self.update_results(self.match_results, filter_state=self.filter_var.get())

        btn_frame = tk.Frame(dialog, bg=COLORS['bg'])
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(btn_frame, text="Apply", font=('Segoe UI', 10, 'bold'),
                  bg=COLORS['primary'], fg='#FFFFFF', relief=tk.FLAT,
                  padx=20, pady=4, cursor='hand2',
                  command=apply_selection).pack(side=tk.RIGHT, padx=(5, 0))
        tk.Button(btn_frame, text="Cancel", font=('Segoe UI', 10),
                  bg=COLORS['card'], fg=COLORS['text_secondary'], relief=tk.FLAT,
                  padx=20, pady=4, cursor='hand2',
                  command=dialog.destroy).pack(side=tk.RIGHT)

    def _refresh_summary(self):
        matched = sum(1 for r in self.match_results
                      if r["status"] in ("matched", "manual"))
        unmatched = len(self.match_results) - matched
        self.badge_label.config(text=f"{matched} MATCHED | {unmatched} UNMATCHED")

    def get_results(self):
        return self.match_results

    def _clear_all(self):
        self.match_results = []
        self._filtered_results = []
        self.tree.delete(*self.tree.get_children())
        self.badge_label.config(text="0 MATCHES")
        self._show_empty_state()

    def _show_empty_state(self):
        """Show Stitch-style empty state"""
        self.status_msg.config(text="Waiting for data\nConnect your folders to start automated matching",
                                fg=COLORS['text_muted'])
        self.status_frame.pack(fill=tk.X, pady=40)


# ============================================================
# 4. Motion UI Widgets (Reused)
# ============================================================
# ... (rest of the code)

# Note: Need to update ImageMatchingTab._generate later

    def _show_empty_state(self):
        """Show Stitch-style empty state with icon and text"""
        empty = tk.Frame(self.scroll_frame, bg=COLORS['glass'])
        empty.pack(expand=True, fill=tk.BOTH, pady=40)

        icon_circle = tk.Frame(empty, bg=COLORS['border'],
                                width=64, height=64)
        icon_circle.pack(pady=(0, 12))
        icon_circle.pack_propagate(False)
        tk.Label(icon_circle, text="?",
                 font=('Segoe UI', 24),
                 bg=COLORS['border'],
                 fg=COLORS['text_muted']).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        tk.Label(empty, text="Waiting for data",
                 font=('Segoe UI', 13, 'bold'),
                 bg=COLORS['glass'], fg=COLORS['text_secondary']).pack(pady=(0, 4))
        tk.Label(empty, text="Connect your folders to start automated matching",
                 font=('Segoe UI', 9),
                 bg=COLORS['glass'], fg=COLORS['text_muted']).pack()


# ============================================================
# 4. Motion UI Widgets (Reused)
# ============================================================

class MotionCard(tk.Frame):
    """Stitch-style motion option card with ring effect on selection"""
    C = {'normal': COLORS['card'], 'hover': COLORS['border'],
         'selected': COLORS['primary'], 'border': COLORS['glass_border'],
         'text': COLORS['text_main'], 'text_muted': COLORS['text_secondary']}

    def __init__(self, parent, icon, title, value, variable, **kwargs):
        super().__init__(parent, **kwargs)
        self.value = value
        self.variable = variable
        self.is_selected = False
        self.configure(width=85, height=62)
        self.pack_propagate(False)
        self.configure(bg=self.C['normal'], highlightthickness=1,
                       highlightbackground=self.C['border'], cursor='hand2')

        self.icon_lbl = tk.Label(self, text=icon, font=('Segoe UI', 14),
                            bg=self.C['normal'], fg=self.C['text_muted'])
        self.icon_lbl.pack(pady=(6, 1))
        self.title_lbl = tk.Label(self, text=title, font=('Segoe UI', 8, 'bold'),
                             bg=self.C['normal'], fg=self.C['text'])
        self.title_lbl.pack()

        for w in [self, self.icon_lbl, self.title_lbl]:
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
            self._set_bg(self.C['hover'])
            self.configure(highlightbackground=COLORS['primary'])

    def on_leave(self, _=None):
        if not self.is_selected:
            self._set_bg(self.C['normal'])
            self.configure(highlightbackground=self.C['border'])

    def _set_bg(self, color):
        self.configure(bg=color)
        for c in self.winfo_children():
            if isinstance(c, tk.Label):
                c.configure(bg=color)

    def select(self):
        self.is_selected = True
        self.configure(highlightbackground=self.C['selected'], highlightthickness=2)
        self._set_bg(self.C['normal'])
        self.icon_lbl.config(fg=COLORS['primary'])
        self.title_lbl.config(fg=COLORS['primary'])

    def deselect(self):
        self.is_selected = False
        self.configure(highlightbackground=self.C['border'], highlightthickness=1)
        self.icon_lbl.config(fg=self.C['text_muted'])
        self.title_lbl.config(fg=self.C['text'])


class AnimatedPreview(tk.Canvas):
    """Stitch-style motion preview with grid pattern and dashed outer frame"""
    FRAME_RATIO = 0.55

    def __init__(self, parent, width=330, height=200, **kwargs):
        super().__init__(parent, width=width, height=height,
                         bg='#000000', highlightthickness=1,
                         highlightbackground=COLORS['glass_border'], **kwargs)
        self.w = width
        self.h = height
        self.cx = width // 2
        self.cy = height // 2

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
                                                 outline=COLORS['primary'], width=2, dash=(4, 2))

    def _draw_static(self):
        # Stitch grid-pattern (#2a2d35 lines, 20px spacing)
        grid_color = '#2a2d35'
        for x in range(0, self.w, 20):
            self.create_line(x, 0, x, self.h, fill=grid_color)
        for y in range(0, self.h, 20):
            self.create_line(0, y, self.w, y, fill=grid_color)
        # Dashed outer frame (muted primary)
        self.create_rectangle(self.frame_x1 - 8, self.frame_y1 - 8,
                              self.frame_x2 + 8, self.frame_y2 + 8,
                              outline='#1E3A5F', width=1, dash=(4, 4))
        # Center crosshairs (dashed)
        self.create_line(self.cx, self.frame_y1, self.cx, self.frame_y2,
                         fill='#333333', dash=(3, 3))
        self.create_line(self.frame_x1, self.cy, self.frame_x2, self.cy,
                         fill='#333333', dash=(3, 3))
        # Solid white inner frame
        self.create_rectangle(self.frame_x1, self.frame_y1,
                              self.frame_x2, self.frame_y2,
                              outline='#FFFFFF', width=2)
        # 16:9 label
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
# 5. Tab 1: Image Matching Tab
# ============================================================

class ImageMatchingTab(tk.Frame):
    """Tab 1: Image-to-subtitle matching workflow"""

    def __init__(self, parent, on_chain_to_motion=None, **kwargs):
        super().__init__(parent, bg=COLORS['bg'], **kwargs)
        self.on_chain_to_motion = on_chain_to_motion
        self.draft_data = None
        self.draft_path = None
        self.image_folder = None
        self.subtitles = []
        self.image_index = {}
        self.match_results = []
        self.generated_path = None
        self.match_mode = tk.StringVar(value="script")  # "script" (Type B) or "srt_index" (Type A)

        self._build_ui()

    def _build_ui(self):
        # Footer FIRST (pack before main so it gets space)
        footer = tk.Frame(self, bg=COLORS['card'],
                          highlightthickness=1,
                          highlightbackground=COLORS['border'])
        footer.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=0)
        footer_inner = tk.Frame(footer, bg=COLORS['card'])
        footer_inner.pack(fill=tk.X, padx=16, pady=10)

        # Left: System Status
        status_area = tk.Frame(footer_inner, bg=COLORS['card'])
        status_area.pack(side=tk.LEFT)
        tk.Label(status_area, text="SYSTEM STATUS",
                 font=('Segoe UI', 7, 'bold'),
                 bg=COLORS['card'], fg=COLORS['text_muted']).pack(anchor=tk.W)
        self.sys_status = tk.Label(
            status_area, text="Ready for input",
            font=('Segoe UI', 8),
            bg=COLORS['card'], fg=COLORS['text_main'])
        self.sys_status.pack(anchor=tk.W)

        # Right: Apply Motion button
        self.chain_btn = tk.Button(
            footer_inner, text="Apply Motion  ->",
            font=('Segoe UI', 10, 'bold'),
            bg=COLORS['card'], fg=COLORS['primary'],
            activebackground=COLORS['card'],
            activeforeground=COLORS['primary_light'],
            relief=tk.FLAT, cursor='hand2',
            highlightthickness=1,
            highlightbackground=COLORS['primary'],
            command=self._chain_to_motion, state=tk.DISABLED)
        self.chain_btn.pack(side=tk.RIGHT, ipadx=16, ipady=6)

        # Center: GENERATE PROJECT button (blue, prominent)
        self.generate_btn = tk.Button(
            footer_inner, text="GENERATE PROJECT",
            font=('Segoe UI', 12, 'bold'),
            bg=COLORS['primary'], fg='#FFFFFF',
            activebackground=COLORS['primary_hover'],
            activeforeground='#FFFFFF',
            relief=tk.FLAT, cursor='hand2',
            command=self._generate, state=tk.DISABLED)
        self.generate_btn.pack(fill=tk.X, expand=True, ipady=8, padx=(16, 16))

        # Main content area (flex-1) - packed after footer
        main = tk.Frame(self, bg=COLORS['bg'])
        main.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        # Left aside (1/3): drop zones
        left = tk.Frame(main, bg=COLORS['bg'])
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 8))
        left.configure(width=340)
        left.pack_propagate(False)

        # Project Folder section
        hdr1 = tk.Frame(left, bg=COLORS['bg'])
        hdr1.pack(fill=tk.X, pady=(0, 4))
        tk.Label(hdr1, text="PROJECT FOLDER",
                 font=('Segoe UI', 8, 'bold'),
                 bg=COLORS['bg'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
        tk.Label(hdr1, text="REQUIRED",
                 font=('Segoe UI', 7, 'bold'),
                 bg='#1E3A5F', fg=COLORS['primary'],
                 padx=6, pady=1).pack(side=tk.RIGHT)

        self.project_drop = DropZone(
            left,
            label="REQUIRED",
            description="Must contain draft_content.json",
            mode="folder",
            icon_text="F",
            on_select=self._on_project_folder)
        self.project_drop.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        # Image Folder section
        hdr2 = tk.Frame(left, bg=COLORS['bg'])
        hdr2.pack(fill=tk.X, pady=(0, 4))
        tk.Label(hdr2, text="SOURCE IMAGE FOLDER",
                 font=('Segoe UI', 8, 'bold'),
                 bg=COLORS['bg'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
        tk.Label(hdr2, text="REQUIRED",
                 font=('Segoe UI', 7, 'bold'),
                 bg='#1E3A5F', fg=COLORS['primary'],
                 padx=6, pady=1).pack(side=tk.RIGHT)

        self.image_drop = DropZone(
            left,
            label="REQUIRED",
            description="Filenames should contain matching\nsubtitle keywords",
            mode="folder",
            icon_text="I",
            on_select=self._on_image_folder)
        self.image_drop.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        # Match Mode selector
        mode_frame = tk.Frame(left, bg=COLORS['glass'],
                              highlightthickness=1,
                              highlightbackground=COLORS['glass_border'])
        mode_frame.pack(fill=tk.X, pady=(8, 0))
        mode_inner = tk.Frame(mode_frame, bg=COLORS['glass'])
        mode_inner.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(mode_inner, text="MATCH MODE",
                 font=('Segoe UI', 7, 'bold'),
                 bg=COLORS['glass'], fg=COLORS['text_muted']).pack(anchor=tk.W)

        rb_a = tk.Radiobutton(
            mode_inner, text="유형 A: SRT 인덱스 매칭",
            variable=self.match_mode, value="srt_index",
            font=('Segoe UI', 9),
            bg=COLORS['glass'], fg=COLORS['text_main'],
            selectcolor=COLORS['card'],
            activebackground=COLORS['glass'],
            activeforeground=COLORS['primary_light'],
            command=self._try_match)
        rb_a.pack(anchor=tk.W, pady=(4, 0))

        rb_b = tk.Radiobutton(
            mode_inner, text="유형 B: 대본 텍스트 매칭",
            variable=self.match_mode, value="script",
            font=('Segoe UI', 9),
            bg=COLORS['glass'], fg=COLORS['text_main'],
            selectcolor=COLORS['card'],
            activebackground=COLORS['glass'],
            activeforeground=COLORS['primary_light'],
            command=self._try_match)
        rb_b.pack(anchor=tk.W, pady=(2, 0))

        # Right section (flex-1): matching results glass panel
        right = tk.Frame(main, bg=COLORS['bg'])
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.matching_table = MatchingTable(right)
        self.matching_table.pack(fill=tk.BOTH, expand=True)

        # Status
        self.status_label = tk.Label(
            left, text="", font=('Segoe UI', 9),
            bg=COLORS['bg'], fg=COLORS['text_secondary'])
        self.status_label.pack(anchor=tk.W, pady=(4, 0))

    def _on_project_folder(self, path):
        # Immediate UI feedback
        self.status_label.config(text="Loading project...", fg=COLORS['primary'])
        self.update()

        def _do_load():
            draft_file = os.path.join(path, "draft_content.json")
            if not os.path.isfile(draft_file):
                messagebox.showerror("Error",
                                     "draft_content.json not found in this folder.")
                self.project_drop._reset()
                return

            try:
                with open(draft_file, "r", encoding="utf-8") as f:
                    self.draft_data = json.load(f)
                self.draft_path = draft_file
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load draft:\n{e}")
                self.project_drop._reset()
                return

            self.subtitles = SubtitleExtractor.extract(self.draft_data)
            if not self.subtitles:
                messagebox.showwarning("Warning", "No subtitles found in project.")

            self.status_label.config(
                text=f"Found {len(self.subtitles)} subtitles",
                fg=COLORS['success'])
            self._try_match()

        # Small delay to ensure UI updates
        self.after(100, _do_load)

    def _on_image_folder(self, path):
        self.status_label.config(text="Indexing images...", fg=COLORS['primary'])
        self.update()

        def _do_index():
            self.image_folder = path
            self.image_index = ImageIndexer.index(path)
            count = len(self.image_index)
            self.status_label.config(
                text=f"Found {count} images",
                fg=COLORS['success'] if count > 0 else COLORS['warning'])
            self._try_match()

        self.after(100, _do_index)

    def _try_match(self):
        if not self.subtitles or not self.image_index:
            return

        # Show busy state
        self.status_label.config(text="Matching...", fg=COLORS['warning'])
        self.update()

        try:
            self.match_results = TextMatcher.match(self.subtitles, self.image_index, self.match_mode.get())
            self.matching_table.update_results(self.match_results, self.image_index)
            self.generate_btn.config(state=tk.NORMAL)

            matched = sum(1 for r in self.match_results
                          if r["status"] in ("matched", "manual"))
            self.status_label.config(
                text=f"{matched}/{len(self.match_results)} subtitles matched",
                fg=COLORS['success'] if matched == len(self.match_results)
                else COLORS['warning'])
        except Exception as e:
            print(f"Matching error: {e}")
            messagebox.showerror("Error", f"Error during matching: {e}")

    def _generate(self):
        if not self.draft_data or not self.match_results:
            messagebox.showerror("Error", "Please load both folders first.")
            return

        # UI Feedback: Disable button and show spinner-like text
        self.generate_btn.config(state=tk.DISABLED, text="⌛ Generating...")
        self.status_label.config(text="Generating project... Please wait.", fg=COLORS['primary'])
        self.update()

        def _do_generate():
            try:
                # Get latest results (includes manual overrides)
                results = self.matching_table.get_results()

                # Backup
                backup_path = self.draft_path + ".bak"
                with open(self.draft_path, "r", encoding="utf-8") as f:
                    original = f.read()
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(original)

                # Generate
                modified = DraftGenerator.generate(
                    self.draft_data, results, self.image_folder)

                # Save
                output_path = self.draft_path
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(modified, f, ensure_ascii=False, indent=2)

                self.generated_path = output_path
                
                # Success UI
                self.chain_btn.config(state=tk.NORMAL)
                matched = sum(1 for r in results
                              if r["status"] in ("matched", "manual"))
                self.status_label.config(
                    text=f"Generated! {matched} images placed.",
                    fg=COLORS['success'])
                
                messagebox.showinfo("Success",
                                    f"Project generated successfully!\n"
                                    f"{matched} images placed on timeline.")

            except Exception as e:
                self.status_label.config(text=f"Error: {e}", fg=COLORS['error'])
                messagebox.showerror("Error", str(e))
            finally:
                # Restore button state
                self.generate_btn.config(state=tk.NORMAL, text="GENERATE PROJECT")

        # Run generate in a slight delay to allow UI to update
        self.after(100, _do_generate)

    def _on_show_all_toggle(self):
        show_all = getattr(self, '_show_all_results', False)
        self._show_all_results = not show_all
        self.matching_table.update_results(self.match_results, self.image_index, show_all=self._show_all_results)

    def _chain_to_motion(self):
        if self.generated_path and self.on_chain_to_motion:
            self.on_chain_to_motion(self.generated_path)

    def _reset(self):
        self.draft_data = None
        self.draft_path = None
        self.image_folder = None
        self.subtitles = []
        self.image_index = {}
        self.match_results = []
        self.generated_path = None

        self.project_drop._reset()
        self.image_drop._reset()
        self.matching_table._clear_all()
        self.generate_btn.config(state=tk.DISABLED)
        self.chain_btn.config(state=tk.DISABLED)
        self.status_label.config(text="", fg=COLORS['text_secondary'])


# ============================================================
# 6. Tab 2: Motion Application Tab
# ============================================================

class MotionTab(tk.Frame):
    """Tab 2: Motion application (refactored from CapCutMotionStudio)"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS['bg'], **kwargs)
        self.input_file = None
        self.clip_count = 0
        self.update_timer = None
        self.source_indicator = None

        self._build_ui()

    def _build_ui(self):
        # Footer FIRST (pack before main so it gets space)
        footer = tk.Frame(self, bg=COLORS['card'],
                          highlightthickness=1,
                          highlightbackground=COLORS['border'])
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer_inner = tk.Frame(footer, bg=COLORS['card'])
        footer_inner.pack(fill=tk.X, padx=16, pady=10)

        # Left: New Project (red text)
        tk.Button(
            footer_inner, text="New Project",
            font=('Segoe UI', 10, 'bold'),
            bg=COLORS['card'], fg=COLORS['error'],
            activebackground=COLORS['card'],
            activeforeground=COLORS['error'],
            relief=tk.FLAT, cursor='hand2',
            command=self._reset_motion).pack(side=tk.LEFT, ipadx=8, ipady=4)

        # Right: APPLY MOTION button (blue, bold)
        self.apply_btn = tk.Button(
            footer_inner, text="APPLY MOTION  ->",
            font=('Segoe UI', 12, 'bold'),
            bg=COLORS['primary'], fg='#FFFFFF',
            activebackground=COLORS['primary_hover'],
            activeforeground='#FFFFFF',
            relief=tk.FLAT, cursor='hand2',
            command=self.apply_motion)
        self.apply_btn.pack(side=tk.RIGHT, ipadx=20, ipady=6)

        self.status_label = tk.Label(
            footer_inner, text="", font=('Segoe UI', 9),
            bg=COLORS['card'], fg=COLORS['text_secondary'])
        self.status_label.pack(side=tk.RIGHT, padx=(0, 12))

        # Drop Zone for JSON file
        top = tk.Frame(self, bg=COLORS['bg'])
        top.pack(fill=tk.X, padx=16, pady=(8, 6))

        self.drop_zone = DropZone(
            top,
            label="DRAFT FILE",
            description="Drop draft_content.json here\nor click to browse",
            mode="file",
            file_types=[("JSON files", "*.json"), ("All files", "*.*")],
            on_select=self._on_file_select)
        self.drop_zone.pack(fill=tk.X)

        # Source indicator (shown when chained from Tab 1)
        self.source_label = tk.Label(
            top, text="", font=('Segoe UI', 9, 'italic'),
            bg=COLORS['bg'], fg=COLORS['primary'])
        self.source_label.pack(anchor=tk.W, pady=(4, 0))

        # Main content (packed after footer, so footer gets its space)
        main = tk.Frame(self, bg=COLORS['bg'])
        main.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 4))

        # Left: settings
        left = tk.Frame(main, bg=COLORS['bg'])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self._build_zoom_section(left)
        self._build_pan_section(left)
        self._build_settings_section(left)

        # Right: preview
        right = tk.Frame(main, bg=COLORS['bg'], width=370)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(8, 0))
        right.pack_propagate(False)

        self._build_preview_section(right)

    def _section(self, parent, title, width=None):
        container = tk.Frame(parent, bg=COLORS['bg'])
        container.pack(fill=tk.X, pady=(0, 6))
        tk.Label(container, text=title.upper(), font=('Segoe UI', 8, 'bold'),
                 bg=COLORS['bg'], fg=COLORS['text_secondary']).pack(
            anchor=tk.W, pady=(0, 3))
        frame = tk.Frame(container, bg=COLORS['card'],
                         highlightthickness=1,
                         highlightbackground=COLORS['border'])
        if width:
            frame.configure(width=width)
        frame.pack(fill=tk.X)
        inner = tk.Frame(frame, bg=COLORS['card'])
        inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        return inner

    def _entry(self, parent, variable):
        e = tk.Entry(parent, textvariable=variable, font=('Segoe UI', 10),
                     bg=COLORS['slate_800'], fg=COLORS['text_main'],
                     insertbackground=COLORS['text_main'],
                     relief=tk.FLAT, width=7)
        e.bind('<KeyRelease>', lambda _: self._schedule_preview())
        return e

    def _build_zoom_section(self, parent):
        inner = self._section(parent, "Zoom")
        row = tk.Frame(inner, bg=COLORS['card'])
        row.pack(fill=tk.X, pady=(4, 0))

        self.zoom_var = tk.StringVar(value="zoom_in")
        for icon, title, value in [
            ("--", "None", "none"), ("ZI", "In", "zoom_in"),
            ("ZO", "Out", "zoom_out"), ("RD", "Random", "zoom_random")
        ]:
            MotionCard(row, icon, title, value, self.zoom_var).pack(
                side=tk.LEFT, padx=(0, 6))
        self.zoom_var.trace_add('write', lambda *_: self._schedule_preview())

    def _build_pan_section(self, parent):
        inner = self._section(parent, "Pan")

        h_header = tk.Frame(inner, bg=COLORS['card'])
        h_header.pack(fill=tk.X, pady=(2, 3))
        tk.Label(h_header, text="H", font=('Segoe UI', 9, 'bold'),
                 bg=COLORS['card'], fg=COLORS['text_secondary'],
                 width=3).pack(side=tk.LEFT)
        h_row = tk.Frame(h_header, bg=COLORS['card'])
        h_row.pack(side=tk.LEFT)

        self.pan_h_var = tk.StringVar(value="random")
        for icon, title, value in [
            ("--", "None", "none"), ("->", "L>R", "positive"),
            ("<-", "R>L", "negative"), ("RD", "Rand", "random")
        ]:
            MotionCard(h_row, icon, title, value, self.pan_h_var).pack(
                side=tk.LEFT, padx=(0, 6))

        v_header = tk.Frame(inner, bg=COLORS['card'])
        v_header.pack(fill=tk.X, pady=(6, 0))
        tk.Label(v_header, text="V", font=('Segoe UI', 9, 'bold'),
                 bg=COLORS['card'], fg=COLORS['text_secondary'],
                 width=3).pack(side=tk.LEFT)
        v_row = tk.Frame(v_header, bg=COLORS['card'])
        v_row.pack(side=tk.LEFT)

        self.pan_v_var = tk.StringVar(value="random")
        for icon, title, value in [
            ("--", "None", "none"), ("v", "T>B", "positive"),
            ("^", "B>T", "negative"), ("RD", "Rand", "random")
        ]:
            MotionCard(v_row, icon, title, value, self.pan_v_var).pack(
                side=tk.LEFT, padx=(0, 6))

        self.pan_h_var.trace_add('write', lambda *_: self._schedule_preview())
        self.pan_v_var.trace_add('write', lambda *_: self._schedule_preview())

    def _build_settings_section(self, parent):
        inner = self._section(parent, "Settings (설정)")
        # Labels and variables for scale are now in % (104 means 1.04)
        rows = [
            ("시작 스케일 (%)", "start_scale", 104.0, None, None),
            ("종료 스케일 (%)", "end_scale_min", 130.0, "end_scale_max", 140.0),
            ("이동 강도 (Pan)", "pan_strength", 0.05, None, None),
        ]
        for i, (label, v1n, v1v, v2n, v2v) in enumerate(rows):
            row = tk.Frame(inner, bg=COLORS['card'])
            row.pack(fill=tk.X, pady=(4 if i == 0 else 0, 4))
            tk.Label(row, text=label, font=('Segoe UI', 10),
                     bg=COLORS['card'], fg=COLORS['text_main'],
                     width=16, anchor=tk.W).pack(side=tk.LEFT)
            v1 = tk.DoubleVar(value=v1v)
            setattr(self, v1n, v1)
            self._entry(row, v1).pack(side=tk.LEFT)
            if v2n:
                tk.Label(row, text=" ~ ", font=('Segoe UI', 10),
                         bg=COLORS['card'],
                         fg=COLORS['text_secondary']).pack(side=tk.LEFT)
                v2 = tk.DoubleVar(value=v2v)
                setattr(self, v2n, v2)
                self._entry(row, v2).pack(side=tk.LEFT)
            elif "pan" in v1n:
                tk.Label(row, text=" +/-", font=('Segoe UI', 10),
                         bg=COLORS['card'],
                         fg=COLORS['text_secondary']).pack(side=tk.LEFT)

    def _build_preview_section(self, parent):
        inner = self._section(parent, "Motion Preview (프리뷰)", width=355)
        inner.master.pack(fill=tk.BOTH, expand=True)

        self.preview = AnimatedPreview(inner, width=330, height=200)
        self.preview.pack(pady=(6, 8), padx=5)

        # Stitch-style info panel (dark bg, mono font)
        self.info_frame = tk.Frame(inner, bg=COLORS['bg_motion'])
        self.info_frame.pack(fill=tk.X, padx=0, pady=(0, 0))

        # Summary line
        self.info_summary = tk.Label(
            self.info_frame, text="",
            font=('Consolas', 8),
            bg=COLORS['bg_motion'], fg=COLORS['text_muted'],
            anchor=tk.W)
        self.info_summary.pack(fill=tk.X, padx=8, pady=(6, 4))

        # Separator
        tk.Frame(self.info_frame, bg=COLORS['glass_border'], height=1).pack(
            fill=tk.X, padx=8, pady=(0, 4))

        # 3-column grid: Attribute | Start | End
        self.info_grid = tk.Frame(self.info_frame, bg=COLORS['bg_motion'])
        self.info_grid.pack(fill=tk.X, padx=8, pady=(0, 8))

        # Header row
        for col, text in enumerate(["ATTRIBUTE", "START", "END"]):
            tk.Label(self.info_grid, text=text,
                     font=('Consolas', 7, 'bold'),
                     bg=COLORS['bg_motion'], fg=COLORS['text_muted'],
                     width=12, anchor=tk.W).grid(row=0, column=col, sticky=tk.W)

        # Data rows (will be updated)
        self.info_rows = {}
        for i, attr in enumerate(["Scale", "Pan X", "Pan Y"]):
            lbl_attr = tk.Label(self.info_grid, text=attr,
                                font=('Consolas', 9),
                                bg=COLORS['bg_motion'], fg=COLORS['primary'],
                                width=12, anchor=tk.W)
            lbl_attr.grid(row=i+1, column=0, sticky=tk.W)
            lbl_start = tk.Label(self.info_grid, text="0.00",
                                 font=('Consolas', 9),
                                 bg=COLORS['bg_motion'], fg=COLORS['text_main'],
                                 width=12, anchor=tk.W)
            lbl_start.grid(row=i+1, column=1, sticky=tk.W)
            lbl_end = tk.Label(self.info_grid, text="0.00",
                               font=('Consolas', 9),
                               bg=COLORS['bg_motion'], fg=COLORS['accent_cyan'],
                               width=12, anchor=tk.W)
            lbl_end.grid(row=i+1, column=2, sticky=tk.W)
            self.info_rows[attr] = (lbl_start, lbl_end)

    def _schedule_preview(self):
        if self.update_timer:
            self.after_cancel(self.update_timer)
        self.update_timer = self.after(300, self._update_preview)

    def _update_preview(self):
        try:
            # Convert UI % to Engine Scale (104 -> 1.04)
            ss = self.start_scale.get() / 100.0
            emin = self.end_scale_min.get() / 100.0
            emax = self.end_scale_max.get() / 100.0
            ps = self.pan_strength.get()

            start_s, end_s = MotionEngine.compute_zoom(
                self.zoom_var.get(), ss, emin, emax)
            start_x, end_x = MotionEngine.compute_pan_axis(
                self.pan_h_var.get(), ps)
            start_y, end_y = MotionEngine.compute_pan_axis(
                self.pan_v_var.get(), ps)

            self.preview.set_motion(start_s, end_s, start_x, end_x,
                                    start_y, end_y)
            self.preview.start_animation()

            zoom_labels = {"none": "None", "zoom_in": "Zoom In",
                           "zoom_out": "Zoom Out", "zoom_random": "Random"}
            pan_labels = {"none": "None", "positive": "+Dir",
                          "negative": "-Dir", "random": "Random"}

            # Update summary line
            self.info_summary.config(
                text=f"Zoom: {zoom_labels.get(self.zoom_var.get(), '?')}    "
                     f"Pan H: {pan_labels.get(self.pan_h_var.get(), '?')}    "
                     f"V: {pan_labels.get(self.pan_v_var.get(), '?')}")

            # Update grid values (End in cyan)
            self.info_rows["Scale"][0].config(text=f"{start_s:.2f}")
            self.info_rows["Scale"][1].config(text=f"{end_s:.2f}")
            self.info_rows["Pan X"][0].config(text=f"{start_x:+.2f}")
            self.info_rows["Pan X"][1].config(text=f"{end_x:+.2f}")
            self.info_rows["Pan Y"][0].config(text=f"{start_y:+.2f}")
            self.info_rows["Pan Y"][1].config(text=f"{end_y:+.2f}")
        except (tk.TclError, ValueError):
            pass

    # File handling

    def _on_file_select(self, path):
        self._load_file(path, source="upload")

    def load_file(self, path, source="upload"):
        """Public method to load file (used by chaining from Tab 1)"""
        self.drop_zone.set_path(path)
        self._load_file(path, source)

    def _load_file(self, path, source="upload"):
        if not path.lower().endswith('.json'):
            messagebox.showwarning("Invalid File",
                                   "Only .json files are supported.")
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

        self.apply_btn.config(text=f"APPLY MOTION  ({self.clip_count} clips)  ->")

        if source == "chain":
            self.source_label.config(
                text="Loaded from Image Matching",
                fg=COLORS['primary'])
        else:
            self.source_label.config(text="")

        self.status_label.config(
            text=f"Ready - {self.clip_count} clips",
            fg=COLORS['success'])

    def _reset_motion(self):
        """Reset motion tab to initial state"""
        self.input_file = None
        self.clip_count = 0
        self.drop_zone._reset()
        self.source_label.config(text="")
        self.apply_btn.config(text="APPLY MOTION  ->")
        self.status_label.config(text="", fg=COLORS['text_secondary'])

    # Motion application

    def apply_motion(self):
        if not self.input_file:
            messagebox.showerror("Error", "Please select a file first.")
            return
        try:
            self.status_label.config(text="Processing...",
                                     fg=COLORS['warning'])
            self.update()
            self._create_backup()

            with open(self.input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = self._process_segments(data)

            with open(self.input_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.status_label.config(
                text=f"Applied to {count} clips",
                fg=COLORS['success'])
            messagebox.showinfo(
                "Success",
                f"Motion applied to {count} clips.\n"
                f"Backup saved in backups/ folder.")
        except Exception as e:
            self.status_label.config(text="Error", fg=COLORS['error'])
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
        
        # Convert UI % to Engine Scale (104 -> 1.04)
        ss = self.start_scale.get() / 100.0
        emin = self.end_scale_min.get() / 100.0
        emax = self.end_scale_max.get() / 100.0
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
# 7. Main Application
# ============================================================

class CapCutFactory:
    """Root application - manages tabs and shared state"""

    def __init__(self, root):
        self.root = root
        self.root.title("CapCut Factory")
        self.root.geometry("1200x750")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS['bg'])

        self.win32_drop_handler = None

        self._build_ui()
        self._init_drag_and_drop()

    def _build_ui(self):
        # Stitch Header: icon + FACTORY AUTOMATION + centered tab pills + settings
        header = tk.Frame(self.root, bg=COLORS['card'],
                          highlightthickness=1,
                          highlightbackground=COLORS['border'])
        header.pack(fill=tk.X)
        header_inner = tk.Frame(header, bg=COLORS['card'])
        header_inner.pack(fill=tk.X, padx=16, pady=8)

        # Left: Icon + Title
        title_area = tk.Frame(header_inner, bg=COLORS['card'])
        title_area.pack(side=tk.LEFT)

        icon_frame = tk.Frame(title_area, bg=COLORS['primary'],
                               width=32, height=32)
        icon_frame.pack(side=tk.LEFT, padx=(0, 8))
        icon_frame.pack_propagate(False)
        tk.Label(icon_frame, text="F",
                 font=('Segoe UI', 14, 'bold'),
                 bg=COLORS['primary'], fg='#FFFFFF').place(
            relx=0.5, rely=0.5, anchor=tk.CENTER)

        tk.Label(title_area, text="FACTORY",
                 font=('Segoe UI', 16, 'bold'),
                 bg=COLORS['card'], fg=COLORS['text_main']).pack(side=tk.LEFT)
        tk.Label(title_area, text=" AUTOMATION",
                 font=('Segoe UI', 16, 'bold'),
                 bg=COLORS['card'], fg=COLORS['primary']).pack(side=tk.LEFT)

        # Center: Tab pill buttons (custom, not ttk)
        tab_area = tk.Frame(header_inner, bg=COLORS['slate_800'])
        tab_area.pack(side=tk.LEFT, expand=True, padx=40)
        tab_inner = tk.Frame(tab_area, bg=COLORS['slate_800'])
        tab_inner.pack(padx=2, pady=2)

        self.tab_buttons = []
        for i, (icon, text) in enumerate([("I", "Image Matching"),
                                           ("M", "Motion Application")]):
            btn = tk.Button(
                tab_inner, text=f"  {text}  ",
                font=('Segoe UI', 10, 'bold'),
                relief=tk.FLAT, cursor='hand2',
                command=lambda idx=i: self._switch_tab(idx))
            btn.pack(side=tk.LEFT, padx=1)
            self.tab_buttons.append(btn)

        # Right: New Project button
        tk.Button(
            header_inner, text="New Project",
            font=('Segoe UI', 9),
            bg=COLORS['card'], fg=COLORS['text_secondary'],
            activebackground=COLORS['card'],
            activeforeground=COLORS['error'],
            relief=tk.FLAT, cursor='hand2',
            command=self._new_project).pack(side=tk.RIGHT, padx=(8, 0))

        # Content area - use plain frames instead of ttk.Notebook
        self.content_frame = tk.Frame(self.root, bg=COLORS['bg'])
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Hidden notebook for tab content management
        style = ttk.Style()
        style.theme_use('default')
        style.configure('Hidden.TNotebook', background=COLORS['bg'],
                        borderwidth=0)
        style.layout('Hidden.TNotebook.Tab', [])  # Hide tab bar

        self.notebook = ttk.Notebook(self.content_frame, style='Hidden.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Image Matching
        self.image_tab = ImageMatchingTab(
            self.notebook,
            on_chain_to_motion=self._chain_to_motion)
        self.notebook.add(self.image_tab, text="Image Matching")

        # Tab 2: Motion Application
        self.motion_tab = MotionTab(self.notebook)
        self.notebook.add(self.motion_tab, text="Motion Application")

        # Set initial tab state
        self._switch_tab(0)

    def _switch_tab(self, index):
        """Switch tab and update pill button styles"""
        self.notebook.select(index)
        for i, btn in enumerate(self.tab_buttons):
            if i == index:
                btn.config(bg=COLORS['primary'], fg='#FFFFFF',
                           activebackground=COLORS['primary_hover'],
                           activeforeground='#FFFFFF')
            else:
                btn.config(bg=COLORS['slate_800'], fg=COLORS['text_secondary'],
                           activebackground=COLORS['slate_800'],
                           activeforeground=COLORS['text_main'])

    def _new_project(self):
        """Reset both tabs"""
        self.image_tab._reset()
        self.motion_tab._reset_motion()
        self._switch_tab(0)

    def _chain_to_motion(self, draft_path):
        """Called by Tab 1 to send generated draft to Tab 2"""
        self._switch_tab(1)
        self.motion_tab.load_file(draft_path, source="chain")

    def _init_drag_and_drop(self):
        if DND_BACKEND == "tkinterdnd2":
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_dnd_drop)
        elif DND_BACKEND == "win32_native":
            self.win32_drop_handler = Win32DropHandler(
                self.root, self._on_native_drop)
            self.win32_drop_handler.enable()

    def _on_dnd_drop(self, event):
        path = event.data.strip('{}')
        self._route_drop(path)

    def _on_native_drop(self, path):
        self._route_drop(path)

    def _route_drop(self, path):
        """Route dropped file/folder to the active tab"""
        current = self.notebook.index(self.notebook.select())
        if current == 0:
            # Image Matching tab - determine if it's a project or image folder
            if os.path.isdir(path):
                draft_file = os.path.join(path, "draft_content.json")
                if os.path.isfile(draft_file):
                    self.image_tab.project_drop.set_path(path)
                    self.image_tab._on_project_folder(path)
                else:
                    self.image_tab.image_drop.set_path(path)
                    self.image_tab._on_image_folder(path)
            elif path.lower().endswith('.json'):
                # Treat as project folder (use parent dir)
                parent = os.path.dirname(path)
                self.image_tab.project_drop.set_path(parent)
                self.image_tab._on_project_folder(parent)
        elif current == 1:
            # Motion tab
            if path.lower().endswith('.json'):
                self.motion_tab.load_file(path)
            elif os.path.isdir(path):
                draft_file = os.path.join(path, "draft_content.json")
                if os.path.isfile(draft_file):
                    self.motion_tab.load_file(draft_file)


# ============================================================
# 8. Entry Point
# ============================================================

def main():
    root = TkinterDnD.Tk() if DND_BACKEND == "tkinterdnd2" else tk.Tk()
    CapCutFactory(root)
    root.mainloop()


if __name__ == "__main__":
    main()
