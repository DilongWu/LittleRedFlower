import assert from 'node:assert/strict';
import { createWorker } from './worker.mjs';

const secret='s'.repeat(40), code='c'.repeat(30);
assert.throws(()=>createWorker({relay:'http://example.com',secret,mock:true}));
assert.throws(()=>createWorker({relay:'https://example.com',secret,bridge:'http://example.com',code}));
let chats=0, starts=0, deliveries=0;
const json=(body,status=200,headers={})=>new Response(JSON.stringify(body),{status,headers});
const fake=async (url, options)=>{
  const path=new URL(url).pathname;
  if(path==='/api/login')return json({ok:true},200,{'set-cookie':'voice_session=fake; HttpOnly'});
  if(path==='/api/status')return json({busy:false});
  if(path.endsWith('/claim'))return json({job:{id:'id',lease:'lease'}});
  if(path.endsWith('/start')){starts++;return starts===1?json({text:'hello',dispatchBefore:Date.now()/1000+3}):json({},409);}
  if(path==='/api/chat'){chats++;throw Error('response lost after tool action');}
  if(path.endsWith('/result')){deliveries++;if(deliveries===1)throw Error('network lost');const data=JSON.parse(options.body);assert.equal(data.state,'failed');return json({ok:true});}
  throw Error('unexpected request');
};
const worker=createWorker({relay:'https://example.com',secret,code,fetchImpl:fake});
await worker.tick();
await assert.rejects(()=>worker.tick());
assert.equal(chats,1);assert.equal(starts,2);assert.equal(deliveries,2);
let dispatched=false;
const stale=createWorker({relay:'https://example.com',secret,code,fetchImpl:async(url,options)=>{
  if(url.endsWith('/start'))return json({text:'stale',dispatchBefore:Date.now()/1000-10});
  if(url.endsWith('/api/chat'))dispatched=true;
  return fake(url,options);
}});
await stale.tick();assert.equal(dispatched,false);
console.log('Worker safety: secret/origin validation, no agent retry, result-only retry, expired dispatch refusal PASS');
