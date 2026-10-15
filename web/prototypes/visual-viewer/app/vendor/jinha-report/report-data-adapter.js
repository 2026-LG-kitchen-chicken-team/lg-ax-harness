/* 정이량 팀 하네스 결과 → 독자용 화면 데이터. 모델 호출·네트워크·HTML 실행 없음.
 * 모든 문자열은 텍스트입니다. 렌더러는 textContent를 사용해야 합니다.
 * 지원: export_session JSON 본문, get_turn/current_request 응답, ProductResult,
 * report_plan, {export, report_plan?, demo?, meta?} 결합 입력.
 */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.HarnessReportAdapter = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var FORMAT_VERSION = '1.0';
  var MAX_JSON_CHARS = 16 * 1024 * 1024;
  var KEYWORD_METHOD = '본문이 있는 출처를 ID별로 자료 1건으로 계산합니다. 같은 출처 ID의 동일 본문은 한 번만 세며, 제목·요약·제안 문장은 집계하지 않습니다. 공백과 문장부호로 구분한 2글자 이상 표기에서 숫자·주소·식별자·일반 연결어를 제외합니다. 영문 대소문자는 합치지만 조사·활용형은 합치지 않습니다. 언급 자료 수는 해당 표기가 나온 자료 수이며, 등장 횟수는 그 자료 본문에서 나온 전체 횟수입니다. 서로 다른 ID에 같은 본문이 있으면 별도 자료로 계산합니다.';
  var KEYWORD_STOP_WORDS = new Set(['그리고','그러나','하지만','또는','또한','따라서','그래서','그런데','때문에','대한','대해','통해','위한','위해','것은','것을','것이','것도','것과','것으로','있는','있다','있고','있으며','있습니다','없는','없다','없고','없으며','없습니다','한다','하는','하여','하며','합니다','했다','하였다','했습니다','된다','되는','되어','되며','됩니다','이런','그런','이러한','그러한','어떤','무엇이','이것','그것','해당','관련','경우','정도','때문','the','and','or','but','a','an','to','of','in','on','for','with','by','as','is','are','was','were','be','been','it','its','this','that','these','those','from','at','not','can','could','would','should','will']);
  var SUPPORTED_FORMATS = Object.freeze(['team-export-session', 'team-turn', 'team-product-result', 'team-report-plan', 'team-report-envelope', 'team-cli-error']);
  var STATUS_LABELS = Object.freeze({completed:'기획 초안 완료',held:'기획 보류',needs_input:'추가 입력 필요',failed:'실패',cancelled:'취소',rejected:'검토 거절',stale:'이전 결과 · 재확인 필요',timeout:'시간 초과',pending:'진행 대기',research_required:'추가 조사 필요',researching:'조사 중',revising:'수정 중',needs_revision:'수정 필요',draft:'초안',unknown:'상태 미제공'});
  function ReportDataError(message, code) { this.name = 'ReportDataError'; this.message = message; this.code = code || 'invalid_report_data'; if (Error.captureStackTrace) Error.captureStackTrace(this, ReportDataError); }
  ReportDataError.prototype = Object.create(Error.prototype);
  ReportDataError.prototype.constructor = ReportDataError;
  function UnsupportedReportSchemaError(message) { ReportDataError.call(this, message || '지원하는 하네스 결과 형식이 아닙니다. export_session JSON 본문 또는 report_plan을 선택해 주세요.', 'unsupported_schema'); this.name = 'UnsupportedReportSchemaError'; }
  UnsupportedReportSchemaError.prototype = Object.create(ReportDataError.prototype);
  UnsupportedReportSchemaError.prototype.constructor = UnsupportedReportSchemaError;
  function obj(v) { return v !== null && typeof v === 'object' && !Array.isArray(v); }
  function arr(v) { return Array.isArray(v) ? v : []; }
  function text(v) { return typeof v === 'string' && v.trim() ? v : null; }
  function number(v) { return typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : null; }
  function own(o,k) { return Object.prototype.hasOwnProperty.call(o,k); }
  function strings(v) { return arr(v).map(text).filter(function(x){return x !== null;}); }
  function ensureArray(v,label) { if (!Array.isArray(v)) throw new ReportDataError(label+'는 배열이어야 합니다.'); return v; }
  function safeClone(value, depth) {
    depth = depth || 0;
    if (depth > 60) throw new ReportDataError('JSON의 중첩 단계가 너무 깊습니다.');
    if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
    if (typeof value === 'number') { if (!Number.isFinite(value)) throw new ReportDataError('유한하지 않은 수치는 표시할 수 없습니다.'); return value; }
    if (typeof value !== 'object') throw new ReportDataError('일반 JSON 값만 연결할 수 있습니다.');
    var proto = Object.getPrototypeOf(value);
    if (!Array.isArray(value) && proto !== Object.prototype && proto !== null) throw new ReportDataError('일반 JSON 객체만 연결할 수 있습니다.');
    var result = Array.isArray(value) ? [] : Object.create(null);
    var descriptors = Object.getOwnPropertyDescriptors(value);
    Object.keys(descriptors).forEach(function(key) {
      if (Array.isArray(value) && key === 'length') return;
      if (key === '__proto__' || key === 'constructor' || key === 'prototype') throw new ReportDataError('허용하지 않는 JSON 키: '+key, 'unsafe_key');
      var descriptor = descriptors[key];
      if (!own(descriptor,'value')) throw new ReportDataError('실행 속성(getter/setter)은 연결할 수 없습니다.', 'unsafe_property');
      result[key] = safeClone(descriptor.value, depth+1);
    });
    return result;
  }
  function safeUrl(v,warnings) {
    if (!text(v)) return null;
    try { var u = new URL(v); if ((u.protocol === 'http:' || u.protocol === 'https:') && !u.username && !u.password) return u.href; } catch (_) {}
    warnings.push('출처에 HTTP(S)가 아닌 주소 또는 인증정보가 포함되어 링크를 표시하지 않았습니다.'); return null;
  }
  function status(code) { code = text(code) || 'unknown'; return {code:code,label:STATUS_LABELS[code] || code,isTerminal:['completed','held','needs_input','failed','cancelled','rejected','stale','timeout'].indexOf(code)>=0}; }
  function empty() {
    return {schemaVersion:FORMAT_VERSION,sourceFormat:null,demo:false,title:null,summary:[],request:null,product:{name:null,model:null,category:null},products:[],status:status(null),evidence:[],keywordCounts:[],keywordSummary:{documentCount:0,syntheticDocumentCount:0,uniqueTermCount:0,totalOccurrences:0,method:KEYWORD_METHOD},discomforts:[],existingFeatures:[],remainingDiscomforts:[],concepts:[],assumptions:[],review:{status:null,summary:null,checks:[]},conclusion:null,decisionNotes:[],nextSteps:[],sections:[],charts:[],unfulfilledRequests:[],execution:{durationSeconds:null,totalTokens:null,inputTokens:null,outputTokens:null,cacheTokens:null,reasoningTokens:null,coverage:null,recordedCalls:null},turns:[],selectedTurnId:null,meta:{reportId:null,generatedAt:null,author:null,harnessVersion:null,sourceFile:null},warnings:[]};
  }
  function keywordTokens(body) {
    var plain = body.normalize('NFC').replace(/(?:https?:\/\/|www\.)\S+/giu,' ').replace(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g,' ');
    return (plain.match(/[\p{L}\p{N}_-]+/gu)||[]).map(function(term){return term.toLowerCase();}).filter(function(term){return term.length>=2 && /^\p{L}+$/u.test(term) && !KEYWORD_STOP_WORDS.has(term);});
  }
  function applyKeywords(out) {
    var documents = new Map();
    var sourceIds = new Set(out.evidence.map(function(e){return e.id.normalize('NFC').toLowerCase();}));
    out.evidence.forEach(function(e){
      if(!text(e.body))return;
      var doc=documents.get(e.id);
      if(!doc){doc={bodies:new Set(),synthetic:false};documents.set(e.id,doc);}
      doc.bodies.add(e.body.normalize('NFC').trim().replace(/\s+/g,' '));
      if(e.synthetic===true)doc.synthetic=true;
    });
    var counts = new Map();
    documents.forEach(function(doc,id){doc.bodies.forEach(function(body){keywordTokens(body).forEach(function(term){
      if(sourceIds.has(term))return;
      var entry=counts.get(term);
      if(!entry){entry={term:term,occurrences:0,sourceIds:new Set()};counts.set(term,entry);}
      entry.occurrences+=1;entry.sourceIds.add(id);
    });});});
    out.keywordCounts=Array.from(counts.values()).map(function(entry){return {term:entry.term,documentCount:entry.sourceIds.size,occurrences:entry.occurrences,sourceIds:Array.from(entry.sourceIds)};}).sort(function(a,b){return b.documentCount-a.documentCount||b.occurrences-a.occurrences||a.term.localeCompare(b.term,'ko');});
    out.keywordSummary={documentCount:documents.size,syntheticDocumentCount:Array.from(documents.values()).filter(function(doc){return doc.synthetic;}).length,uniqueTermCount:out.keywordCounts.length,totalOccurrences:out.keywordCounts.reduce(function(sum,entry){return sum+entry.occurrences;},0),method:KEYWORD_METHOD};
  }
  function isPlan(p) { return obj(p) && typeof p.title === 'string' && Array.isArray(p.summary) && Array.isArray(p.sources) && Array.isArray(p.sections); }
  function isResult(p) { return obj(p) && typeof p.status === 'string' && ['pains','existing_features','remaining_pains','concepts','evidence_refs'].every(function(k){return Array.isArray(p[k]);}); }
  function isTurn(p) { return obj(p) && typeof p.turn_id === 'string' && obj(p.input) && (own(p,'latest_result') || typeof p.status === 'string'); }
  function isSession(p) { return obj(p) && typeof p.session_id === 'string' && Array.isArray(p.turns) && Array.isArray(p.requests); }
  function applyMeta(out,meta) { if (!obj(meta)) return; ['reportId','generatedAt','author','harnessVersion','sourceFile'].forEach(function(k){if(text(meta[k]))out.meta[k]=meta[k];}); }
  function claim(item,index,kind) {
    if (!obj(item)) throw new ReportDataError(kind+' 항목은 객체여야 합니다.');
    var body = text(item.text) || text(item.body);
    return {id:text(item.id)||kind+'-'+(index+1),title:text(item.title)||body,body:body,sourceIds:strings(item.source_ids),requirements:strings(item.requirements),requiresHardware:typeof item.requires_hardware==='boolean'?item.requires_hardware:null,assumptions:strings(item.assumptions),implementationSteps:strings(item.implementation_steps),validationPlan:obj(item.validation_plan)?safeClone(item.validation_plan):null};
  }
  function checkRefs(out) {
    var ids = new Set(out.evidence.map(function(e){return e.id;}));
    var seen = new Set();
    var records = [].concat(out.discomforts,out.existingFeatures,out.remainingDiscomforts,out.concepts,out.decisionNotes);
    out.sections.forEach(function(s){records=records.concat(s.blocks);});
    records.forEach(function(item){arr(item.sourceIds).forEach(function(id){if(!ids.has(id) && !seen.has(id)){out.warnings.push('연결된 출처가 없습니다: '+id);seen.add(id);}});});
  }
  function refEvidence(ref,metadata,out,index) {
    if (!obj(ref)) throw new ReportDataError('근거 항목은 객체여야 합니다.');
    var id = text(ref.source_id)||text(ref.id)||'source-'+(index+1);
    var match = arr(metadata).find(function(m){return obj(m)&&m.source_id===id && (!m.sha256 || m.sha256===ref.sha256);});
    var origin = obj(ref.origin)?ref.origin:{};
    return {id:id,title:text(ref.title)||[text(ref.model_id),text(ref.location)].filter(Boolean).join(' · ')||id,body:text(ref.quote)||text(ref.text),url:safeUrl(origin.source_url||ref.url,out.warnings),type:text(ref.kind)||(match&&text(match.kind))||null,model:text(ref.model_id)||text(ref.model),location:text(ref.location),synthetic:typeof ref.synthetic==='boolean'?ref.synthetic:null,binding:match?text(match.binding):null,sourceIds:[],provenance:{retrievedDate:text(origin.retrieved_date),publishedDate:text(origin.published_date),representation:text(origin.representation),modelMatching:text(origin.model_matching),purchaseVerified:typeof origin.purchase_verified==='boolean'?origin.purchase_verified:null,sponsorship:typeof origin.sponsorship==='boolean'?origin.sponsorship:null}};
  }
  function applyUsage(out,usage) {
    if (!obj(usage)) return;
    var totals=obj(usage.totals)?usage.totals:{};
    var e=out.execution;
    e.inputTokens=number(totals.input_tokens);e.outputTokens=number(totals.output_tokens);e.cacheTokens=number(totals.cache_tokens);e.reasoningTokens=number(totals.reasoning_tokens);
    e.totalTokens=e.inputTokens!==null&&e.outputTokens!==null?e.inputTokens+e.outputTokens:null;
    e.coverage=text(usage.coverage);e.recordedCalls=number(usage.recorded_calls);
    if(usage.status==='partially_measured' || (obj(usage.unknown_counts)&&Object.values(usage.unknown_counts).some(function(n){return typeof n==='number'&&n>0;}))) out.warnings.push('사용량은 기록된 호출의 관측값이며 전체 실행 사용량은 확인되지 않았습니다.');
  }
  function applyResult(out,result,planning,state,metadata) {
    if (result && !isResult(result)) throw new ReportDataError('ProductResult의 필수 결과 배열이 누락되었습니다.');
    planning=obj(planning)?planning:{};state=obj(state)?state:{};
    out.request=text(planning.question);
    out.products=arr(planning.model_scope).map(function(m){return {name:text(m.name),model:text(m.model_id),category:text(planning.product_family),modelVersion:text(m.model_version),documentVersion:text(m.document_version)};});
    if(out.products.length)out.product={name:out.products[0].name,model:out.products.map(function(p){return p.model;}).filter(Boolean).join(', ')||null,category:text(planning.product_family)};
    else out.product.category=text(planning.product_family);
    out.meta.reportId=text(state.turn_id)||text(planning.request_key);
    out.selectedTurnId=text(state.turn_id);
    var code=text(state.status)||(result&&text(result.status))||'unknown';
    if(code==='completed'&&result&&result.status!=='completed'){code=result.status;out.warnings.push('완료 상태와 후보 상태가 충돌하여 완료로 표시하지 않았습니다.');}
    if(state.valid===false){code='stale';out.warnings.push('이전 입력 또는 자료에 연결된 결과입니다. 현재 유효한 결과로 재확인되지 않았습니다.');}
    if(obj(state.last_validation)&&state.last_validation.valid===false && code==='completed')code='rejected';
    if(obj(state.last_validation)&&state.last_validation.contract_valid===false && code==='completed')code='rejected';
    out.status=status(code);
    out.review.status=text(state.semantic_status)||'unverified';
    if(state.acceptance_ready===false)out.warnings.push('저장된 결과의 의미와 사업 적용 가능성은 별도 검토가 필요합니다.');
    var validation=obj(state.last_validation)?state.last_validation:{};
    out.review.checks=strings(validation.findings).concat(strings(obj(validation.review_summary)?validation.review_summary.findings:[]));
    applyUsage(out,state.usage_summary);
    if(!result) {out.warnings.push('이 요청에 표시할 최종 결과 본문이 없습니다.');return;}
    [['pains','discomforts'],['existing_features','existingFeatures'],['remaining_pains','remainingDiscomforts'],['concepts','concepts']].forEach(function(pair){out[pair[1]]=result[pair[0]].map(function(c,i){return claim(c,i,pair[0]);});});
    out.assumptions=strings(result.assumptions);
    out.review.checks=out.review.checks.concat(strings(result.validation_findings));
    out.review.summary=strings(result.validation_findings).join('\n')||null;
    out.evidence=result.evidence_refs.map(function(r,i){return refEvidence(r,metadata,out,i);});
    out.decisionNotes=arr(result.decision_notes).map(function(n,i){var c=claim(n,i,'decision');c.basis=text(n.basis);return c;});
    out.conclusion=out.decisionNotes.map(function(n){return n.body;}).filter(Boolean).join('\n')||null;
    out.concepts.forEach(function(c){c.implementationSteps.forEach(function(step,i){out.nextSteps.push({id:c.id+'-step-'+(i+1),title:step,body:step,sourceIds:c.sourceIds,conceptId:c.id});});});
    if(!obj(state.usage_summary))applyUsage(out,result.usage_summary);
    if(out.evidence.some(function(e){return e.synthetic===true;}))out.warnings.push('합성으로 표시된 근거가 포함되어 있습니다. 실제 고객 관측과 구분해 읽어 주세요.');
    if(result.status && state.status && result.status!==state.status)out.warnings.push('후보 본문의 상태('+result.status+')와 저장 상태('+state.status+')가 다릅니다. 저장 상태를 우선 표시합니다.');
  }
  function block(item,index,out) {
    if(!obj(item)||['paragraph','table','chart'].indexOf(item.type)<0)throw new ReportDataError('지원하지 않는 report_plan 블록입니다.');
    var b={id:'block-'+(index+1),type:item.type,title:text(item.title),body:text(item.text),sourceIds:strings(item.source_ids)};
    if(item.type==='paragraph'){if(!b.body)throw new ReportDataError('문단 내용이 없습니다.');b.style=text(item.style)||'body';}
    if(item.type==='table'){
      b.columns=ensureArray(item.columns,'표 열').map(function(c){if(!text(c))throw new ReportDataError('표 열 이름이 없습니다.');return c;});
      b.rows=ensureArray(item.rows,'표 행').map(function(row){if(!Array.isArray(row)||row.length!==b.columns.length)throw new ReportDataError('표의 열 수와 행의 값 수가 다릅니다.');return row.map(function(cell){if(typeof cell==='string'||typeof cell==='number'&&Number.isFinite(cell))return cell;throw new ReportDataError('표에는 텍스트 또는 유한한 수치만 사용할 수 있습니다.');});});
      b.totalRows=arr(item.total_rows);b.highlightCells=arr(item.highlight_cells);
    }
    if(item.type==='chart'){
      if(['bar','line','pie','donut','scatter'].indexOf(item.chart_type)<0)throw new ReportDataError('지원하지 않는 그래프 종류입니다.');
      b.chartType=item.chart_type;b.labels=ensureArray(item.labels,'그래프 항목').map(function(v){if(!text(v))throw new ReportDataError('그래프 항목 이름이 없습니다.');return v;});
      if(!b.labels.length)throw new ReportDataError('그래프 항목이 없습니다.');
      b.series=ensureArray(item.series,'그래프 계열').map(function(s){if(!obj(s)||!text(s.name))throw new ReportDataError('그래프 계열 이름이 없습니다.');var values=ensureArray(s.values,'그래프 수치');if(values.length!==b.labels.length||values.some(function(v){return typeof v!=='number'||!Number.isFinite(v);}))throw new ReportDataError('그래프 수치 누락 또는 항목 수 불일치가 있습니다.');var r={name:s.name,values:values};if(item.chart_type==='scatter'){var xs=ensureArray(s.x_values,'산점도 X축');if(xs.length!==values.length||xs.some(function(v){return typeof v!=='number'||!Number.isFinite(v);}))throw new ReportDataError('산점도 X축 수치가 올바르지 않습니다.');r.xValues=xs;}return r;});
      if(!b.series.length)throw new ReportDataError('그래프 계열이 없습니다.');
      b.unit=text(item.unit);b.caption=text(item.caption);b.highlights=arr(item.highlights);
      if(['pie','donut'].indexOf(b.chartType)>=0&&(b.series.length!==1||b.series[0].values.some(function(v){return v<0;})||b.series[0].values.reduce(function(a,v){return a+v;},0)<=0||!b.unit||!b.caption))throw new ReportDataError('구성비 그래프에는 하나의 유효한 전체 구성과 단위·설명이 필요합니다.');
      if(!b.sourceIds.length)out.warnings.push('출처가 연결되지 않은 그래프: '+(b.title||'제목 없음'));
    }
    return b;
  }
  function applyPlan(out,plan) {
    if(!isPlan(plan))throw new ReportDataError('report_plan에는 title, summary, sources, sections가 필요합니다.');
    out.title=text(plan.title);out.summary=strings(plan.summary);
    // ProductResult may quote one source at several locations. Keep every quote;
    // report_plan metadata may enrich a matching quote but must not collapse it.
    var evidence=out.evidence.slice();
    var planIds=new Set();
    plan.sources.forEach(function(s,i){
      if(!obj(s)||!text(s.id))throw new ReportDataError('보고서 출처에는 ID가 필요합니다.');
      var e=refEvidence(s,[],out,i);
      if(planIds.has(e.id))throw new ReportDataError('중복된 보고서 출처 ID: '+e.id);
      planIds.add(e.id);
      var matches=evidence.map(function(old,index){return {item:old,index:index};}).filter(function(pair){return pair.item.id===e.id;});
      var same=matches.find(function(pair){return pair.item.body===e.body;});
      if(!same&&!e.body&&matches.length)same=matches[0];
      if(same){
        var old=same.item;
        e.provenance=old.provenance;
        if(!e.body)e.body=old.body;
        if(!e.type)e.type=old.type;
        if(e.synthetic===null)e.synthetic=old.synthetic;
        if(!e.url)e.url=old.url;
        if(!e.location)e.location=old.location;
        if(!e.binding)e.binding=old.binding;
        evidence[same.index]=e;
      }else{
        if(e.body&&matches.some(function(pair){return pair.item.body&&e.body.indexOf(pair.item.body)===-1&&pair.item.body.indexOf(e.body)===-1;}))out.warnings.push('동일 출처 ID의 본문이 서로 다릅니다: '+e.id);
        evidence.push(e);
      }
    });
    out.evidence=evidence;
    out.sections=plan.sections.map(function(s,i){if(!obj(s)||!text(s.title))throw new ReportDataError('보고서 구역 제목이 없습니다.');var blocks=ensureArray(s.blocks,'보고서 구역 블록').map(function(b,bi){return block(b,bi,out);});return {id:'section-'+(i+1),title:s.title,body:blocks.filter(function(b){return b.type==='paragraph';}).map(function(b){return b.body;}).join('\n')||null,blocks:blocks,items:blocks};});
    out.charts=[];out.sections.forEach(function(s){s.blocks.forEach(function(b){if(b.type==='chart')out.charts.push(Object.assign({},b,{sectionId:s.id}));});});
    out.unfulfilledRequests=arr(plan.unfulfilled_requests).map(function(r){if(!obj(r)||!text(r.request)||!text(r.reason))throw new ReportDataError('미수행 요청에는 요청 내용과 사유가 필요합니다.');return {request:r.request,reason:r.reason};});
    if(out.status.code==='unknown')out.warnings.push('report_plan은 본문·도표 계약입니다. 실행 상태를 제공하지 않아 완료 여부를 추정하지 않았습니다.');
  }
  function session(out,p,options) {
    var histories=p.turns;
    histories.forEach(function(h){if(!obj(h)||!isTurn(h.state))throw new ReportDataError('세션 내 turn.state 구조가 올바르지 않습니다.');});
    out.turns=histories.map(function(h,i){return {id:h.state.turn_id,label:text(h.state.input.question)||'요청 '+(i+1),status:status(h.state.valid===false?'stale':h.state.status)};});
    var selected=options.turnId?histories.find(function(h){return h.state.turn_id===options.turnId;}):histories[histories.length-1];
    if(options.turnId&&!selected)throw new ReportDataError('선택한 turn_id가 결과 파일에 없습니다: '+options.turnId,'turn_not_found');
    if(selected){applyResult(out,selected.state.latest_result,selected.state.input,selected.state,selected.source_metadata);out.selectedTurnId=selected.state.turn_id;}
    else {
      var request=arr(p.requests)[p.requests.length-1];
      if(request){out.request=text(obj(request.input)?request.input.question:null);out.status=status(obj(request.response)?request.response.status:null);}
      out.warnings.push('세션에 저장된 실행 결과(turn)가 없습니다.');
    }
    if(p.requests.some(function(r){return obj(r)&&!r.turn_id;}))out.warnings.push('최종 결과에 연결되지 않은 요청이 있습니다. 선택한 실행 결과와 구분해야 합니다.');
    out.meta.reportId=out.meta.reportId||text(p.session_id);
  }
  function normalize(payload,options) {
    options=options||{};
    var p=safeClone(payload);var out=empty();
    if(!obj(p))throw new UnsupportedReportSchemaError();
    var envelope=own(p,'export')||own(p,'report_plan');
    if(envelope&&own(p,'report_plan')&&p.report_plan!==null&&!isPlan(p.report_plan))throw new ReportDataError('연결된 report_plan 구조가 올바르지 않습니다.');
    var source=envelope?(obj(p.export)?p.export:p.report_plan):p;
    if(envelope&&!obj(source))throw new UnsupportedReportSchemaError('결합 입력의 export 또는 report_plan에 JSON 본문이 필요합니다. 파일 경로 영수증만으로는 보고서를 만들 수 없습니다.');
    if(obj(source)&&source.ok===true&&obj(source.result))source=source.result;
    if(obj(source)&&source.ok===false&&obj(source.error)){out.sourceFormat='team-cli-error';out.status=status('failed');out.review.summary=text(source.error.message);out.review.checks=out.review.summary?[out.review.summary]:[];out.meta.reportId=text(source.error.code);out.demo=p.demo===true;applyMeta(out,p.meta);return out;}
    if(obj(source)&&isTurn(source.turn))source=source.turn;
    if(isSession(source)){out.sourceFormat='team-export-session';session(out,source,options);}
    else if(isTurn(source)){out.sourceFormat='team-turn';applyResult(out,source.latest_result,source.input,source,source.source_metadata);out.turns=[{id:source.turn_id,label:out.request||source.turn_id,status:out.status}];}
    else if(isResult(source)){out.sourceFormat='team-product-result';applyResult(out,source,{},null,source.source_metadata);}
    else if(isPlan(source)){out.sourceFormat='team-report-plan';applyPlan(out,source);}
    else if(obj(source)&&((source.path&&source.sha256)||(obj(source.export)&&source.export.path)))throw new UnsupportedReportSchemaError('이 파일은 export 경로 영수증입니다. path가 가리키는 export-*.json 본문을 불러와 주세요.');
    else throw new UnsupportedReportSchemaError();
    if(envelope&&isPlan(p.report_plan)&&source!==p.report_plan){
      var planTurn=text(p.report_plan_turn_id)||(isSession(source)&&source.turns.length?source.turns[source.turns.length-1].state.turn_id:null);
      if(planTurn&&out.selectedTurnId&&planTurn!==out.selectedTurnId)out.warnings.push('다른 실행에 연결된 report_plan은 현재 선택한 실행에 섞어 표시하지 않았습니다.');
      else {applyPlan(out,p.report_plan);if(isSession(source)&&!text(p.report_plan_turn_id)&&!out.demo&&p.demo!==true)out.warnings.push('별도 보고서 계획은 마지막 실행에 표시했습니다. report_plan_turn_id가 없어 실행과의 연결은 확인되지 않았습니다.');}
    }
    if(envelope)out.sourceFormat='team-report-envelope';
    out.demo=p.demo===true;
    applyMeta(out,p.meta);applyMeta(out,options.meta);
    if(out.demo)out.warnings.unshift('디자인 확인용 합성 예시입니다. 실제 하네스 실행·고객 조사·성능 측정 결과가 아닙니다.');
    applyKeywords(out);
    checkRefs(out);
    out.warnings=Array.from(new Set(out.warnings));
    return out;
  }
  function parse(input,options) {
    if(typeof input!=='string')throw new ReportDataError('parse에는 JSON 문자열을 전달해 주세요. 객체는 normalize로 연결합니다.');
    if(input.length>MAX_JSON_CHARS)throw new ReportDataError('JSON 파일은 16 MiB 이하로 나누어 불러와 주세요.','input_limit');
    var p;
    try {p=JSON.parse(input.replace(/^\uFEFF/,''));} catch(e){throw new ReportDataError('JSON 문법을 확인해 주세요: '+e.message,'invalid_json');}
    return normalize(p,options);
  }
  function trace(report,selection) {
    // Inspect only the selected normalized report. Shared source IDs establish
    // a reference relationship, never causality, support, or ranking.
    var current=safeClone(report),pick=safeClone(selection||{});
    if(!obj(current)||current.schemaVersion!==FORMAT_VERSION||!Array.isArray(current.evidence))throw new ReportDataError('근거 따라보기에는 정규화된 보고서가 필요합니다.','invalid_trace_report');
    if(!obj(pick)||['decision','concept'].indexOf(pick.kind)<0)throw new ReportDataError('결론 또는 개선안을 선택해 주세요.','invalid_trace_selection');
    var groups=['discomforts','existingFeatures','remainingDiscomforts','concepts','decisionNotes'];
    var related={};groups.forEach(function(key){related[key]=[];});
    var output={status:'not_found',kind:pick.kind,selectedTurnId:text(current.selectedTurnId),seed:null,sourceIds:[],sources:[],missingSourceIds:[],related:related,method:'선택한 항목에 명시된 출처 ID만 따라갑니다. 관련 항목은 같은 출처 ID를 직접 참조하며, 인과관계·제안의 우선순위·검증 완료를 뜻하지 않습니다.'};
    if(own(pick,'turnId')&&pick.turnId!==current.selectedTurnId){output.status='turn_mismatch';return output;}
    var selectedGroup=pick.kind==='decision'?'decisionNotes':'concepts';
    var items=arr(current[selectedGroup]),index=-1;
    if(own(pick,'index')){
      if(!Number.isInteger(pick.index)||pick.index<0||pick.index>=items.length)return output;
      index=pick.index;
      if(own(pick,'id')&&items[index].id!==pick.id)return output;
    }else if(text(pick.id)){
      var indexes=[];items.forEach(function(item,i){if(item.id===pick.id)indexes.push(i);});
      if(indexes.length>1){output.status='ambiguous';return output;}
      if(indexes.length===1)index=indexes[0];
    }
    if(index<0||!obj(items[index]))return output;
    var seed=items[index];
    output.seed=Object.assign({},seed,{index:index});
    output.sourceIds=Array.from(new Set(strings(seed.sourceIds)));
    if(!output.sourceIds.length){output.status='no_sources';return output;}
    output.status='connected';
    var sourceSet=new Set(output.sourceIds),found=new Set();
    current.evidence.forEach(function(e,i){if(obj(e)&&sourceSet.has(e.id)){found.add(e.id);output.sources.push(Object.assign({},e,{evidenceIndex:i}));}});
    output.missingSourceIds=output.sourceIds.filter(function(id){return !found.has(id);});
    groups.forEach(function(key){arr(current[key]).forEach(function(item,i){
      if(!obj(item)||(key===selectedGroup&&i===index))return;
      var matched=Array.from(new Set(strings(item.sourceIds).filter(function(id){return sourceSet.has(id);})));
      if(matched.length)related[key].push(Object.assign({},item,{index:i,matchedSourceIds:matched}));
    });});
    return output;
  }
  return Object.freeze({normalize:normalize,parse:parse,trace:trace,normalizeText:text,supportedFormats:SUPPORTED_FORMATS,version:FORMAT_VERSION,ReportDataError:ReportDataError,UnsupportedReportSchemaError:UnsupportedReportSchemaError});
});
