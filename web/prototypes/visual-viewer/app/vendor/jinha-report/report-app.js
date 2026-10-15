(function(){
'use strict';
const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
const e=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const list=v=>Array.isArray(v)?v:[], number=v=>typeof v==='number'&&Number.isFinite(v);
const fmt=v=>number(v)?v.toLocaleString('ko-KR',{maximumFractionDigits:3}):'미제공';
const plain=v=>typeof v==='string'?v:(v&&typeof v==='object'?(v.body||v.text||v.title||JSON.stringify(v)):String(v==null?'':v));
const safeUrl=v=>{try{const u=new URL(v);return /^https?:$/.test(u.protocol)&&!u.username&&!u.password?u.href:null;}catch(_){return null;}};
let payload=null, report=null, figureNo=0, sectionNo=0, sourceIds=new Map(), selectedFilter='all', fileLabel='', traceState=null, traceReturnTarget=null;
const color=['#c81637','#182125','#777f85','#aeb4b7','#456785','#21695e'];
const label=v=>({refrigerator:'냉장고',fridge:'냉장고',microwave:'전자레인지',dishwasher:'식기세척기',review:'고객 후기',product_document:'제품 문서',product_fact:'제품 사실',manual:'사용 설명서',web:'웹 자료'}[v]||v);
function validationPanel(item){
 let html='';if(typeof item.requiresHardware==='boolean')html+='<p class="metric-note">추가 하드웨어 '+(item.requiresHardware?'필요':'없이 검토하는 후보')+'</p>';
 if(item.assumptions?.length)html+='<h3>확인할 전제</h3><ul>'+item.assumptions.map(t=>'<li>'+e(plain(t))+'</li>').join('')+'</ul>';
 if(item.validationPlan){const p=item.validationPlan,keys=[['metric','확인 지표'],['baseline','비교 기준'],['method','확인 방법'],['success_criterion','성공 조건'],['business_value','확인할 가치']];html+='<details class="concept-validation"><summary>검증 계획 · 효과 미확정</summary>'+keys.filter(([k])=>p[k]!=null).map(([k,t])=>'<p><b>'+t+'</b><br>'+e(plain(p[k]))+'</p>').join('')+'</details>';}
 return html;
}
function sourceMetadata(s){const p=s.provenance||{},rows=[['제품 모델',s.model],['자료 발행일',p.publishedDate],['자료 확인일',p.retrievedDate],['모델 일치 확인',p.modelMatching],['구매 인증',p.purchaseVerified==null?'미확인':(p.purchaseVerified?'확인됨':'확인되지 않음')],['협찬 여부',p.sponsorship==null?'미확인':(p.sponsorship?'있음':'없음')]];return '<details class="source-metadata"><summary>자료 정보</summary>'+rows.filter(x=>x[1]).map(x=>'<p><b>'+e(x[0])+'</b> '+e(x[1])+'</p>').join('')+'</details>';}
const notice=(message,error=false)=>{const box=$('#load-notice');box.className=error?'load-error':'load-success';box.textContent=message;box.hidden=false;$('#announcement').textContent=message;};
function sourceLabel(id){return sourceIds.has(id)?sourceIds.get(id).replace('evidence-','근거 '):'미연결 근거';}
function refs(ids){return list(ids).length?'<div class="evidence-refs">'+list(ids).map(id=>sourceIds.has(id)?'<a href="#'+sourceIds.get(id)+'">'+e(sourceLabel(id))+'</a>':'<span class="paper-note">출처 미연결</span>').join('')+'</div>':'';}
function section(title,body,id){sectionNo++;return '<section class="paper-section" id="'+(id||'result-section-'+sectionNo)+'"><h2>'+sectionNo+'. '+e(title)+'</h2>'+body+'</section>';}
function figure(title,body,caption='',ids=[]){figureNo++;return '<figure class="visual-figure intext-figure"><header class="figure-heading"><span>도표 '+String(figureNo).padStart(2,'0')+'</span><h3>'+e(title)+'</h3></header><div class="figure-content">'+body+'</div>'+(caption||ids.length?'<figcaption>'+e(caption)+refs(ids)+'</figcaption>':'')+'</figure>';}
function prose(texts){return '<div class="paper-prose">'+list(texts).filter(Boolean).map(t=>'<p class="body-block">'+e(plain(t))+'</p>').join('')+'</div>';}
function cards(items,kind=''){return '<div class="result-cards">'+list(items).map((item,i)=>'<article class="result-card" data-claim-kind="'+e(kind)+'" data-claim-index="'+i+'"><span class="card-number">항목 '+String(i+1).padStart(2,'0')+'</span><h3>'+e(item.title||item.body||'항목 '+(i+1))+'</h3>'+(item.body&&item.body!==item.title?'<p>'+e(item.body)+'</p>':'')+(item.requirements?.length?'<h3>요구사항</h3><ul>'+item.requirements.map(x=>'<li>'+e(plain(x))+'</li>').join('')+'</ul>':'')+(item.implementationSteps?.length?'<h3>적용 순서</h3><ul>'+item.implementationSteps.map(x=>'<li>'+e(plain(x))+'</li>').join('')+'</ul>':'')+validationPanel(item)+refs(item.sourceIds)+(kind==='concepts'?'<button class="trace-inline-open" data-trace-kind="concept" data-trace-index="'+i+'">이 개선안의 근거 따라보기 →</button>':'')+'</article>').join('')+'</div>';}
function table(headers,rows,highlights=[],totalRows=[]){return '<div class="table-wrap"><table class="result-table"><thead><tr>'+headers.map(h=>'<th scope="col">'+e(plain(h))+'</th>').join('')+'</tr></thead><tbody>'+rows.map((row,i)=>'<tr class="'+(totalRows.includes(i)?'total-row':'')+'">'+row.map((v,j)=>'<td'+(highlights.some(x=>x[0]===i&&x[1]===j)?' class="highlight-cell"':'')+'>'+e(number(v)?String(v):plain(v))+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';}
function wrapSvgText(text,x,y,maxChars=13,anchor='start',size=12){const s=String(text);const chunks=[];for(let i=0;i<s.length;i+=maxChars)chunks.push(s.slice(i,i+maxChars));return '<text x="'+x+'" y="'+y+'" text-anchor="'+anchor+'" fill="#62696f" font-size="'+size+'">'+chunks.map((t,i)=>'<tspan x="'+x+'" dy="'+(i?15:0)+'">'+e(t)+'</tspan>').join('')+'</text>';}
function chart(block){
 const labels=list(block.labels),series=list(block.series),kind=block.chartType||block.chart_type;
 const highlights=list(block.highlights),baseColor=j=>color[(j+(highlights.length?1:0))%color.length],pointColor=(j,i)=>highlights.some(h=>h[0]===j&&h[1]===i)?'#c81637':baseColor(j);
 if(!series.length||!labels.length)return '<p class="empty-result">차트에 필요한 수치가 제공되지 않았습니다.</p>';
 const values=series.flatMap(s=>list(s.values));
 if(!values.every(number))return '<p class="empty-result">유효한 수치가 없는 항목이 있어 그래프를 표시하지 않았습니다.</p>';
 const chartHeaders=kind==='scatter'?['항목',...series.flatMap(s=>[(s.name||'계열')+' X',(s.name||'계열')+' Y'])]:['항목',...series.map(s=>s.name||'계열')];
 const chartRows=labels.map((l,i)=>[l,...series.flatMap(s=>kind==='scatter'?[(s.xValues||s.x_values||[])[i],s.values[i]]:[s.values[i]])]);
 const detail='<details class="chart-values"><summary>그래프 원자료 보기</summary>'+table(chartHeaders,chartRows)+'</details>';
 const unit=block.unit?'<p class="chart-unit">단위: '+e(block.unit)+'</p>':'';
 const legend='<div class="chart-legend">'+series.map((s,i)=>'<span><i style="background:'+baseColor(i)+'"></i>'+e(s.name||'계열 '+(i+1))+'</span>').join('')+'</div>';
 let svg='';
 if(kind==='donut'||kind==='pie'){
  const vals=series[0].values,total=vals.reduce((a,b)=>a+b,0);if(total<=0||vals.some(v=>v<0))return '<p class="empty-result">구성비는 합계가 양수인 음수 없는 수치에만 표시합니다.</p>'+detail;
  let offset=0;const radius=82, circumference=2*Math.PI*radius,pieColor=i=>highlights.length?pointColor(0,i):color[i%color.length];
  svg='<svg viewBox="0 0 240 240" role="img" aria-label="'+e(block.title||'구성비')+'"><title>'+e(block.title||'구성비')+'</title><circle cx="120" cy="120" r="82" fill="none" stroke="#eef0f0" stroke-width="34"/>';
  vals.forEach((v,i)=>{const dash=v/total*circumference;svg+='<circle cx="120" cy="120" r="82" fill="none" stroke="'+pieColor(i)+'" stroke-width="34" stroke-dasharray="'+dash+' '+(circumference-dash)+'" stroke-dashoffset="'+(-offset)+'" transform="rotate(-90 120 120)"><title>'+e(labels[i])+': '+fmt(v)+'</title></circle>';offset+=dash;});
  svg+='<text x="120" y="118" text-anchor="middle" font-size="30" font-weight="700" fill="#182125">'+fmt(total)+'</text><text x="120" y="143" text-anchor="middle" font-size="12" fill="#62696f">합계'+(block.unit?' · '+e(block.unit):'')+'</text></svg>';
  return '<div class="result-chart">'+unit+'<div class="donut-layout">'+svg+'<div class="donut-legend">'+labels.map((l,i)=>'<div><i style="background:'+pieColor(i)+'"></i><span>'+e(l)+'</span><b>'+fmt(vals[i])+' · '+(vals[i]/total*100).toFixed(1)+'%</b></div>').join('')+'</div></div>'+detail+'</div>';
 }
 const min=Math.min(0,...values),max=Math.max(0,...values),range=max-min||1;
 if(kind==='bar'){
  const W=800,L=166,R=70,T=35,rowH=Math.max(46,22*series.length+18,...labels.map(l=>Math.ceil(String(l).length/12)*15+20)),H=T+labels.length*rowH+30,plot=W-L-R,x=v=>L+(v-min)/range*plot;
  svg='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+e(block.title)+'"><title>'+e(block.title)+'</title>';
  for(let n=0;n<=4;n++){const v=min+range*n/4,xx=x(v);svg+='<line x1="'+xx+'" x2="'+xx+'" y1="26" y2="'+(H-20)+'" stroke="#e4e7e8"/><text x="'+xx+'" y="16" text-anchor="middle" fill="#62696f" font-size="11">'+fmt(v)+'</text>';}
  labels.forEach((l,i)=>{const y=T+i*rowH;svg+=wrapSvgText(l,0,y+16,12);series.forEach((s,j)=>{const v=s.values[i],yy=y+j*22,a=x(v),z=x(0);svg+='<rect x="'+Math.min(a,z)+'" y="'+yy+'" width="'+Math.abs(a-z)+'" height="16" fill="'+pointColor(j,i)+'"><title>'+e(l)+' / '+e(s.name)+': '+fmt(v)+'</title></rect><text x="'+(v<0?a-6:a+6)+'" y="'+(yy+13)+'" text-anchor="'+(v<0?'end':'start')+'" font-size="11" fill="#182125">'+fmt(v)+'</text>';});});
  svg+='</svg>';
 }else if(kind==='line'||kind==='scatter'){
  const W=800,H=330,L=64,R=35,T=26,B=80,ph=H-T-B;
  const xs=kind==='scatter'?series.flatMap(s=>list(s.xValues||s.x_values)):labels.map((_,i)=>i);
  if(xs.length===0||!xs.every(number))return '<p class="empty-result">좌표 값이 없어 산점도를 표시하지 않았습니다.</p>'+detail;
  const xMin=Math.min(...xs),xMax=Math.max(...xs),xRange=xMax-xMin||1,x=v=>L+(v-xMin)/xRange*(W-L-R),y=v=>T+(max-v)/range*ph;
  svg='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+e(block.title)+'"><title>'+e(block.title)+'</title>';
  for(let n=0;n<=4;n++){const v=min+range*n/4,yy=y(v);svg+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+yy+'" y2="'+yy+'" stroke="#e4e7e8"/><text x="'+(L-12)+'" y="'+(yy+4)+'" text-anchor="end" font-size="11" fill="#62696f">'+fmt(v)+'</text>';}
  if(kind==='scatter'){for(let n=0;n<=4;n++){const v=xMin+xRange*n/4;svg+=wrapSvgText(fmt(v),x(v),H-B+25,15,'middle',11);}}
  else labels.forEach((l,i)=>{svg+=wrapSvgText(l,x(i),H-B+25,Math.max(4,Math.floor(75/labels.length)),'middle',11);});
  series.forEach((s,j)=>{const points=s.values.map((v,i)=>[x(kind==='scatter'?(s.xValues||s.x_values)[i]:i),y(v)]);if(kind==='line')svg+='<polyline points="'+points.map(p=>p.join(',')).join(' ')+'" fill="none" stroke="'+baseColor(j)+'" stroke-width="2.5"'+(j%2?' stroke-dasharray="7 4"':'')+'/>';points.forEach((p,i)=>{svg+='<circle cx="'+p[0]+'" cy="'+p[1]+'" r="4" fill="'+pointColor(j,i)+'"><title>'+e(labels[i])+' / '+e(s.name)+': '+fmt(s.values[i])+'</title></circle>';});});
  svg+='</svg>';
 }else return '<p class="empty-result">지원되지 않는 그래프 종류: '+e(kind)+'. 원자료를 확인하세요.</p>'+detail;
 return '<div class="result-chart">'+unit+'<div class="chart-scroll">'+svg+'</div>'+legend+detail+'</div>';
}
function renderPlanSections(sections){return list(sections).map(s=>{
 let html='',paras=[];const flush=()=>{if(paras.length){html+=prose(paras);paras=[];}};
 list(s.blocks).forEach(b=>{if(b.type==='paragraph'){if(b.style==='quote'){flush();html+='<blockquote class="result-quote">'+e(b.body||b.text)+'</blockquote>'+refs(b.sourceIds);return;}if(b.style==='emphasis'){flush();html+='<p class="result-emphasis">'+e(b.body||b.text)+'</p>'+refs(b.sourceIds);return;}paras.push(b.body||b.text);if(b.sourceIds?.length){flush();html+=refs(b.sourceIds);}return;}flush();if(b.type==='table')html+=figure(b.title||'분석 결과 표',table(b.columns||b.headers||[],b.rows||[],b.highlightCells||[],b.totalRows||[]),b.caption||'',b.sourceIds||[]);else if(b.type==='chart')html+=figure(b.title||'분석 결과 그래프',chart(b),b.caption||'',b.sourceIds||[]);else html+=prose([b.body||b.text]);});flush();
 if(!html&&s.body)html=prose([s.body]);return section(s.title||'분석 결과',html||'<p class="empty-result">이 절의 본문이 제공되지 않았습니다.</p>');
 }).join('');}
function renderKeywords(r){
 const words=list(r.keywordCounts),summary=r.keywordSummary||{};
 if(!words.length)return section('키워드별 언급 건수','<p class="empty-result">집계할 원자료 본문이나 단어가 없습니다.</p>','keyword-frequency');
 const countTable=rows=>'<div class="keyword-table-wrap"><table class="keyword-table"><thead><tr><th scope="col">단어</th><th scope="col">언급 자료</th><th scope="col">등장 횟수</th></tr></thead><tbody>'+rows.map(w=>'<tr><th scope="row">'+e(w.term)+'</th><td><strong>'+e(w.documentCount)+'</strong><span>건</span></td><td><strong>'+e(w.occurrences)+'</strong><span>회</span></td></tr>').join('')+'</tbody></table></div>';
 const shown=words.slice(0,50),first=shown.slice(0,12),rest=shown.slice(12);
 const countGrid=rows=>rows.length>6?'<div class="keyword-tables">'+countTable(rows.slice(0,Math.ceil(rows.length/2)))+countTable(rows.slice(Math.ceil(rows.length/2)))+'</div>':countTable(rows);
 return section('키워드별 언급 건수','<p class="keyword-intro">원자료 <strong>'+e(summary.documentCount||0)+'건</strong>에서 집계했습니다. <b>언급 자료</b>는 단어가 나온 자료 수, <b>등장 횟수</b>는 같은 자료 안의 반복을 포함한 횟수입니다.</p>'+countGrid(first)+(rest.length?'<details class="keyword-more"><summary>단어 '+rest.length+'개 더 보기</summary>'+countGrid(rest)+'</details>':'')+(words.length>50?'<p class="metric-note">전체 '+words.length+'개 단어 중 상위 50개를 표시합니다.</p>':'')+'<details class="keyword-method"><summary>집계 기준 확인</summary><p>'+e(summary.method||'원자료 본문에서 같은 표기의 단어를 집계합니다.')+'</p>'+(summary.syntheticDocumentCount?'<p>이 중 '+e(summary.syntheticDocumentCount)+'건은 합성 예시 자료입니다.</p>':'')+'</details>','keyword-frequency');
}
function renderBusiness(r){
 let html='';
 if(r.request||r.products?.length){html+=section('기획 요청과 분석 범위',(r.request?'<blockquote class="request-quote">'+e(r.request)+'</blockquote>':'')+(r.products?.length?table(['제품 모델','제품군','자료 버전'],r.products.map(p=>[p.model||p.name||'미제공',label(p.category)||'미제공',p.documentVersion||p.modelVersion||'미제공'])):'')+figure('이번 결과에 포함된 분석 항목','<div class="metric-grid">'+[[r.evidence.length,'연결 근거','원문·자료 항목'],[r.discomforts.length,'고객 불편','결과에 정리된 항목'],[r.existingFeatures.length,'기존 기능','비교한 기능 항목'],[r.concepts.length,'개선안 후보','하네스가 제시한 후보']].map(x=>'<article class="stat"><strong>'+x[0]+'</strong><h3>'+x[1]+'</h3><p>'+x[2]+'</p></article>').join('')+'</div>','현재 결과 파일의 항목 수입니다. 고객 수·시장 비율·성능 점수를 뜻하지 않습니다.'));}
 html+=renderKeywords(r);
 if(r.discomforts.length||r.existingFeatures.length||r.remainingDiscomforts.length){
  html+=section('고객 불편과 기존 기능 대조',(r.discomforts.length?figure('결과에서 확인한 고객 불편',cards(r.discomforts,'discomforts')):'')+(r.existingFeatures.length?figure('대조한 기존 기능',cards(r.existingFeatures,'existingFeatures')):'')+(r.remainingDiscomforts.length?figure('기존 기능으로도 남는 문제',cards(r.remainingDiscomforts,'remainingDiscomforts')):'') );
 }
 if(r.concepts.length)html+=section('개선안과 요구사항',figure('검토할 상품기획 후보',cards(r.concepts,'concepts'),'후보의 효과와 실현 가능성은 연결된 근거·가정과 함께 검토합니다.'));
 if(r.assumptions.length)html+=section('확인할 가정',prose(r.assumptions));
 if(r.review.checks?.length||r.review.summary){html+=section('검토 결과',(r.review.summary&&!r.review.checks?.length?prose([r.review.summary]):'')+(r.review.checks?.length?table(['검토 항목','판정·내용'],r.review.checks.map((c,i)=>[c.title||c.id||'항목 '+(i+1),c.body||c.message||plain(c)])):'') );}
 return html;
}
function renderFollowUp(r){let html='';
 if(r.decisionNotes.length)html+=section('결론과 판단 근거',r.decisionNotes.map((n,i)=>'<div class="decision-note"><span class="source-kind">'+e({source_fact:'확인 사실',ai_interpretation:'인공지능 해석',unverified:'미확인'}[n.basis]||'판단 근거 미분류')+'</span><button class="decision-trigger" data-trace-kind="decision" data-trace-index="'+i+'"><span>'+e(n.body||n.title)+'</span><b>이 결론의 근거 따라보기 →</b></button>'+refs(n.sourceIds)+'</div>').join(''));
 else if(r.conclusion)html+=section('결론','<div class="summary-callout"><p>'+e(r.conclusion)+'</p></div>');
 if(r.nextSteps.length)html+=section('다음 실행',figure('결과에서 제안한 후속 작업','<div class="step-list">'+r.nextSteps.map((s,i)=>'<article><h3>'+e(typeof s==='string'?'후속 작업 '+(i+1):s.title||'후속 작업 '+(i+1))+'</h3>'+(plain(s)!==s.title?'<p>'+e(plain(s))+'</p>':'')+'</article>').join('')+'</div>','실행 결과에 담긴 제안입니다. 수행 완료를 의미하지 않습니다.'));
 return html;
}
function renderExecution(r){const x=r.execution;if(!x||![x.durationSeconds,x.totalTokens,x.inputTokens,x.outputTokens].some(number))return '';return section('실행 기록',table(['기록 항목','값'],[['실행 상태',r.status.label],['경과 시간',number(x.durationSeconds)?fmt(x.durationSeconds)+'초':'미제공'],['입력 토큰',fmt(x.inputTokens)],['출력 토큰',fmt(x.outputTokens)],['총 관측 토큰',fmt(x.totalTokens)]])+'<p class="metric-note">수치가 없는 항목은 미제공으로 표시합니다. 관측 토큰은 실제 청구 비용이나 개선 효과를 뜻하지 않습니다.</p>');}
function renderEvidence(){
 const query=$('#evidence-search').value.trim().toLowerCase(),all=report.evidence;
 const selected=all.filter(s=>(selectedFilter==='all'||(s.type||'자료')===selectedFilter)&&[s.id,s.title,s.body,s.url].join(' ').toLowerCase().includes(query));
 $('#evidence-count').textContent=selected.length+' / '+all.length+'개';
 $('#evidence-list').innerHTML=all.length?all.map((s,si)=>'<article id="evidence-'+(si+1)+'" data-evidence-index="'+si+'" class="tool-item source-card"'+(!selected.includes(s)?' hidden':'')+'><span class="source-kind">'+e(sourceLabel(s.id))+' · '+e(label(s.type)||'자료')+(s.synthetic===true?' · 합성 자료':'')+'</span><h3>'+e(s.title||s.id)+'</h3>'+(s.body?'<p class="source-body">'+e(s.body)+'</p>':'')+(s.location?'<p>'+e(s.location)+'</p>':'')+(safeUrl(s.url)?'<a class="source-url" href="'+e(safeUrl(s.url))+'" target="_blank" rel="noopener noreferrer">원문 열기 ↗</a>':'<p class="paper-note">연결된 원문 URL 없음</p>')+sourceMetadata(s)+'</article>').join(''):'<p class="source-empty">이 결과 파일에 전달된 출처가 없습니다.</p>';
 if(all.length&&!selected.length)$('#evidence-list').insertAdjacentHTML('beforeend','<p class="source-empty">검색 조건에 맞는 근거가 없습니다.</p>');
 if(traceState)highlightTrace(getTraceBundle().focus);
}
function render(raw,options={}){
 const next=window.HarnessReportAdapter.normalize(raw,options); // 검증 완료 후에만 이전 화면 교체
 payload=raw;report=next;figureNo=0;sectionNo=0;sourceIds=new Map();report.evidence.forEach((s,i)=>{if(!sourceIds.has(s.id))sourceIds.set(s.id,'evidence-'+(i+1));});selectedFilter='all';traceState=null;
 $('#report-title').textContent=report.title||[report.product.model||report.product.category||'키친 상품기획','분석 결과 보고서'].join('\n');
 document.title=($('#report-title').textContent.replace(/\n/g,' '))+' · LG AX';
 $('#report-byline').textContent=[report.meta.author||'키친에서치킨먹기',report.meta.generatedAt].filter(Boolean).join(' · ');
 $('#report-context-label').innerHTML=report.demo?'<span class="demo-badge">디자인 확인용 예시</span> · 실제 팀 하네스 실행 결과가 아닙니다.':e(fileLabel||report.meta.sourceFile||'연결된 하네스 결과')+' · <span class="report-status '+e(report.status.code)+'">'+e(report.status.label)+'</span>';
 $('#show-sample').hidden=report.demo||$('#embedded-report').textContent.trim()!=='null';
 const summary=report.summary?.length?report.summary:(report.conclusion?[report.conclusion]:[report.request||'하네스에서 전달한 결과를 본문과 근거 목록으로 정리했습니다.']);
 $('#report-summary').innerHTML=summary.map(p=>'<p>'+e(plain(p))+'</p>').join('');
 $('#report-keywords').textContent='보고 상태  '+report.status.label+(report.product.model?'  ·  대상 모델  '+report.product.model:'');
 const hasBusiness=report.request||report.discomforts.length||report.concepts.length||report.conclusion||report.review.summary||report.review.checks.length;
 let body=hasBusiness?renderBusiness(report):(report.evidence.length?renderKeywords(report):'');
 if(report.sections.length)body+=renderPlanSections(report.sections);
 body+=renderFollowUp(report);
 body+=renderExecution(report);
 if(report.unfulfilledRequests.length)body+=section('반영하지 못한 요청',table(['요청','반영하지 못한 이유'],report.unfulfilledRequests.map(x=>[x.request||plain(x),x.reason||'미제공'])));
 if(report.warnings.length)body+='<aside class="warnings-list"><strong>결과를 읽을 때 확인할 사항</strong><ul>'+report.warnings.map(w=>'<li>'+e(w)+'</li>').join('')+'</ul></aside>';
 $('#result-body').innerHTML=body||'<p class="empty-result">현재 상태는 '+e(report.status.label)+'이며, 표시할 최종 분석 내용이 제공되지 않았습니다.</p>';
 $('#source-description').textContent='본문·표·그래프에 연결된 '+report.evidence.length+'개 자료입니다. 항목을 검색하고 원문을 확인할 수 있습니다.';
 const kinds=[...new Set(report.evidence.map(s=>s.type||'자료'))];
 $('#evidence-filters').innerHTML=['all',...kinds].map(k=>'<button data-filter="'+e(k)+'" aria-pressed="'+(k==='all')+'">'+e(k==='all'?'전체':label(k))+'</button>').join('');
 $('#evidence-search').value='';renderEvidence();renderTraceLaunchers();
 $('#run-selector').hidden=report.turns.length<2;$('#turn-select').innerHTML=report.turns.map(t=>'<option value="'+e(t.id)+'"'+(t.id===report.selectedTurnId?' selected':'')+'>'+e(t.label||t.id)+'</option>').join('');$('#run-state').textContent=report.status.label;
 const heads=[{id:'paper',title:'표지 · 결과 요약'},...(!$('#evidence-trace').hidden?[{id:'evidence-trace',title:'결론 → 근거 따라보기'}]:[]),...$$('#result-body .paper-section').map(s=>({id:s.id,title:s.querySelector('h2').textContent})),{id:'sources',title:'원자료와 출처'}];
 $('#contents-list').innerHTML=heads.map((h,i)=>'<a href="#'+h.id+'"><b>'+String(i).padStart(2,'0')+'</b>'+e(h.title)+'</a>').join('');
 $('#quick-contents-list').innerHTML=heads.slice(1).map(h=>'<a href="#'+h.id+'">'+e(h.title)+'</a>').join('');
 $('#report-footer').textContent=report.demo?'디자인 확인을 위한 합성 예시입니다. 실제 하네스 파일을 불러오면 본문·표·그래프·근거가 해당 결과로 바뀝니다.':'이 보고서는 연결한 결과 파일을 표시한 문서입니다. 보고서 표시와 인쇄 과정에서 새로운 분석을 실행하지 않습니다.';
}
const traceBasis=b=>({source_fact:'확인 사실',ai_interpretation:'인공지능 해석',unverified:'미확인'}[b]||'기록된 판단');
function renderTraceLaunchers(){
 const entries=report.decisionNotes.length?report.decisionNotes.map((item,index)=>({item,index,kind:'decision'})):report.concepts.map((item,index)=>({item,index,kind:'concept'}));
 $('#evidence-trace').hidden=!entries.length;$('#trace-workspace').hidden=true;$('#trace-workspace').innerHTML='';document.body.classList.remove('trace-active');
 $('#trace-launchers').innerHTML=entries.map(({item,index,kind})=>'<button class="trace-launcher" id="trace-start-'+kind+'-'+index+'" data-trace-kind="'+kind+'" data-trace-index="'+index+'" aria-controls="trace-workspace" aria-expanded="false"><span class="trace-launcher-label">'+(kind==='decision'?'결론 '+(index+1)+' · '+e(traceBasis(item.basis)):'개선안 '+(index+1))+'</span><strong>'+e(item.body||item.title)+'</strong><span class="trace-launcher-footer"><span>명시된 근거 '+new Set(item.sourceIds).size+'건</span><b>근거 따라보기 →</b></span></button>').join('');
}
function getTraceBundle(){
 const origin=window.HarnessReportAdapter.trace(report,{kind:traceState.kind,index:traceState.index,turnId:report.selectedTurnId||undefined});
 const candidates=traceState.kind==='decision'?origin.related.concepts:[origin.seed].filter(Boolean);
 const focus=traceState.conceptIndex!=null?window.HarnessReportAdapter.trace(report,{kind:'concept',index:traceState.conceptIndex,turnId:report.selectedTurnId||undefined}):origin;
 return {origin,candidates,focus};
}
function traceSourceButtons(ids){return '<div class="trace-source-buttons">'+list(ids).map(id=>sourceIds.has(id)?'<button data-trace-source="'+e(id)+'">'+e(sourceLabel(id))+' ↗</button>':'<span>원자료 미제공</span>').join('')+'</div>';}
function traceItemHTML(item){return '<article class="trace-claim"><h4>'+e(item.title||item.body||'기록된 항목')+'</h4>'+(item.body&&item.title!==item.body?'<p>'+e(item.body)+'</p>':'')+(item.requirements?.length?'<ul>'+item.requirements.map(t=>'<li>'+e(t)+'</li>').join('')+'</ul>':'')+traceSourceButtons(item.matchedSourceIds||item.sourceIds)+'</article>';}
const tracePlanFields=[['metric','확인 지표'],['baseline','비교 기준'],['method','확인 방법'],['success_criterion','성공 조건'],['business_value','확인할 가치']];
const presentPlanFields=plan=>tracePlanFields.filter(([k])=>plan?.[k]!=null&&plain(plan[k]).trim());
function tracePlanHTML(seed){
 const plan=seed?.validationPlan,assumptions=list(seed?.assumptions);
 let html=assumptions.length?'<h4>확인할 전제</h4><ul>'+assumptions.map(t=>'<li>'+e(t)+'</li>').join('')+'</ul>':'';
 if(presentPlanFields(plan).length){html+='<dl class="trace-plan">'+presentPlanFields(plan).map(([k,t])=>'<div><dt>'+t+'</dt><dd>'+e(plain(plan[k]))+'</dd></div>').join('')+'</dl><p class="trace-note">기록된 검증 계획입니다. 검증 수행이나 효과 확정을 뜻하지 않습니다.</p>';}else html+='<p class="trace-empty">이 항목에 연결된 검증 계획이 없습니다.</p>';
 if(typeof seed?.requiresHardware==='boolean')html+='<p class="trace-note">추가 하드웨어: '+(seed.requiresHardware?'필요로 기록됨':'필요하지 않은 후보로 기록됨')+'</p>';
 return html||'<p class="trace-empty">이 항목에 연결된 검증 계획이 없습니다.</p>';
}
function traceSteps(focus){return [
 {title:'고객 불편',subtitle:'같은 근거를 참조하는 고객 불편',items:focus.related.discomforts},
 {title:'기존 기능',subtitle:'같은 근거를 참조하는 기존 기능',items:focus.related.existingFeatures},
 {title:'남은 문제',subtitle:'같은 근거를 참조하는 남은 문제',items:focus.related.remainingDiscomforts},
 {title:'개선안',subtitle:'선택한 개선안과 요구사항',items:focus.kind==='concept'&&focus.seed?[focus.seed]:focus.related.concepts},
 {title:'검증 계획',subtitle:'확인할 가정과 검증 방법',plan:true,seed:focus.kind==='concept'?focus.seed:null}
 ];}
function stageHTML(step){return step.plan?tracePlanHTML(step.seed):step.items.length?step.items.map(traceItemHTML).join(''):'<p class="trace-empty">같은 근거를 참조하는 '+e(step.title)+' 항목이 없습니다. 제공된 연결만 표시합니다.</p>';}
function renderTraceSources(focus,origin=focus){
 const seen=new Set(),rows=[...focus.sources,...origin.sources].filter(s=>{if(seen.has(s.evidenceIndex))return false;seen.add(s.evidenceIndex);return true;});
 return '<aside class="trace-evidence" aria-label="선택한 항목의 원자료"><header><h3>원자료 확인</h3><span>'+new Set(rows.map(s=>s.id)).size+'건 · '+rows.length+'개 인용</span></header><p class="trace-note">결론과 선택한 개선안이 직접 참조한 자료입니다. 근거 번호를 누르면 해당 인용이 강조됩니다.</p><div class="trace-evidence-scroll">'+rows.map((s,i)=>'<article class="trace-evidence-card" data-trace-evidence-id="'+e(s.id)+'"><span>'+e(sourceLabel(s.id))+' · '+e(label(s.type)||'자료')+(s.synthetic?' · 합성 예시':'')+'</span><small>'+[origin.kind==='decision'&&origin.sourceIds.includes(s.id)?'결론에 명시':'',focus.kind==='concept'&&focus.sourceIds.includes(s.id)?'선택한 개선안에 명시':''].filter(Boolean).join(' · ')+'</small><h4>'+e(s.title||sourceLabel(s.id))+'</h4>'+(s.body?'<blockquote>'+e(s.body)+'</blockquote>':'<p class="trace-empty">원문 인용이 제공되지 않았습니다.</p>')+(s.location?'<p class="trace-location">'+e(s.location)+'</p>':'')+(safeUrl(s.url)?'<a href="'+e(safeUrl(s.url))+'" target="_blank" rel="noopener noreferrer">원문 열기 ↗</a>':'')+'</article>').join('')+'</div>'+([...new Set([...focus.missingSourceIds,...origin.missingSourceIds])].length?'<p class="trace-empty">참조된 출처 중 원자료가 제공되지 않은 항목이 있습니다.</p>':'')+(!rows.length?'<p class="trace-empty">이 항목에 명시된 원자료가 없습니다.</p>':'')+'</aside>';
}
function highlightTrace(focus){
 const matched=new Set();['discomforts','existingFeatures','remainingDiscomforts','concepts'].forEach(k=>focus.related[k].forEach(item=>matched.add(k+':'+item.index)));
 if(focus.kind==='concept'&&focus.seed)matched.add('concepts:'+focus.seed.index);
 $$('.result-card[data-claim-kind]').forEach(card=>card.classList.toggle('trace-match',matched.has(card.dataset.claimKind+':'+card.dataset.claimIndex)));
 const ids=new Set(focus.sourceIds);$$('.source-card').forEach(card=>card.classList.toggle('trace-match',ids.has(report.evidence[Number(card.dataset.evidenceIndex)]?.id)));
 document.body.classList.add('trace-active');
}
function renderTraceWorkspace(focusHeading=false){
 const {origin,candidates,focus}=getTraceBundle();if(!origin.seed){closeTrace(false);return;}
 const steps=traceSteps(focus),step=steps[traceState.step];
 const switches=candidates.length?'<div class="trace-concept-options"><span>'+(origin.kind==='decision'?'결론과 같은 근거를 참조하는 개선안':'선택한 개선안')+'</span><div>'+candidates.map(c=>'<button data-trace-concept="'+c.index+'" aria-pressed="'+(c.index===traceState.conceptIndex)+'">'+e(c.title||c.body)+'</button>').join('')+'</div></div>':'<p class="trace-note">결론과 같은 근거를 참조하는 개선안이 기록되어 있지 않습니다.</p>';
 const originRefs=origin.kind==='decision'?'<div class="trace-origin-refs"><span>결론에 명시된 근거</span>'+traceSourceButtons(origin.sourceIds)+'</div>':'';
 $('#trace-workspace').innerHTML='<header class="trace-workspace-head"><div><span class="trace-eyebrow">선택한 '+(origin.kind==='decision'?'결론':'개선안')+'</span><h3 id="trace-focus-title" tabindex="-1">'+e(origin.seed.body||origin.seed.title)+'</h3></div><button class="trace-close" data-trace-close aria-label="근거 따라보기 닫기">닫기 ×</button></header>'+originRefs+switches+'<p class="trace-method">연결 기준: 같은 출처를 참조하는 항목을 함께 보여줍니다. 표시 순서는 확인 순서이며, 인과관계나 검증 완료를 의미하지 않습니다.</p>'+
 '<nav class="trace-step-nav" aria-label="근거 확인 단계">'+steps.map((s,i)=>'<button data-trace-step="'+i+'" aria-current="'+(i===traceState.step?'step':'false')+'"><span>'+String(i+1).padStart(2,'0')+'</span><strong>'+s.title+'</strong><small>'+(s.plan?(presentPlanFields(s.seed?.validationPlan).length?'계획 있음':'계획 미제공'):s.items.length+'개 항목')+'</small></button>').join('')+'</nav>'+
 '<div class="trace-detail-grid"><section class="trace-stage" aria-labelledby="trace-stage-title"><p class="trace-eyebrow">'+(traceState.step+1)+' / 5 단계</p><h3 id="trace-stage-title" tabindex="-1">'+e(step.subtitle)+'</h3>'+stageHTML(step)+'<div class="trace-stage-controls"><button data-trace-prev'+(traceState.step===0?' disabled':'')+'>← 이전</button><button data-trace-next'+(traceState.step===4?' disabled':'')+'>'+(traceState.step===4?'마지막 단계':'다음: '+e(steps[traceState.step+1].title)+' →')+'</button></div></section>'+renderTraceSources(focus,origin)+'</div>'+
 '<section class="trace-print"><h3>선택한 개선안의 근거 연결</h3>'+steps.map(s=>'<article><h4>'+e(s.title)+'</h4>'+stageHTML(s)+'</article>').join('')+'</section>';
 $('#trace-workspace').hidden=false;
 $$('#trace-launchers button').forEach(b=>b.setAttribute('aria-expanded',String(b.dataset.traceKind===traceState.kind&&Number(b.dataset.traceIndex)===traceState.index)));
 highlightTrace(focus);
 if(focusHeading)$('#trace-stage-title').focus({preventScroll:true});
 $('#announcement').textContent=step.subtitle+'을 표시했습니다.';
}
function openTrace(kind,index,trigger){
 const origin=window.HarnessReportAdapter.trace(report,{kind,index,turnId:report.selectedTurnId||undefined});if(!origin.seed)return;
 traceReturnTarget=trigger||null;traceState={kind,index,conceptIndex:kind==='concept'?index:(origin.related.concepts[0]?.index??null),step:0};
 renderTraceWorkspace();$('#trace-workspace').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});$('#trace-focus-title').focus({preventScroll:true});
}
function closeTrace(restore=true){traceState=null;$('#trace-workspace').hidden=true;$('#trace-workspace').innerHTML='';document.body.classList.remove('trace-active');$$('.trace-match').forEach(el=>el.classList.remove('trace-match'));$$('#trace-launchers button').forEach(b=>b.setAttribute('aria-expanded','false'));if(restore&&traceReturnTarget?.isConnected)traceReturnTarget.focus();}
function restoreTraceSelection(){
 let saved;try{saved=JSON.parse($('#embedded-report').getAttribute('data-trace-selection')||'null');}catch(_){return;}
 if(!saved||!['decision','concept'].includes(saved.kind)||!Number.isSafeInteger(saved.index)||saved.index<0)return;
 const origin=window.HarnessReportAdapter.trace(report,{kind:saved.kind,index:saved.index,turnId:report.selectedTurnId||undefined});if(!origin.seed)return;
 const candidates=saved.kind==='decision'?origin.related.concepts:[origin.seed];
 const chosen=candidates.find(c=>c.index===saved.conceptIndex)||candidates[0];
 traceState={kind:saved.kind,index:saved.index,conceptIndex:chosen?.index??null,step:Number.isInteger(saved.step)&&saved.step>=0&&saved.step<5?saved.step:0};
 traceReturnTarget=$$('#trace-launchers button').find(b=>b.dataset.traceKind===saved.kind&&Number(b.dataset.traceIndex)===saved.index)||null;
 renderTraceWorkspace();
}
document.addEventListener('click',event=>{
 const open=event.target.closest('[data-trace-kind]');if(open){openTrace(open.dataset.traceKind,Number(open.dataset.traceIndex),open);return;}
 if(event.target.closest('[data-trace-close]')){closeTrace();return;}
 if(!traceState)return;
 const concept=event.target.closest('[data-trace-concept]');if(concept){traceState.conceptIndex=Number(concept.dataset.traceConcept);traceState.step=0;renderTraceWorkspace(true);return;}
 const step=event.target.closest('[data-trace-step]');if(step){traceState.step=Number(step.dataset.traceStep);renderTraceWorkspace(true);return;}
 if(event.target.closest('[data-trace-next]')){traceState.step=Math.min(4,traceState.step+1);renderTraceWorkspace(true);return;}
 if(event.target.closest('[data-trace-prev]')){traceState.step=Math.max(0,traceState.step-1);renderTraceWorkspace(true);return;}
 const source=event.target.closest('[data-trace-source]');if(source){const id=source.dataset.traceSource;let first;$$('.trace-evidence-card').forEach(el=>{const match=el.dataset.traceEvidenceId===id;el.classList.toggle('is-highlighted',match);if(match&&!first)first=el;});if(first){first.setAttribute('tabindex','-1');first.focus({preventScroll:true});first.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'nearest'});$('#announcement').textContent=sourceLabel(id)+' 원자료를 강조했습니다.';}}
});
function toggleDrawer(open){$('#contents-drawer').hidden=!open;$('#drawer-backdrop').hidden=!open;$('#contents-toggle').setAttribute('aria-expanded',String(open));if(open)$('#contents-close').focus();}
function download(name,text,type){const blob=new Blob([text],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);}
function safeJSON(v){return JSON.stringify(v).replace(/[<>&\u2028\u2029]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));}
async function downloadHTML(){
 const clone=document.documentElement.cloneNode(true);
 clone.querySelector('#embedded-report').textContent=safeJSON(payload);
 clone.querySelector('#embedded-report').setAttribute('data-turn-id',report.selectedTurnId||'');
 clone.querySelector('#embedded-report').setAttribute('data-trace-selection',JSON.stringify(traceState));
 const css=list(Array.from(clone.querySelectorAll('link[rel="stylesheet"]'))),js=list(Array.from(clone.querySelectorAll('script[src]')));
 for(const link of css){const res=await fetch(new URL(link.getAttribute('href'),location.href));if(!res.ok)throw Error('스타일 파일을 가져오지 못했습니다.');const style=document.createElement('style');style.textContent=(await res.text()).replace(/<\/style/gi,'<\\/style');link.replaceWith(style);}
 for(const script of js){const res=await fetch(new URL(script.getAttribute('src'),location.href));if(!res.ok)throw Error('보고서 표시 코드를 가져오지 못했습니다.');const content=(await res.text()).replace(/<\/script/gi,'<\\/script');script.removeAttribute('src');script.textContent=content;}
 clone.querySelector('#load-notice').hidden=true;clone.querySelector('#contents-drawer').hidden=true;clone.querySelector('#drawer-backdrop').hidden=true;
 const dialog=clone.querySelector('dialog');dialog?.removeAttribute('open');
 download('kitchen-harness-result.html','<!doctype html>\n'+clone.outerHTML,'text/html;charset=utf-8');notice('현재 결과와 그래프를 담은 HTML 파일을 저장했습니다.');
}
async function loadSample(){const res=await fetch('report-sample.json',{cache:'no-cache'});if(!res.ok)throw Error('예시 결과를 읽지 못했습니다. 결과 파일을 불러와 주세요.');const raw=await res.json();fileLabel='';render(raw);}
$('#import-report').addEventListener('click',()=>$('#report-file').click());
$('#report-file').addEventListener('change',async event=>{try{const files=Array.from(event.target.files||[]);if(!files.length)return;if(files.length>2)throw Error('결과 JSON과 보고서 계획 JSON을 최대 2개 선택하세요.');if(files.some(f=>f.size>16*1024*1024))throw Error('각 파일은 16 MiB 이하여야 합니다.');const raws=await Promise.all(files.map(async f=>JSON.parse(await f.text())));let data=raws[0];if(raws.length===2){const idx=raws.findIndex(x=>x&&Array.isArray(x.sections)&&Array.isArray(x.sources)&&Array.isArray(x.summary));if(idx<0)throw Error('두 파일 중 하나는 보고서 계획 JSON이어야 합니다.');data={export:raws[1-idx],report_plan:raws[idx]};}fileLabel=files.map(f=>f.name).join(' + ');render(data);$('#load-notice').hidden=true;notice('결과 파일을 반영했습니다. 파일은 서버로 전송하지 않았습니다.');window.scrollTo({top:0,behavior:'smooth'});}catch(err){notice(err.message||'결과 파일을 읽지 못했습니다.',true);}finally{event.target.value='';}});
$('#turn-select').addEventListener('change',event=>{try{render(payload,{turnId:event.target.value});}catch(err){notice(err.message,true);}});
$('#evidence-search').addEventListener('input',()=>report&&renderEvidence());
document.addEventListener('click',event=>{if(event.target.closest('.evidence-refs a')){selectedFilter='all';$('#evidence-search').value='';$$('#evidence-filters button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filter==='all')));renderEvidence();}});
$('#evidence-filters').addEventListener('click',event=>{const button=event.target.closest('[data-filter]');if(!button)return;selectedFilter=button.dataset.filter;$$('#evidence-filters button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));renderEvidence();});
$('#contents-toggle').addEventListener('click',()=>toggleDrawer($('#contents-drawer').hidden));$('#contents-close').addEventListener('click',()=>toggleDrawer(false));$('#drawer-backdrop').addEventListener('click',()=>toggleDrawer(false));$('#contents-list').addEventListener('click',event=>{if(event.target.closest('a'))toggleDrawer(false);});
document.addEventListener('keydown',event=>{if(event.key==='Escape')toggleDrawer(false);});
$('#print-report').addEventListener('click',()=>{toggleDrawer(false);window.print();});
let printDetails=[];
window.addEventListener('beforeprint',()=>{printDetails=$$('#paper details:not([open])');printDetails.forEach(d=>d.open=true);});
window.addEventListener('afterprint',()=>{printDetails.forEach(d=>d.open=false);printDetails=[];});
$('#show-sample').addEventListener('click',()=>loadSample().then(()=>{$('#load-notice').hidden=true;}).catch(err=>notice(err.message,true)));
$('#download-data').addEventListener('click',()=>{if(payload)download('harness-report-data.json',JSON.stringify(payload,null,2),'application/json;charset=utf-8');});
$('#download-html').addEventListener('click',()=>downloadHTML().catch(err=>notice(err.message,true)));
$('#copy-link').addEventListener('click',async()=>{try{await navigator.clipboard.writeText('https://kitchen-agent-evidence-report.tlswlsgk7174.chatgpt.site/');notice('뷰어 주소를 복사했습니다. 불러온 결과를 공유하려면 HTML 저장을 이용하세요.');}catch(_){notice('브라우저 주소를 복사해 주세요. 결과는 HTML 파일로 저장할 수 있습니다.');}});
$('#detail-close').addEventListener('click',()=>$('#detail-dialog').close());
window.addEventListener('scroll',()=>{const total=document.documentElement.scrollHeight-innerHeight;$('#reading-progress').style.width=(total>0?scrollY/total*100:0)+'%';},{passive:true});
(async()=>{try{const embedded=JSON.parse($('#embedded-report').textContent);if(embedded){fileLabel='저장된 결과 보고서';render(embedded,{turnId:$('#embedded-report').getAttribute('data-turn-id')||undefined});restoreTraceSelection();}else await loadSample();}catch(err){notice(err.message||'결과를 표시할 수 없습니다.',true);$('#result-body').innerHTML='<p class="empty-result">상단의 결과 불러오기에서 하네스 JSON 파일을 선택하세요.</p>';}})();
})();
