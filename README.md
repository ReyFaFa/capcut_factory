# CapCut 모션 자동화 도구

CapCut의 `draft_content.json` 파일을 직접 수정하여 모든 이미지/비디오 클립에 자동으로 모션 효과를 추가하는 도구입니다.

## 주요 기능

- 🎬 **자동 모션 적용**: 모든 비디오 세그먼트에 줌/이동 효과 자동 적용
- 🎨 **7가지 모션 패턴**: 기본 줌인, 줌인/줌아웃 랜덤, 방향별 이동, 중앙 줌
- 🖥️ **직관적인 GUI**: 간편한 파일 선택과 설정
- 💾 **자동 백업**: 원본 파일 자동 백업 기능
- ⚙️ **세밀한 설정**: 스케일, 이동 범위 커스터마이징
- 📦 **EXE 변환 지원**: PyInstaller로 단독 실행 파일 생성 가능

## 설치 방법

### 1. Python으로 실행 (권장)

```bash
# Python 3.7 이상 필요
python capcut_motion.py
```

### 2. EXE 파일로 빌드

```bash
# PyInstaller 설치
pip install pyinstaller

# EXE 빌드
build.bat
```

빌드 후 `dist/capcut_motion.exe` 파일이 생성됩니다.

## 사용 방법

### 1. CapCut 프로젝트 준비

1. CapCut에서 작업 중인 프로젝트를 **저장하고 종료**
2. CapCut 프로젝트 폴더 찾기:
   - Windows: `C:\Users\사용자명\AppData\Local\CapCut\User Data\Projects\`
   - 프로젝트 폴더 안의 `draft_content.json` 파일 확인

### 2. 도구 실행

1. `capcut_motion.py` 실행 (또는 `capcut_motion.exe`)
2. "파일 선택" 버튼 클릭하여 `draft_content.json` 선택
3. 원하는 모션 패턴 선택
4. 스케일/이동 범위 조정 (기본값 권장)
5. "모션 적용하기" 클릭

### 3. CapCut에서 확인

1. `draft_content_motion.json` 파일이 생성됨
2. 원본 파일 이름을 `draft_content_backup.json`으로 변경
3. `draft_content_motion.json`을 `draft_content.json`으로 이름 변경
4. CapCut 재실행하여 효과 확인

## 모션 패턴 설명

### 1. 기본 줌인
- 시작: 1.04배 스케일
- 끝: 1.08~1.10배 랜덤 스케일
- X/Y 랜덤 이동 (±0.05)

### 2. 줌인/줌아웃 랜덤
- 50% 확률로 줌인 또는 줌아웃
- 드라마틱한 효과

### 3. 좌→우 이동
- 왼쪽에서 오른쪽으로 이동하며 줌인

### 4. 우→좌 이동
- 오른쪽에서 왼쪽으로 이동하며 줌인

### 5. 상→하 이동
- 위에서 아래로 이동하며 줌인

### 6. 하→상 이동
- 아래에서 위로 이동하며 줌인

### 7. 중앙 줌 (확대만)
- 위치 이동 없이 중앙에서 확대만

## 설정 가이드

### 안정적인 값 (YouTube 스토리텔링)
- 시작 스케일: 1.04
- 끝 스케일: 1.08~1.09
- 이동 범위: ±0.03

### 드라마틱한 값
- 시작 스케일: 1.05
- 끝 스케일: 1.10~1.12
- 이동 범위: ±0.07

## 주의사항

⚠️ **반드시 CapCut을 종료한 후 실행하세요**
- CapCut이 실행 중이면 파일 변경이 적용되지 않습니다

⚠️ **백업을 권장합니다**
- 자동 백업 기능이 있지만, 중요한 프로젝트는 수동으로도 백업하세요

⚠️ **테스트 프로젝트로 먼저 시도**
- 처음 사용할 때는 테스트 프로젝트로 먼저 시도해보세요

## 파일 구조

```
capcut-motion-automation/
├── capcut_motion.py      # 메인 프로그램
├── README.md             # 이 파일
├── build.bat             # EXE 빌드 스크립트
├── requirements.txt      # Python 패키지 목록
├── examples/             # 예시 파일 (선택)
└── backups/              # 백업 파일 저장 (자동 생성)
```

## 문제 해결

### Q: 모션이 적용되지 않아요
A:
1. CapCut이 완전히 종료되었는지 확인
2. 파일 이름이 정확히 `draft_content.json`인지 확인
3. 백업 파일과 출력 파일 이름을 올바르게 교체했는지 확인

### Q: 특정 클립만 적용하고 싶어요
A: 현재 버전은 모든 비디오 세그먼트에 적용됩니다. 선택적 적용은 향후 업데이트 예정입니다.

### Q: EXE 실행 시 오류가 발생해요
A: Windows Defender나 백신 프로그램에서 차단할 수 있습니다. 신뢰할 수 있는 파일로 예외 처리하세요.

## 기술 정보

### 작동 원리
1. `draft_content.json` 파일 로드
2. `tracks` → `video` → `segments` 경로 탐색
3. 각 세그먼트에 `common_keyframes` 추가:
   - KFTypePositionX (X축 이동)
   - KFTypePositionY (Y축 이동)
   - KFTypeScaleX (스케일 변화)
4. `clip` 최종 상태 동기화
5. 수정된 JSON 저장

### 주요 구성 요소
- **GUI**: tkinter (Python 표준 라이브러리)
- **JSON 처리**: json 모듈
- **UUID 생성**: uuid 모듈 (CapCut 키프레임 ID)

## 라이선스

개인 및 상업적 용도로 자유롭게 사용 가능합니다.

## 개발 정보

- 개발 언어: Python 3.7+
- GUI 프레임워크: tkinter
- 의존성: 없음 (Python 표준 라이브러리만 사용)

## 업데이트 예정

- [ ] 특정 클립 선택 기능
- [ ] 이미지/비디오 필터링
- [ ] 커스텀 모션 패턴 저장/불러오기
- [ ] 일괄 처리 (여러 프로젝트 동시 처리)
- [ ] 미리보기 기능

---

**제작**: 2024
**버전**: 1.0.0
