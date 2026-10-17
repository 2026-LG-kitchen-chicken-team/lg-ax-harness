import operations from '../shared/skill-operations.json' with {type:'json'};
export const SKILL_OPERATIONS = Object.freeze(operations);
export const skillOperation = name => SKILL_OPERATIONS[name] || null;
export function operationText(name, state='running') {
 const op=skillOperation(name);
 if(!op)return null;
 return state==='running'?op.text:`${op.label} · ${{completed:'완료',failed:'실패',cancelled:'취소',unknown:'종료 결과 확인 필요'}[state]||'기록 확인'}`;
}
