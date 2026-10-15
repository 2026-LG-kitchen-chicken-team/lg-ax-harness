"""Prepare isolated Claude product files; no installation/auth/inference."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PROFILES = {
    "claude": {"name": "Claude Code", "cli": "claude", "skills": ".claude/skills", "entry": "CLAUDE.md"},
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def codex_source(root):
    spec = importlib.util.spec_from_file_location("shared_product_source", root / "adapters/codex/install.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install(target, engine, root=ROOT):
    if engine not in PROFILES:
        raise ValueError("Unsupported runtime profile; Gemini support was withdrawn on 2026-10-11")
    profile = PROFILES[engine]
    root, target = root.resolve(strict=True), Path(target).expanduser().resolve()
    if target == root or target.is_relative_to(root) or root.is_relative_to(target):
        raise ValueError("Product target must be outside the development repository")
    if target.exists():
        raise ValueError("Use a new folder; existing product/state is never overwritten")
    if any((p / ".git").exists() for p in target.parents):
        raise ValueError("Use an isolated target without ancestor Git instructions")
    shared_source = codex_source(root)
    manifest, paths = shared_source.source_files(root)
    native_assets = shared_source.reviewer_assets(root, engine)
    entries = []
    target.mkdir(parents=True)

    def write(name, raw, source, original, transformation="unchanged", source_inputs=None):
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        entry = {"path":name,"sha256":digest(raw),"source":source,"source_sha256":original,"transformation":transformation}
        if source_inputs:
            entry["source_inputs"] = source_inputs
        entries.append(entry)

    for name in paths:
        raw = (root / name).read_bytes()
        write(name,raw,name,digest(raw))
    for skill in manifest["skills"]:
        for entry in skill["files"]:
            name = entry["path"]
            raw = (root/name).read_bytes()
            change = "unchanged"
            if name.endswith("SKILL.md"):
                raw = raw.decode("utf-8").replace("](../../docs/", "](../../../docs/").replace("python skills/", "python " + profile["skills"] + "/").encode("utf-8")
                change = "Rewrite contract links and native project Skill command paths"
            write(profile["skills"] + "/" + name.removeprefix("skills/"),raw,name,entry["sha256"],change)
    for name in ("AGENTS.md","pyproject.toml","uv.lock",".gitignore"):
        source = root / "adapters/codex/templates" / name
        raw = source.read_bytes()
        if name == "AGENTS.md":
            raw = raw.decode("utf-8").replace(".agents/skills",profile["skills"]).replace("Codex가 발견",profile["name"] + "가 발견").replace("현재 Codex 모델", "현재 " + profile["name"] + " 모델").encode("utf-8")
        write(name,raw,source.relative_to(root).as_posix(),digest(source.read_bytes()),"Shared product template; native Skill path only")
    for name, source in ((profile["entry"], root / "adapters" / engine / "templates" / profile["entry"]),
                         ("product-doctor.py", root / "adapters/common/product-doctor.py")):
        raw=source.read_bytes()
        write(name,raw,source.relative_to(root).as_posix(),digest(raw),"Runtime-specific entry or auth-free local doctor")
    for name, raw, source, source_sha, inputs in native_assets:
        write(name, raw, source, source_sha, "One read-only product reviewer; native invocation unverified", inputs)
    readme = f'''# LG AX {profile["name"]} 상품기획 하네스

이 설치기는 파일·공통 Tool만 준비한다. native 실행의 실제 지원 범위는 배포 검증 기록을 확인한다.
공통 Tool에는 Python3.12·uv가 필요하다. 설치기는 전역 패키지·설정·계정·권한을 변경하지 않는다.
Desktop Code GUI를 사용하면 본인 앱 계정으로 인증된 Code 로컬 세션에서 이 폴더를 선택한다. 별도 CLI 설치·로그인을 요구하지 않는다.
CLI를 선택하는 경우에만 공식 CLI 설치·로그인 후 아래 선택 명령을 실행한다. 폴더 신뢰·Skill 활성화 동의는 해당 실행기의 안내를 따른다.
별도 LLM API 프로그램·필수 MCP·플러그인을 추가하지 않는다. 웹·브라우저·PDF는 실제 제공될 때만 사용한다.

```powershell
uv sync --locked --python 3.12
uv run python product-doctor.py
```

Desktop Code 사용자는 Claude CLI 설치나 별도 CLI 인증이 필요 없다. 앱에 본인 Code 사용 가능 계정으로 로그인하고 Code → Local → 이 설치 폴더를 기본 작업 폴더로 선택한다. 모델 Opus5.5·추론 중간의 접근 가능 여부를 앱에서 확인하고 폴더 신뢰·권한 요청을 정상 처리한다. CLI 버전 검사가 실패해도 기본 doctor는 경고와 로컬 설치 결과를 구분한다. 상세 준비·오류 조치는 [심사 실행자 첫 설정](docs/contracts/runtime-access.md)을 따른다.

CLI를 선택한 실행자만 자신의 CLI를 설치·인증한 뒤:

```powershell
{profile["cli"]}
```

기본 catalog는 비어 있다. 첫 질문: `냉장고 사용 불편을 실제 리뷰에서 조사하고 새 부품 없이 개선할 안을 제안해줘.`
추가 질문: `이전 안을 장보기 전에 쓰는 3단계 안내로 구체화해줘. 조건은 유지해.`
업무 Skill은 {profile["skills"]}의6개이며 개발 역할/Skill은 포함하지 않는다.
자연어 요청에 맞는 자동 선택이 기본이고 Claude /evidence-retrieval 등 /Skill이름으로 명시 호출해도 같은 처리 경로다. @ subagent 선택은 .claude/agents의 선택 역할이며 Skill 호출과 구별한다.
필요 본문이 현재 문맥에 없으면 get_work_instructions로 main/선택 Skill/payload만 받고 동일 문맥·지문은 known_context 신고로 중복 반환을 생략한다. 반환 receipt는 독해·이해·적용 인증이 아니다. docs/contracts/instruction-loading.md를 따른다.
공식 안내: https://code.claude.com/docs/en/skills · https://code.claude.com/docs/en/sub-agents#invoke-subagents-explicitly
선택적 공식 자료 조사자·후기 조사분석자·근거 검토자 3개를 .claude/agents에 설치한다. 메인이 필요한 역할만 선택하며 대화·단순 수정에는 호출하지 않는다.
Claude Desktop의 Code 로컬 세션에서도 이 폴더를 열 수 있다. 일반 Chat 세션은 프로젝트 Agent 설치·발견 검증과 별개다.
역할 파일 준비와 실제 위임은 구분한다. 역할별 시간은 실제 spawn 응답부터 최대180초와 전체 마감/최종90초 중 더 짧은 범위로 관리한다.
uv sync --locked는 같은 공통 문서 의존성(python-docx/openpyxl/reportlab/Pillow/pypdf)을 이 폴더의 로컬 환경에 설치한다.
pip 대체 경로는 Python3.12 가상환경에서만 사용하고 docs/contracts/runtime-access.md의 명령을 따른다. 시스템 Python3.14 등에서 직접 실행하지 않는다.
공통 Skill은 기본 save_and_export(report:false)의 현재버전 웹결과/전체선택원문을 전달한다. 설치된 뷰어는 같은데이터로작업화면·별도HTML보고서를일반코드로만들며추가모델호출을하지않는다. PDF/DOCX/XLSX생성은명시report:true 요청만사용한다.
화면연결은설치폴더에서 uv run python web/prototypes/visual-viewer/viewer.py install --claude . 을한번실행한다. 이후 uv run python web/prototypes/visual-viewer/viewer.py open . 으로현재저장결과를열수있다.
별도보고서는 uv run python web/prototypes/visual-viewer/build_view.py --export <현재세션JSON> --out-dir runtime-data/visual-viewer --standalone runtime-data/visual-viewer/report.html --mode ops 로만든다. AI에게HTML레이아웃을다시작성하게하지않는다.
권장프로파일은유료Desktop Code의 Opus5.5/중간이다. 본인앱에보이는모델·노력설정을확인하고다른설정을같은검증결과로간주하지않는다.
실행 권한은 docs/contracts/runtime-access.md를 따른다. 기본 작업 폴더를 이 설치 폴더로 선택하고 Manual(default) 또는 제공되는 자동 모드에서 필요한 공통 Tool 명령·웹 조회를 확인한다. 모든 권한 우회는 기본값이 아니다. 자식은 tools/disallowedTools로 직접 도구를 제한하며 permissionMode만으로 부모보다 좁은 OS 권한을 만들었다고 설명하지 않는다.
자료량에 따라 파일·절·페이지 수가 달라지며 내부 JSON·검수 기록은 runtime-data에 보관한다.
report_plan_path는 runtime-data의 내부 작성 파일이다. open_folder:false로 결과 폴더 열기를 생략할 수 있다.
제작 실패는 업무 저장을 유지하고 같은 session_id/turn_id/expected_result_version의 deliver_result로 복구한다.
Claude의 실제 AI 인수 범위는 배포 검증 기록을 따른다. 설치/로컬 검사를 native 업무 통과로 바꾸지 않는다.
세션·요청 키는 공통 Tool이 만든다. 결과의 출처·held/needs_input·runtime-data/exports를 확인한다.
doctor는 Python3.12·파일·문서 의존성 import/버전·선택 CLI 버전·로컬 공통 Tool/SQLite만 확인한다. native 세션 권한·네트워크·모델 접근을 검사하지 않으며 파일 제작/레이아웃·인증·Skill 발견·AI 품질을 보증하지 않는다.
native CLI가 없으면 doctor는 local_only로 표시한다. `--require-native`는 CLI 진단 선택이며 CLI 부재를 실패로 처리한다. GUI Code 세션 인증·발견·위임은 doctor의 CLI 진단과 별도로 확인한다.
대화 재개는 실행기의 해당 대화 기능을 사용하며 기존 session/turn과 이력을 유지한다.
원문 로그·DB·인증·개인 설정·의존성 환경은 공유하지 않는다.
'''.encode("utf-8")
    write("README.md",readme,"adapters/common/install.py",digest(Path(__file__).read_bytes()),"Generated setup guide; native support explicitly unverified")
    record={"format":"portable-product-install-v1","engine":engine,"profile":profile,"source_manifest_sha256":digest((root/"skills/manifest.json").read_bytes()),
            "files":entries,"skills":[s["name"] for s in manifest["skills"]],"native_agents":[slug for slug, _ in shared_source.PRODUCT_ROLES],"native_verified":False,
            "scope":"Project regular files only; no auth/global settings/automatic model invocation"}
    (target/"product-install.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    return {"target":str(target),"engine":engine,"installed_skills":len(manifest["skills"]),"files":len(entries),"native_verified":False}


def check(target):
    target=Path(target).resolve(strict=True)
    record=json.loads((target/"product-install.json").read_text(encoding="utf-8"))
    errors=[]
    if record.get("format")!="portable-product-install-v1" or record.get("profile")!=PROFILES.get(record.get("engine")):
        errors.append("Invalid portable runtime profile")
    for entry in record["files"]:
        path=(target/entry["path"]).resolve()
        if not path.is_relative_to(target) or not path.is_file() or digest(path.read_bytes())!=entry["sha256"]:
            errors.append("Changed/missing installed file: "+entry["path"])
    if "native_agents" in record:
        if record["native_agents"] != [slug for slug, _ in codex_source(ROOT).PRODUCT_ROLES]:
            errors.append("Invalid product-native agent list")
        actual = sorted(p.name for p in (target / ".claude/agents").glob("*.md"))
        if actual != sorted(slug + ".md" for slug, _ in codex_source(ROOT).PRODUCT_ROLES):
            errors.append("Unexpected/missing product-native agent file")
    return {"errors":errors,"native_verified":False,"scope":"installed files only"}


def main(engine=None):
    if hasattr(sys.stdout,"reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser=argparse.ArgumentParser(description=__doc__)
    if engine is None:
        parser.add_argument("--engine",choices=PROFILES,required=True)
    parser.add_argument("--target",type=Path,required=True)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    try:
        result=check(args.target) if args.check else install(args.target,engine or args.engine)
        print(json.dumps(result,ensure_ascii=False))
        return int(bool(result.get("errors")))
    except (OSError,ValueError,KeyError) as exc:
        print(json.dumps({"ok":False,"error":str(exc)},ensure_ascii=False))
        return 1


if __name__=="__main__":
    raise SystemExit(main())
