// Local presentation adaptation. Preserve vendor/SOURCE.md and the five original
// files byte-for-byte; no model call, evidence truncation, or product-specific rule.
export function plannerReport({ code, html, css, once }) {
  const replaceFunction = (name, following, replacement) => {
    const start = `function ${name}(`, end = `function ${following}(`
    const a = code.app.indexOf(start), b = code.app.indexOf(end, a + start.length)
    if (a < 0 || b < 0 || code.app.indexOf(start, a + start.length) !== -1) throw new Error(`planner-report: changed function ${name}`)
    code.app = code.app.slice(0, a) + replacement + '\n' + code.app.slice(b)
  }
  // Optional business content comes from the selected canonical result, never
  // an unbound display sidecar. Imported old results simply omit these fields.
  code.adapter = once(code.adapter, 'out.assumptions=strings(result.assumptions);',
    `out.assumptions=strings(result.assumptions);
    if(result.planning_decision!=null){
      var d=result.planning_decision,ids=new Set(out.concepts.map(function(c){return c.id;}));
      if(!obj(d)||typeof d.summary!=='string'||!Array.isArray(d.selected_concept_ids)||d.selected_concept_ids.some(function(id){return typeof id!=='string'||!ids.has(id);})||new Set(d.selected_concept_ids).size!==d.selected_concept_ids.length||!Array.isArray(d.comparisons))throw new ReportDataError('선택 이유의 결과 연결을 읽지 못했습니다.');
      if(d.comparisons.some(function(c){return !obj(c)||!ids.has(c.concept_id)||typeof c.reason!=='string'||typeof c.tradeoff!=='string';})||new Set(d.comparisons.map(function(c){return c.concept_id;})).size!==d.comparisons.length)throw new ReportDataError('후보 비교의 결과 연결을 읽지 못했습니다.');
      out.planningDecision=safeClone(d);
    }
    result.concepts.forEach(function(c,i){if(c.work_draft==null)return;var w=c.work_draft;if(!obj(w)||typeof w.title!=='string'||!Array.isArray(w.columns)||!w.columns.length||w.columns.some(function(v){return typeof v!=='string';})||!Array.isArray(w.rows)||w.rows.some(function(row){return !Array.isArray(row)||row.length!==w.columns.length||row.some(function(v){return typeof v!=='string';});}))throw new ReportDataError('업무 초안을 읽지 못했습니다.');out.concepts[i].workDraft=safeClone(w);});`, 'planner canonical decision and draft')
  code.adapter = once(code.adapter, 'out.title=text(plan.title);out.summary=strings(plan.summary);',
    `out.title=text(plan.title);out.summary=strings(plan.summary);
    out.appendix=obj(plan.appendix)?safeClone(plan.appendix):{sources:[]};
    out.diagnostics=obj(plan.diagnostics)?safeClone(plan.diagnostics):null;
    out.presentation=(function(){
      if(plan.presentation==null)return {summary:[],concepts:{}};
      if(!obj(plan.presentation))throw new ReportDataError('기획 표시 문구는 객체여야 합니다.');
      var p=plan.presentation,view={summary:[],concepts:{}};
      function copyString(from,to,key){if(from[key]==null)return;if(typeof from[key]!=='string')throw new ReportDataError('기획 표시 '+key+'는 문자열이어야 합니다.');if(text(from[key]))to[key]=from[key];}
      function copyTexts(from,to,key){if(from[key]==null)return;if(!Array.isArray(from[key])||from[key].some(function(v){return typeof v!=='string';}))throw new ReportDataError('기획 표시 '+key+'는 문자열 배열이어야 합니다.');to[key]=strings(from[key]);}
      copyString(p,view,'title');copyTexts(p,view,'summary');
      if(p.concepts!=null&&!obj(p.concepts))throw new ReportDataError('제안 표시 문구는 ID별 객체여야 합니다.');
      var ids=new Set(out.concepts.map(function(c){return c.id;}));
      Object.keys(p.concepts||{}).forEach(function(id){if(!ids.has(id))return;var v=p.concepts[id];if(!obj(v))throw new ReportDataError('제안 표시 항목은 객체여야 합니다.');var c={};['title','summary','next_action','follow_up'].forEach(function(k){copyString(v,c,k);});copyTexts(v,c,'background');view.concepts[id]=c;});
      if(p.scope!=null){if(!obj(p.scope))throw new ReportDataError('등록 자료 범위는 객체여야 합니다.');view.scope={};['reviews','facts','other','models'].forEach(function(k){if(p.scope[k]==null)return;if(!Number.isSafeInteger(p.scope[k])||p.scope[k]<0)throw new ReportDataError('등록 자료 수는 0 이상의 정수여야 합니다.');view.scope[k]=p.scope[k];});copyString(p.scope,view.scope,'as_of');}
      return view;
    })();`, 'planner appendix payload')
  code.adapter = once(code.adapter, "return {id:'section-'+(i+1),title:s.title,body:",
    "return {id:'section-'+(i+1),audience:text(s.audience)||'body',title:s.title,body:", 'planner section audience')
  code.app = once(code.app, 'function validationPanel(item){', `function savedLead(value){const whole=plain(value).trim();return /^(.+?[.!?])(?=\\s|$)/s.exec(whole)?.[1]||whole;}
function uniqueTexts(items){const seen=new Set();return list(items).filter(item=>{const value=plain(item).trim();if(!value||seen.has(value))return false;seen.add(value);return true;});}
function proposalView(item,index,presentation){const stored=presentation?.concepts?.[item.id]||{};return {title:stored.title||(item.title&&item.title!==item.body?item.title:'제안 '+String(index+1).padStart(2,'0')),summary:stored.summary||'',background:list(stored.background),nextAction:stored.next_action||plain(list(item.implementationSteps)[0]||''),followUp:stored.follow_up||''};}
function workDraft(draft){return draft?'<section class="planner-work-draft"><h4>'+e(draft.title)+'</h4><div class="table-wrap"><table class="result-table"><thead><tr>'+draft.columns.map(c=>'<th scope="col">'+e(c)+'</th>').join('')+'</tr></thead><tbody>'+draft.rows.map(row=>'<tr>'+row.map(cell=>'<td>'+e(cell)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div></section>':'';}
function scopedConditions(items,title){const rows=uniqueTexts(items);if(!rows.length)return '';return '<div class="planner-conditions"><p class="planner-condition"><b>'+e(title)+'</b> '+e(plain(rows[0]))+'</p>'+(rows.length>1?'<details class="planner-condition-detail"><summary>'+e(title)+' '+(rows.length-1)+'개 더 보기</summary>'+prose(rows.slice(1))+'</details>':'')+'</div>';}
function readable(value){if(value==null)return '';if(Array.isArray(value))return '<ul>'+value.map(v=>'<li>'+readable(v)+'</li>').join('')+'</ul>';if(typeof value==='object')return '<dl class="planner-fields">'+Object.entries(value).map(([key,v])=>'<div><dt>'+e(key.replace(/_/g,' '))+'</dt><dd>'+readable(v)+'</dd></div>').join('')+'</dl>';return e(value);}
function validationPanel(item){`, 'planner display helpers')
  replaceFunction('cards', 'table', `function cards(items,kind='',presentation=null){return '<div class="result-cards">'+list(items).map((item,i)=>{
 const detail=(item.implementationSteps?.length?'<h4>적용 순서</h4>'+prose(uniqueTexts(item.implementationSteps)):'')+(item.validationPlan?'<h4>검증 계획</h4>'+readable(item.validationPlan):'');
 const requirements=scopedConditions(item.requirements,'기획 요구사항');
 const conditions=(item.requiresHardware===true?'<p class="planner-condition">추가 하드웨어가 필요한 후보</p>':'')+scopedConditions(item.assumptions,'적용 전제');
 const concept=kind==='concepts',view=proposalView(item,i,presentation),explicitTitle=item.title&&item.title!==item.body;
 const title=concept?view.title:(explicitTitle?item.title:'조사 내용 '+String(i+1).padStart(2,'0'));
 const summary=concept&&view.summary&&view.summary!==item.body&&!String(item.body||'').includes(view.summary)?'<p class="planner-proposal-lead">'+e(view.summary)+'</p>':'';
 // A label/summary never substitutes for the stored mechanism. Keep the full
 // description open by default and include it in core-only print even if folded.
 const full=item.body?'<details class="planner-description" open><summary>작동 방식과 전체 설명</summary><p>'+e(item.body)+'</p></details>':'';
 const background=concept&&view.background.length?'<div class="planner-background"><h4>이 기획의 배경</h4>'+prose(uniqueTexts(view.background))+'</div>':'';
 return '<article'+(concept?' id="proposal-'+(i+1)+'"':'')+' class="result-card'+(item.workDraft?' planner-draft-card':'')+'" data-claim-kind="'+e(kind)+'" data-claim-index="'+i+'"><h3>'+e(title)+'</h3>'+(concept&&item.body?'':summary)+full+background+workDraft(item.workDraft)+conditions+requirements+refs(item.sourceIds)+(detail?'<details class="planner-detail"><summary>적용·검증 상세</summary>'+detail+'</details>':'')+'</article>';
 }).join('')+'</div>';}`)
  replaceFunction('renderBusiness', 'renderFollowUp', `function renderBusiness(r){
 let html='';
 const decision=r.planningDecision,comp=c=>list(decision?.comparisons).find(v=>v.concept_id===c.id),hardwareDiff=new Set(r.concepts.map(c=>c.requiresHardware)).size>1;
 if(decision?.summary)html+='<p class="planner-decision">'+e(decision.summary)+'</p>';
 if(r.concepts.length===1&&comp(r.concepts[0])){const choice=comp(r.concepts[0]);html+='<div class="planner-decision">'+(choice.reason?'<p><strong>선택 이유</strong> '+e(choice.reason)+'</p>':'')+(choice.tradeoff?'<p><strong>고려할 점</strong> '+e(choice.tradeoff)+'</p>':'')+'</div>';}
 if(r.concepts.length>1)html+=section('제안 비교','<div class="table-wrap"><table class="result-table planner-comparison"><thead><tr><th>제안</th><th>기획 요약</th>'+(decision?'<th>선택 이유</th><th>고려할 점</th>':'')+(hardwareDiff?'<th class="planner-hardware">추가 하드웨어</th>':'')+'</tr></thead><tbody>'+r.concepts.map((c,i)=>{const v=proposalView(c,i,r.presentation),choice=comp(c);return '<tr><th scope="row"><a href="#proposal-'+(i+1)+'">'+e(v.title)+'</a>'+(decision?.selected_concept_ids.includes(c.id)?'<span class="planner-selected">착수 제안</span>':'')+'</th><td>'+(v.summary?e(v.summary):'<a href="#proposal-'+(i+1)+'">전체 설명 보기</a>')+'</td>'+(decision?'<td>'+e(choice?.reason||'')+'</td><td>'+e(choice?.tradeoff||'')+'</td>':'')+(hardwareDiff?'<td>'+e(c.requiresHardware===true?'필요':c.requiresHardware===false?'추가 없음':'')+'</td>':'')+'</tr>';}).join('')+'</tbody></table></div>');
 if(r.concepts.length)html+=section('제안하는 상품기획',cards(r.concepts,'concepts',r.presentation));
 const hasLinkedBackground=r.concepts.some(c=>proposalView(c,0,r.presentation).background.length);
 const background=r.remainingDiscomforts.length?r.remainingDiscomforts:r.discomforts;
 if(background.length)html+=hasLinkedBackground?'<details class="planner-detail"><summary>기획 배경 전체</summary>'+cards(background,'remainingDiscomforts')+'</details>':section('기획의 배경',cards(background,'remainingDiscomforts'));
 if(r.existingFeatures.length)html+='<details class="planner-detail"><summary>기존 기능과 비교한 내용</summary>'+cards(r.existingFeatures,'existingFeatures')+'</details>';
 // Global and per-proposal assumptions have different scope, even if wording matches.
 const conditions=uniqueTexts(r.assumptions);
 if(conditions.length)html+=scopedConditions(conditions,'전체 기획의 적용 조건 · 조사 범위');
 return html;
}`)
  replaceFunction('renderFollowUp', 'renderExecution', `function renderFollowUp(r){
 // Implementation steps already belong to each proposal's detail. Repeating them
 // again as a task list creates pages without adding a decision for the planner.
 const storedSteps=new Set(r.concepts.flatMap(c=>list(c.implementationSteps)).map(plain));
 const next=uniqueTexts(r.nextSteps).filter(s=>!storedSteps.has(plain(s)));
 const starts=r.concepts.map((c,i)=>proposalView(c,i,r.presentation)).filter(v=>v.nextAction||v.followUp).map(v=>'<li><b>'+e(v.title)+'</b>'+(v.nextAction?'<p>'+e(v.nextAction)+'</p>':'')+(v.followUp?'<details class="planner-detail"><summary>이어서 요청할 문장</summary><blockquote>'+e(v.followUp)+'</blockquote></details>':'')+'</li>');
 return starts.length||next.length?section('다음 행동',(starts.length?'<ul class="planner-starts">'+starts.join('')+'</ul>':'')+prose(next)):'';
}`)
  code.app = once(code.app, "const summary=report.summary?.length?report.summary:(report.conclusion?[report.conclusion]:[report.request||'하네스에서 전달한 결과를 본문과 근거 목록으로 정리했습니다.']);",
    "const summary=uniqueTexts(report.summary?.length?report.summary:(report.presentation?.summary?.length?report.presentation.summary:(report.concepts.length?report.concepts.map(c=>savedLead(c.body)):[report.status.label])));", 'planner key conclusions')
  code.app = once(code.app, "$('#report-summary').innerHTML=summary.map(p=>'<p>'+e(plain(p))+'</p>').join('');",
    `$('#report-summary').innerHTML=summary.map((p,i)=>'<div class="planner-judgment"><p>'+e(plain(p))+'</p>'+(!report.summary?.length&&report.concepts[i]?refs(report.concepts[i].sourceIds):'')+'</div>').join('');
 $('.report-opening').hidden=!report.summary?.length&&report.concepts.length>0;
 const scope=report.presentation?.scope,scopeItems=scope?[[scope.reviews,'후기','건'],[scope.facts,'제품 자료','건'],[scope.other,'기타','건'],[scope.models,'모델','개']].filter(row=>Number.isInteger(row[0])).map(row=>row[1]+' '+fmt(row[0])+row[2]):[];
 $('#report-scope').textContent=scopeItems.length?'선택 등록 자료 · '+scopeItems.join(' · ')+(scope.as_of?' · 확인일 '+scope.as_of:''):'';$('#report-scope').hidden=!scopeItems.length;`, 'planner summary evidence')
  code.app = once(code.app, "let body=hasBusiness?renderBusiness(report):(report.evidence.length?renderKeywords(report):'');\r\n if(report.sections.length)body+=renderPlanSections(report.sections);\r\n body+=renderFollowUp(report);\r\n body+=renderExecution(report);",
    `let body=hasBusiness?renderBusiness(report):'';
 if(report.sections.length)body+=renderPlanSections(report.sections.filter(s=>!hasBusiness&&s.audience!=='appendix'));
 body+=renderFollowUp(report);
 $('#appendix-analysis').innerHTML=(report.request?section('기획 요청과 조사 범위',prose([report.request])+(report.products.length?table(['대상','제품군'],report.products.map(p=>[p.model||p.name||'미제공',label(p.category)||'미제공'])):'')):'')+(report.discomforts.length?section('조사에서 정리한 불편',cards(report.discomforts,'discomforts')):'')+(report.evidence.length?renderKeywords(report):'')+renderPlanSections(report.sections.filter(s=>hasBusiness||s.audience==='appendix'));
 const appendix=report.appendix||{},registered=list(appendix.sources);
 $('#registered-sources').innerHTML=(appendix.scope_note?'<p class="paper-note">'+e(appendix.scope_note)+'</p>':'')+registered.map((source,i)=>'<details class="registered-source"><summary>등록 원문 '+(i+1)+' · '+e(source.title||source.model_id||source.kind||'자료')+'</summary><blockquote>'+e(source.text||'')+'</blockquote>'+((source.source_url||source.origin?.source_url)&&safeUrl(source.source_url||source.origin?.source_url)?'<a class="source-url" href="'+e(safeUrl(source.source_url||source.origin?.source_url))+'" target="_blank" rel="noopener noreferrer">원문 열기 ↗</a>':'')+'<details><summary>자료 식별 정보</summary>'+readable(Object.fromEntries(Object.entries(source).filter(([key])=>key!=='text')))+'</details></details>').join('');
 $('#appendix-analysis').innerHTML+=(report.decisionNotes.length?section('분석 판단과 조사 메모',report.decisionNotes.map(n=>'<div class="planner-judgment"><span class="source-kind">'+e({source_fact:'확인 사실',ai_interpretation:'인공지능 해석',unverified:'미확인'}[n.basis]||'기록된 판단')+'</span><p>'+e(n.body||n.title)+'</p>'+refs(n.sourceIds)+'</div>').join('')):'');
 $('#diagnostic-data').textContent=JSON.stringify({execution:report.execution,review:report.review,warnings:report.warnings,coverage:appendix.coverage||null,records:report.diagnostics||null},null,2);
 $('#diagnostic-metrics').innerHTML=renderExecution(report);`, 'planner main and appendix separation')
  // Warnings which change applicability stay visible; internal state records are
  // reached only via diagnostics. No automatic content/length cutoff is applied.
  code.app = once(code.app, "$('#source-description').textContent='본문·표·그래프에 연결된 '+report.evidence.length+'개 자료입니다. 항목을 검색하고 원문을 확인할 수 있습니다.';",
    "$('#source-description').textContent='본문의 근거 번호로 연결된 자료입니다. 원문은 필요한 항목만 열어 확인하세요. 기본 인쇄에는 이 부록을 포함하지 않습니다.';", 'planner source wording')
  code.app = once(code.app, "e(fileLabel||report.meta.sourceFile||'연결된 하네스 결과')", "'상품기획 보고서'", 'planner hide technical filename')
  code.app = once(code.app, "report.title||[report.product.model||report.product.category||'키친 상품기획','분석 결과 보고서'].join('\\n')", "report.presentation?.title||report.title||[label(report.product.category)||'상품기획','기획 제안서'].join(' ')", 'planner report heading')
  code.app = once(code.app, 'if(report.warnings.length)body+=', "const visibleWarnings=report.warnings.filter(w=>w!=='저장된 결과의 의미와 사업 적용 가능성은 별도 검토가 필요합니다.'&&!w.startsWith('사용량은 기록된 호출의 관측값'));if(visibleWarnings.length)body+=", 'planner diagnostic warnings')
  code.app = once(code.app, "report.warnings.map(w=>'<li>'+e(w)+'</li>')", "visibleWarnings.map(w=>'<li>'+e(w)+'</li>')", 'planner applicable warnings')
  code.app = once(code.app, "document.addEventListener('click',event=>{if(event.target.closest('.evidence-refs a')){",
    `document.addEventListener('click',event=>{const anchor=event.target.closest('a[href^="#"]');if(anchor){event.preventDefault();let id;try{id=decodeURIComponent(anchor.getAttribute('href').slice(1));}catch(_){id='';}setTimeout(()=>{const destination=document.getElementById(id);if(!destination)return;let parent=destination.parentElement;while(parent){if(parent.tagName==='DETAILS')parent.open=true;parent=parent.parentElement;}destination.scrollIntoView({behavior:'smooth',block:'start'});},0);}if(event.target.closest('a[href="#sources"]'))$('#report-appendix').open=true;if(event.target.closest('.evidence-refs a')){$('#report-appendix').open=true;`, 'planner citation expansion')
  code.app = once(code.app, "const open=event.target.closest('[data-trace-kind]');if(open){", "const open=event.target.closest('[data-trace-kind]');if(open){$('#report-appendix').open=true;", 'planner trace expansion')
  code.app = once(code.app, "window.addEventListener('beforeprint',()=>{printDetails=$$('#paper details:not([open])');printDetails.forEach(d=>d.open=true);});\r\nwindow.addEventListener('afterprint',()=>{printDetails.forEach(d=>d.open=false);printDetails=[];});",
    `window.addEventListener('beforeprint',()=>{const all=$('#include-appendix').checked;document.body.classList.toggle('print-with-appendix',all);printDetails=[...new Set([...$$('#result-body details.planner-description:not([open]),#result-body details.planner-condition-detail:not([open])'),...(all?$$('#paper details:not([open]):not(.report-diagnostics)'):[])])];printDetails.forEach(d=>d.open=true);});
window.addEventListener('afterprint',()=>{printDetails.forEach(d=>d.open=false);printDetails=[];document.body.classList.remove('print-with-appendix');});`, 'planner intentional print scope')
  // Move original source and trace elements (including their stable anchors) into
  // an optional appendix rather than copying or dropping any evidence record.
  const trace = html.match(/<section id="evidence-trace"[^]*?<div id="trace-workspace" hidden><\/div><\/section>/g)
  if (!trace || trace.length !== 1) throw new Error('planner-report: changed trace section')
  html = once(html, trace[0], '', 'planner move trace')
  html = once(html, '<section class="paper-section" id="sources"', '<details id="report-appendix" class="report-appendix"><summary>근거·상세 자료 보기</summary><p id="report-scope" class="report-scope" hidden></p>'+trace[0]+'<div id="appendix-analysis"></div><section class="paper-section" id="registered-evidence"><h2>선택 등록 원문 전체</h2><div id="registered-sources"></div></section><section class="paper-section" id="sources"', 'planner appendix opening')
  html = once(html, '<div class="download-actions"><button id="download-data">결과 데이터 저장 ↓</button>', '<div class="download-actions">', 'planner move data download')
  html = once(html, '</details></section></article></section>', '</details></section></details><details class="report-diagnostics"><summary>고급 · 실행·연결 진단</summary><div id="diagnostic-metrics"></div><pre id="diagnostic-data"></pre><button id="download-data">진단용 결과 데이터 저장</button></details></article></section>', 'planner appendix closing')
  html = once(html, '<button id="download-html">보고서 파일 저장 ↓</button>', '', 'planner move HTML save from appendix')
  html = once(html, '<button id="print-report">인쇄 / PDF</button>', '<button id="download-html">보고서 파일 저장</button><button id="print-report">보고서 인쇄</button><label class="print-scope"><input type="checkbox" id="include-appendix">부록 포함</label>', 'planner visible save and print choice')
  html = once(html, '<h2 id="abstract-title">결과 요약</h2>', '<h2 id="abstract-title">핵심 결론</h2>', 'planner conclusion title')
  // Keep one accessible contents drawer. Suppress redundant navigation and normal
  // saved-status chrome while retaining error notices, imports and prior turns.
  html = once(html, '<div class="chapter-links"><a href="#paper">요약</a><a href="#result-body">분석 결과</a><a href="#sources">근거·출처</a></div>', '', 'planner single contents path')
  html = once(html, '<a class="back-to-contents" href="#quick-contents-title" aria-label="목차 바로가기로 이동">목차로 ↑</a>', '', 'planner remove duplicate contents control')
  css += `
/* Planner-first output. Detail visibility never changes the stored source/result. */
#report-footer,.quick-contents,#report-keywords,#report-byline,.report-context:has(.report-status.completed){display:none}
.result-card.planner-draft-card{grid-column:1/-1}.planner-comparison th:first-child{min-width:9em;width:16%}
.planner-decision{font-size:15px;line-height:1.8;background:#edf5e9;padding:16px;border-radius:10px}.planner-selected{display:block;font-size:10px;color:#2f7d4f;margin-top:4px}.planner-work-draft{background:#f8fbf6;border:1px solid #cbdcc8;border-radius:10px;padding:14px;margin:18px 0}.planner-work-draft h4{font-size:15px;margin:0 0 12px}.planner-work-draft td,.planner-work-draft th{white-space:pre-wrap;font-size:12px;vertical-align:top}
.report-opening[hidden]{display:none!important}.planner-proposal-lead{font-size:14px;line-height:1.8}.result-card>h3{font-size:17px;line-height:1.5;margin:0 0 10px}.paper-title{font-size:clamp(21px,2.5vw,29px);line-height:1.25}.result-cards{gap:20px}.result-card{padding:21px}.paper-header{padding:10px 0!important;margin:0 0 12px;min-height:0}.paper-header>p:first-child{display:none}.paper-header>p:last-child{font-size:11px;margin-top:7px}.planner-starts{font-size:13px;line-height:1.8}.planner-description{margin:12px 0}.planner-description>summary{font-size:12px;font-weight:700;cursor:pointer}.planner-description>p{font-size:13px;line-height:1.8;white-space:pre-wrap}.planner-background h4{font-size:12px;margin:14px 0 6px}.planner-background .paper-prose{font-size:12px}.planner-condition-detail{font-size:12px;margin:5px 0 10px}.planner-condition-detail>summary{cursor:pointer}.report-scope{font-size:11px;color:var(--muted);margin:8px 0 18px}.planner-comparison td{white-space:normal;vertical-align:top;font-size:12px;padding:12px 8px}.planner-comparison th{vertical-align:top;font-size:12px}.planner-comparison tbody th{font-weight:600}.planner-comparison .planner-hardware{white-space:nowrap;min-width:6em}.planner-comparison a{text-decoration:underline;text-underline-offset:3px}
.report-appendix,.report-diagnostics{margin:32px 0;border-top:1px solid var(--line);padding:20px 0}.report-appendix>summary,.report-diagnostics>summary{font-weight:700;cursor:pointer}.report-diagnostics pre{white-space:pre-wrap;font:11px/1.7 Consolas,monospace}.registered-source{padding:15px 0;border-bottom:1px solid var(--line)}.registered-source>summary{cursor:pointer}.registered-source blockquote{white-space:pre-wrap;font-size:12px;line-height:1.8}.planner-detail{margin-top:16px;border-top:1px solid var(--line);padding-top:12px}.planner-detail>summary{font-size:12px;cursor:pointer}.planner-condition{font-size:12px;line-height:1.7;margin-top:12px}.planner-condition .paper-prose{columns:auto;font-size:12px}.planner-fields{font-size:12px;line-height:1.8}.planner-fields>div{margin:9px 0}.planner-fields dt{font-weight:700}.planner-fields dd{margin:3px 0 0}.planner-fields li{margin:5px 0}.print-scope{font-size:11px;white-space:nowrap}.paper-section{min-height:0}.result-card{break-inside:auto}.report-opening{grid-template-columns:minmax(0,1fr)}.quick-contents{border-left:0;border-top:1px solid var(--line);padding:15px 0 0}.paper-prose{columns:auto}
@media print{.report-diagnostics,.print-scope,.report-appendix>summary{display:none!important}body:not(.print-with-appendix) .report-appendix,body:not(.print-with-appendix) .planner-detail,body:not(.print-with-appendix) .trace-section{display:none!important}.planner-description,.planner-condition-detail{display:block!important}.planner-description>summary{display:none}.planner-description>p{font-size:10px}.planner-condition-detail,.planner-condition{font-size:9px}.paper-prose{columns:auto!important}.paper-section{break-before:auto}.result-card{break-inside:auto}.paper-header{margin-bottom:9px}.paper-main{display:block}.report-opening{display:block}.quick-contents{display:none}.result-cards{grid-template-columns:repeat(2,minmax(0,1fr))}.planner-comparison th,.planner-comparison td{white-space:normal;font-size:9px;padding:7px 5px}body.print-with-appendix .report-appendix{display:block!important;break-before:page}body.print-with-appendix .planner-detail{display:block!important}body.print-with-appendix .trace-section{display:block!important}}
`
  return { code, html, css }
}
