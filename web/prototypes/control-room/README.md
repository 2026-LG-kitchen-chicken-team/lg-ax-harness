# LG AX · Agent Control Room

> **상태: 체험용 초기 프로토타입 (v0.10.0 기반)**
>
> 공간·모션·조작감을 체험하고 시각화 방향을 검토하기 위한 초기 버전입니다. 기본 실행은 합성 데모이며, 최종 출품 UI·완성 제품이나 실시간 에이전트 통신 연결 완료본이 아닙니다.

`product-v0.10.0` (`cdf0e6e1970c6e0b8d1cc728a6838dabf9188e29`)의 메인 1개, 선택 연구 역할 3개, 업무 Skill 6개를 표현하는 3D 관제 프로토타입입니다. 기존 제품 코드·Skill·설치 훅을 수정하지 않는 독립적인 로컬 프런트엔드입니다.

## 실행

Node.js 20.19+ 또는 22.12+에서 이 폴더를 열고 실행합니다.

```powershell
npm ci
npm run dev
```

브라우저에서 `http://127.0.0.1:5174/`를 엽니다. 프로젝트 폰트와 장면 리소스는 로컬에 포함되며 실행 중 외부 이미지·폰트·모델 API를 호출하지 않습니다.

```powershell
npm test
npm run build
npm run preview
```

## 화면

- 중앙 메인 코어, 연구 역할 스테이션 3개, 업무 Skill 모듈 6개
- 시각에 맞춰 흐르는 위임·반환·도구 호출 신호와 선택한 노드의 작업 내용
- 재생·정지·배속·타임라인 및 위임/병렬 조사/검토/완료 챕터
- 노드 선택, 역할·Skill 목록, 보류 후 같은 요청에서 수정하는 gate 연출
- v0.10.0 세션 export JSON 로컬 불러오기와 현재 화면 trace 내려받기

## 관측 범위

기본 84초 재생은 **명시적인 합성 데모**입니다. 실제 하네스 inventory에 맞춰 공간·조명·모션과 상태 변화를 검수하기 위한 연출이며 모델 실행, 업무 시간, 성과나 사용량을 인증하지 않습니다.

`세션 불러오기`는 `export_session`으로 저장된 세션 JSON 본문을 읽습니다. export receipt(경로·SHA만 있는 응답)는 입력이 아닙니다. JSON 파일 선택 또는 붙여넣기를 지원하며 이 화면에서 내려받은 trace도 다시 읽을 수 있습니다. 사용자가 선택한 파일은 브라우저 안에서만 파싱하며 서버로 업로드하지 않습니다. 시각이 있는 journal·근거 전달/검토·후보 저장·보류·취소만 해당 시각에 표시합니다. 호출 시각이 없는 invocation은 별도 메타데이터로 보존합니다.

v0.10.0 export에는 native 서브에이전트 실행·통신 장부가 없습니다. 설치된 역할, source_scan, 검토 packet만으로 실제 위임·메시지를 추정하지 않으며, 기록 재생에서 연구 역할의 가짜 통신을 생성하지 않습니다. 실제 실시간 위임·Skill 통신을 연결하려면 실행기가 `agent_started`, `tool_started`, `message_sent`, `agent_returned` 등에 실제 시각·호출 ID를 포함해 기록하는 별도의 관측 어댑터가 필요합니다. 이번 프로토타입은 그 실행기나 전역 훅을 설치하지 않습니다.

`fixtures/format-fixture.json`은 import 경로 검수용 합성 형식 예제입니다. 실제 냉장고 분석이나 실제 원문 근거가 아닙니다. 자세한 원본 필드 매핑은 [README-adapter.md](README-adapter.md)에 있습니다.

## 구현과 출처

React + Three.js + React Three Fiber + Drei + React Postprocessing. 구도와 하드웨어 형상, Fresnel shader, 신호 경로는 이 프로토타입에서 구현했습니다. force-directed layout 대신 고정 위치와 Bezier 경로를 사용해 화면 구도를 유지합니다.

- [Three.js](https://github.com/mrdoob/three.js) — MIT
- [React Three Fiber](https://github.com/pmndrs/react-three-fiber), [Drei](https://github.com/pmndrs/drei), [React Postprocessing](https://github.com/pmndrs/react-postprocessing) — MIT
- [공식 선택 발광 가이드](https://react-postprocessing.docs.pmnd.rs/effects/bloom) 및 [Three.js selective bloom 예제](https://github.com/mrdoob/three.js/blob/dev/examples/webgl_postprocessing_unreal_bloom_selective.html)를 렌더링 설정 참고로 사용
- [Lucide](https://github.com/lucide-icons/lucide) — ISC
- Space Grotesk / IBM Plex Sans KR — SIL OFL, Fontsource 패키지의 라이선스 참조

AJ Sahni Agents Office 등의 제한된 소스·3D 모델·화면은 복사하지 않았습니다.

좁은 휴대전화의 touch-first 화면은 이번 프로토타입 범위가 아니며 데스크톱 화면을 대상으로 합니다. import는 단일 세션 25MB 이하를 지원합니다.
