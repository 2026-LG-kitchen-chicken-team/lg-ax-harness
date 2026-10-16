export const ZONE_IDS = ['overview','retrieve','structure','compare','concept','validate'];
const BASE = {overview:[0,0],retrieve:[-5.9,.1],structure:[-2.9,-4.9],compare:[3.4,-4.05],concept:[5.3,1.9],validate:[-1.05,5.7]};
const horizontal=Math.hypot(13,18),length=Math.hypot(13,17,18);
export const VIEW={rx:18/horizontal,rz:-13/horizontal,dx:17/length*13/horizontal,dz:17/length*18/horizontal,uy:horizontal/length};
export function worldToField(x,y,z){return {u:VIEW.rx*x+VIEW.rz*z,v:VIEW.dx*x+VIEW.dz*z-VIEW.uy*y};}
export function fieldToWorld(u,v){const determinant=VIEW.rx*VIEW.dz-VIEW.rz*VIEW.dx;return {x:(u*VIEW.dz-VIEW.rz*v)/determinant,z:(VIEW.rx*v-VIEW.dx*u)/determinant};}

export function factoryLayout({width=1280,height=800,panelWidth=0,activeIds=[]}={}){
  const available=Math.max(240,width-Math.max(0,panelWidth)),active=ZONE_IDS.filter(id=>activeIds.includes(id));
  const compact=available<720,short=compact&&height<540&&available/height>1.22;
  const zones=Object.fromEntries(ZONE_IDS.map(id=>[id,{id,x:BASE[id][0],z:BASE[id][1],scale:1,active:active.includes(id)}]));
  const place=(id,u,v,scale)=>Object.assign(zones[id],fieldToWorld(u,v),{scale});
  if(compact){
    const order=[...active,...ZONE_IDS.filter(id=>!active.includes(id))],columns=short?3:2,rows=Math.ceil(order.length/columns);
    order.forEach((id,i)=>place(id,(i%columns-(columns-1)/2)*7.1,(Math.floor(i/columns)-(rows-1)/2)*7.3,id==='overview'&&!active.includes(id)?.72:active.includes(id)?1.12:.82));
  }else if(active.length===1){
    place(active[0],0,-.7,1.9);
    const rest=ZONE_IDS.filter(id=>!active.includes(id)&&id!=='overview');
    rest.forEach((id,i)=>{const slots=[[-8.7,-5.5],[8.7,-5.5],[-8.7,4.1],[8.7,4.1],[0,8.3]];place(id,...slots[i],.68);});
    if(!active.includes('overview'))place('overview',0,6.7,.72);
  }else if(active.length===2){
    active.forEach((id,i)=>place(id,(i-.5)*10.0,-.3,1.55));
    const rest=ZONE_IDS.filter(id=>!active.includes(id)&&id!=='overview');
    rest.forEach((id,i)=>place(id,(i-(rest.length-1)/2)*6.8,-6.7,.65));
    if(!active.includes('overview'))place('overview',0,5.9,.68);
  }else if(active.length>2){
    const columns=available/height>1.4?3:2,rows=Math.ceil(active.length/columns);
    active.forEach((id,i)=>{const row=Math.floor(i/columns),count=Math.min(columns,active.length-row*columns);place(id,(i%columns-(count-1)/2)*7.8,(row-(rows-1)/2)*6.5-1.2,active.length===3?1.18:1.08);});
    const rest=ZONE_IDS.filter(id=>!active.includes(id)&&id!=='overview');
    rest.forEach((id,i)=>place(id,(i-(rest.length-1)/2)*16,-6.5,.65));
    if(!active.includes('overview'))place('overview',0,rows>1?8.3:5.8,.68);
  }
  // Keep raised islands and their circulation lanes apart, including when two
  // independently reported Skills become active at the same time.
  const list=Object.values(zones);
  for(let pass=0;pass<16;pass++)for(let a=0;a<list.length;a++)for(let b=a+1;b<list.length;b++){
    const one=list[a],two=list[b],dx=two.x-one.x,dz=two.z-one.z,distance=Math.hypot(dx,dz),minimum=(one.id==='overview'?2.2:2.8)*one.scale+(two.id==='overview'?2.2:2.8)*two.scale+.38;
    if(distance<minimum){const nx=distance?dx/distance:1,nz=distance?dz/distance:0,move=(minimum-distance)/2;one.x-=nx*move;one.z-=nz*move;two.x+=nx*move;two.z+=nz*move;}
  }
  return {zones,compact,short,active};
}

