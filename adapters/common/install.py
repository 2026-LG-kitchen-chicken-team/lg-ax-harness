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
    manifest, paths = codex_source(root).source_files(root)
    entries = []
    target.mkdir(parents=True)

    def write(name, raw, source, original, transformation="unchanged"):
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        entries.append({"path":name,"sha256":digest(raw),"source":source,"source_sha256":original,"transformation":transformation})

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
    readme = f'''# LG AX {profile["name"]} 상품기획 하네스

이 설치 사본은 파일·공통 Tool 준비 단계다. {profile["name"]} native 실행은 아직 검증하지 않았다.
Python3.12·uv와 실행자 자신의 {profile["name"]} 설치·인증이 필요하다. 설치기는 전역 패키지·설정·계정·권한을 변경하지 않는다.
공식 CLI 설치 및 로그인·폴더 신뢰·Skill 활성화 동의는 실행자가 해당 제품 안내에 따라 진행한다.
별도 LLM API 프로그램·필수 MCP·플러그인을 추가하지 않는다. 웹·브라우저·PDF는 실제 제공될 때만 사용한다.

```powershell
uv sync --locked
uv run python product-doctor.py
{profile["cli"]}
```

기본 catalog는 비어 있다. 첫 질문: `냉장고 사용 불편을 실제 리뷰에서 조사하고 새 부품 없이 개선할 안을 제안해줘.`
추가 질문: `이전 안을 장보기 전에 쓰는 3단계 안내로 구체화해줘. 조건은 유지해.`
업무 Skill은 {profile["skills"]}의6개이며 개발 역할/Skill은 포함하지 않는다.
uv sync --locked는 같은 공통 문서 의존성(python-docx/openpyxl/reportlab/Pillow/pypdf)을 이 폴더의 로컬 환경에 설치한다.
pip 환경은 python -m pip install --require-hashes -r product-tools/requirements.lock을 사용할 수 있다.
공통 Skill의 최종 출력은 save_and_export에 report:true를 명시하고 종류별 원문 XLSX·필요한 DOCX·최종 DOCX/PDF를 만든다.
자료량에 따라 파일·절·페이지 수가 달라지며 내부 JSON·검수 기록은 runtime-data에 보관한다.
report_plan_path는 runtime-data의 내부 작성 파일이다. open_folder:false로 결과 폴더 열기를 생략할 수 있다.
제작 실패는 업무 저장을 유지하고 같은 session_id/turn_id/expected_result_version의 deliver_result로 복구한다.
Claude의 실제 AI 인수는 최길웅 환경에서 별도로 확인해야 하며 설치/로컬 검사를 native 업무 통과로 바꾸지 않는다.
세션·요청 키는 공통 Tool이 만든다. 결과의 출처·held/needs_input·runtime-data/exports를 확인한다.
doctor는 파일·문서 의존성 import/버전·CLI 버전·공통 Tool만 확인하며 파일 제작/레이아웃·인증·Skill 발견·AI 품질·Tool 권한을 보증하지 않는다.
native CLI가 없으면 local_only로 표시한다. `--require-native`는 CLI 부재를 실패로 처리한다.
대화 재개는 실행기의 해당 대화 기능을 사용하며 기존 session/turn과 이력을 유지한다.
원문 로그·DB·인증·개인 설정·의존성 환경은 공유하지 않는다.
'''.encode("utf-8")
    write("README.md",readme,"adapters/common/install.py",digest(Path(__file__).read_bytes()),"Generated setup guide; native support explicitly unverified")
    record={"format":"portable-product-install-v1","engine":engine,"profile":profile,"source_manifest_sha256":digest((root/"skills/manifest.json").read_bytes()),
            "files":entries,"skills":[s["name"] for s in manifest["skills"]],"native_verified":False,
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
