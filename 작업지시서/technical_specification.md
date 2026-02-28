# CapCut 컷편집 자동화 기능 기술 명세서 (Technical Specification)

본 문서는 사용자가 제공한 CapCut 프로젝트 폴더(`draft_content.json` 포함)와 이미지 폴더를 기반으로, 자막 내용에 맞춰 이미지를 자동으로 타임라인에 배치하는 기능의 구현 명세를 다룹니다.

## 1. 개요 (Overview)
*   **목표**: 기존 수작업으로 진행하던 "자막 내용 확인 -> 맞는 이미지 검색 -> 타임라인 배치 -> 길이 조절" 과정을 **완전 자동화**.
*   **핵심 기능**:
    1.  CapCut 프로젝트 파일(`draft_content.json`) 내부의 숨겨진 자막 데이터 추출.
    2.  이미지 파일명에 포함된 대사 텍스트 파싱.
    3.  자막과 이미지를 텍스트 기반으로 매칭.
    4.  타임라인에 이미지 클립 생성 및 배치 (빈 공간 채우기 포함).
*   **전제 조건**:
    *   CapCut 프로젝트에 자막(Text) 트랙이 생성되어 있어야 함.
    *   이미지 파일명에 자막 내용(대사)이 포함되어 있어야 함 (예: `Scene001_내용.jpg`).
    *   CapCut에 임의의 이미지 1장이 "미디어(Materials)"에 등록되어 있을 것 (템플릿 용도).

---

## 2. 입력 데이터 (Input Data)
1.  **CapCut 프로젝트 폴더 경로**: `draft_content.json` 파일이 위치한 디렉토리.
2.  **이미지 소스 폴더 경로**: 타임라인에 삽입할 이미지 파일들이 모여 있는 디렉토리.

---

## 3. 프로세스 로직 (Process Logic)

UI 워크플로우에 맞춰 **1단계: 분석 및 매칭 (Preview)**과 **2단계: 생성 (Generation)**으로 분리하여 구현해야 합니다.

### 3.1. 1단계: 분석 및 매칭 (Preview Phase)
사용자가 폴더를 업로드했을 때 실행되며, 실제 파일을 변경하지 않고 매칭 결과만 시뮬레이션하여 UI에 표시합니다.

1.  **자막 데이터 추출 (Text Extraction)**:
    *   `draft_content.json` 로드.
    *   `materials` -> `texts`에서 자막 텍스트 파싱 및 정규화.
2.  **이미지 인덱싱 (Image Indexing)**:
    *   이미지 폴더 스캔.
    *   파일명에서 대사 추출 및 정규화.
3.  **매칭 시뮬레이션 (Matching Simulation)**:
    *   자막 리스트를 순회하며 이미지 맵과 대조.
    *   **결과 반환**: 매칭 성공 여부, 매칭된 이미지 파일명, 실패 시 사유 리스트 반환 (UI 표시용).

### 3.2. 2단계: 프로젝트 생성 (Generation Phase)
사용자가 [GENERATE PROJECT] 버튼을 클릭했을 때 실행됩니다.

1.  **백업 생성**: `draft_content.json.bak` 생성.
2.  **Materials 등록**:
    *   매칭된 이미지들을 `materials` -> `videos`에 등록 (UUID 발급).
3.  **타임라인 배치 (Timeline Placement)**:
    *   `video` 트랙의 세그먼트를 재구성.
    *   매칭된 이미지를 자막 타이밍(`target_timerange`)에 맞춰 배치.
4.  **빈 공간 채우기 (Gap Filling)**:
    *   각 세그먼트의 길이를 다음 세그먼트 시작점까지 연장하여 공백 제거.
5.  **저장**: 수정된 JSON 파일 저장.

---

## 4. UI/UX 디자인 가이드 (UI/UX Guidelines)
사용자가 제공한 레퍼런스 이미지(CapCut Factory)를 기반으로 한 디자인 및 인터랙션 명세입니다.

### 4.1. 전체 레이아웃 (Layout)
*   **테마**: 다크 모드 (Dark Theme) 기반.
    *   배경: 짙은 회색 (`#1E1E1E` ~ `#2D2D2D`).
    *   포인트 컬러: 민트/청록색 (`#00C4A9`, `#00E0C7`) - 완료 및 긍정적 액션.
    *   강조/삭제 컬러: 핑크/레드 (`#FF4D4D`, `#FF6B6B`) - 취소 및 초기화 액션.
*   **헤더**: "CAPCUT FACTORY" 타이틀과 Client/Lang 스위치 배치.

