"use strict";
const DataView=(()=>{
  const object=x=>x!==null&&typeof x==="object"&&!Array.isArray(x);
  const array=x=>Array.isArray(x)?x:[];
  const display=x=>x===null||x===undefined?"미확인":typeof x==="string"?x:JSON.stringify(x);
  const safeURL=x=>{try{const url=new URL(x);return ["http:","https:"].includes(url.protocol)?url.href:null;}catch{return null;}};
  const safeImageURL=x=>{
    const href=safeURL(x);if(!href)return null;const url=new URL(href),host=url.hostname.toLowerCase();
    if(url.protocol!=="https:"||url.username||url.password||host==="localhost"||/\.(localhost|local|internal)$/.test(host))return null;
    if(host.includes(":")||host.startsWith("["))return null;
    if(/^[0-9.]+$/.test(host))return null;
    return href;
  };
  const numeric=x=>{if(typeof x==="number")return Number.isFinite(x)?x:null;if(typeof x!=="string"||!/^[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?$/i.test(x.trim()))return null;const value=Number(x);return Number.isFinite(value)?value:null;};
  function exportFile(value){return object(value)&&typeof value.session_id==="string"&&Array.isArray(value.turns)&&value.turns.every(t=>object(t)&&object(t.state));}
  function turnView(value,index){
    const turns=array(value.turns),turn=turns[index];if(!turn)return null;
    const state=turn.state,candidates=array(turn.candidates),last=candidates[candidates.length-1];
    const result=object(state.latest_result)?state.latest_result:object(last?.result)?last.result:null;
    const stored=object(state.latest_result),status=state.status??"미기록";
    return {state,result,candidates,stored,status,valid:state.valid,reason:state.invalidation_reason,session:value.session_id,semantic:state.semantic_status??value.semantic_status??"미기록",acceptance:state.acceptance_ready??value.acceptance_ready,question:state.input?.question,models:array(state.input?.model_scope).map(x=>x.model_id).filter(x=>typeof x==="string"),dataVersion:state.input?.data_version,claims:{pains:array(result?.pains),existing_features:array(result?.existing_features),remaining_pains:array(result?.remaining_pains),concepts:array(result?.concepts)},refs:array(result?.evidence_refs),findings:array(result?.validation_findings),assumptions:array(result?.assumptions)};
  }
  function table(value){
    if(!Array.isArray(value)||!value.length)return null;
    if(!value.every(object))return {columns:["값"],rows:value.slice(0,200).map(x=>[display(x)]),total_rows:value.length};
    const keys=[...new Set(value.flatMap(x=>Object.keys(x)))].slice(0,30);
    return {columns:keys,rows:value.slice(0,200).map(x=>keys.map(k=>display(x[k]))),total_rows:value.length};
  }
  function numericColumns(data){return array(data.columns).map((_,i)=>i).filter(i=>array(data.rows).some(row=>numeric(row[i])!==null)&&array(data.rows).every(row=>row[i]===undefined||row[i]===""||numeric(row[i])!==null));}
  return {object,array,display,safeURL,safeImageURL,numeric,exportFile,turnView,table,numericColumns};
})();
if(typeof module!=="undefined")module.exports=DataView;
