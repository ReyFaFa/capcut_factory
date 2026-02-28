# 프로젝트 요약

## 📁 프로젝트 구조

```
capcut-motion-automation/
├── capcut_motion.py      # 메인 프로그램 (GUI + 로직)
├── README.md             # 전체 사용 설명서
├── QUICKSTART.md         # 5분 빠른 시작 가이드
├── build.bat             # EXE 빌드 자동화 스크립트
├── requirements.txt      # Python 패키지 목록
├── examples/             # 예시 파일 폴더
└── PROJECT_SUMMARY.md    # 이 파일
```

## 🚀 주요 기능

### 1. GUI 인터페이스 (tkinter)
- 파일 선택 다이얼로그
- 7가지 모션 패턴 라디오 버튼
- 스케일/이동 범위 설정 입력
- 백업 옵션 체크박스
- 실시간 상태 표시

### 2. 7가지 모션 패턴
1. **기본 줌인**: 랜덤 줌 + 랜덤 이동
2. **줌인/줌아웃 랜덤**: 50% 확률로 방향 전환
3. **좌→우 이동**: 왼쪽에서 오른쪽으로
4. **우→좌 이동**: 오른쪽에서 왼쪽으로
5. **상→하 이동**: 위에서 아래로
6. **하→상 이동**: 아래에서 위로
7. **중앙 줌**: 위치 고정, 확대만

### 3. 자동 백업 시스템
- 타임스탬프 기반 백업 파일명
- `backups/` 폴더 자동 생성
- 원본 파일 안전 보호

### 4. CapCut JSON 처리
- `draft_content.json` 파싱
- 비디오 트랙 자동 탐지
- 키프레임 자동 생성:
  - KFTypePositionX (X축 이동)
  - KFTypePositionY (Y축 이동)
  - KFTypeScaleX (스케일 변화)
- clip 상태 동기화

## 🔧 기술 스택

- **언어**: Python 3.7+
- **GUI**: tkinter (표준 라이브러리)
- **의존성**: 없음 (순수 Python)
- **빌드 도구**: PyInstaller (EXE 변환)

## 📋 사용 시나리오

### 시나리오 1: Python 직접 실행
```bash
python capcut_motion.py
```

### 시나리오 2: EXE 배포
```bash
# 1. 빌드
build.bat

# 2. 배포
dist\CapCut_모션_자동화.exe 파일을 다른 PC에 복사

# 3. 실행 (Python 설치 불필요)
더블클릭으로 실행
```

## ⚙️ 설정 값 가이드

### 안정적 (YouTube 스토리텔링)
```
시작 스케일: 1.04
끝 스케일: 1.08~1.09
이동 범위: ±0.03
```

### 드라마틱 (뮤직비디오)
```
시작 스케일: 1.05
끝 스케일: 1.10~1.12
이동 범위: ±0.07
```

### 미니멀 (뉴스/다큐)
```
시작 스케일: 1.02
끝 스케일: 1.04~1.06
이동 범위: ±0.02
```

## 🎯 워크플로우

```
1. CapCut 종료
   ↓
2. 프로그램 실행
   ↓
3. draft_content.json 선택
   ↓
4. 모션 패턴 & 설정 선택
   ↓
5. "모션 적용하기" 클릭
   ↓
6. draft_content_motion.json 생성
   ↓
7. 파일 이름 교체
   ↓
8. CapCut 재실행
   ↓
9. 효과 확인
```

## 🔍 코드 주요 부분

### 1. 키프레임 생성 함수
```python
def build_keyframe(self, kf_type, start_value, end_value, duration):
    # UUID 기반 고유 ID
    # Line 보간 (선형)
    # 시작/끝 값 설정
```

### 2. 패턴 값 계산
```python
def get_pattern_values(self, pattern):
    # 패턴별 start/end 값 계산
    # 랜덤 범위 적용
```

### 3. 세그먼트 처리
```python
def process_segments(self, data):
    # video 트랙 필터링
    # 각 세그먼트에 키프레임 추가
    # clip 상태 동기화
```

## 📦 EXE 빌드 상세

### build.bat 동작
1. PyInstaller 설치 확인
2. 이전 빌드 정리
3. PyInstaller 실행:
   - `--onefile`: 단일 실행 파일
   - `--windowed`: 콘솔 창 숨김
   - `--name`: 한글 파일명
4. `dist/` 폴더에 EXE 생성

### 빌드 후 파일 크기
- 예상 크기: 8~12 MB
- 포함 내용: Python 인터프리터 + 표준 라이브러리 + 코드

## ⚠️ 주의사항

1. **CapCut 종료 필수**
   - 실행 중에는 파일 변경 불가

2. **백업 권장**
   - 중요 프로젝트는 수동 백업도 병행

3. **테스트 프로젝트 우선**
   - 처음 사용 시 테스트용으로 시도

4. **uniform_scale 전제**
   - CapCut의 uniform_scale이 true인 경우만 고려
   - ScaleX만 설정 (ScaleY는 자동)

## 🔮 향후 개선 계획

- [ ] 특정 클립 선택 기능
- [ ] 이미지/비디오 필터링
- [ ] 커스텀 패턴 저장/불러오기
- [ ] 일괄 처리 (여러 프로젝트)
- [ ] 프리뷰 기능
- [ ] 키프레임 타이밍 조정
- [ ] 곡선(Bezier) 보간 지원

## 📞 문제 해결

자세한 내용은 `README.md`의 "문제 해결" 섹션 참고

---

**개발 완료일**: 2024
**버전**: 1.0.0
**라이선스**: 자유 사용
