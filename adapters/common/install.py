"""Prepare isolated Claude/Gemini product files; no installation/auth/inference."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PROFILES = {
    "claude": {"name": "Claude Code", "cli": "claude", "skills": ".claude/skills", "entry": "CLAUDE.md"},
    "gemini": {"name": "Gemini CLI", "cli": "gemini", "skills": ".gemini/skills", "entry": "GEMINI.md"},
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def codex_source(root):
    spec = importlib.util.spec_from_file_location("shared_product_source", root / "adapters/codex/install.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install(target, engine, root=ROOT):
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

첫 질문: `T876MQQ012를 기준으로 수납·정리 개선안을 만들어줘. 하드웨어 추가 없이.`
추가 질문: `이전 안을 장보기 전에 쓰는 3단계 안내로 구체화해줘. 조건은 유지해.`
업무 Skill은 {profile["skills"]}의6개이며 개발 역할/Skill은 포함하지 않는다.
세션·요청 키는 공통 Tool이 만든다. 결과의 출처·held/needs_input·runtime-data/exports를 확인한다.
doctor는 파일·CLI 버전·공통 Tool만 확인하며 인증·Skill 발견·AI 품질·Tool 권한을 보증하지 않는다.
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
