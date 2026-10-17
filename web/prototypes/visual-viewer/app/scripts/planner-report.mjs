// Local presentation adaptation. Preserve vendor/SOURCE.md and the five original
// files byte-for-byte; no model call, evidence truncation, or product-specific rule.
export function plannerReport({ code, html, css, once }) {
  const replaceFunction = (name, following, replacement) => {
    const start = `function ${name}(`, end = `function ${following}(`
    const a = code.app.indexOf(start), b = code.app.indexOf(end, a + start.length)
    if (a < 0 || b < 0 || code.app.indexOf(start, a + start.length) !== -1) throw new Error(`planner-report: changed function ${name}`)
    code.app = code.app.slice(0, a) + replacement + '\n' + code.app.slice(b)
  }
  code.adapter = once(code.adapter, 'out.title=text(plan.title);out.summary=strings(plan.summary);',
    `out.title=text(plan.title);out.summary=strings(plan.summary);
    out.appendix=obj(plan.appendix)?safeClone(plan.appendix):{sources:[]};
    out.diagnostics=obj(plan.diagnostics)?safeClone(plan.diagnostics):null;`, 'planner appendix payload')
  code.adapter = once(code.adapter, "return {id:'section-'+(i+1),title:s.title,body:",
    "return {id:'section-'+(i+1),audience:text(s.audience)||'body',title:s.title,body:", 'planner section audience')
  code.app = once(code.app, 'function validationPanel(item){', `function uniqueTexts(items){const seen=new Set();return list(items).filter(item=>{const value=plain(item).trim();if(!value||seen.has(value))return false;seen.add(value);return true;});}
function readable(value){if(value==null)return '';if(Array.isArray(value))return '<ul>'+value.map(v=>'<li>'+readable(v)+'</li>').join('')+'</ul>';if(typeof value==='object')return '<dl class="planner-fields">'+Object.entries(value).map(([key,v])=>'<div><dt>'+e(key.replace(/_/g,' '))+'</dt><dd>'+readable(v)+'</dd></div>').join('')+'</dl>';return e(value);}
function validationPanel(item){`, 'planner display helpers')
  replaceFunction('cards', 'table', `function cards(items,kind=''){return '<div class="result-cards">'+list(items).map((item,i)=>{
 const detail=(item.implementationSteps?.length?'<h4>적용 순서</h4>'+prose(uniqueTexts(item.implementationSteps)):'')+(item.validationPlan?'<h4>검증 계획</h4>'+readable(item.validationPlan):'');
 const requirements=item.requirements?.length?'<div class="planner-requirements"><h4>기획 요구사항</h4><ul>'+uniqueTexts(item.requirements).map(t=>'<li>'+e(plain(t))+'</li>').join('')+'</ul></div>':'';
 const conditions=(typeof item.requiresHardware==='boolean'?'<p class="planner-condition">'+(item.requiresHardware?'추가 하드웨어가 필요한 후보':'추가 하드웨어 없이 검토하는 후보')+'</p>':'')+(item.assumptions?.length?'<div class="planner-condition"><b>적용 전제</b>'+prose(uniqueTexts(item.assumptions))+'</div>':'');
 return '<article class="result-card" data-claim-kind="'+e(kind)+'" data-claim-index="'+i+'"><h3>'+e(item.title||item.body||'항목 '+(i+1))+'</h3>'+(item.body&&item.body!==item.title?'<p>'+e(item.body)+'</p>':'')+requirements+conditions+(kind==='concepts'&&item.validationPlan?'<p class="planner-condition">효과는 아직 실측하지 않은 기획 후보입니다.</p>':'')+refs(item.sourceIds)+(detail?'<details class="planner-detail"><summary>적용·검증 상세</summary>'+detail+'</details>':'')+(kind==='concepts'?'<button class="trace-inline-open" data-trace-kind="concept" data-trace-index="'+i+'">이 개선안의 근거 보기 →</button>':'')+'</article>';
 }).join('')+'</div>';}`)
  replaceFunction('renderBusiness', 'renderFollowUp', `function renderBusiness(r){
 let html='';
 if(r.remainingDiscomforts.length)html+=section('해결해야 할 문제',cards(r.remainingDiscomforts,'remainingDiscomforts'));
 else if(r.discomforts.length)html+=section('해결해야 할 문제',cards(r.discomforts,'discomforts'));
 if(r.existingFeatures.length)html+=section('현재 기능과 기획의 출발점',cards(r.existingFeatures,'existingFeatures'));
 if(r.concepts.length)html+=section('제안하는 상품기획',cards(r.concepts,'concepts'));
 const localConditions=new Set(r.concepts.flatMap(c=>list(c.assumptions)).map(plain));
 const conditions=uniqueTexts(r.assumptions).filter(a=>!localConditions.has(plain(a)));
 if(conditions.length)html+=section('적용 전에 확인할 조건',prose(conditions));
 return html;
}`)
  replaceFunction('renderFollowUp', 'renderExecution', `function renderFollowUp(r){
 // Implementation steps already belong to each proposal's detail. Repeating them
 // again as a task list creates pages without adding a decision for the planner.
 const storedSteps=new Set(r.concepts.flatMap(c=>list(c.implementationSteps)).map(plain));
 const next=uniqueTexts(r.nextSteps).filter(s=>!storedSteps.has(plain(s)));
 const starts=r.concepts.filter(c=>c.implementationSteps?.length).map(c=>'<li><b>'+e(c.title||c.body)+'</b><p>'+e(plain(c.implementationSteps[0]))+'</p></li>');
 return starts.length||next.length?section('다음 행동',(starts.length?'<p class="paper-note">각 기획에 저장된 첫 단계를 표시합니다. 수행 완료나 후보의 우선순위를 뜻하지 않습니다.</p><ul class="planner-starts">'+starts.join('')+'</ul>':'')+prose(next)):'';
}`)
  code.app = once(code.app, "const summary=report.summary?.length?report.summary:(report.conclusion?[report.conclusion]:[report.request||'하네스에서 전달한 결과를 본문과 근거 목록으로 정리했습니다.']);",
    "const summary=uniqueTexts(report.summary?.length?report.summary:(report.decisionNotes.length?report.decisionNotes.map(n=>n.body||n.title):(report.conclusion?[report.conclusion]:[report.request||'상품기획 결과를 확인하세요.'])));", 'planner key conclusions')
  code.app = once(code.app, "$('#report-summary').innerHTML=summary.map(p=>'<p>'+e(plain(p))+'</p>').join('');",
    `$('#report-summary').innerHTML=report.decisionNotes.length&&!report.summary?.length?report.decisionNotes.map(n=>'<div class="planner-judgment"><span class="source-kind">'+e({source_fact:'확인 사실',ai_interpretation:'인공지능 해석',unverified:'미확인'}[n.basis]||'기록된 판단')+'</span><p>'+e(n.body||n.title)+'</p>'+refs(n.sourceIds)+'</div>').join(''):summary.map(p=>'<p>'+e(plain(p))+'</p>').join('');`, 'planner summary evidence')
  code.app = once(code.app, "let body=hasBusiness?renderBusiness(report):(report.evidence.length?renderKeywords(report):'');\r\n if(report.sections.length)body+=renderPlanSections(report.sections);\r\n body+=renderFollowUp(report);\r\n body+=renderExecution(report);",
    `let body=hasBusiness?renderBusiness(report):'';
 if(report.sections.length)body+=renderPlanSections(report.sections.filter(s=>!hasBusiness&&s.audience!=='appendix'));
 body+=renderFollowUp(report);
 $('#appendix-analysis').innerHTML=(report.request?section('기획 요청과 조사 범위',prose([report.request])+(report.products.length?table(['대상','제품군'],report.products.map(p=>[p.model||p.name||'미제공',label(p.category)||'미제공'])):'')):'')+(report.discomforts.length?section('조사에서 정리한 불편',cards(report.discomforts,'discomforts')):'')+(report.evidence.length?renderKeywords(report):'')+renderPlanSections(report.sections.filter(s=>hasBusiness||s.audience==='appendix'));
 const appendix=report.appendix||{},registered=list(appendix.sources);
 $('#registered-sources').innerHTML=(appendix.scope_note?'<p class="paper-note">'+e(appendix.scope_note)+'</p>':'')+registered.map((source,i)=>'<details class="registered-source"><summary>등록 원문 '+(i+1)+' · '+e(source.title||source.model_id||source.kind||'자료')+'</summary><blockquote>'+e(source.text||'')+'</blockquote>'+((source.source_url||source.origin?.source_url)&&safeUrl(source.source_url||source.origin?.source_url)?'<a class="source-url" href="'+e(safeUrl(source.source_url||source.origin?.source_url))+'" target="_blank" rel="noopener noreferrer">원문 열기 ↗</a>':'')+'<details><summary>자료 식별 정보</summary>'+readable(Object.fromEntries(Object.entries(source).filter(([key])=>key!=='text')))+'</details></details>').join('');
 $('#diagnostic-data').textContent=JSON.stringify({execution:report.execution,review:report.review,coverage:appendix.coverage||null,records:report.diagnostics||null},null,2);
 $('#diagnostic-metrics').innerHTML=renderExecution(report);`, 'planner main and appendix separation')
  // Warnings which change applicability stay visible; internal state records are
  // reached only via diagnostics. No automatic content/length cutoff is applied.
  code.app = once(code.app, "$('#source-description').textContent='본문·표·그래프에 연결된 '+report.evidence.length+'개 자료입니다. 항목을 검색하고 원문을 확인할 수 있습니다.';",
    "$('#source-description').textContent='본문의 근거 번호로 연결된 자료입니다. 원문은 필요한 항목만 열어 확인하세요. 기본 인쇄에는 이 부록을 포함하지 않습니다.';", 'planner source wording')
  code.app = once(code.app, "document.addEventListener('click',event=>{if(event.target.closest('.evidence-refs a')){",
    "document.addEventListener('click',event=>{if(event.target.closest('a[href=\"#sources\"]'))$('#report-appendix').open=true;if(event.target.closest('.evidence-refs a')){$('#report-appendix').open=true;", 'planner citation expansion')
  code.app = once(code.app, "const open=event.target.closest('[data-trace-kind]');if(open){", "const open=event.target.closest('[data-trace-kind]');if(open){$('#report-appendix').open=true;", 'planner trace expansion')
  code.app = once(code.app, "window.addEventListener('beforeprint',()=>{printDetails=$$('#paper details:not([open])');printDetails.forEach(d=>d.open=true);});\r\nwindow.addEventListener('afterprint',()=>{printDetails.forEach(d=>d.open=false);printDetails=[];});",
    `window.addEventListener('beforeprint',()=>{const all=$('#include-appendix').checked;document.body.classList.toggle('print-with-appendix',all);printDetails=all?$$('#paper details:not([open]):not(.report-diagnostics)'):[];printDetails.forEach(d=>d.open=true);});
window.addEventListener('afterprint',()=>{printDetails.forEach(d=>d.open=false);printDetails=[];document.body.classList.remove('print-with-appendix');});`, 'planner intentional print scope')
  // Move original source and trace elements (including their stable anchors) into
  // an optional appendix rather than copying or dropping any evidence record.
  const trace = html.match(/<section id="evidence-trace"[^]*?<div id="trace-workspace" hidden><\/div><\/section>/g)
  if (!trace || trace.length !== 1) throw new Error('planner-report: changed trace section')
  html = once(html, trace[0], '', 'planner move trace')
  html = once(html, '<section class="paper-section" id="sources"', '<details id="report-appendix" class="report-appendix"><summary>근거·상세 자료 보기</summary>'+trace[0]+'<div id="appendix-analysis"></div><section class="paper-section" id="registered-evidence"><h2>선택 등록 원문 전체</h2><div id="registered-sources"></div></section><section class="paper-section" id="sources"', 'planner appendix opening')
  html = once(html, '<div class="download-actions"><button id="download-data">결과 데이터 저장 ↓</button>', '<div class="download-actions">', 'planner move data download')
  html = once(html, '</details></section></article></section>', '</details></section></details><details class="report-diagnostics"><summary>고급 · 실행·연결 진단</summary><div id="diagnostic-metrics"></div><pre id="diagnostic-data"></pre><button id="download-data">진단용 결과 데이터 저장</button></details></article></section>', 'planner appendix closing')
  html = once(html, '<button id="print-report">인쇄 / PDF</button>', '<label class="print-scope"><input type="checkbox" id="include-appendix">부록 포함</label><button id="print-report">보고서 인쇄</button>', 'planner print choice')
  html = once(html, '<h2 id="abstract-title">결과 요약</h2>', '<h2 id="abstract-title">핵심 결론</h2>', 'planner conclusion title')
  css += `
/* Planner-first output. Detail visibility never changes the stored source/result. */
.report-appendix,.report-diagnostics{margin:32px 0;border-top:1px solid var(--line);padding:20px 0}.report-appendix>summary,.report-diagnostics>summary{font-weight:700;cursor:pointer}.report-diagnostics pre{white-space:pre-wrap;font:11px/1.7 Consolas,monospace}.registered-source{padding:15px 0;border-bottom:1px solid var(--line)}.registered-source>summary{cursor:pointer}.registered-source blockquote{white-space:pre-wrap;font-size:12px;line-height:1.8}.planner-detail{margin-top:16px;border-top:1px solid var(--line);padding-top:12px}.planner-detail>summary{font-size:12px;cursor:pointer}.planner-condition{font-size:12px;line-height:1.7;margin-top:12px}.planner-condition .paper-prose{columns:auto;font-size:12px}.planner-fields{font-size:12px;line-height:1.8}.planner-fields>div{margin:9px 0}.planner-fields dt{font-weight:700}.planner-fields dd{margin:3px 0 0}.planner-fields li{margin:5px 0}.print-scope{font-size:11px;white-space:nowrap}.paper-section{min-height:0}.result-card{break-inside:auto}.report-opening{grid-template-columns:minmax(0,1fr)}.quick-contents{border-left:0;border-top:1px solid var(--line);padding:15px 0 0}.paper-prose{columns:auto}
@media print{.report-diagnostics,.print-scope,.report-appendix>summary{display:none!important}body:not(.print-with-appendix) .report-appendix,body:not(.print-with-appendix) .planner-detail,body:not(.print-with-appendix) .trace-section{display:none!important}.paper-prose{columns:auto!important}.paper-section{break-before:auto}.result-card{break-inside:auto}.paper-header{margin-bottom:12px}.paper-main{display:block}.report-opening{display:block}.quick-contents{display:none}.result-cards{grid-template-columns:repeat(2,minmax(0,1fr))}body.print-with-appendix .report-appendix{display:block!important;break-before:page}body.print-with-appendix .planner-detail{display:block!important}body.print-with-appendix .trace-section{display:block!important}}
`
  return { code, html, css }
}
