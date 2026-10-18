import {ROOM_ORDER,fieldToWorld} from './factory-layout.js';
// Presentation only: use the same run-derived room sizes in the approved two-row lab composition.
export function composeWorkshopLayout(layout){
 const {available=1280,height=800}=layout.viewport||{};
 const columns=available<760&&!(height<520&&available/height>1.4)?2:3;
 const compact=columns===2;
 const usableHeight=Math.max(240,height-(compact?184:116));
 const pitch=compact?Math.max(11.6,Math.min(18,available/usableHeight*31.5-8.9)):Math.max(14,Math.min(20,(available/usableHeight*24.6-9.7)/2));
 const row=compact?Math.max(11.6,Math.min(16,(usableHeight/Math.max(240,available-24)*(pitch+9.1)-8.4)/2)):0;
 const depth=compact?[-row,-row,0,0,row,row]:[-4.4,-5.4,-4.4,10.8,11.6,10.8];
 const plannerV=compact?4.4:-.3;
 const zones=Object.fromEntries(Object.entries(layout.zones).map(([id,z])=>{
  if(id==='overview')return [id,{...z,...fieldToWorld(0,plannerV)}];
  const index=ROOM_ORDER.indexOf(id);
  const v=id==='validate'&&z.active&&!compact?Math.max(depth[index],plannerV+6.5*z.scale+2.2*layout.zones.overview.scale+.7):depth[index];
  return [id,index<0?z:{...z,...fieldToWorld((index%columns-(columns-1)/2)*pitch,v)}];
 }));
 return {...layout,zones,columns,compact};
}
