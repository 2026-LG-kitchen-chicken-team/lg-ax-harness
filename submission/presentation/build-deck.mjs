// Authoring helper for submission slides, outside the product runtime.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const skill=process.env.LG_PRESENTATION_SKILL;
const packages=process.env.LG_RUNTIME_NODE_MODULES;
const python=process.env.LG_RUNTIME_PYTHON;
if(!skill || !packages || !python) throw new Error('Set the three documented bundled runtime paths');
process.env.RUNTIME_NODE_MODULES=packages;
process.env.RUNTIME_NODE=process.execPath;
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(packages,'@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const model=JSON.parse(await fs.readFile(path.join(root,'submission/presentation/slides.json'),'utf8'));
const build=path.join(root,'.harness/presentation-build');
const output=path.join(root,'submission/presentation');
await fs.mkdir(build,{recursive:true});
process.chdir(build);
const presentation=Presentation.create({slideSize:{width:1280,height:720}});
const font='Malgun Gothic';
const ink='#123029', accent='#176F53', muted='#56655E', background='#F5F4EE';
function text(slide,value,x,y,w,h,size=28,color=ink,bold=false){
 const box=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 box.text=value;
 box.text.style={fontSize:size,typeface:font,color,bold,alignment:'left',wrap:'square',autoFit:'none',insets:0};
 return box;
}
function rect(slide,x,y,w,h,fill){return slide.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:'none',width:0}});}
for(const [index,data] of model.slides.entries()){
 const slide=presentation.slides.add();
 slide.background.fill=background;
 rect(slide,64,36,72,5,accent);
 text(slide,data.title,64,58,1152,118,42,ink,true);
 if(data.subtitle) text(slide,data.subtitle,66,176,1136,42,27,accent,true);
 let y=data.subtitle?244:228;
 if(data.rows){
  const columns=data.rows[0].length;
  const height=data.rows.length*72;
  const table=slide.tables.add({rows:data.rows.length,columns,left:64,top:y,width:1152,height,
   columnWidths:columns===3?[210,435,507]:[540,612],values:data.rows});
  for(let r=0;r<data.rows.length;r++) for(let c=0;c<columns;c++){
   const cell=table.getCell(r,c);
   cell.fill=r%2===0?'#E5ECE3':'#F5F4EE';
   cell.text.style={fontSize:23,typeface:font,color:ink,bold:c===0};
  }
  y+=height+26;
 }
 if(data.flow){
  const n=data.flow.length, width=1112/n;
  data.flow.forEach((label,i)=>{
   text(slide,String(i+1).padStart(2,'0'),64+i*width,y,100,50,35,accent,true);
   text(slide,label,64+i*width,y+60,width-30,76,24,ink,true);
   if(i<n-1)text(slide,'→',64+(i+1)*width-42,y+28,45,50,30,accent);
  });
  y+=158;
 }
 if(data.bars){
  const chart=slide.charts.add('bar',{position:{left:64,top:y,width:1152,height:246},
   categories:data.bars.map(r=>r[0]),series:[{name:'일반 AI 대비 비율',values:data.bars.map(r=>r[1]),fill:accent}],
   hasLegend:false,dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.00'},
   yAxis:{numberFormatCode:'0.0',majorGridlines:{style:'solid',fill:'#D2DBD2',width:1}}});
  applyPresentationChartFont(chart,{fontFamily:font});
  y+=254;
 }
 const available=648-y;
 const spacing=Math.min(data.rows||data.bars?52:76,Math.floor(available/data.lines.length));
 const size=data.rows||data.bars?22:27;
 for(const [i,line] of data.lines.entries()) text(slide,line,66,y+i*spacing,1146,spacing,size,i===data.lines.length-1?muted:ink,false);
 text(slide,`검토용 발표초안 · 실제 영상/리허설 별도  |  ${index+1} / ${model.slides.length}`,64,677,1160,26,14,muted);
 slide.speakerNotes.text=`발표 예정 ${data.seconds}초. 평가 ${data.requirements.join(', ')}\n근거:\n${data.sources.join('\n')}\n관측·계획·미확인을 구분. 이 발표파일은 실제 영상/리허설/접수 완료를 뜻하지 않는다.`;
 const image=await presentation.export({slide,format:'png',scale:1});
 await fs.writeFile(path.join(build,`slide-${String(index+1).padStart(2,'0')}.png`),new Uint8Array(await image.arrayBuffer()));
}
const candidate=path.join(build,'candidate.pptx');
await(await PresentationFile.exportPptx(presentation)).save(candidate);
const report=await finalizePresentation({workspaceDir:root,candidatePath:candidate,
 finalPath:path.join(output,'kitchen-planning.pptx'),pythonExecutable:python,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--require-native-table-slide','3','--require-native-table-slide','5'],
 explicitTotalSlideCount:model.slides.length,requiredNativeTableOwnerSlides:[3,5],requiredNativeChartOwnerSlides:[10],
 materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
 receiptPath:path.join(build,'validation.json')});
