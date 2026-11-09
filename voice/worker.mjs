// Outbound-only relay consumer. No listener, no Gateway credential access.
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

export function createWorker({relay, secret, bridge='http://127.0.0.1:8765', code, localTest=false, mock=false, fetchImpl=fetch}) {
  const remote = new URL(relay), local = new URL(bridge);
  if (remote.username || remote.password || remote.search || remote.hash || remote.pathname !== '/' || !(remote.protocol==='https:' || (localTest && remote.protocol==='http:' && remote.hostname==='127.0.0.1'))) throw Error('Relay must be an HTTPS origin');
  if(local.protocol!=='http:' || local.hostname!=='127.0.0.1' || local.username || local.password || local.pathname!=='/' || local.search || local.hash) throw Error('Bridge must be loopback HTTP');
  if(!secret || secret.length<32 || (!mock && (!code || code.length<20 || code===secret))) throw Error('Independent worker / bridge credentials required');
  let cookie='';
  async function post(path, body={}) {
    const response=await fetchImpl(remote.origin+'/api/voice'+path,{method:'POST',redirect:'error',headers:{'Content-Type':'application/json',Authorization:'Bearer '+secret},body:JSON.stringify(body),signal:AbortSignal.timeout(10000)});
    if(!response.ok)throw Error('relay_request_failed');
    return response.json();
  }
  async function bridgeCall(path, body, timeout=5000) {
    const response=await fetchImpl(local.origin+path,{method:body?'POST':'GET',redirect:'error',headers:{Origin:local.origin,...(cookie?{Cookie:cookie}:{}),...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(timeout)});
    if(response.status===401)cookie='';
    if(!response.ok)throw Error('bridge_request_failed');
    if(path==='/api/login')cookie=response.headers.get('set-cookie')?.split(';')[0] || '';
    return response.json();
  }
  async function tick() {
    // Authenticate / check availability before reserving work. Never start stale work.
    if(!mock){
      if(!cookie)await bridgeCall('/api/login',{code});
      const status=await bridgeCall('/api/status');
      if(status.busy)return false;
    }
    const {job}=await post('/worker/claim');
    if(!job)return false;
    // A lost start response is deliberately NOT retried. Relay never requeues leases.
    const task=await post('/worker/'+job.id+'/start',{lease:job.lease});
    if(Date.now()/1000>task.dispatchBefore) return false;
    let reply, state='done';
    try {
      reply=mock?'[MOCK agent] '+task.text:(await bridgeCall('/api/chat',{text:task.text},123000)).reply;
      if(typeof reply!=='string' || !reply.trim())throw Error('invalid_reply');
      reply=reply.slice(0,6000);
    } catch {
      state='failed';reply='白总连接失败；动作可能已执行，请确认结果后再发问。';
    }
    // Only result delivery may be retried, never the agent invocation.
    for(let i=0;i<3;i++) {
      try{await post('/worker/'+job.id+'/result',{lease:job.lease,state,reply});return true;}
      catch{if(i===2)throw Error('result_delivery_failed');}
    }
    return true;
  }
  return {tick};
}

if(process.argv[1]===fileURLToPath(import.meta.url)) {
  const mock=process.env.VOICE_MOCK_AGENT==='1';
  const code=mock?'':(await readFile(process.env.VOICE_BRIDGE_CODE_FILE,'utf8')).trim();
  const worker=createWorker({relay:process.env.VOICE_RELAY_ORIGIN,secret:process.env.VOICE_WORKER_SECRET,bridge:process.env.VOICE_BRIDGE_ORIGIN,code,mock,localTest:process.env.VOICE_LOCAL_TEST==='1'});
  console.log(mock?'Voice worker: MOCK agent (no real tools)':'Voice worker: loopback bridge, outbound relay');
  let stopped=false;
  for(const sig of ['SIGINT','SIGTERM'])process.on(sig,()=>{stopped=true;});
  while(!stopped){
    try{await worker.tick();}catch{console.error('Voice worker cycle failed; no agent retry.');await new Promise(r=>setTimeout(r,15000));}
    if(!stopped)await new Promise(r=>setTimeout(r,1500));
  }
}
