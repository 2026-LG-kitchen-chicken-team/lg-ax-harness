"use strict";
const $=id=>document.getElementById(id);
const state={items:[],history:[],cards:new Map(),filter:"all",fetching:false,zoom:null};
const kindNames={html:"인터랙티브 화면",image:"이미지",pdf:"문서",csv:"데이터 표",json:"저장된 데이터"};
const statuses={completed:"완료",held:"보류",needs_input:"추가 정보 필요",needs_revision:"수정 필요",cancelled:"취소",failed:"실패",pending:"진행 기록",rejected:"거절"};
function node(tag,text,className){const el=document.createElement(tag);if(text!==undefined&&text!==null)el.textContent=DataView.display(text);if(className)el.className=className;return el;}
function detail(label,content,open=false){const el=node("details");el.open=open;el.append(node("summary",label),content);return el;}
function list(items){const el=node("ul");for(const item of DataView.array(items).slice(0,150))el.append(node("li",typeof item==="string"?item:DataView.display(item)));if(items.length>150)el.append(node("li","전체 항목은 원본 다운로드에서 확인하세요."));return el;}
function short(x,max=4000){const text=DataView.display(x);return text.length>max?text.slice(0,max)+"… (전체 원문은 다운로드)":text;}
function assetURL(item){return "/api/assets/"+item.watch_id+"/"+item.id+"/"+encodeURIComponent(item.entry);}
async function get(url){const response=await fetch(url,{headers:url==="/api/state"?{"X-Viewer-UI":"1"}:{}});const value=await response.json();if(!response.ok)throw Error(value.error||"파일을 읽을 수 없습니다.");return value;}
function zoom(preview,item){if(state.zoom?.preview===preview){closeZoom();return;}closeZoom();const card=preview.parentNode;state.zoom={preview,card};card.classList.add("zoomed");document.body.classList.add("zoom-active");const button=card.querySelector(".zoom-action");if(button){button.textContent="확대 닫기 ×";button.setAttribute("aria-label","확대 닫기");}}
function closeZoom(){if(!state.zoom)return;const card=state.zoom.card;card.classList.remove("zoomed");document.body.classList.remove("zoom-active");const button=card.querySelector(".zoom-action");if(button){button.textContent="확대 ↗";button.removeAttribute("aria-label");}state.zoom=null;}
document.addEventListener("keydown",event=>{if(event.key==="Escape"&&state.zoom){event.preventDefault();closeZoom();}});
function renderTree(value,depth=0,budget={remaining:600}){
  if(budget.remaining--<=0)return node("p","미리보기 상한입니다. 전체 기록은 원본 다운로드에서 확인하세요.","small");
  if(!DataView.object(value)&&!Array.isArray(value))return node("p",short(value),"small");
  const wrap=node("div"),entries=Object.entries(value);
  if(depth>=4)return node("p",short(value),"small");
  for(const [key,item] of entries.slice(0,80)){
    if(budget.remaining<=0){wrap.append(node("p","이하 항목은 원본 다운로드에서 확인하세요.","small"));break;}
    if(DataView.object(item)||Array.isArray(item))wrap.append(detail(key+(Array.isArray(item)?" · "+item.length+"개":""),renderTree(item,depth+1,budget)));
    else {const p=node("p",null,"small");p.append(node("strong",key+": "),node("span",short(item)));wrap.append(p);}
  }
  if(entries.length>80)wrap.append(node("p","일부 항목만 미리보기로 표시합니다. 전체 내용은 원본 다운로드에서 확인하세요.","small"));
  return wrap;
}
function renderTable(data){
  const wrap=node("div");wrap.append(node("p",data.total_rows+"행 · "+data.columns.length+"열"+(data.total_rows>data.rows.length?" · 처음 "+data.rows.length+"행 미리보기":""),"small"));
  if(data.omitted_columns)wrap.append(node("p",data.omitted_columns+"열은 원본 다운로드에서 확인하세요.","small"));
  const numeric=DataView.numericColumns(data);
  if(numeric.length){
    const label=node("label","비교할 수치 ","chart-label"),select=node("select"),chart=node("div");select.setAttribute("aria-label","비교할 수치");
    for(const i of numeric){const option=node("option",data.columns[i]||"열 "+(i+1));option.value=String(i);select.append(option);}label.append(select);wrap.append(label,chart);
    const draw=()=>{
      chart.replaceChildren();const col=Number(select.value),rows=data.rows.slice(0,20).filter(row=>DataView.numeric(row[col])!==null);
      const values=rows.map(row=>DataView.numeric(row[col])),min=Math.min(0,...values),max=Math.max(0,...values),span=max-min||1;
      chart.append(node("p",(data.columns[col]||"선택한 열")+"의 실제 값 · 처음 "+rows.length+"행","small"));
      for(const [index,row] of rows.entries()){
        const value=DataView.numeric(row[col]),line=node("div",null,"bar-row"),track=node("div",null,"bar-track");
        const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");svg.setAttribute("viewBox","0 0 100 16");svg.setAttribute("preserveAspectRatio","none");svg.setAttribute("aria-hidden","true");
        const rect=document.createElementNS(svg.namespaceURI,"rect");rect.setAttribute("x",String((Math.min(0,value)-min)/span*100));rect.setAttribute("y","2");rect.setAttribute("width",String(Math.abs(value)/span*100));rect.setAttribute("height","12");rect.setAttribute("rx","2");rect.setAttribute("fill",value<0?"#b0a0ca":"#9474d7");svg.append(rect);track.append(svg);
        const name=col===0?"행 "+(index+1):String(row[0]??"행 "+(index+1));line.append(node("span",name),track,node("span",value,"bar-value"));chart.append(line);
      }
    };select.onchange=draw;draw();
  }
  const scroll=node("div",null,"data-table-wrap"),table=node("table"),head=node("tr"),tbody=node("tbody");
  for(const column of data.columns)head.append(node("th",short(column,200)));
  const thead=node("thead");thead.append(head);table.append(thead);
  for(const row of data.rows){const tr=node("tr");for(let i=0;i<data.columns.length;i++)tr.append(node("td",short(row[i]??"",3000)));tbody.append(tr);}table.append(tbody);scroll.append(table);wrap.append(scroll);return wrap;
}
function renderExport(value,item){
  const wrap=node("div");wrap.append(node("p","저장 당시의 결과입니다. 현재 CLI의 진행 상태와 의미 품질을 확인한 화면은 아닙니다.","snapshot-note"));
  if(!value.turns.length){wrap.append(node("p","저장된 turn이 없습니다.","small"));return wrap;}
  const controls=node("label","요청 이력 ","chart-label"),select=node("select"),content=node("div");select.setAttribute("aria-label","요청 이력 · "+item.name);
  value.turns.forEach((turn,index)=>{const option=node("option",(index+1)+"번째 요청 · "+(statuses[turn.state.status]||turn.state.status||"상태 미기록")+(turn.state.valid===false?" · 무효화된 기록":""));option.value=String(index);select.append(option);});select.value=String(value.turns.length-1);controls.append(select);wrap.append(controls,content);
  const render=()=>{
    const view=DataView.turnView(value,Number(select.value));content.replaceChildren();
    const top=node("div",null,"result-top"),title=node("div");title.append(node("p",view.dataVersion||"자료 버전 미기록","small"),node("h3",view.models.join(" · ")||"하네스 결과"));
    if(view.question)title.append(detail("CLI에 입력한 요청",node("p",view.question)));top.append(title,node("span",statuses[view.status]||view.status,"badge "+(["held","needs_input","needs_revision","failed","cancelled"].includes(view.status)?"warn":"")));content.append(top);
    const facts=["업무 상태: "+view.status,"저장 시점 유효성: "+(view.valid===true?"유효로 기록됨":view.valid===false?"무효화됨":"미기록"),"의미 검토: "+view.semantic,"출품 인수: "+(view.acceptance===true?"true로 기록됨":view.acceptance===false?"미통과로 기록됨":"미기록")];
    content.append(node("p",facts.join(" · "),"small"));
    if(view.valid===false||view.reason){const reason=node("div",null,"findings");reason.append(node("strong","이전 조건의 기록"),node("p",view.reason||"무효화된 결과입니다."));content.append(reason);}
    if(!view.stored&&view.result)content.append(node("p","보관된 마지막 후보를 표시합니다. 채택된 최신 결과로 확인된 것은 아닙니다.","findings"));
    if(!view.result){content.append(node("p","이 요청에 저장된 결과 내용은 없습니다.","small"));return;}
    if(view.findings.length){const box=node("div",null,"findings");box.append(node("strong",view.status==="held"?"보류 사유와 확인할 조건":"검토 시 확인할 내용"));for(const finding of view.findings)box.append(node("p",short(finding)));content.append(box);}
    const metrics=node("div",null,"metrics");for(const [key,label] of [["pains","불편 주장"],["concepts","기획안"],["refs","명시된 근거"]]){const metric=node("div",null,"metric");metric.append(node("strong",key==="refs"?view.refs.length:view.claims[key].length),node("span",label));metrics.append(metric);}content.append(metrics,node("p","위 수량은 저장된 주장과 근거의 개수입니다. 고객 수나 시장 규모를 나타내지 않습니다.","small"));
    const refElements=new Map(),evidence=node("section",null,"evidence");evidence.append(node("h4","근거 원문 · 출처"));
    view.refs.slice(0,150).forEach(ref=>{
      const body=node("div");body.append(node("blockquote",ref.quote??"인용문 미기록"));const url=DataView.safeURL(ref.origin?.source_url);
      if(url){const link=node("a","출처 페이지 ↗");link.href=url;link.target="_blank";link.rel="noopener noreferrer";body.append(link);}
      const dl=node("dl"),origin=ref.origin||{};
      for(const [label,datum] of [["위치",ref.location],["제품 모델",ref.model_id],["모델 버전",ref.model_version],["문서 버전",ref.document_version],["자료 버전",ref.data_version],["자료 표현",origin.representation],["모델 연결",origin.model_matching],["구매 인증",origin.purchase_verified],["협찬 여부",origin.sponsorship],["조회일",origin.retrieved_date],["게시일",origin.published_date],["합성 표시",ref.synthetic],["원문 지문",ref.sha256]])dl.append(node("dt",label),node("dd",datum));body.append(dl);
      const d=detail(ref.source_id||"근거 ID 미기록",body);refElements.set(ref.source_id,d);evidence.append(d);
    });
    const chips=(parent,ids)=>{for(const id of DataView.array(ids).slice(0,100)){const button=node("button",id,"source-chip");button.type="button";button.onclick=()=>{const ref=refElements.get(id);if(ref){ref.open=true;ref.scrollIntoView({block:"center",behavior:"smooth"});}else button.textContent=id+" · 연결된 원문 없음";};parent.append(button);}};
    const columns=node("div",null,"comparison");for(const [key,label] of [["pains","고객이 말한 불편"],["existing_features","기존 제품의 기능"],["remaining_pains","남아 있는 불편"]]){
      const column=node("section",null,"claim-column");column.append(node("h4",label));const claims=view.claims[key];
      if(!claims.length)column.append(node("p","저장된 항목 없음","small"));for(const claim of claims.slice(0,100)){const c=node("div",null,"claim");c.append(node("p",short(claim.text)));chips(c,claim.source_ids);column.append(c);}columns.append(column);
    }content.append(columns);
    const concepts=node("section",null,"concepts");concepts.append(node("h4","제안한 기획안"));
    for(const [i,concept] of view.claims.concepts.slice(0,100).entries()){
      const card=node("article",null,"concept");card.append(node("h5",String(i+1).padStart(2,"0")+" · "+(concept.id||"기획안")),node("p",short(concept.text)));chips(card,concept.source_ids);
      card.append(node("p","추가 하드웨어 요구: "+DataView.display(concept.requires_hardware),"small"));
      if(DataView.array(concept.requirements).length)card.append(detail("요구사항 · "+concept.requirements.length+"개",list(concept.requirements),true));
      if(DataView.array(concept.assumptions).length)card.append(detail("기획안의 가정 · 확인 사항",list(concept.assumptions)));concepts.append(card);
    }content.append(concepts);
    if(view.assumptions.length)content.append(detail("전체 가정과 확인할 사항 · "+view.assumptions.length+"개",list(view.assumptions)));
    if(view.candidates.length){const history=node("div");for(const candidate of view.candidates){const c=node("div");c.append(node("p","후보 버전 "+DataView.display(candidate.result_version)+" · 업무 수정 횟수 "+DataView.display(candidate.result?.revisions)+" · 구조 검사 "+DataView.display(candidate.validation?.contract_valid),"small"),renderTree(candidate.validation||{}),detail("후보 원문",renderTree(candidate.result||{})));history.append(c);}content.append(detail("저장 후보와 검토 이력 · "+view.candidates.length+"개",history));}
    content.append(evidence);
    content.append(detail("원본 구조 · 전체 기록",renderTree(value)));
  };select.onchange=render;render();return wrap;
}
function renderCollected(value,imageAllowed){
  const wrap=node("div");wrap.append(node("p",value.source+" · "+(value.tool||"CLI 응답"),"snapshot-note"));
  if(value.kind==="inline_image"&&/^data:image\/(?:png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+$/.test(value.data_url||"")){
    const img=node("img");img.src=value.data_url;img.alt=value.caption||"CLI가 반환한 이미지";wrap.append(img,node("p",value.caption,"small"));
  }else if(value.kind==="remote_image"){
    const url=imageAllowed?DataView.safeImageURL(value.url):null;if(!url){wrap.append(node("p","이미지 주소를 확인할 수 없습니다.","small"));return wrap;}
    const img=node("img");img.src=url;img.alt=value.caption||"CLI가 반환한 이미지";img.referrerPolicy="no-referrer";wrap.append(img);
    const link=node("a",value.caption||"이미지 출처 ↗");link.href=url;link.target="_blank";link.rel="noopener noreferrer";wrap.append(link,node("p","반환된 이미지 주소를 표시합니다. 원격 이미지의 내용과 접근 가능성은 원본 제공처에 따릅니다.","small"));
  }else if(value.kind==="matrix"){wrap.append(node("p",value.note,"small"),renderTable(value));
  }else if(value.kind==="table"){
    wrap.append(node("p",(value.data_version?"자료 버전 "+value.data_version+" · ":"")+value.note+(value.truncated?" · 조회 범위에서 일부만 반환됨":"")+(value.synthetic===true?" · 합성 시험 자료":""),"small"));
    const table=DataView.table(value.value);if(table)wrap.append(renderTable(table));else wrap.append(node("p","표로 표시할 반환 자료가 없습니다.","small"));
  }else wrap.append(renderTree(value));
  return wrap;
}
function card(item){
  const el=node("article",null,"visual-card"+(item.kind==="html"||item.kind==="json"?" wide":""));el.dataset.key=item.watch_id+":"+item.path;
  const header=node("div",null,"card-header"),heading=node("div",null,"card-heading"),copy=node("div"),actions=node("div",null,"card-actions");
  copy.append(node("h2",item.name),node("div",item.folder+" · "+kindNames[item.kind]+" · "+new Date(item.modified*1000).toLocaleString("ko-KR"),"file-meta"));heading.append(node("span",({html:"↗",image:"▧",pdf:"▤",csv:"▥",json:"◇"})[item.kind],"file-icon"),copy);
  const download=node("a","원본 ↓");download.href=assetURL(item)+"?download=1";download.setAttribute("download",item.name);actions.append(download);header.append(heading,actions);el.append(header);
  const preview=node("div",null,"preview");el.append(preview);
  if(item.kind==="image"){const img=node("img");img.src=assetURL(item);img.alt=item.name;preview.append(img);}
  else if(item.kind==="html"||item.kind==="pdf"){const iframe=node("iframe");iframe.src=assetURL(item);iframe.title=item.name;iframe.setAttribute("sandbox","allow-scripts");preview.append(iframe);}
  else {preview.classList.add("data-body");preview.append(node("p","파일을 읽고 있어요.","small"));get("/api/data?watch="+item.watch_id+"&id="+item.id+"&name="+encodeURIComponent(item.entry)).then(data=>{
      if(data.format==="csv")preview.replaceChildren(renderTable(data));
      else if(data.collected&&data.value?.viewer_record==="public_cli_output_v1")preview.replaceChildren(renderCollected(data.value,data.image_allowed));
      else if(DataView.exportFile(data.value)){const latest=DataView.turnView(data.value,data.value.turns.length-1);if(latest){copy.querySelector("h2").textContent=(latest.models.join(" · ")||"하네스")+" · "+(statuses[latest.status]||latest.status)+" 기록";copy.querySelector("h2").title=item.name;}preview.replaceChildren(renderExport(data.value,item));}
      else {const table=DataView.table(data.value);preview.replaceChildren(table?renderTable(table):renderTree(data.value));}
    }).catch(error=>preview.replaceChildren(node("p",error.message,"findings")));}
  if(["image","html","pdf"].includes(item.kind)){const button=node("button","확대 ↗","zoom-action");button.type="button";button.onclick=()=>zoom(preview,item);actions.prepend(button);}
  if(item.historical)el.append(node("p","저장된 이전 버전입니다. 현재 파일의 내용과 다를 수 있습니다.","file-note"));
  else if(item.on_disk===false)el.append(node("p","원본 파일이 이동·삭제되어 보관된 내용을 표시합니다.","file-note"));
  for(const warning of item.warnings)el.append(node("p",warning,"file-note"));
  return el;
}
function filterGallery(){let count=0;for(const view of state.cards.values()){const visible=state.filter==="all"? !view.historical:state.filter==="history"?view.historical:!view.historical&&view.categories.includes(state.filter);view.el.classList.toggle("hidden",!visible);if(visible)count++;}$("empty").classList.toggle("hidden",count>0);}
for(const button of document.querySelectorAll("[data-filter]"))button.onclick=()=>{state.filter=button.dataset.filter;for(const b of document.querySelectorAll("[data-filter]")){b.classList.toggle("selected",b===button);b.setAttribute("aria-pressed",String(b===button));}filterGallery();refresh();};
async function refresh(){
  if(state.fetching)return;state.fetching=true;
  try{
    const value=await get("/api/state");state.items=value.items;state.history=value.history||[];const keys=new Set();const displayed=state.items.concat(state.filter==="history"?state.history.map(item=>({...item,historical:true})):[]);
    const oldFirst=$("gallery").firstChild;
    for(const item of displayed){const key=item.historical?"history:"+item.id:(item.source_key||(item.watch_id+":"+item.path));keys.add(key);const prior=state.cards.get(key);if(prior&&prior.id===item.id&&prior.on_disk===item.on_disk)continue;if(state.zoom&&prior?.el===state.zoom.card)closeZoom();const el=card(item);if(prior)prior.el.replaceWith(el);else $("gallery").insertBefore(el,oldFirst?.parentNode===$("gallery")?oldFirst:null);state.cards.set(key,{el,id:item.id,on_disk:item.on_disk,categories:item.categories||["evidence"],historical:!!item.historical});}
    for(const [key,view] of state.cards){if(!keys.has(key)){if(state.zoom&&view.el===state.zoom.card)closeZoom();view.el.remove();state.cards.delete(key);}}
    // Existing frames stay mounted between polls so local interactions keep their state.
    $("file-count").textContent=value.items.length+"개의 시각 자료";$("watch-label").textContent=value.watches.filter(w=>w.available).length+"곳의 자료 폴더 · 이전 자료 보관";
    $("connection").textContent="로컬 연결됨";$("notices").replaceChildren(...value.warnings.map(w=>node("p",w,"notice")));filterGallery();
  }catch(error){$("connection").textContent="연결 확인 필요";$("notices").replaceChildren(node("p",error.message,"notice"));}finally{state.fetching=false;}
}
refresh();setInterval(refresh,1500);
