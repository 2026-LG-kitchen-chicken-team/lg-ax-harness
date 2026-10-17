import React,{useState} from 'react';
import {Activity,ChevronDown,ChevronUp,Terminal,Clock3} from 'lucide-react';
import {cliActivity} from './cli-activity.js';
import './cli-activity.css';
const time=value=>value&&Number.isFinite(Date.parse(value))?new Date(value).toLocaleTimeString('ko-KR',{hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'}):'';
export default function CliActivityPanel({summary,view,onDetails}){
 const [folded,setFolded]=useState(false),model=cliActivity(summary,view);
 return <aside className={'cli-activity-panel '+(folded?'is-folded':'')} aria-label="CLI 실시간 작업 소식">
  <header><span><Terminal size={15}/>CLI 작업 소식</span><button onClick={()=>setFolded(!folded)} aria-label={folded?'작업 소식 펼치기':'작업 소식 접기'} aria-expanded={!folded}>{folded?<ChevronDown size={15}/>:<ChevronUp size={15}/>}</button></header>
  {!folded&&<><div className="cli-activity-status"><span className={model.active?'is-active':''}><i/>{model.status}</span>{time(model.lastAt)&&<time><Clock3 size={10}/>{time(model.lastAt)}</time>}</div>
   <section className="cli-now" aria-live="polite" aria-atomic="true"><small>지금 하는 일</small><h2>{model.title}</h2><p>{model.detail}</p></section>
   <section className="cli-skills"><h3>{model.preview?'시연 중인 Skill':'사용 중인 Skill'}</h3>{model.skills.length?<div>{model.skills.map(s=><span key={s.id}><Activity size={11}/>{s.label}</span>)}</div>:<p>확인된 실행 없음</p>}</section>
   <section className="cli-recent"><h3>방금 한 일</h3>{model.recent.length?<ol>{model.recent.map(e=><li key={e.id}><i/><div><p>{e.text}</p>{time(e.time)&&<time>{time(e.time)}</time>}</div></li>)}</ol>:<p>{model.preview?'실제 작업 이력은 만들지 않아요.':'아직 받은 작업 기록이 없어요.'}</p>}</section>
   <details className="cli-next"><summary>다음 순서</summary><p>{model.next}</p></details>
   {onDetails&&<button className="cli-details-button" onClick={onDetails}>상세 기록 보기</button>}
  </>}
 </aside>;
}
