# Design: CapCut Factory - Tab-Based Integration

## 1. Architecture Design

### 1.1 Class Diagram
```
CapCutFactory (Root Window)
├── ttk.Notebook (Tab Container)
│   ├── ImageMatchingTab (Tab 1)
│   │   ├── DropZone x2 (project folder, image folder)
│   │   ├── MatchingTable (scrollable result list)
│   │   ├── SubtitleExtractor (logic)
│   │   ├── ImageIndexer (logic)
│   │   ├── TextMatcher (logic)
│   │   └── DraftGenerator (output)
│   │
│   └── MotionTab (Tab 2) [refactored existing]
│       ├── DropZone x1 (draft file)
│       ├── MotionCard selections
│       ├── AnimatedPreview
│       ├── MotionEngine (logic)
│       └── Settings panel
│
├── Win32DropHandler (shared DnD)
└── StatusBar (shared bottom bar)
```

### 1.2 Data Flow
```
[Tab 1: Image Matching]
  draft_content.json ──┐
                       ├──> SubtitleExtractor ──> subtitles[]
  image_folder/ ───────┤
                       └──> ImageIndexer ──> images{}
                                │
                                v
                          TextMatcher.match(subtitles, images)
                                │
                                v
                          MatchResult[] ──> MatchingTable (UI review)
                                │
                          [User edits/approves]
                                │
                                v
                          DraftGenerator.generate(draft, matchResults)
                                │
                                v
                          modified_draft_content.json
                                │
                        ────────┼──────────── [Optional Chain] ───>
                                │
[Tab 2: Motion Application]     v
  draft_content.json ──> MotionEngine.process()
  (from Tab 1 or upload)        │
                                v
                          draft_content_motion.json
```

---

## 2. Detailed Component Design

### 2.1 SubtitleExtractor

```python
class SubtitleExtractor:
    """Extract subtitle data from draft_content.json"""

    @staticmethod
    def extract(draft_data: dict) -> list[dict]:
        """
        Returns: [
            {
                "id": "segment_id",
                "text": "subtitle text (normalized)",
                "raw_text": "original text",
                "start": 0,          # ticks
                "duration": 3000000,  # ticks
                "track_index": 0,
                "segment_index": 0
            },
            ...
        ]

        Parsing path:
          draft_data["materials"]["texts"] -> each text item
            -> item["content"] (JSON string) -> parse -> extract text
          Cross-reference with tracks to get timing info:
            tracks[type=="text"].segments -> target_timerange
        """
```

**Subtitle text extraction logic**:
1. Navigate to `materials.texts[]`
2. For each text material, parse `content` field (JSON string inside JSON)
3. Extract actual text from nested structure: `content -> text` or `content -> styles -> text`
4. Cross-reference `material_id` with text track segments to get timing
5. Return ordered list by timeline position

### 2.2 ImageIndexer

```python
class ImageIndexer:
    """Scan image folder and index by extracted text"""

    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif'}

    @staticmethod
    def index(folder_path: str) -> dict:
        """
        Returns: {
            "normalized_text": {
                "filename": "Scene001_subtitle_text.jpg",
                "path": "C:/absolute/path/to/image.jpg",
                "raw_name": "Scene001_subtitle_text"
            },
            ...
        }

        Filename parsing:
          "Scene001_text_here.jpg" -> extract "text_here"
          "001_some subtitle.png" -> extract "some subtitle"
          Strip prefix pattern: digits + underscore or "SceneNNN_"
        """
```

**Filename parsing strategy**:
1. Strip file extension
2. Remove common prefixes: `SceneNNN_`, `NNN_`, `EP\d+_S\d+_`
3. Normalize remaining text (see TextMatcher)
4. Handle edge cases: multiple underscores, spaces, special characters

### 2.3 TextMatcher

```python
class TextMatcher:
    """Match subtitles to images using text normalization"""

    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalization rules:
        1. Unicode NFC normalization
        2. Strip whitespace (all types including \u3000)
        3. Remove punctuation (.,!?;:'"(){}[])
        4. Lowercase
        5. Remove common filler words (optional)
        """

    @staticmethod
    def match(subtitles: list, image_index: dict) -> list[dict]:
        """
        Returns: [
            {
                "subtitle": subtitle_dict,
                "image": image_dict or None,
                "status": "matched" | "unmatched",
                "confidence": 1.0 | 0.0,
                "match_type": "exact" | "contains" | "none"
            },
            ...
        ]

        Matching strategy (in priority order):
        1. Exact match: normalized(subtitle) == normalized(image_text)
        2. Contains match: normalized(subtitle) in normalized(image_text)
           OR normalized(image_text) in normalized(subtitle)
        3. No match: mark as unmatched
        """
```

### 2.4 DraftGenerator

