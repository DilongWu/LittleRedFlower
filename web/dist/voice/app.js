const $=id=>document.getElementById(id);
const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
let currentJob=null,cancelRequested=false, active=false,busy=false,speaking=false,recognition=null,lastReply='',wake=null,retry=0,speechTimer;
const status=s=>{$('status').textContent=s;};
async function api(path,body){const r=await fetch(path,{signal:AbortSignal.timeout(15000),method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},...(body?{body:JSON.stringify(body)}:{})});const d=await r.json();if(r.status===401){$('controls').hidden=true;$('login').hidden=false;}if(!r.ok)throw Error(d.detail||d.error||'连接失败');return d;}
function add(who,text){const p=document.createElement('p');p.className=who==='我'?'mine':'reply';p.textContent=who+'：'+text;$('history').append(p);p.scrollIntoView({block:'nearest'});}
function endRecognition(){const r=recognition;recognition=null;if(r){r.onend=null;r.onresult=null;r.onerror=null;try{r.abort();}catch{}}}
function stop(message){active=false;endRecognition();clearTimeout(speechTimer);window.speechSynthesis?.cancel();speaking=false;wake?.release().catch(()=>{});wake=null;status(message||(busy?'已停止收音和播报；已发送的问题仍在后端处理。':'已停止。点击开始可继续。'));}
async function getWake(){try{wake=await navigator.wakeLock?.request('screen');}catch{/* Foreground is still required. */}}
function listen(){if(!active||busy||speaking||document.hidden||recognition)return;if(!Recognition||!window.isSecureContext){active=false;status('当前环境不能网页收音，请用文字或键盘听写。');return;}const r=new Recognition();recognition=r;r.lang='zh-CN';r.continuous=false;r.interimResults=true;let final='';status('正在听…说完稍停即可');
 r.onresult=e=>{if(recognition!==r)return;let partial='';for(let i=e.resultIndex;i<e.results.length;i++){if(e.results[i].isFinal)final+=e.results[i][0].transcript;else partial+=e.results[i][0].transcript;}status('听到：'+(final||partial));if(final.trim()){retry=0;endRecognition();send(final);}};
 r.onerror=e=>{if(recognition!==r)return;endRecognition();if(e.error==='no-speech'&&active&&retry++<3){setTimeout(listen,700);return;}stop('收音暂停：'+e.error+'。请点开始重试，或用文字。');};
 r.onend=()=>{if(recognition!==r)return;recognition=null;if(active&&!busy&&!speaking){if(retry++<3)setTimeout(listen,700);else stop('长时间未听到声音，点击开始继续。');}};
 try{r.start();}catch{endRecognition();stop('浏览器未允许开始收音，请再次点击开始。');}}
function speak(text){endRecognition();if(!window.speechSynthesis){stop('当前浏览器不能播报，请阅读回答。');return;}clearTimeout(speechTimer);window.speechSynthesis.cancel();speaking=true;const u=new SpeechSynthesisUtterance(text);u.lang='zh-CN';u.rate=1;const voice=window.speechSynthesis.getVoices().find(v=>v.lang.startsWith('zh'));if(voice)u.voice=voice;status('白总正在说…');
 u.onend=()=>{clearTimeout(speechTimer);speaking=false;if(active&&$('auto').checked)setTimeout(listen,500);else status('回答完毕。点击开始继续或重播。');};
 u.onerror=()=>{clearTimeout(speechTimer);speaking=false;stop('播报被浏览器阻止或中断，点击重播回答。');};
 // Avoid starting the microphone if Safari silently blocks audio or loses its end event.
 speechTimer=setTimeout(()=>stop('播报未正常结束。请点击重播，或继续用文字。'),Math.min(180000,Math.max(30000,text.length*350)));
 window.speechSynthesis.speak(u);
}
async function send(text){text=text.trim();if(!text||busy)return;endRecognition();cancelRequested=false;busy=true;$('send').disabled=true;status('白总正在想…');add('我',text);try{const job=await api('/api/voice/jobs',{text,idempotencyKey:crypto.randomUUID(),issuedAt:Date.now()/1000});currentJob=job.id;if(cancelRequested)await api('/api/voice/jobs/'+job.id+'/cancel',{});let d; const deadline=Date.now()+175000;while(Date.now()<deadline){d=await api('/api/voice/jobs/'+job.id);if(d.state==='done')break;if(['failed','expired','cancelled'].includes(d.state))throw Error(d.reply||(d.state==='cancelled'?'已取消等待；已开始的操作可能继续，请确认结果。':'任务已超时；可能已经执行，请先确认结果，勿自动重发。'));await new Promise(resolve=>setTimeout(resolve,1000));}if(d?.state!=='done')throw Error('等待超时；可能已执行，请先确认结果，勿自动重发。');lastReply=d.reply;add('白总',d.reply);if(active)speak(d.reply);else status('回答已显示，可点击重播回答。');}catch(e){stop(e.message+' 已发送的问题可能仍在执行，请确认结果后再发问；本页不会自动重发。');}finally{currentJob=null;busy=false;$('send').disabled=false;}}
function connected(){$('login').hidden=true;$('controls').hidden=false;$('support').textContent=Recognition&&window.isSecureContext?'支持前台连续对话：播报时暂停收音，播完再听。':'此浏览器无法网页收音，请用文字或键盘听写；回答可点击重播。';status('已通过认证。发送后由私人 worker 接通白总；worker 离线时任务会超时。');}
$('start').onclick=()=>{if(busy){status('请等待当前回答，期间可停止播报。');return;}active=true;retry=0;getWake();if(window.speechSynthesis){const u=new SpeechSynthesisUtterance('');u.lang='zh-CN';window.speechSynthesis.speak(u);}listen();};
$('logout').onclick=async()=>{stop();try{await api('/api/logout',{});window.top.location.href='/';}catch(e){status(e.message);}};
$('stop').onclick=()=>{cancelRequested=true;stop();if(currentJob)api('/api/voice/jobs/'+currentJob+'/cancel',{}).catch(e=>status(e.message));};$('replay').onclick=()=>{if(lastReply){active=false;speak(lastReply);}else status('还没有可重播的回答。');};
$('textForm').onsubmit=e=>{e.preventDefault();const text=$('text').value;if(text.trim()&&!busy){$('text').value='';send(text);}};
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop('页面已进入后台。返回后请点击开始；锁屏不保证收音或播报。');});
window.addEventListener('pagehide',()=>stop());
api('/api/voice/status').then(connected).catch(e=>{$('login').hidden=false;status(e.message);});
