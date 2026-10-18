import test from 'node:test';
import assert from 'node:assert/strict';
import {localViewerToken} from '../src/local-bootstrap.js';
import {createReleaseStore} from '../src/release.js';
const origin='http://127.0.0.1:8036',token='synthetic-viewer-credential-01234567890123456789';
test('viewer renewal reads only its own loopback origin as JSON data, not code',async()=>{
 let calls=0;const fetchImpl=async()=>{calls++;return {ok:true,text:async()=>'<script type="application/json" id="ax-release-bootstrap">'+JSON.stringify({kind:'lgax_local_release_connection',url:origin,token})+'</script>'};};
 assert.equal(await localViewerToken(origin,{locationOrigin:origin,fetchImpl}),token);
 assert.equal(await localViewerToken(origin,{locationOrigin:'https://public.example',fetchImpl}),null);assert.equal(calls,1);
 assert.equal(await localViewerToken(origin,{locationOrigin:origin,fetchImpl:async()=>({ok:true,text:async()=>'<script id="ax-release-bootstrap">alert(1)</script>'})}),null);
});
test('a restarted same-origin viewer can renew once after 401 without exposing or persisting the credential',async()=>{
 const now=Date.now(),stamp=new Date(now).toISOString(),requests=[];
 const snapshot={schema_version:1,source:{kind:'lgax_release_observer',engine:'claude',release:null,observed_at:stamp,source_updated_at:null,observer_status:'waiting_for_session'},events:[],db:null};
 const store=createReleaseStore({clock:()=>now,setTimer:()=>1,clearTimer:()=>{},renewToken:async target=>{assert.equal(target,origin);return token;},fetchImpl:async(url,options)=>{requests.push({url,authorization:options.headers.Authorization});return requests.length===1?{ok:false,status:401}:{ok:true,status:200,json:async()=>snapshot};}});
 await store.connect({url:origin,token:'old-credential'});
 assert.equal(requests.length,2);assert.equal(requests[1].authorization,'Bearer '+token);assert.equal(store.getSnapshot().connection.status,'connected');assert.ok(!JSON.stringify(store.getSnapshot()).includes(token));store.disconnect();
});