```python
class DraftGenerator:
    """Generate modified draft_content.json with matched images"""

    @staticmethod
    def generate(draft_data: dict, match_results: list,
                 image_folder: str) -> dict:
        """
        Steps:
        1. Find template material from existing materials.videos[0]
        2. For each matched result:
           a. Clone template material, update with image info
           b. Register in materials.videos with new UUID
           c. Create video segment with subtitle timing
        3. Replace/create video track segments
        4. Fill gaps between segments (extend duration)
        5. Return modified draft_data (deep copy)
        """
```

### 2.5 DropZone Widget (Reusable)

```python
class DropZone(tk.Frame):
    """Reusable drag & drop zone for file/folder selection"""

    def __init__(self, parent, label, description, mode="file"|"folder",
                 file_types=None, on_select=callable, **kwargs):
        """
        mode="file": single file selection (for .json)
        mode="folder": folder selection (for image folder)
        file_types: [("JSON", "*.json")] for file mode

        States:
        - empty: shows "+" icon and instructions
        - loaded: shows filename/foldername + "Delete" button
        - error: shows error message in red
        """
```

### 2.6 MatchingTable Widget

```python
class MatchingTable(tk.Frame):
    """Scrollable table showing subtitle-image matching results"""

    def __init__(self, parent, **kwargs):
        """
        Columns:
        [#] [Subtitle Text] [Matched Image] [Status]

        Features:
        - Scrollable (tk.Canvas + scrollbar)
        - Color-coded rows: green=matched, red=unmatched
        - Click unmatched row -> dropdown to manually assign image
        - Summary header: "N/M matched (X%)"
        - "DELETE ALL" button to reset
        """

    def update_results(self, match_results: list):
        """Populate table with match results"""

    def get_final_results(self) -> list:
        """Return results including manual overrides"""
```

### 2.7 ImageMatchingTab

```python
class ImageMatchingTab(tk.Frame):
    """Tab 1: Complete image matching workflow"""

    def __init__(self, parent, on_chain_to_motion: callable, colors: dict):
        """
        Layout:
        ┌─────────────────────────────────────────────────┐
        │ [DropZone: CapCut Project Folder]                │
        │ [DropZone: Image Folder]                         │
        ├─────────────────────────────────────────────────┤
        │ Matching Results: 45/50 matched (90%)            │
        │ ┌───┬──────────────┬───────────────┬──────┐     │
        │ │ # │ Subtitle     │ Image         │Status│     │
        │ ├───┼──────────────┼───────────────┼──────┤     │
        │ │ 1 │ "안녕하세요" │ S001_안녕.jpg │  ✓   │     │
        │ │ 2 │ "감사합니다" │ (unmatched)   │  ✗   │     │
        │ └───┴──────────────┴───────────────┴──────┘     │
        ├─────────────────────────────────────────────────┤
        │ [GENERATE PROJECT]  [Apply Motion ->]            │
        │ [NEW PROJECT]                                    │
        └─────────────────────────────────────────────────┘
        """
```

### 2.8 MotionTab

```python
class MotionTab(tk.Frame):
    """Tab 2: Refactored from existing CapCutMotionStudio"""

    def __init__(self, parent, colors: dict):
        """
        Same layout as current CapCutMotionStudio but:
        - Wrapped in tk.Frame (not root window)
        - DropZone widget replaces custom drop zone
        - Accepts external file loading via load_file(path)
        - Shows "Loaded from Image Matching" badge when chained
        """

    def load_file(self, path: str, source: str = "upload"):
        """Load draft file, source can be "upload" or "chain" """
```

### 2.9 CapCutFactory (Root)

```python
class CapCutFactory:
    """Main application - manages tabs and shared state"""

    def __init__(self, root):
        """
        - Window: 1200x750 (wider for tab content)
        - Header: "CapCut Factory" title
        - ttk.Notebook with 2 tabs
        - StatusBar at bottom
        - DnD handler on root window
        """

    def _chain_to_motion(self, draft_path: str):
        """Called by Tab 1 to send output to Tab 2"""
        self.notebook.select(1)  # Switch to Tab 2
        self.motion_tab.load_file(draft_path, source="chain")
```

---

## 3. UI Design Specification

### 3.1 Color Palette (Dark Theme - consistent with existing)
```python
COLORS = {
    'bg': '#121212',
    'card': '#1E1E1E',
    'border': '#2A2A2A',
    'primary': '#3B82F6',       # Blue - main actions
    'primary_hover': '#2563EB',
    'success': '#10B981',       # Green - matched/complete
    'warning': '#F59E0B',       # Orange - processing
    'error': '#EF4444',         # Red - unmatched/failed
    'mint': '#00C4A9',          # Mint - generate (per spec)
    'text_main': '#F1F1F1',
    'text_secondary': '#9CA3AF',
    'drop_zone': '#1A1A2E',
    'drop_zone_border': '#3B82F6',
    'tab_active': '#1E1E1E',
    'tab_inactive': '#121212',
}
```

