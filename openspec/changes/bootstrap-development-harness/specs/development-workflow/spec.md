## ADDED Requirements

### Requirement: Independent shared development state

개발 체계는 기존 LG 작업물을 재사용하지 않는 신규 저장소의 OpenSpec 요구사항·변경 문서를 작업 상태 원본으로 사용할 SHALL 의무가 있다.

#### Scenario: Resume work in another coding tool
- **WHEN** 다른 coding 도구가 진행 중 변경을 이어받는다
- **THEN** 같은 proposal·design·tasks, Git 변경과 실제 검사 결과를 읽고 진행 상태를 판단한다
- **AND** 대화 기억이나 별도 복제된 task ledger를 원본으로 삼지 않는다

### Requirement: Project-local tool integration

개발 체계는 고정된 OpenSpec 로컬 의존성과 Codex·Claude용 생성 연결 파일을 제공할 SHALL 의무가 있다.

#### Scenario: Install development dependencies
- **WHEN** 새 checkout에서 npm ci를 실행한다
- **THEN** lockfile의 OpenSpec 버전이 설치된다
- **AND** 생성 Skill·명령과 공통 지침이 저장소에서 공유된다

### Requirement: Real check execution and failure propagation

개발 체계는 OpenSpec 구조 검사와 자체 테스트를 실제로 실행하고 실패를 반환할 SHALL 의무가 있다.

#### Scenario: A check fails
- **WHEN** 검사 프로세스가 실패하거나 실행되지 못한다
- **THEN** check 명령이 실패 exit code를 반환한다
- **AND** 검사 결과와 실패 이유를 보고서에 기록한다

### Requirement: Evidence and unavailable measurements

개발 체계는 실행 식별자, 도구 문맥, 코드 버전, 검사별 결과와 시간을 JSON으로 기록할 SHALL 의무가 있다.

#### Scenario: No model usage is observed
- **WHEN** 검사 중 실제 모델 사용량을 관측하지 않는다
- **THEN** 토큰 사용량을 미측정으로 기록한다
- **AND** 0 토큰 또는 업무 평가 통과로 해석하지 않는다

### Requirement: Honest tool readiness

개발 체계는 연결 파일·CLI 준비 상태와 실제 세션 검증을 구분할 SHALL 의무가 있다.

#### Scenario: Claude Code is unavailable
- **WHEN** Claude CLI가 현재 환경에서 발견되지 않는다
- **THEN** 해당 도구의 실행 준비를 미확인 상태로 표시한다
- **AND** 프로젝트의 검사 성공을 Claude 세션 또는 인수인계 성공이라고 보고하지 않는다

### Requirement: Separate competition implementation

초기 개발 체계는 출품용 업무·모델·실행 구조의 미정 상태를 보존할 SHALL 의무가 있다.

#### Scenario: Initial development checks pass
- **WHEN** 개발 도구의 구조 검사와 자체 테스트가 통과한다
- **THEN** 출품 Agent 구현 또는 업무 평가가 통과했다고 주장하지 않는다
- **AND** 에이전트·메시지 시각화는 출품 하네스에서 필요할 때 별도로 검토한다
