"""Bounded native Codex/Claude product comparison. Evaluation tool, excluded from product ZIP."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, sqlite3, subprocess, sys, threading, time
from datetime import datetime, timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from native_eval import rollout_observation, stop_owned, usage_delta
MAX_LOG=32*1024*1024
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
def protected(workspace):
    manifest=json.loads((workspace/"product-install.json").read_text(encoding="utf-8"))
    return {x["path"]:sha(workspace/x["path"]) for x in manifest["files"]}
def bucket(command):
    text=command.lower()
    for name,needles in [
      ("save_export_report",("save_and_export","deliver_result")),
      ("retrieve_or_open",("open_request_bundle","retrieve_reviews","retrieve_product_facts","prepare_planning_input")),
      ("review_code",("review_product_result",)),
      ("skill_read",("skill.md",)),
      ("source_or_contract_read",("docs/contracts","product_tools","models.json","sources.jsonl")),
      ("candidate_or_plan_write",("runtime-data",)),
    ]:
      if any(x in text for x in needles):return name
    return "other_command"
def observe_event(event,at,spans,state):
    typ=event.get("type")
    item=event.get("item") or {}
    if typ=="thread.started":state["native_id"]=event.get("thread_id")
    if typ=="turn.completed":
      state["completed"]=True;state["usage"]=event.get("usage");state["completed_at"]=at
    if typ=="system" and event.get("subtype")=="init":
      state["native_id"]=event.get("session_id");state["actual_model"]=event.get("model")
    if typ=="result":
      state["completed"]=not event.get("is_error",False)
      state["usage"]=event.get("usage");state["model_usage"]=event.get("modelUsage")
      state["reported_cost_usd"]=event.get("total_cost_usd")
      state["claude_result"]=event.get("result")
      state["completed_at"]=at
    if typ=="item.started" and item.get("type") in ("command_execution","web_search"):
      spans[item["id"]]={"started":at,"command":item.get("command",""),"item_type":item["type"]}
    if typ=="item.completed" and item.get("type") in ("command_execution","web_search"):
      span=spans.setdefault(item["id"],{"started":None,"command":item.get("command",""),"item_type":item["type"]})
      span.update(ended=at,exit_code=item.get("exit_code"),bucket=bucket(span["command"]) if item["type"]=="command_execution" else "web_search",
                  output_bytes=len(item.get("aggregated_output","").encode("utf-8")))
    if typ=="item.completed" and item.get("type")=="agent_message":
      state["last_message"]=item.get("text");state["last_message_at"]=at
def interval_union_seconds(spans):
    """Completed observed wall intervals only; never sum parallel/nested spans."""
    intervals=sorted((s["started"],s["ended"]) for s in spans if s.get("started") is not None and s.get("ended") is not None)
    total=0.;end=None
    for start,stop in intervals:
      total+=max(0.,stop-max(start,end)) if end is not None else max(0.,stop-start)
      end=max(end,stop) if end is not None else stop
    return total

def execute(args,cwd,prompt,directory,timeout):
    if directory.exists():raise ValueError("Never re-execute an attempted job")
    directory.mkdir(parents=True)
    (directory/"prompt.txt").write_text(prompt,encoding="utf-8")
    state={"native_id":None,"completed":False,"usage":None};spans={};errors=[]
    env=dict(os.environ);env.pop("VIRTUAL_ENV",None);env["PYTHONUTF8"]="1"
    start=time.monotonic();start_utc=datetime.now(timezone.utc).isoformat()
    creation=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0
    with (directory/"native.jsonl").open("wb") as out,(directory/"stderr.txt").open("wb") as err:
      process=subprocess.Popen(args,cwd=cwd,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
          stderr=err,shell=False,creationflags=creation,start_new_session=os.name!="nt")
      def consume():
        try:
          with (directory/"observations.jsonl").open("w",encoding="utf-8") as observed:
            for raw in iter(process.stdout.readline,b""):
              at=time.monotonic()-start;out.write(raw);out.flush()
              try:event=json.loads(raw)
              except ValueError:continue
              observe_event(event,at,spans,state)
              observed.write(json.dumps({"at_seconds":at,"type":event.get("type"),
                "item_type":(event.get("item") or {}).get("type"),"item_id":(event.get("item") or {}).get("id")})+"\n")
              observed.flush()
        except Exception as exc:errors.append(type(exc).__name__+": "+str(exc))
      reader=threading.Thread(target=consume,daemon=True);reader.start()
      try:process.stdin.write(prompt.encode("utf-8"))
      except BrokenPipeError:errors.append("CLI closed stdin before prompt delivery")
      finally:process.stdin.close()
      status="finished";termination=None;timeout_at=None
      try:
        while process.poll() is None:
          if time.monotonic()-start>=timeout:
            timeout_at=time.monotonic()-start;status="timeout";termination=stop_owned(process);break
          if (directory/"native.jsonl").stat().st_size+(directory/"stderr.txt").stat().st_size>MAX_LOG:
            status="output_limit";termination=stop_owned(process);break
          time.sleep(.2)
      except BaseException:
        stop_owned(process);raise
      exit_at=time.monotonic()-start
      if status=="finished" and exit_at>timeout:status="deadline_exceeded"
      reader.join(timeout=5)
      if reader.is_alive():errors.append("stdout collector incomplete")
      else:process.stdout.close()
      collector_at=time.monotonic()-start
    if status=="finished":
      status="succeeded" if process.returncode==0 and state["completed"] else "failed"
    message=state.get("claude_result") or state.get("last_message")
    delivered=status=="succeeded" and bool(message) and not errors
    if message:(directory/("final.txt" if delivered else "last-message.txt")).write_text(message,encoding="utf-8")
    for span in spans.values():
      span["inclusive_seconds"]=(span["ended"]-span["started"]
        if span.get("ended") is not None and span.get("started") is not None else None)
    result={"status":status,"exit_code":process.returncode,"elapsed_seconds":round(time.monotonic()-start,4),
      "started_utc":start_utc,"ended_utc":datetime.now(timezone.utc).isoformat(),
      "native_id":state["native_id"],"turn_completed":state["completed"],
      "last_message_at_seconds":state.get("last_message_at"),"turn_completed_at_seconds":state.get("completed_at"),
      "final_delivery_observed":delivered,"termination":termination,
      "timeout_detected_at_seconds":timeout_at,"process_exit_observed_at_seconds":exit_at,
      "collector_finished_at_seconds":collector_at,"observation_complete":not errors,
      "reported_usage":state["usage"],"reported_model_usage":state.get("model_usage"),
      "actual_model":state.get("actual_model"),"actual_billed_cost":None,
      "reported_cost_usd":state.get("reported_cost_usd"),"command_spans":[s for s in spans.values() if s["item_type"]=="command_execution"],
      "tool_spans":list(spans.values()),"completed_tool_wall_seconds":interval_union_seconds(spans.values()),
      "observation_errors":errors}
    dump(directory/"process-result.json",result)
    return result
def stored(workspace):
    db=workspace/"runtime-data/product.sqlite"
    if not db.exists():return {"turns":[],"db_present":False}
    con=sqlite3.connect("file:"+db.as_posix()+"?mode=ro",uri=True)
    try:
      turns=[dict(zip(("turn_id","status","result_version","payload","validation"),r))
        for r in con.execute("SELECT t.turn_id,t.status,t.result_version,r.payload,r.validation_json FROM turns t LEFT JOIN results r ON r.turn_id=t.turn_id AND r.result_version=t.result_version")]
      for t in turns:
        for k in ("payload","validation"):
          t[k]=json.loads(t[k]) if t[k] else None
        t["assessment"]=(t.get("validation") or {}).get("assessment")
      requests=[{"payload":json.loads(r[0]),"response":json.loads(r[1]) if r[1] else None}
        for r in con.execute("SELECT payload,response FROM conversation_requests")]
      return {"db_present":True,"turns":turns,"requests":requests}
    finally:con.close()
def prepare_job(job,plan):
    ws=Path(plan["workspace_root"])/job["id"]
    if ws.exists():raise ValueError("Existing workspace is not a fresh job")
    source=Path(plan["sources"][job["provider"]])
    shutil.copytree(source,ws,ignore=shutil.ignore_patterns(".venv","runtime-data","__pycache__"))
    if plan.get("mode")!="fresh_online_e2e":
      target=ws/"data/business/evaluation-v4"
      shutil.copytree(Path(plan["dataset"]),target)
    env=dict(os.environ);env.pop("VIRTUAL_ENV",None);env["PYTHONUTF8"]="1"
    sync=subprocess.run(["uv","sync","--locked"],cwd=ws,env=env,capture_output=True,timeout=90)
    if sync.returncode:raise RuntimeError("locked workspace preparation failed")
    if job["provider"]=="codex" and not (job.get("product_reviewer",False) or job.get("product_researchers",False)):
      config=ws/".codex/config.toml";config.parent.mkdir(exist_ok=True)
      config.write_text('[features]\nmulti_agent = false\n[agents]\nenabled = false\n',encoding="utf-8")
    return ws
def run_job(job,plan,run_root):
    delegated=job.get("product_reviewer",False) or job.get("product_researchers",False)
    if job.get("provider")=="claude" and delegated:
      raise ValueError("Claude delegated-role evaluation requires the GUI protocol; this CLI path is parent-only")
    if plan.get("mode")=="fresh_online_e2e" and job.get("product_reviewer",False):
      raise ValueError("Fresh online phase supports parent-only or research roles, not candidate-reviewer A/B")
    directory=run_root/job["id"]
    if directory.exists():
      print(json.dumps({"job":job["id"],"event":"already_attempted"}),flush=True)
      receipt=directory/"result.json"
      return json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else {"status":"attempt_incomplete"}
    prepare_start=time.monotonic();ws=prepare_job(job,plan);before=protected(ws)
    preparation_seconds=time.monotonic()-prepare_start
    if job["provider"]=="codex":
      command=[plan["codex"],"-a","never","exec","--sandbox","danger-full-access",
        "--ignore-user-config","--skip-git-repo-check",
        "--enable" if (job.get("product_reviewer",False) or job.get("product_researchers",False)) else "--disable","multi_agent",
        "-c",'web_search="'+("live" if plan.get("mode")=="fresh_online_e2e" else "disabled")+'"',"-c",'model_reasoning_effort="'+job["effort"]+'"',
        "--model",job["model"],"--json","-C",str(ws),"-"]
    else:
      command=[plan["claude"],"-p","--model",job["model"],"--effort",job["effort"],
        "--output-format","stream-json","--verbose","--setting-sources","project,local",
        "--tools","Bash,Read,Write,Edit,Glob,Grep,Skill","--allowedTools","Bash,Read,Write,Edit,Glob,Grep,Skill",
        "--strict-mcp-config","--mcp-config","{}", "--settings",'{"disableAllHooks":true}']
    prompt=(job["question"]+"\n\n[이번 평가 실행 조건]\n"+
      "이번 요청은 이 신규 프로젝트에서 관측·보존한 data/business/evaluation-v4 실제 자료만 재사용하는 기획 평가다. "+
      "제품의 기존 Agent·업무 Skill과 일반 코드 Tool을 사용해 판단·검토·현재 버전 저장·원문 자료집/최종 보고서 전달까지 수행해줘. "+
      (("이번 요청의 model_id는 "+job["product"]+"이며 ") if job.get('product') else "제품군/정확 모델은 사용자 질문으로 해석하고 ")+"관련 Tool에는 --data data/business/evaluation-v4를 명시해. "+
      "새 웹 조사·외부 API·소스/설정 변경은 수행하지 마. 근거가 부족한 판단은 가설/보류로 밝혀. "+
      "상세 답안을 특정 문구로 맞추지 말고 실제 자료로 판단해. 내부 원문/계약 전체를 반복 출력하지 말고 필요한 부분을 읽어. "+
      "파일 물리 화면 검수 도구가 없으면 not_run으로 표시하고 최종 응답을 마쳐. 실행 전체 평가 상한은 "+
      str(plan["timeout_seconds"])+"초이며 관측하지 못한 실행시간·토큰·절감률을 만들지 마.")
    if plan.get('mode')=='bounded_corpus':
      prompt+=('\n목표300초/전체상한600초인 현재 workflow를 열고 실제 시계를 확인해. 선택 범위의 등록 자료 전체를 evidence_inventory/read_evidence_batch로 끝까지 전달받아 읽고 기록해. 처음3~4개를 전체로 취급하지 마. 소수 자료만 고르거나 원문 단축으로 시간을 줄이지 마. 코드 렌더러를 사용하고 HTML/프론트를 새로 만들지 마. 마지막90초는 저장·검사·최종 전달에 써. '
        + ('이번 A/B는 선택적 연구 역할 있는 쪽이다. 설치된 product_official_researcher와 product_review_researcher를 처음입력 기준 잔여420초 이상일 때 각1회180초·병렬최대2명으로 사용해 공식 자료와 후기 전체를 분담 독해해. fixed_catalog 모드·정확scope·code/data/context지문·원문 경로·source_ids·실제deadline을 먼저 읽게 하고 온라인조사/쓰기/추가위임은 금지해. source ID 신고만으로 전달/독해를 대신하지 말고 기존 완전본문delivery gate와 실제반환을 대조해 부모만 검토기록·후보/저장을 작성해. 실패/partial/중단/미검토·전체usage를 보존해.' if job.get('product_researchers',False) else
           '후보가 준비되면 실제 네이티브 product_evidence_reviewer를 잔여210초 이상일 때 최대1명/1회90초 호출해. prepare_review_packet 불변packet을 먼저읽게하고 반환후verify_review_packet·현재결속을 대조해. 실제 ID/반환/채택/실패를 남겨. 이 조건은 A/B 검토자 있는 쪽이다.' if job.get('product_reviewer',False) else
           '이번 A/B는 단일 부모만 실행하는 쪽이므로 서브에이전트를 호출하지 마. 같은 기준으로 자체 검토해.'))
    if plan.get("mode")=="fresh_online_e2e":
      prompt=(job["question"]+"\n\n[운영 계측 조건]\n이번 실행은 최신 제품의 빈 catalog에서 실제 새 조사부터 기획·검토·저장·보고서·최종 응답 전달까지 계측한다. 목표300초, 외부 실행기 전체 상한600초다. "
        "새 workflow 기본600초/허용300~1800초와 native 외부600초 경계는 별도다. 600초를 사용하며 예산/소스를 변경하거나 재설정하지 마. 실제 시작시각과 현재시각을 확인하고 최종 전달 시간을 남겨. "
        "속도를 맞추기 위해 리뷰를 극소수만 고르거나 조사 범위를 국소적으로 축소하면 안 된다. 긍정/부정·장기 사용·사용 조건·반례와 여러 원출처/판매처·후기 페이지, 제품 전반 공식 사양/설명서 범위를 실제 접근 가능한 수준에서 넓게 검토해. "
        "임의의 소수 건수·페이지 수를 충분성 기준으로 삼지 마. 원문·날짜·모델 옵션·중복/이전 제품/제외·full/partial 문맥과 source_scan을 보존하고 부족하면 정직하게 보류/한계를 전달해. "
        "원문 추출·일괄 수집·중복 식별·집계·파일 제작은 가능한 일반 코드로 처리하고 근거를 버리거나 의미 판단을 형식검사로 대체하지 마. "
        "현재 설치 Agent·업무 Skill·Tool로 정상적인 요청 기반 흐름을 수행하고 실제 제공되는 웹 도구만 사용해. 브라우저/권한이 없으면 실제 실패로 기록하고 접근 가능한 대안을 검토해. 보안 차단·로그인/결제·CAPTCHA를 우회하지 마. "
        "HTML을 새로 코딩하지 말고 기존 코드 렌더러와 저장 결과를 사용해. 소스/설정 변경, 외부 메시지 전송은 하지 마. "
        "PDF/Word/Excel 실제 물리 화면 검수 도구가 없으면 not_run으로 명시하고 그 상태를 숨기지 말아줘. 300초쯤 실제 현재시각·남은 조사/분석/전달 작업을 확인하고, 600초 안에 결과 또는 정직한 미완료/보류를 저장·최종 전달해.")
      prompt+=("\n필요한 신규 공식자료/후기 조사를 설치된 두 연구역할에 실제 native로 각1회180초·병렬최대2명으로 분담해. 외부잔여420초가 없으면 skipped로 남겨. 정확모델/시장 정체성을 먼저 확정하고 같은scope/mode online/원질문/지문/deadline을 전달해. 부모만 원문관측/검증/직렬등록·기획·저장을 수행해. child summary/잘림/재서술은 원문등록하지 마. 실제artifact가없으면partial이며 부모새fetch는별도관측/시간/SHA로남겨. 중단후등록하지말고마감/미완료/nativeID/반환/전체usage관측한계를보존해." if job.get("product_researchers",False) else
               "\n이번 원인분리 실험은 부모단독이며 서브에이전트를 호출하지 마.")
    print(json.dumps({"job":job["id"],"event":"started","provider":job["provider"],
      "model":job["model"],"effort":job["effort"]}),flush=True)
    result=execute(command,ws,prompt,directory,plan["timeout_seconds"])
    result["preparation_seconds"]=preparation_seconds
    try:result["stored"]=stored(ws)
    except Exception as exc:
      result["stored"]={"error":str(exc)}
      result["observation_errors"].append("database observation: "+str(exc))
    try:result["protected_files_unchanged"]=before==protected(ws)
    except Exception as exc:
      result["protected_files_unchanged"]=None;result["observation_errors"].append("protected files observation: "+str(exc))
    if job["provider"]=="codex":
      try:observation=rollout_observation(result["native_id"])
      except Exception as exc:
        observation={};result["observation_errors"].append("rollout observation: "+str(exc))
      result["rollout"]=observation
      result["usage"]=usage_delta(observation.get("cumulative_usage") or result["reported_usage"])
      metadata=observation.get("metadata") or {}
      result["actual_model"]=metadata.get("model");result["actual_effort"]=metadata.get("effort")
    result.update(job=job,workspace=str(ws),prompt_sha256=sha(directory/"prompt.txt"),stdout_sha256=sha(directory/"native.jsonl"))
    try:result["skills_manifest_sha256"]=sha(ws/"skills/manifest.json")
    except Exception as exc:
      result["skills_manifest_sha256"]=None;result["observation_errors"].append("skills manifest observation: "+str(exc))
    result["observation_complete"]=not result["observation_errors"]
    dump(directory/"result.json",result)
    print(json.dumps({"job":job["id"],"event":"completed","status":result["status"],
      "seconds":result["elapsed_seconds"],"actual_model":result["actual_model"]}),flush=True)
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument("--plan",type=Path,required=True)
    p.add_argument("--provider",choices=("codex","claude"),required=True)
    p.add_argument("--jobs",nargs="*");args=p.parse_args()
    plan=json.loads(args.plan.read_text(encoding="utf-8"))
    identities=[x["id"] for x in plan["jobs"]]
    if len(identities)!=len(set(identities)):raise ValueError("Job IDs must be unique before any execution")
    run_root=Path(plan["run_root"]);run_root.mkdir(parents=True,exist_ok=True)
    jobs=[x for x in plan["jobs"] if x["provider"]==args.provider and (not args.jobs or x["id"] in args.jobs)]
    ceiling=600 if plan.get("mode") in ('fresh_online_e2e','bounded_corpus') else 420
    if len(plan["jobs"])>30 or not 30<=plan["timeout_seconds"]<=ceiling:raise ValueError("Evaluation bound")
    outcomes=[]
    for job in jobs:
      try:outcomes.append(run_job(job,plan,run_root))
      except Exception as exc:
        directory=run_root/job["id"]
        if (directory/"result.json").exists():raise
        receipt={"status":"runner_failed","job":job,"exception":type(exc).__name__+": "+str(exc),
          "native_execution":"unknown; inspect retained logs/process-result if present", "usage":usage_delta(None)}
        process_result=directory/"process-result.json"
        if process_result.exists():
          receipt.update(process_observation=json.loads(process_result.read_text(encoding="utf-8")))
        dump(directory/"result.json",receipt)
        print(json.dumps({"job":job["id"],"event":"runner_failed"}),flush=True)
        outcomes.append(receipt)
    return 0 if outcomes and all(r["status"]=="succeeded" and not r.get("observation_errors") and r.get("protected_files_unchanged") is True for r in outcomes) else 1
if __name__=="__main__":raise SystemExit(main())
