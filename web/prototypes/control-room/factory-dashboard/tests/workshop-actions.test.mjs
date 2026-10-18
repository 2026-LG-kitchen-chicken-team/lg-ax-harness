import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {createWorkshopActions} from '../src/workshop-actions.js';
import {ROOM_ORDER,factoryLayout,fitFactory,worldToField} from '../src/factory-layout.js';
import {composeWorkshopLayout} from '../src/workshop-composition.js';

test('two and three concurrent Skills stay visibly larger with clear original artwork in both responsive grids',()=>{
 for(const [width,height] of [[1440,900],[1920,1080],[754,768],[390,844],[320,568],[844,390]]){
  for(let mask=0;mask<64;mask++){
   const activeIds=ROOM_ORDER.filter((_,i)=>mask&(1<<i));if(![2,3].includes(activeIds.length))continue;
   const layout=composeWorkshopLayout(factoryLayout({width,height,roomIds:ROOM_ORDER,activeIds}));
   const fit=fitFactory(layout.zones,{width,height,artwork:true,top:110,bottom:74});
   const boxes=ROOM_ORDER.map(id=>{const z=layout.zones[id],p=worldToField(z.x,0,z.z);return {id,left:p.u-4.6*z.scale,right:p.u+4.6*z.scale,top:p.v-6.5*z.scale,bottom:p.v+2.2*z.scale};});
   for(const a of boxes){
    assert.ok(a.left>=fit.bounds.minU-.001&&a.right<=fit.bounds.maxU+.001&&a.top>=fit.bounds.minV-.001&&a.bottom<=fit.bounds.maxV+.001);
    for(const b of boxes)if(a.id!==b.id)assert.ok(Math.min(a.right,b.right)-Math.max(a.left,b.left)<.001||Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)<.001,`artwork overlap ${width}: ${a.id}/${b.id}`);
   }
   for(const id of activeIds)for(const idle of ROOM_ORDER.filter(x=>!activeIds.includes(x)))assert.ok(layout.zones[id].scale>layout.zones[idle].scale*1.8);
  }
 }
});

test('moving Skill props stay behind researcher faces and freeze on idle or reduced motion',()=>{
 const resources=[],stations=Object.fromEntries(ROOM_ORDER.map(id=>[id,new THREE.Group()]));
 const sprite=new THREE.Object3D();sprite.scale.set(9.2,8,1);
 const art={room:id=>({frame:{},sprite})},actions=createWorkshopActions(stations,art,resources);
 const groups=Object.fromEntries(ROOM_ORDER.map(id=>[id,stations[id].getObjectByName('skill-action-'+id)]));
 const pose=g=>{const values=[];g.traverse(p=>values.push([...p.position.toArray(),...p.rotation.toArray(),p.visible]));return JSON.stringify(values);};
 actions.update({activeIds:['structure','compare'],dt:.1});
 for(const id of ROOM_ORDER){
  assert.equal(groups[id].visible,['structure','compare'].includes(id));
  groups[id].traverse(p=>{if(p.isMesh)assert.ok(p.renderOrder>-1&&p.renderOrder<.5,'props may never paint over the researcher face');});
 }
 const before=pose(groups.structure);actions.update({activeIds:['structure','compare'],dt:.1,reducedMotion:true});assert.equal(pose(groups.structure),before);
 actions.update({activeIds:[],dt:.1});const idle=pose(groups.structure);actions.update({activeIds:[],dt:.1});assert.equal(pose(groups.structure),idle);
 for(const r of resources)r.dispose();
});