### 3.2 Window Layout
```
1200 x 750px

┌──────────────────────────────────────────────────┐
│  CapCut Factory                                   │  Header (40px)
├──────────────────┬───────────────────────────────┤
│ [Image Matching] │ [Motion Application]           │  Tab Bar (35px)
├──────────────────┴───────────────────────────────┤
│                                                   │
│  (Tab Content Area - 620px height)                │
│                                                   │
├──────────────────────────────────────────────────┤
│  Status Bar                                       │  Status (25px)
└──────────────────────────────────────────────────┘
```

### 3.3 Tab 1 Detail Layout
```
┌───────────────────────────────────────────────────┐
│  Left Panel (55%)          │  Right Panel (45%)    │
│                            │                       │
│  [CapCut Project Folder]   │  Matching Results     │
│  ┌────────────────────┐    │  45/50 (90%)          │
│  │  + Drop folder     │    │  ┌─────────────────┐  │
│  └────────────────────┘    │  │ # │ Text │ Image │  │
│                            │  │ 1 │ ...  │ ...   │  │
│  [Image Folder]            │  │ 2 │ ...  │ ...   │  │
│  ┌────────────────────┐    │  │ ...               │  │
│  │  + Drop folder     │    │  └─────────────────┘  │
│  └────────────────────┘    │                       │
│                            │  [DELETE ALL]          │
├────────────────────────────┴───────────────────────┤
│  [GENERATE PROJECT]            [Apply Motion ->]    │
│  [NEW PROJECT]                                      │
└────────────────────────────────────────────────────┘
```

---

## 4. Data Structure Reference

### 4.1 CapCut draft_content.json - Subtitle Location
```json
{
  "materials": {
    "texts": [
      {
        "id": "TEXT_MATERIAL_ID",
        "content": "{\"styles\":[{\"range\":[0,5],\"font\":{...}}],\"text\":\"subtitle text here\"}",
        "type": "subtitle"
      }
    ],
    "videos": [
      {
        "id": "EXISTING_IMAGE_MATERIAL_ID",
        "path": "C:\\path\\to\\image.jpg",
        "material_name": "image.jpg"
      }
    ]
  },
  "tracks": [
    {
      "type": "text",
      "segments": [
        {
          "material_id": "TEXT_MATERIAL_ID",
          "target_timerange": { "start": 0, "duration": 3000000 }
        }
      ]
    },
    {
      "type": "video",
      "segments": [...]
    }
  ]
}
```

### 4.2 Match Result Data Structure
```python
MatchResult = {
    "index": int,                    # subtitle order
    "subtitle_id": str,              # material_id for timing reference
    "subtitle_text": str,            # display text
    "subtitle_start": int,           # ticks
    "subtitle_duration": int,        # ticks
    "image_path": str | None,        # absolute path if matched
    "image_filename": str | None,    # display name
    "status": "matched" | "unmatched" | "manual",
    "match_type": "exact" | "contains" | "manual" | None,
}
```

---

## 5. Implementation Order (Detailed)

### Phase 1: Foundation Refactoring
1. Create `capcut_factory.py` (copy from `capcut_motion.py`)
2. Extract `DropZone` widget from existing drop zone code
3. Create `CapCutFactory` root class with `ttk.Notebook`
4. Wrap existing motion UI into `MotionTab(tk.Frame)`
5. Move `MotionEngine`, `MotionCard`, `AnimatedPreview` as-is
6. Style ttk.Notebook for dark theme
7. **Verify**: Existing motion functionality works as Tab 2

### Phase 2: Image Matching Engine
8. Implement `SubtitleExtractor.extract()` with error handling
9. Implement `ImageIndexer.index()` with Korean filename support
10. Implement `TextMatcher.normalize()` and `TextMatcher.match()`
11. Implement `DraftGenerator.generate()` using template material approach
12. **Verify**: Engine correctly processes real CapCut draft files

### Phase 3: Image Matching UI
13. Build `ImageMatchingTab` layout (two DropZones + action buttons)
14. Implement `MatchingTable` with scrollable results
15. Wire up: folder selection -> auto matching -> table update
16. Add manual reassignment UI (combobox in unmatched rows)
17. Implement GENERATE button logic
18. Implement NEW PROJECT reset
19. **Verify**: Full matching workflow works

### Phase 4: Integration
20. Implement chain button ("Apply Motion ->")
21. Wire `_chain_to_motion()` to switch tab and load file
22. Add "Loaded from Image Matching" badge in Tab 2
23. End-to-end test: Tab 1 -> Generate -> Chain -> Tab 2 -> Apply
24. Update `build.bat` for `capcut_factory.py`
25. Final testing with real CapCut projects

---

## 6. Error Handling Strategy

| Scenario | Handling |
|----------|----------|
| Invalid folder (no draft_content.json) | Show error in DropZone, prevent matching |
| JSON parse error | Show specific error message, don't crash |
| No subtitles found in draft | Warning message, empty table |
| No images in folder | Warning message, all unmatched |
| 0% match rate | Allow generate anyway (user may manually assign) |
| Image file not found during generate | Skip with warning, continue |
| Korean encoding issues | Try utf-8, fallback utf-8-sig, fallback cp949 |
