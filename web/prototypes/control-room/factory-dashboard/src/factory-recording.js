// Record the actual rendered factory frames. Nameplates are copied from their
// live DOM positions so the saved video keeps the station names readable.
export function createFactoryRecording({ durationMs = 24000, getCaption, onComplete, onError }) {
  if (!globalThis.MediaRecorder || !HTMLCanvasElement.prototype.captureStream) throw Error('이 브라우저는 영상 저장을 지원하지 않습니다.');
  const output = document.createElement('canvas'), ctx = output.getContext('2d');
  let recorder = null, timer = null, stream = null, finished = false, cancelled = false;
  const chunks = [];
  const finish = () => { if (recorder?.state === 'recording') recorder.stop(); };
  const box = (x,y,w,h,r,fill) => {ctx.fillStyle=fill;ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fill();};
  const text = (value,x,y,maxWidth,font,color='#f7faf7') => {ctx.font=font;ctx.fillStyle=color;ctx.fillText(value,x,y,maxWidth);};
  return {
    draw({ canvas, host, labels }) {
      if (finished) return;
      try {
        const bounds = host.getBoundingClientRect(), w = Math.max(2,Math.round(bounds.width/2)*2), h = Math.max(2,Math.round(bounds.height/2)*2);
        if (!recorder) {
          output.width=w;output.height=h;
          stream=output.captureStream(30);
          const mime=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'].find(t=>MediaRecorder.isTypeSupported(t));
          recorder=new MediaRecorder(stream,mime?{mimeType:mime,videoBitsPerSecond:6_000_000}:undefined);
          recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
          recorder.onerror=()=>{cancelled=true;finished=true;clearTimeout(timer);stream.getTracks().forEach(t=>t.stop());onError?.('영상 저장 중 오류가 발생했습니다.');};
          recorder.onstop=()=>{finished=true;clearTimeout(timer);stream.getTracks().forEach(t=>t.stop());if(!cancelled)onComplete(new Blob(chunks,{type:recorder.mimeType||'video/webm'}));};
          recorder.start(500);timer=setTimeout(finish,durationMs);
        }
        ctx.fillStyle='#e9eeeb';ctx.fillRect(0,0,w,h);ctx.drawImage(canvas,0,0,w,h);
        for (const [id,element] of Object.entries(labels)) {
          if(!element||getComputedStyle(element).visibility==='hidden')continue;
          const r=element.getBoundingClientRect(),x=r.left-bounds.left,y=r.top-bounds.top;
          if(id==='overview'){
            box(x,y,r.width,r.height,8,'#fbfff9');ctx.strokeStyle='#98b8ad';ctx.strokeRect(x,y,r.width,r.height);
            text('MAIN PLANNER',x+10,y+15,r.width-20,'700 8px sans-serif','#9e7649');
            text(element.querySelector('strong')?.textContent||'메인 기획자',x+10,y+34,r.width-20,'800 15px sans-serif','#2c454c');
            text('연구원 모션 미리보기',x+10,y+r.height-8,r.width-20,'10px sans-serif','#728780');
          }else{
            const active=element.classList.contains('status-running');
            box(x,y,r.width,r.height,8,active?'#5b4837':'#30454b');
            ctx.strokeStyle=active?'#ffa75c':'#c4d4cd';ctx.strokeRect(x,y,r.width,r.height);
            text(element.querySelector('.factory-station-number')?.textContent||'',x+10,y+15,r.width-20,'700 9px sans-serif',active?'#ffd298':'#b9d0cb');
            text(element.querySelector('strong')?.textContent||'',x+10,y+35,r.width-20,'800 15px sans-serif');
            text(element.querySelector('.factory-station-caption')?.textContent||'',x+10,y+r.height-8,r.width-20,'9px sans-serif','#dce7e1');
          }
        }
        box(14,14,w-28,50,12,'#ffffffef');
        text('KITCHEN AX',28,45,155,'900 20px sans-serif','#29434a');
        text(getCaption?.()||'연구원 모션 시연',Math.min(200,w*.35),43,w-230,'700 15px sans-serif','#47615d');
        box(Math.max(16,w/2-225),h-46,Math.min(450,w-32),30,10,'#ffffffed');
        text('동작 미리보기 · 실제 CLI / LLM 실행 화면이 아닙니다',Math.max(27,w/2-213),h-26,Math.min(426,w-54),'600 12px sans-serif','#526b63');
      }catch(error){cancelled=true;finished=true;clearTimeout(timer);stream?.getTracks().forEach(t=>t.stop());if(recorder?.state==='recording')recorder.stop();onError?.(error.message);}
    },
    stop:finish,
    cancel(){cancelled=true;clearTimeout(timer);if(recorder?.state==='recording')recorder.stop();else stream?.getTracks().forEach(t=>t.stop());finished=true;},
  };
}
