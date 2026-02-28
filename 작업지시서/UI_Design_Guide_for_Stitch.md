# CapCut Factory - UI Design Guide (Google Stitch)

> 구글 스티치에서 UI 디자인 작업 시 참고하는 기능/화면/컴포넌트 명세서

---

## 1. 앱 개요

| 항목 | 내용 |
|------|------|
| 앱 이름 | **CapCut Factory** |
| 타입 | 데스크톱 앱 (Windows) |
| 창 크기 | **1200 x 750px** (고정) |
| 테마 | **Dark Mode** |
| 탭 구성 | Tab 1: Image Matching / Tab 2: Motion Application |
| 주요 사용자 | 영상 편집자 (CapCut 사용자) |

---

## 2. Color System

### 2.1 기본 컬러

| 용도 | Color | Hex | 사용처 |
|------|-------|-----|--------|
| Background | 매우 짙은 회색 | `#121212` | 앱 전체 배경 |
| Card / Panel | 짙은 회색 | `#1E1E1E` | 카드, 패널, 섹션 배경 |
| Border | 회색 | `#2A2A2A` | 카드 테두리, 구분선 |
| Drop Zone | 남색 계열 | `#1A1A2E` | 파일 드롭 영역 배경 |
| Drop Zone Hover | 밝은 남색 | `#1E2A4A` | 드롭 영역 호버 |

### 2.2 액센트 컬러

| 용도 | Color | Hex | 사용처 |
|------|-------|-----|--------|
| Primary (Blue) | 파란색 | `#3B82F6` | 탭 활성, 모션 적용 버튼, 드롭존 테두리 |
| Primary Hover | 진파란 | `#2563EB` | 파란 버튼 호버 |
| Mint / Generate | 민트 | `#00C4A9` | GENERATE 버튼, 체이닝 소스 표시 |
| Mint Hover | 진민트 | `#00A88E` | 민트 버튼 호버 |
| Success | 초록 | `#10B981` | 매칭 성공, 파일 로드 완료 |
| Warning | 주황 | `#F59E0B` | 처리 중, 부분 매칭 |
| Error / Delete | 빨강 | `#EF4444` | 매칭 실패, DELETE 버튼, NEW PROJECT |

### 2.3 텍스트 컬러

| 용도 | Hex | 사용처 |
|------|-----|--------|
| Main Text | `#F1F1F1` | 제목, 본문, 파일명 |
| Secondary Text | `#9CA3AF` | 설명문, 라벨, 비활성 텍스트 |
| White | `#FFFFFF` | 버튼 텍스트, 활성 탭 텍스트 |

---

## 3. Typography

| 용도 | Font | Size | Weight |
|------|------|------|--------|
| 앱 타이틀 | Segoe UI | 20px | Bold |
| 섹션 타이틀 | Segoe UI | 12px | Bold |
| 탭 이름 | Segoe UI | 11px | Bold |
| 본문 / 라벨 | Segoe UI | 10px | Regular |
| 버튼 (대) | Segoe UI | 12px | Bold |
| 버튼 (소) | Segoe UI | 10px | Regular |
| 설명 텍스트 | Segoe UI | 8-9px | Regular |
| 프리뷰 정보 | Consolas (모노) | 9px | Regular |
| 상태바 | Segoe UI | 8px | Regular |

---

## 4. 전체 레이아웃 구조

```
┌──────────────────────────────────────────────────────────┐
│  CAPCUT FACTORY                                    [v1.0]│ Header  40px
├────────────────────┬─────────────────────────────────────┤
│ [Image Matching]   │ [Motion Application]                │ Tab Bar 35px
├────────────────────┴─────────────────────────────────────┤
│                                                          │
│              Tab Content Area                            │ 620px
│              (각 탭별 내용이 여기 표시)                      │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ CapCut Factory v1.0                    DnD: Windows Native│ Status Bar 25px
└──────────────────────────────────────────────────────────┘
```