const esc=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const markup=model.slides.map((s,i)=>`<section class="slide" id="s${i+1}"><h1>${esc(s.title)}</h1>${s.subtitle?`<h2>${esc(s.subtitle)}</h2>`:''}${s.flow?`<div class="flow">${s.flow.map((v,i)=>`<div><b>${String(i+1).padStart(2,'0')}</b><strong>${esc(v)}</strong></div>`).join('')}</div>`:''}${s.rows?`<table>${s.rows.map(r=>`<tr>${r.map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</table>`:''}${s.bars?`<div class="chart" role="img" aria-label="일반 AI 대비 관측 지표의 비율"><small>일반 AI = 1.00 · 각2회 평균</small>${s.bars.map(([label,value])=>`<div class="barrow"><span>${esc(label)}</span><div class="track"><div style="width:${value/3.3*100}%"></div></div><b>${value.toFixed(2)}배</b></div>`).join('')}</div>`:''}<div class="lines">${s.lines.map(v=>`<p>${esc(v)}</p>`).join('')}</div><footer>검토용 발표초안 · 실제 영상/리허설 별도 <span>${i+1} / ${model.slides.length}</span></footer><details><summary>근거 및 발표 시간</summary><p>${s.seconds}초 예정 · ${s.requirements.join(', ')}</p>${s.sources.map(v=>`<div>${esc(v)}</div>`).join('')}</details></section>`).join('\n');
await fs.writeFile(path.join(output,'presentation.html'),`<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LG AX 키친 상품기획</title><style>
*{box-sizing:border-box}body{margin:0;background:#172C25;color:#123029;font-family:"Malgun Gothic",sans-serif}.slide{width:min(1280px,100%);min-height:720px;position:relative;padding:58px 64px 90px;margin:24px auto;background:#F5F4EE;scroll-margin-top:16px}h1{font-size:40px;line-height:1.3;margin:0 0 36px;max-width:1152px}h2{font-size:27px;color:#176F53;margin:0 0 30px}p{font-size:27px;line-height:1.45;margin:20px 0}.lines p:last-child{color:#56655E}footer{position:absolute;bottom:26px;left:64px;right:64px;font-size:14px;color:#56655E}footer span{float:right}.flow{display:flex;gap:32px;margin:45px 0}.flow div{flex:1}.flow b{display:block;color:#176F53;font-size:36px}.flow strong{display:block;font-size:24px;margin-top:20px}table{width:100%;border-collapse:collapse;margin:20px 0 30px;font-size:23px}td{padding:20px;border-bottom:1px solid #D2DBD2}tr:nth-child(odd){background:#E5ECE3}td:first-child{font-weight:bold}.chart{margin:20px 0 30px}.barrow{display:flex;align-items:center;gap:24px;margin:16px 0;font-size:22px}.barrow>span{width:160px}.track{flex:1;background:#E1E5DD;height:24px}.track>div{height:100%;background:#176F53}.barrow>b{width:94px}small{font-size:18px}details{margin:32px 0 0;color:#56655E;font-size:15px}details p{font-size:17px}nav{position:fixed;bottom:14px;right:18px;display:flex;gap:8px;z-index:3}button{font:inherit;padding:10px 18px;color:#fff;background:#176F53;border:0;cursor:pointer}@media(max-width:800px){.slide{padding:35px 25px 75px;min-height:auto}h1{font-size:29px}p{font-size:22px}.flow{flex-wrap:wrap}.flow div{min-width:35%}td{font-size:18px;padding:12px}footer{left:25px;right:25px;font-size:12px}.barrow{font-size:18px;gap:12px}.barrow>span{width:105px}}@media print{@page{size:landscape;margin:0}body{background:none}.slide{margin:0;height:100vh;min-height:0;width:100%;page-break-after:always;break-after:page}nav,details{display:none}}
</style></head><body>${markup}<nav aria-label="슬라이드 이동"><button id="prev" aria-label="이전 슬라이드">←</button><button id="next" aria-label="다음 슬라이드">→</button><button onclick="window.print()">인쇄</button></nav><script>let index=0;const slides=[...document.querySelectorAll('.slide')];function go(delta){index=Math.max(0,Math.min(slides.length-1,index+delta));slides[index].scrollIntoView({behavior:'smooth'});}document.getElementById('prev').onclick=()=>go(-1);document.getElementById('next').onclick=()=>go(1);window.addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key==='PageDown')go(1);if(e.key==='ArrowLeft'||e.key==='PageUp')go(-1);});</script></body></html>`,'utf8');
console.log(JSON.stringify({pages:model.slides.length,planned_seconds:model.planned_seconds,pptx:'submission/presentation/kitchen-planning.pptx',html:'submission/presentation/presentation.html',validation:report}));
