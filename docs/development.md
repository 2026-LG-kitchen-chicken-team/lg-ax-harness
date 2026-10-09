# 개발 체계 사용법

## 설치와 업데이트

`npm ci`로 lockfile과 일치하는 개발 의존성을 설치한다. 초기 기반은 `@fission-ai/openspec` 1.14.1이다. 양쪽 도구 연결 파일은 다음 명령으로 생성했다.

```powershell
npm run spec -- init --tools codex,claude --profile core --language Korean --no-animation
```

초기화 명령은 이미 수행되었으므로 보통 다시 실행할 필요가 없다. 생성 Skill·명령은 Git으로 공유한다. 도구 버전을 올릴 때 package와 lockfile, 생성 파일의 변경을 함께 검토하고 다시 검사한다.

저장소의 `npm run spec -- ...` 연결 프로그램은 로컬 OpenSpec만 실행한다. CLI child process의 telemetry·completion 안내를 끄고, 설정·데이터 경로를 gitignored `.cache/openspec/`로 지정한다. 사용자 CODEX_HOME이나 Claude 전역 설정은 바꾸지 않는다. init/update가 기존 전역 OpenSpec 프롬프트를 자동 migration할 수 있으므로, 연결 프로그램은 해당 파일이 발견되면 실행을 중단한다.

`npm run spec -- config ...` 설정은 이 저장소용 cache에 적용된다. cache는 공유 상태가 아니므로 팀 기본 설정을 그곳에 의존시키지 않는다.

## 두 도구의 역할

Codex는 루트 `AGENTS.md`와 `.agents/skills/openspec-*`를 사용한다. Claude Code는 `CLAUDE.md`에서 `AGENTS.md`를 가져오고 `.claude/skills/`, `.claude/commands/opsx/`를 사용한다.

| 작업 | Codex | Claude Code |
|---|---|---|
| 아이디어 조사 | `$openspec-explore` | `/opsx:explore` |
| 요구사항·설계·작업 작성 | `$openspec-propose` | `/opsx:propose` |
| 구현 | `$openspec-apply-change` | `/opsx:apply` |
| 진행 중 계획 변경 | `$openspec-update-change` | `/opsx:update` |
| 검증 후 정리 | `$openspec-archive-change` | `/opsx:archive` |

Codex Desktop에서는 Skills에서 선택할 수 있다. 도구가 생성 Skill을 발견하지 못하면 새 세션에서 확인한다. Codex·Claude 자체 설치·로그인은 OpenSpec 설치와 별개다. 개별 도구 설치가 없는 CI에서도 문서·코드 검사 프로그램은 실행된다.

루트 공통 규칙 외에 사용자 전역 지침이 적용될 수 있다. 첫 세션에서 프로젝트 규칙과 Skill을 실제로 읽는지 확인한다.

## 작업과 인수인계

요구사항은 `openspec/specs/`, 진행 중 변경은 `openspec/changes/<id>/`에서 관리한다. 한 변경의 proposal·design·tasks·spec delta를 함께 읽는다. 같은 checkout의 파일·Git 작성은 한 도구가 담당한다.

예를 들어 Codex가 작업 중 멈췄다면 Claude에게 다음처럼 요청한다.

> bootstrap-development-harness의 변경 문서와 tasks, git diff, 최신 검사 결과를 읽고 현재 진행 상태를 설명한 뒤 남은 작업을 이어서 수행해줘.

도구 간 자동 메시지 전달이나 자동 잠금 서버는 없다. 분리 가능한 리뷰는 읽기 전용으로 진행할 수 있고, 병렬 작성이 필요해지면 독립 worktree를 사용한다.

## 실제 검사

```powershell
npm run doctor
npm run check -- --tool codex --change bootstrap-development-harness
npm run report
npm run audit
```

`doctor`는 Node·OpenSpec·프로젝트 연결 파일을 검사하고 coding CLI의 사용 가능 여부를 별도로 표시한다. CLI 존재나 버전만으로 로그인·Skill 인식을 증명하지 않는다.

`check`는 OpenSpec 구조 검사와 개발 하네스 자체 테스트를 실제로 실행한다. 실패한 검사, timeout, 실행 오류는 실패로 기록되고 성공 exit code로 바뀌지 않는다. 출력 보고서는 `reports/`에 있으며 `report`는 이를 CLI에서 요약한다. 사용 도구 표기는 사용자의 실행 문맥이며 실제 모델 호출 관찰을 의미하지 않는다. 토큰 사용량은 현재 미측정이다.

현재 체크에는 출품 프로그램 실행·업무 평가가 없다. 실제 제품 entrypoint와 평가 기준이 생기면 별도 검증으로 연결한다. OpenSpec `validate`·`status`나 코딩 도구의 완료 선언은 업무 정확성을 증명하지 않는다.

## 의존성 보안의 현재 제한

2026-10-09의 `npm audit`에서는 `braces` 3.0.3의 중첩 패턴 처리 stack exhaustion 취약점 **GHSA-vfj7-8cjw-p6xm**을 확인했다. 한 advisory가 OpenSpec → fast-glob → micromatch → braces 경로의 4개 high 항목으로 보고된다. 공개 advisory에는 patched version이 없고, npm이 제안하는 OpenSpec 0.17.2로의 강제 downgrade는 현재 설계를 변경하므로 수행하지 않았다.

이 제한은 숨기지 않으며 `npm run audit`가 현재 실패함을 기능 검사와 구분한다. 이 도구는 로컬 개발에 사용하고 외부 입력을 받는 서비스로 노출하지 않는다. 업데이트 시 수정 버전과 audit 결과를 다시 확인해야 한다.

출처: [GitHub Advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm), [OpenSpec 1.14.1](https://github.com/Fission-AI/OpenSpec/tree/v1.14.1), [지원 도구](https://github.com/Fission-AI/OpenSpec/blob/v1.14.1/docs/supported-tools.md), [Codex 지침](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Claude 지침](https://code.claude.com/docs/en/memory).