### 4.1 Header (40px)
- 좌측: "CAPCUT FACTORY" 타이틀 (20px Bold, #F1F1F1)
- 배경: #121212

### 4.2 Tab Bar (35px)
- 비활성 탭: bg #1E1E1E, text #9CA3AF
- 활성 탭: bg #3B82F6, text #FFFFFF
- 호버 탭: bg #2A2A2A, text #F1F1F1
- 탭 패딩: 좌우 20px, 상하 8px

### 4.3 Status Bar (25px)
- 배경: #2A2A2A
- 좌측: "CapCut Factory v1.0"
- 우측: DnD 백엔드 상태

---

## 5. Tab 1: Image Matching (화면 상세)

### 5.1 전체 레이아웃

```
┌─────────────────────────────┬────────────────────────────────┐
│      Left Panel (50%)       │       Right Panel (50%)         │
│                             │                                 │
│  ┌───────────────────────┐  │  ┌───────────────────────────┐  │
│  │ CAPCUT PROJECT FOLDER │  │  │ Matching Results: 45/50   │  │
│  │ ┌───────────────────┐ │  │  │ (90%)          [DELETE ALL]│  │
│  │ │      +            │ │  │  ├───┬──────────┬──────┬─────┤  │
│  │ │ Drop folder here  │ │  │  │ # │ Subtitle │Image │ Sts │  │
│  │ └───────────────────┘ │  │  ├───┼──────────┼──────┼─────┤  │
│  └───────────────────────┘  │  │ 1 │ 안녕하세요│S001..│  O  │  │
│                             │  │ 2 │ 감사합니다│(unmtd)│  X  │  │
│  ┌───────────────────────┐  │  │ 3 │ 반갑습니다│S003..│  O  │  │
│  │ IMAGE FOLDER          │  │  │ . │ ...      │ ...  │ ... │  │
│  │ ┌───────────────────┐ │  │  │ . │ ...      │ ...  │ ... │  │
│  │ │      +            │ │  │  └───┴──────────┴──────┴─────┘  │
│  │ │ Drop folder here  │ │  │                                 │
│  │ └───────────────────┘ │  │                                 │
│  └───────────────────────┘  │                                 │
│                             │                                 │
│  Found 45 subtitles         │                                 │
├─────────────────────────────┴────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐│
│  │                   GENERATE PROJECT                       ││ Mint #00C4A9
│  └──────────────────────────────────────────────────────────┘│
│  [NEW PROJECT]                            [Apply Motion ->]  │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 컴포넌트: Drop Zone (재사용)

두 곳에서 동일 컴포넌트 사용 (프로젝트 폴더 / 이미지 폴더)

#### State 1: 비어있음 (Empty)
```
┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐
│  REQUIRED                              │  라벨: 9px Bold, #9CA3AF
│                                        │
│              +                         │  아이콘: 18px Bold, #9CA3AF
│   Drop CapCut project folder           │  설명: 8px, #9CA3AF
│   (must contain draft_content.json)    │
│                                        │
└─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘
배경: #1A1A2E / 테두리: #3B82F6 (2px dashed 느낌)
```

#### State 2: 호버 (Hover)
- 배경만 `#1E2A4A`로 변경
- 나머지 동일

#### State 3: 로드 완료 (Loaded)
```
┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐
│  REQUIRED                              │
│                                        │
│  📁 MyCapCutProject          [Delete]  │  폴더명: 9px Bold, #F1F1F1
│                                        │  Delete: 8px, bg #EF4444
└─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘
```

### 5.3 컴포넌트: Matching Table

#### 헤더 영역
```
┌────────────────────────────────────────────────────────┐
│ Matching Results: 45/50 (90%)           [DELETE ALL]   │
├────────────────────────────────────────────────────────┤
│  #  │     Subtitle      │      Image      │  Status   │  8px Bold, #9CA3AF
│─────┼────────────────────┼─────────────────┼──────────│  bg #2A2A2A
```

- 요약 텍스트 색상:
  - 80%+ 매칭: `#10B981` (초록)
  - 50~79% 매칭: `#F59E0B` (주황)
  - 50% 미만: `#EF4444` (빨강)
- DELETE ALL 버튼: bg #EF4444, text white, 8px

#### Row: 매칭 성공
```
│  1  │  안녕하세요         │ S001_안녕.jpg   │    O     │
```
- 배경: #1E1E1E
- Subtitle: #F1F1F1, 9px
- Image: #F1F1F1, 9px
- Status "O": #10B981 (초록), 9px Bold

#### Row: 매칭 실패
```
│  2  │  감사합니다         │ [▼ (unmatched)] │    X     │
```
- Image 칸에 **드롭다운 (Combobox)** 표시
  - 기본값: "(unmatched)"
  - 옵션: 이미지 폴더의 모든 이미지 파일명 목록
  - 사용자가 수동으로 이미지 선택 가능
- Status "X": #EF4444 (빨강), 9px Bold

#### 스크롤
- 테이블은 세로 스크롤 가능
- 스크롤바: 우측, 기본 OS 스타일
- 마우스 휠 지원

### 5.4 액션 버튼 영역

| 버튼 | 스타일 | 크기 | 조건 |
|------|--------|------|------|
| **GENERATE PROJECT** | Solid, bg #00C4A9, text white | Full width, 12px Bold, ipady 6px | 두 폴더 모두 로드 시 활성 |
| **NEW PROJECT** | Outline, border #EF4444, text #EF4444 | Auto width, 10px | 항상 활성 |
| **Apply Motion ->** | Solid, bg #3B82F6, text white | Auto width, 10px Bold | GENERATE 완료 후 활성 |

버튼 배치:
- GENERATE: 상단 전체 너비
- 하단 행: NEW PROJECT (좌측) / Apply Motion -> (우측)

### 5.5 상태 메시지

Drop Zone 아래에 표시되는 한줄 상태:

| 상태 | 텍스트 | 색상 |
|------|--------|------|
| 자막 추출 완료 | "Found 45 subtitles" | #10B981 |
| 이미지 스캔 완료 | "Found 120 images" | #10B981 |
| 매칭 완료 | "45/50 subtitles matched" | #10B981 또는 #F59E0B |
| 생성 중 | "Generating..." | #F59E0B |
| 생성 완료 | "Generated! 45 images placed. Backup saved as .bak" | #10B981 |
| 에러 | "Error: draft_content.json not found" | #EF4444 |

---

## 6. Tab 2: Motion Application (화면 상세)

### 6.1 전체 레이아웃

```
┌──────────────────────────────────────────────────────────┐
│  ┌──────────────────────────────────────────────────────┐│
│  │ DRAFT FILE                                           ││ Drop Zone
│  │      + Drop draft_content.json or click to browse    ││
│  └──────────────────────────────────────────────────────┘│
│  Loaded from Image Matching                              │ (체이닝 시)
├──────────────────────────────┬───────────────────────────┤
│      Left Panel (55%)        │    Right Panel (45%)       │
│                              │                            │
│  Zoom                        │  Motion Preview            │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐│  ┌────────────────────┐   │
│  │None│ │ In │ │Out │ │Rand││  │                    │   │
│  └────┘ └────┘ └────┘ └────┘│  │    [16:9 Frame]    │   │
│                              │  │    + Grid BG       │   │
│  Pan                         │  │    + Moving Rect   │   │
│  H ┌────┐┌────┐┌────┐┌────┐ │  │                    │   │
│    │None││L>R ││R>L ││Rand│ │  └────────────────────┘   │
│    └────┘└────┘└────┘└────┘ │                            │
│  V ┌────┐┌────┐┌────┐┌────┐ │  Zoom: Zoom In            │
│    │None││T>B ││B>T ││Rand│ │  Pan H: Random  V: Random │
│    └────┘└────┘└────┘└────┘ │  ════════════════════════  │
│                              │       Start     End       │
│  Settings                    │  Scale  1.0400  1.0900    │
│  Start Scale    [1.04  ]     │  Pan X  +0.0000 +0.0300   │
│  End Scale      [1.08] ~ [1.10]│Pan Y  +0.0000 -0.0200   │
│  Pan Strength   [0.05 ] +/-  │                            │
├──────────────────────────────┴───────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐│
│  │           Apply Motion to 45 Clips                   ││ Blue #3B82F6
│  └──────────────────────────────────────────────────────┘│
│  Ready - 45 clips                                        │
└──────────────────────────────────────────────────────────┘
```

### 6.2 컴포넌트: Motion Card (선택 카드)

#### 크기 & 레이아웃
- 85 x 62px 고정
- 아이콘 (14px) + 타이틀 (8px Bold) 수직 배치

#### State: Normal
```
┌──────────┐
│   아이콘   │  bg: #1E1E1E
│   타이틀   │  border: #2A2A2A (2px)
└──────────┘  text: #F1F1F1
```

#### State: Hover
- bg: #252525
- border 동일

#### State: Selected
```
┌──────────┐
│   아이콘   │  bg: #1E1E1E
│   타이틀   │  border: #3B82F6 (3px) ← 파란 테두리 강조
└──────────┘
```

#### Zoom 카드 목록
| 아이콘 | 타이틀 | 값 |
|--------|--------|-----|
| -- | None | none |
| ZI | In | zoom_in (기본 선택) |
| ZO | Out | zoom_out |
| RD | Random | zoom_random |

#### Pan H 카드 목록
| 아이콘 | 타이틀 | 값 |
|--------|--------|-----|
| -- | None | none |
| -> | L>R | positive |
| <- | R>L | negative |
| RD | Rand | random (기본 선택) |

#### Pan V 카드 목록
| 아이콘 | 타이틀 | 값 |
|--------|--------|-----|
| -- | None | none |
| v | T>B | positive |
| ^ | B>T | negative |
| RD | Rand | random (기본 선택) |

### 6.3 컴포넌트: Settings Panel

| 설정 | 기본값 | 입력 형태 |
|------|--------|----------|
| Start Scale | 1.04 | 숫자 입력 (width 7) |
| End Scale | 1.08 ~ 1.10 | 숫자 입력 x2 + "~" 구분자 |
| Pan Strength | 0.05 | 숫자 입력 + "+/-" 표시 |

- 입력 필드: bg #252525, text #F1F1F1, flat border
- 라벨: 10px, #F1F1F1, width 14 고정

### 6.4 컴포넌트: Animated Preview

- Canvas 크기: 330 x 200px
- 배경: #0D0D0D (거의 검정)
- 격자: #1A1A1A (40px 간격)
- 16:9 프레임: 흰색 테두리 2px
- 십자선: #333333 (점선)
- 이동하는 사각형: #3B82F6 테두리 2px (점선)
- 프레임 비율: 캔버스의 55%
- 좌상단 "16:9" 텍스트: #555555, Consolas 7px

### 6.5 체이닝 소스 표시

Tab 1에서 넘어온 경우:
```
Loaded from Image Matching
```
- 폰트: 9px Italic
- 색상: #00C4A9 (민트)
- 위치: Drop Zone 바로 아래

---

## 7. 인터랙션 Flow

### 7.1 Flow A: 이미지 매칭만 사용

```
[앱 실행]
  │
  ▼
Tab 1 활성 (기본)
  │
  ├─ 프로젝트 폴더 드롭/선택
  │    └─ draft_content.json 검증
  │    └─ 자막 추출 → 상태 표시 "Found N subtitles"
  │
  ├─ 이미지 폴더 드롭/선택
  │    └─ 이미지 스캔 → 상태 표시 "Found N images"
  │    └─ [자동] 매칭 실행 → 테이블에 결과 표시
  │
  ├─ (선택) 매칭 실패 항목 수동 재지정
  │    └─ 드롭다운에서 이미지 선택
  │
  ├─ [GENERATE PROJECT] 클릭
  │    └─ 백업 생성 (.bak)
  │    └─ 수정된 draft_content.json 저장
  │    └─ 완료 메시지 + "Apply Motion ->" 활성화
  │
  └─ 끝 (또는 NEW PROJECT로 리셋)
```

### 7.2 Flow B: 이미지 매칭 + 모션 적용 (체이닝)

```
[Flow A 완료 후]
  │
  ├─ [Apply Motion ->] 클릭
  │    └─ 자동으로 Tab 2로 전환
  │    └─ 생성된 draft_content.json 자동 로드
  │    └─ "Loaded from Image Matching" 표시
  │
  ├─ Zoom / Pan / Settings 설정
  │    └─ 프리뷰에서 실시간 미리보기
  │
  ├─ [Apply Motion to N Clips] 클릭
  │    └─ 백업 생성
  │    └─ _motion.json 저장
  │    └─ 완료 메시지
  │
  └─ 끝
```

### 7.3 Flow C: 모션만 사용

```
[앱 실행]
  │
  ├─ Tab 2 클릭 (직접 이동)
  │
  ├─ JSON 파일 드롭/선택
  │    └─ 파일 검증 → "Ready - N clips"
  │
  ├─ 설정 조정 → 프리뷰 확인
  │
  ├─ [Apply Motion] 클릭
  │
  └─ 끝
```

---

## 8. 상태별 UI 변화 정리

### 8.1 Tab 1 버튼 활성화 조건

| 버튼 | 조건 | 비활성 스타일 |
|------|------|-------------|
| GENERATE PROJECT | 두 폴더 모두 로드됨 | opacity 50%, 클릭 불가 |
| Apply Motion -> | GENERATE 완료 후 | opacity 50%, 클릭 불가 |
| NEW PROJECT | 항상 활성 | - |
| DELETE ALL | 테이블에 결과 있을 때 | 결과 없으면 숨김 |

### 8.2 Drop Zone 상태 전이

```
Empty  ──(클릭/드롭)──>  Loaded
  ^                        │
  └───(Delete 클릭)────────┘
```

### 8.3 매칭 테이블 상태 전이

```
빈 테이블  ──(두 폴더 로드)──>  자동 매칭 결과 표시
                                    │
                               (수동 재지정)
                                    │
                               결과 업데이트
                                    │
                            (DELETE ALL)──> 빈 테이블
```

---

## 9. 디자인 시 주의사항

### 9.1 반응형 아님
- 1200x750 고정 사이즈, 리사이즈 불가
- 모바일/태블릿 고려 불필요

### 9.2 다크 테마 일관성
- 모든 배경은 #121212 ~ #1E1E1E 범위
- 밝은 요소는 텍스트와 아이콘만
- 흰 배경 요소 절대 없음

### 9.3 텍스트 길이 처리
- 자막 텍스트: 최대 22자 표시, 초과 시 "..." 처리
- 파일명: 최대 40자 표시, 초과 시 "..." 처리
- 폴더명: 최대 40자

### 9.4 한글 지원
- 모든 텍스트 영역에서 한글 표시 필수
- 파일명, 자막, 폴더명 모두 한글 가능
- 영문/한글 혼합 표시 지원

### 9.5 컴포넌트 간격 기준
- 섹션 간: 6~12px
- 카드 간: 6px
- 패딩 (카드 내부): 8~12px
- 버튼 하단 여백: 6~12px

---

## 10. 디자인해야 할 화면 목록 (Stitch Frames)

| # | Frame 이름 | 설명 |
|---|-----------|------|
| 1 | **App Shell** | 전체 윈도우 + Header + Tab Bar + Status Bar |
| 2 | **Tab1 - Empty** | 두 Drop Zone 비어있는 초기 상태 |
| 3 | **Tab1 - Folders Loaded** | 두 폴더 로드 완료 + 매칭 결과 테이블 표시 |
| 4 | **Tab1 - Partial Match** | 일부 매칭 실패 + 드롭다운 수동 재지정 열린 상태 |
| 5 | **Tab1 - Generate Complete** | 생성 완료 + "Apply Motion ->" 활성 상태 |
| 6 | **Tab2 - Empty** | Drop Zone 비어있는 초기 상태 |
| 7 | **Tab2 - File Loaded** | 파일 로드됨 + 설정 패널 + 프리뷰 |
| 8 | **Tab2 - Chained** | Tab1에서 넘어온 상태 ("Loaded from Image Matching" 표시) |
| 9 | **Tab2 - Motion Applied** | 적용 완료 + 성공 메시지 |
| 10 | **Components** | DropZone(3 states), MotionCard(3 states), MatchingRow(2 types) |