export function fitFactory(zones,{width,height,panelWidth=0,top=84,bottom=88}={}){
  const availableWidth=Math.max(180,width-panelWidth-24),availableHeight=Math.max(140,height-top-bottom);
  let minU=Infinity,maxU=-Infinity,minV=Infinity,maxV=-Infinity;
  for(const zone of Object.values(zones)){
    const r=zone.id==='overview'?2.45:3.05,h=zone.id==='overview'?3.0:3.5;
    for(const x of [-r,r])for(const z of [-r,r])for(const y of [0,h]){
      const p=worldToField(zone.x+x*zone.scale,y*zone.scale,zone.z+z*zone.scale);
      minU=Math.min(minU,p.u);maxU=Math.max(maxU,p.u);minV=Math.min(minV,p.v);maxV=Math.max(maxV,p.v);
    }
  }
  const unit=Math.max((maxU-minU+1.4)/availableWidth,(maxV-minV+1.6)/availableHeight);
  const centerU=(minU+maxU)/2,centerV=(minV+maxV)/2-(top+(height-top-bottom)/2-height/2)*unit;
  return {extent:Math.max(4,unit*height/2),...fieldToWorld(centerU,centerV+VIEW.uy*.35),bounds:{minU,maxU,minV,maxV},unit};
}

export function popScale(from,to,age,reduced=false){
  if(reduced||age>=1.2)return to;
  const t=Math.max(0,age),response=1-Math.exp(-7*t)*(Math.cos(12*t)+7/12*Math.sin(12*t));
  return from+(to-from)*response;
}

export function patrolPosition(time,{planner=false}={}){
  const x=planner?1.85:2.32,z=planner?1.65:2.12;
  const points=[[0,z],[x,z],[x,-z],[-x,-z],[-x,z],[0,z]],lengths=points.slice(1).map((p,i)=>Math.hypot(p[0]-points[i][0],p[1]-points[i][1]));
  const distance=lengths.reduce((a,b)=>a+b,0),walking=distance/.83,cycle=walking+3.4,phase=((Math.max(0,time)%cycle)+cycle)%cycle;
  if(phase>=walking)return {x:0,z,y:.06,walking:false,dx:0,dz:0,cycle};
  let at=phase*.83;
  for(let i=0;i<lengths.length;i++){
    if(at<=lengths[i]){const t=at/lengths[i],a=points[i],b=points[i+1];return {x:a[0]+(b[0]-a[0])*t,z:a[1]+(b[1]-a[1])*t,y:.06,walking:true,dx:(b[0]-a[0])/lengths[i],dz:(b[1]-a[1])/lengths[i],cycle};}
    at-=lengths[i];
  }
  return {x:0,z,y:.06,walking:false,dx:0,dz:0,cycle};
}

// Relocation uses shrink → reappear rather than crossing occupied islands.
// Positions stay fixed until the old islands are fully collapsed.
export function transitionFactory(from,to,age,reduced=false){
  const collapse=.18,t=Math.max(0,age);
  return Object.fromEntries(Object.entries(to).map(([id,dest])=>{
    const start=from[id]||dest;
    if(reduced)return [id,{...dest,visible:true}];
    if(t<collapse){const p=t/collapse,ease=p*p*(3-2*p),scale=start.scale*(1-ease);return [id,{...start,scale,visible:scale>.06}];}
    const scale=popScale(0,dest.scale,t-collapse);
    return [id,{...dest,scale,visible:scale>.06}];
  }));
}
