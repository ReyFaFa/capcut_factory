# Release Notes (2026-04-01)

## 변경 요약
- 이미지 매칭 기본 모드를 `유형 A: SRT 인덱스 매칭`으로 변경
- 프로젝트 폴더 업로드 시 `draft_content.json` 다중 파일(루트 + Timelines 하위) 동시 처리 지원
- Generate 단계에서 동일 이미지 연속 세그먼트 병합 로직 추가
- Motion Application 단계에서 다중 draft 동시 적용 지원
- 모션 키프레임 적용 범위 보강 (`ScaleX` + `ScaleY` + `UniformScale`)
- 드래프트 단일 파일 선택 시 동일 프로젝트 내 다른 `draft_content.json` 자동 포함
- Generate 시 CapCut 캐시 자동 정리 기능 추가(안전 범위 캐시 디렉터리만)
- 모션 적용 결과 문구를 `clips` 기준에서 `images` 기준으로 변경

## 해결된 이슈
- 인덱스 기반 매칭에서 세그먼트가 1개씩 쪼개져 보이던 타임라인 문제
- Timelines 하위 draft가 누락되어 모션이 일부만 적용되던 문제
- 성공 메시지의 클립 수 표기가 사용자 관점에서 혼동되던 문제

## 사용자 체감 변경
- `GENERATE PROJECT` 한 번으로 프로젝트 내 관련 draft들을 함께 갱신
- `APPLY MOTION` 결과가 이미지 장수 기준으로 표시되어 이해가 쉬워짐
- CapCut 캐시 정리가 자동화되어 반복 작업 감소

## 백업
- 코드 백업 폴더: `backups/release_20260401_211209`
- 포함 파일:
  - `capcut_factory.py`
  - `capcut_factory.diff`
