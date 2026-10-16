import test from 'node:test';
import assert from 'node:assert/strict';
import {ZONE_IDS,factoryLayout,fitFactory,worldToField,fieldToWorld,popScale,patrolPosition,transitionFactory} from '../src/factory-layout.js';
import {advanceResearcherClock,researcherPose,previewActiveNodes} from '../src/researcher-motion.js';

test('every parallel group fits portrait, short landscape, desktop and open drawer bounds',()=>{
  for(const [width,height,panelWidth] of [[390,844,0],[320,568,0],[844,390,0],[1280,800,0],[1920,1080,0],[1280,800,470],[800,600,330]]){
    for(let count=0;count<=6;count++){
      const layout=factoryLayout({width,height,panelWidth,activeIds:ZONE_IDS.slice(0,count)});
      const fit=fitFactory(layout.zones,{width,height,panelWidth});
      const scale=height/(2*fit.extent),available=width-panelWidth-24;
      assert.ok((fit.bounds.maxU-fit.bounds.minU)*scale<=available+.01);
      assert.ok((fit.bounds.maxV-fit.bounds.minV)*scale<=height-84-88+.01);
      const zones=Object.values(layout.zones);
      for(let a=0;a<zones.length;a++)for(let b=a+1;b<zones.length;b++){
        const one=zones[a],two=zones[b];
        const clearance=(one.id==='overview'?2.2:2.8)*one.scale+(two.id==='overview'?2.2:2.8)*two.scale+.38;
        assert.ok(Math.hypot(one.x-two.x,one.z-two.z)>=clearance-.02,JSON.stringify({width,height,count,a,b}));
      }
      for(const id of ZONE_IDS.slice(0,count))assert.ok(layout.zones[id].scale>layout.zones[ZONE_IDS.at(-1)].scale||count===6||id===ZONE_IDS.at(-1));
    }
  }
});

test('field placement round trips through the fixed camera basis',()=>{
  for(const [u,v] of [[0,0],[-15,10],[12,-9]]){
    const p=fieldToWorld(u,v),back=worldToField(p.x,0,p.z);
    assert.ok(Math.abs(back.u-u)<1e-10);assert.ok(Math.abs(back.v-v)<1e-10);
  }
});

test('active island springs past its final size and reduced motion goes directly there',()=>{
  assert.equal(popScale(1,1.58,0),1);
  assert.ok(Math.max(...Array.from({length:30},(_,i)=>popScale(1,1.58,i/30)))>1.60);
  assert.equal(popScale(1,1.58,2),1.58);
  assert.equal(popScale(1,1.58,.15,true),1.58);
});

test('researcher completes a bounded loop then stops to inspect and repeats without teleporting',()=>{
  for(const planner of [false,true]){
    const start=patrolPosition(0,{planner}),seen=[];
    for(let t=0;t<start.cycle;t+=.05){
      const p=patrolPosition(t,{planner});
      assert.ok(Math.abs(p.x)<=(planner?1.85:2.32)+1e-8);assert.ok(Math.abs(p.z)<=(planner?1.65:2.12)+1e-8);
      if(seen.length)assert.ok(Math.hypot(p.x-seen.at(-1).x,p.z-seen.at(-1).z)<.05);
      seen.push(p);
    }
    assert.ok(seen.some(p=>!p.walking));assert.ok(seen.some(p=>p.x<0));assert.ok(seen.some(p=>p.z<0));
    const repeat=patrolPosition(start.cycle,{planner});assert.ok(Math.hypot(repeat.x-start.x,repeat.z-start.z)<1e-8);
  }
});

test('execution pause and reduced motion freeze the route clock; selection does not start work',()=>{
  assert.equal(advanceResearcherClock(5,{working:false,dt:.08}),5);
  assert.equal(advanceResearcherClock(5,{working:true,reducedMotion:true,dt:.08}),5);
  assert.equal(advanceResearcherClock(5,{working:true,dt:.08}),5.08);
  assert.equal(advanceResearcherClock(5,{working:true,dt:50}),5.1);
  assert.equal(researcherPose('compare',{activeIds:['structure'],selected:'compare'}).working,false);
  assert.equal(researcherPose('structure',{activeIds:['structure'],selected:'compare'}).working,true);
});

test('motion fixtures are explicitly separate, concurrent and stable long enough for a lap',()=>{
  assert.deepEqual(previewActiveNodes(0,'parallel2'),['structure','compare']);
  assert.deepEqual(previewActiveNodes(24,'parallel2'),['structure','compare']);
  assert.equal(previewActiveNodes(0,'parallel3').length,3);
  assert.deepEqual(previewActiveNodes(0,'all'),ZONE_IDS.slice(1));
  assert.equal(previewActiveNodes(0,'single').length,1);
});

test('changed active groups collapse before relocation and never cross another visible platform',()=>{
  for(const [width,height] of [[1280,800],[390,844],[844,390]]){
    const from=factoryLayout({width,height,activeIds:['structure','compare']}).zones;
    for(const activeIds of [['concept','validate'],['retrieve','structure','compare','concept','validate'],[]]){
      const to=factoryLayout({width,height,activeIds}).zones;
      for(let age=0;age<1.5;age+=1/120){
        const frame=transitionFactory(from,to,age);
        const zones=Object.values(frame).filter(z=>z.visible);
        for(let a=0;a<zones.length;a++)for(let b=a+1;b<zones.length;b++){
          const one=zones[a],two=zones[b],ax=one.id==='overview'?1.5:1.9,az=one.id==='overview'?1.35:1.625,bx=two.id==='overview'?1.5:1.9,bz=two.id==='overview'?1.35:1.625;
          assert.ok(Math.abs(one.x-two.x)>=(ax*one.scale+bx*two.scale)||Math.abs(one.z-two.z)>=(az*one.scale+bz*two.scale),'visible platforms intersect during transition');
        }
      }
      assert.deepEqual(Object.fromEntries(Object.entries(transitionFactory(from,to,.1,true)).map(([id,z])=>[id,{...z,visible:undefined}])),Object.fromEntries(Object.entries(to).map(([id,z])=>[id,{...z,visible:undefined}])));
    }
  }
});