### 4.2. 입력 영역 (Input Area) -> 2단 구성
1.  **CapCut Project Folder 업로드 영역**
    *   **UI**: 점선 테두리의 드래그 앤 드롭 영역 + 중앙 `+` 버튼.
    *   **라벨**: "CAPCUT PROJECT FOLDER" (REQUIRED).
    *   **설명**: "The CapCut Project must contain at least one image" (템플릿용 이미지 필수 안내).
    *   **동작**: 폴더 선택 시 `draft_content.json` 파일 유효성 검사 수행.
    *   **상태 표시**: 업로드 후 폴더명 표시 및 "Delete" 버튼 활성화.

2.  **Image Folder 업로드 영역**
    *   **UI**: 상단 프로젝트 폴더 영역과 동일한 스타일.
    *   **라벨**: "IMAGE FOLDER" (REQUIRED).
    *   **설명**: "Image filenames must contain the subtitle text for matching".
    *   **동작**: 폴더 선택 시 이미지 파일 리스트 로딩.

### 4.3. 매칭 상태 및 리스트 (Matching Status List)
*   **위치**: 이미지 폴더 업로드 영역 하단.
*   **기능**: 자막 매칭 시뮬레이션 결과 실시간 표시.
*   **아이템 표시**:
    *   성공: `[아이콘] 파일명.jpg` (흰색 텍스트).
    *   실패: `MATCH FAILED: 파일명.jpg` (붉은색 텍스트) - 매칭되지 않은 사유 표시 (예: 텍스트 불일치).
*   **요약 정보**: "... AND 129 MORE FILES" 형태로 리스트 축약 표시.
*   **초기화**: "DELETE ALL" 버튼으로 리스트 비우기 기능.

### 4.4. 액션 버튼 (Action Buttons)
*   **GENERATE PROJECT (생성)**:
    *   스타일: 넓은 너비, 민트색 솔리드 버튼.
    *   기능: 실제 `draft_content.json` 수정 및 결과 파일 생성 로직 실행.
    *   활성화 조건: 두 폴더가 모두 로드되고 유효할 때.
*   **NEW PROJECT (초기화)**:
    *   스타일: 넓은 너비, 붉은색/핑크색 아웃라인 버튼.
    *   기능: 모든 입력 상태 초기화.

### 4.5. 완료 화면 (Completion Screen)
*   **메시지**: "GENERATION COMPLETE!"
*   **안내**: "Copy draft_content.json to your CapCut project folder".
*   **다운로드 버튼**: "JSON DOWNLOAD" (수정된 `draft_content.json` 다운로드).

---

## 5. 데이터 구조 명세 (Data Structure Specs)

### 5.1. Material (Image) 템플릿
이미지를 `materials['videos']`에 추가할 때 사용하는 기본 구조입니다. CapCut 버전에 따라 필드가 다를 수 있으므로, **기존에 포함된 샘플 이미지를 복사하여 사용하는 것이 가장 안전**합니다.

```json
{
  "id": "UUID_V4_STRING",
  "type": 0,  // 0: Video/Image (Context dependent)
  "category_name": "local",
  "material_name": "FILENAME.jpg",
  "path": "ABSOLUTE_PATH\\TO\\IMAGE.jpg",
  "width": 0,   // 자동 감지
  "height": 0,  // 자동 감지
  "duration": 10800000000, // 충분히 긴 시간 (혹은 0)
  "source_platform": 0
}
```

### 5.2. Video Segment 구조
타임라인 트랙(`tracks[i]['segments']`)에 들어갈 객체입니다.

```json
{
  "id": "UUID_V4_STRING",
  "material_id": "LINKED_IMAGE_MATERIAL_ID",
  "source_timerange": {
    "start": 0,
    "duration": DURATION_TICKS
  },
  "target_timerange": {
    "start": START_TICK,
    "duration": DURATION_TICKS
  },
  "render_timerange": { "start": 0, "duration": 0 },
  "visible": true,
  "speed": 1.0,
  "volume": 1.0
}
```
*   **Time Unit**: CapCut은 마이크로초 단위 혹은 독자적인 Ticks 단위를 사용합니다 (보통 1000000 scale). 원본 자막 세그먼트의 값을 그대로 사용하는 것이 안전합니다.

---


## 6. 구현 시 주의사항
1.  **UUID 생성**: 모든 ID(Material ID, Segment ID)는 고유한 UUID (Uppercase 권장)여야 합니다.
2.  **경로 처리**: Windows 환경의 경우 파일 경로의 백슬래시(`\`) 처리에 주의해야 합니다. Json dump 시 escape 처리가 필요합니다.
3.  **인코딩**: 한글 파일명 처리를 위해 반드시 파일 입출력 시 `utf-8` (혹은 `utf-8-sig`)을 명시해야 합니다.
4.  **자막 파싱 예외처리**: 자막의 `content` JSON 파싱 실패 시 프로그램이 멈추지 않도록 `try-catch` 처리가 필요합니다.
