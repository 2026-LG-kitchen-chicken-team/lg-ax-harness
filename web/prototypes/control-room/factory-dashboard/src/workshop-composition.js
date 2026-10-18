import {ROOM_ORDER,fieldToWorld} from './factory-layout.js';
// Presentation only: use the same run-derived room sizes in the approved two-row lab composition.
export function composeWorkshopLayout(layout){
 if(layout.columns!==3)return layout;
 const depth=[-5.25,-7.5,-5.25,7,9,7];
 const zones=Object.fromEntries(Object.entries(layout.zones).map(([id,z])=>{
  const index=ROOM_ORDER.indexOf(id);
  const v=id==='validate'&&z.active?Math.max(depth[index],6.5*z.scale+2.2*layout.zones.overview.scale+.7):depth[index];
  return [id,index<0?z:{...z,...fieldToWorld((index%3-1)*13,v)}];
 }));
 return {...layout,zones};
}
