# Plan: CapCut Factory - Tab-Based Integration

## 1. Feature Overview

### 1.1 Background
- **Current**: `capcut_motion.py` - standalone tkinter app that applies motion effects (zoom/pan) to CapCut `draft_content.json`
- **New requirement**: Image-to-subtitle matching feature (from `technical_specification.md`) - automatically places images on timeline based on subtitle text matching
- **Decision**: Tab-based integration (Option C) - two independent tabs in a single app with optional chaining

### 1.2 Goal
Single application "CapCut Factory" with two tabs:
1. **Tab 1 - Image Matching**: Upload draft + image folder -> subtitle extraction -> image-subtitle matching -> review/edit -> generate modified draft
2. **Tab 2 - Motion Application**: Upload draft (or auto-receive from Tab 1) -> configure motion -> apply -> download

### 1.3 Core Value
- Each tab works independently
- Optional chaining: Tab 1 output -> Tab 2 input (one-click)
- No duplicate uploads when using full workflow
- Clean separation of interactive review (Tab 1) vs batch processing (Tab 2)

---

## 2. Requirements

### 2.1 Functional Requirements

#### FR-01: Tab Navigation System
- ttk.Notebook or custom tab bar with 2 tabs
- Tab switching preserves state in each tab
- Dark theme consistent with existing design (#121212 bg)

#### FR-02: Image Matching Tab (Tab 1)
- **Input Area 1**: CapCut project folder upload (drag & drop or browse) - must contain `draft_content.json`
- **Input Area 2**: Image folder upload (drag & drop or browse)
- **Subtitle Extraction**: Parse `materials.texts` from draft_content.json, extract subtitle text with timing info
- **Image Indexing**: Scan image folder, parse filenames to extract subtitle text
- **Text Matching**: Normalize both sides -> fuzzy/exact match -> produce matching results
- **Matching Preview Table**: Show list of subtitles with matched/unmatched status
  - Each row: subtitle text | matched image filename | status (success/fail)
  - Failed matches highlighted in red
  - Manual re-assignment dropdown for failed matches
- **Generate Button**: Create modified draft_content.json with images placed on timeline
- **Chain Button**: "Apply Motion ->" sends generated draft to Tab 2

#### FR-03: Motion Application Tab (Tab 2) - Refactored Existing
- Preserve ALL existing functionality from capcut_motion.py
- Accept file from Tab 1 chain OR independent file upload
- Same zoom/pan card selection UI
- Same settings (start scale, end scale range, pan strength)
- Same animated preview
- Same apply logic with backup creation

#### FR-04: Tab Chaining
- After Tab 1 generates output, show "Apply Motion ->" button
- Clicking switches to Tab 2 with the generated draft auto-loaded
- Tab 2 shows "Loaded from Image Matching" indicator
- User can still override with their own file

#### FR-05: Backup & Output
- Tab 1: Creates `draft_content.json.bak` before modifying, outputs modified `draft_content.json`
- Tab 2: Creates timestamped backup, outputs `_motion.json` suffix
- Combined workflow: original -> image-matched -> motion-applied

### 2.2 Non-Functional Requirements

#### NFR-01: Performance
- Subtitle extraction < 2 seconds for typical project (100 subtitles)
- Image folder scanning < 3 seconds for 200+ images
- Matching computation < 1 second

#### NFR-02: Compatibility
- Python 3.7+ (same as current)
- Windows primary (CapCut is Windows-focused)
- tkinter only (no additional GUI framework dependencies)
- UTF-8/UTF-8-BOM support for Korean filenames

#### NFR-03: Single File Distribution
- Must build to single .exe with PyInstaller (like current build.bat)
- Target size < 15MB

---

## 3. Technical Analysis

### 3.1 Current Architecture (793 lines, single file)
```
capcut_motion.py
  Win32DropHandler     - Native drag & drop (Win32 API)
  MotionEngine         - Static motion computation methods
  MotionCard           - Custom selection widget
  AnimatedPreview      - Canvas animation widget
  CapCutMotionStudio   - Main app (UI + logic mixed)
  main()               - Entry point
```

### 3.2 Target Architecture (estimated ~1500 lines, single file)
```
capcut_factory.py
  # Shared Infrastructure
  Win32DropHandler         - (reuse) Native drag & drop
  MotionEngine             - (reuse) Motion computation
  MotionCard               - (reuse) Selection widget
  AnimatedPreview          - (reuse) Preview widget

  # NEW: Image Matching Engine
  SubtitleExtractor        - Parse draft_content.json texts
  ImageIndexer             - Scan image folder, parse filenames
  TextMatcher              - Normalize & match subtitle ↔ image

  # NEW: UI Components
  DropZone                 - Reusable folder/file drop zone widget
  MatchingTable            - Scrollable table showing match results

  # Tab Implementations
  ImageMatchingTab         - Tab 1: full matching workflow
  MotionTab                - Tab 2: refactored from CapCutMotionStudio

  # Main App
  CapCutFactory            - Root window + tab management + chaining
  main()
```

### 3.3 Key Technical Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Tab widget | `ttk.Notebook` | Built-in, reliable, dark-themeable |
| File structure | Single file | Consistency with current, simple PyInstaller build |
| Matching algorithm | Normalized text contains-match | Per spec: image filename contains subtitle text |
| Draft modification | In-memory JSON manipulation | Same approach as existing motion feature |
| State between tabs | Shared variable (file path) | Simple, no complex state management needed |

### 3.4 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Korean text normalization issues | Matching fails | Strip whitespace, normalize Unicode (NFC), case-insensitive |
| CapCut JSON structure varies by version | Parsing fails | Use try-catch, validate key fields exist |
| Large image folders slow down UI | UX degradation | Background scanning, progress indicator |
| ttk.Notebook dark theme styling | Visual inconsistency | Custom ttk.Style configuration |
| Window size increase needed for tabs | Layout issues | Increase to ~1200x750 |

---

## 4. Implementation Order

### Phase 1: Foundation (Refactoring)
1. Rename `capcut_motion.py` -> `capcut_factory.py`
2. Extract reusable widgets (DropZone, shared helpers)
3. Wrap existing motion UI into `MotionTab` class
4. Create `CapCutFactory` root with `ttk.Notebook`
5. Verify existing motion functionality still works in Tab 2

### Phase 2: Image Matching Engine (Backend)
6. Implement `SubtitleExtractor` - parse draft_content.json
7. Implement `ImageIndexer` - scan image folder, parse filenames
8. Implement `TextMatcher` - normalize + match logic
9. Implement draft modification (materials registration + timeline placement)

### Phase 3: Image Matching UI (Frontend)
10. Build `ImageMatchingTab` layout (two upload zones + matching table)
11. Implement matching preview table with status indicators
12. Add manual re-assignment for failed matches (optional dropdown)
13. Implement "Generate" button logic

### Phase 4: Integration & Chaining
14. Implement Tab 1 -> Tab 2 chaining ("Apply Motion ->" button)
15. Auto-load generated draft into Tab 2
16. End-to-end testing of full workflow
17. Update build.bat for new filename

---

## 5. Success Criteria

- [ ] Tab 1 correctly extracts subtitles from real CapCut draft_content.json
- [ ] Tab 1 matches images to subtitles with visual preview
- [ ] Tab 1 generates valid modified draft_content.json (can open in CapCut)
- [ ] Tab 2 preserves ALL existing motion functionality
- [ ] Tab chaining works: Tab 1 output -> Tab 2 auto-load
- [ ] Each tab works independently
- [ ] Single .exe build succeeds
- [ ] Korean filename/subtitle handling works correctly

---

## 6. Out of Scope
- Web-based UI (staying with tkinter desktop)
- AI-based image matching (text-based only per spec)
- Batch processing of multiple projects
- CapCut project creation from scratch (only modification)
