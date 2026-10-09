## Why

신규 LG AX 프로젝트를 Codex와 Claude Code로 개발하려면 같은 요구사항·작업 기록을 읽고 실제 검사 근거로 이어받을 초기 체계가 필요하다. 기존 LG 작업물은 사용하지 않는다.

## What Changes

- 고정된 로컬 OpenSpec과 Codex·Claude 연결 파일을 구성한다.
- 공통 개발 지침과 도구별 사용법을 작성한다.
- 환경 확인, 실제 검사, JSON 실행 결과, 실패 전파와 자체 테스트를 구현한다.
- Windows·Linux CI를 연결하고 양쪽 도구의 실행 준비와 실제 검증 여부를 구분한다.

## Capabilities

### New Capabilities

- `development-workflow`: 두 coding 도구의 공유 변경 관리와 실행 근거 기반 검증.

### Modified Capabilities

없음.

## Impact

신규 저장소의 개발 도구·문서·CI에만 적용한다. 출품 업무·언어·모델·런타임은 미정이며 출품 구현과 개발용 시각화는 포함하지 않는다. OpenSpec 하위 의존성의 미패치 audit 경고는 현재 제한으로 공개한다.
