const SOURCE = window.SIM_DATA;
if (!SOURCE?.config?.formats || !Object.keys(SOURCE.config.formats).length) {
  document.body.innerHTML = '<main class="load-error"><h1>模擬器資料未載入</h1><p>此頁是前端模板，或同一資料夾缺少 <code>data.js</code>。請開啟 build_simulator.py 產出的完整資料夾。</p></main>';
  throw new Error('SIM_DATA is missing or has no box formats. Keep data.js beside index.html.');
}
const CONFIG = SOURCE.config.formats;

const $ = s => document.querySelector(s);
const data = SOURCE;
const sectionEntries = Object.entries(data.sections).filter(([,v]) => v.length);
const basePool = data.sections[SOURCE.config.baseSection] || sectionEntries[0][1];
let format = Object.keys(CONFIG)[0];
let box = null;
let busy = false;

const norm = s => s.toUpperCase().replace(/REFRACTOR|RAYWAVE|X-FRACTOR|GEOMETRIC|WAVE|PRINTING PLATE|SUPERFRACTOR/g,'').replace(/\b(GREEN|PURPLE|GOLD|ORANGE|BLACK|RED|BLUE|AQUA|PINK|WHITE|TEAL|YELLOW|NEGATIVE|PRISM|BASE)\b/g,'').replace(/[^A-Z0-9]+/g,' ').trim();

function poolFor(setName){
  const target = norm(setName);
  let best = null, score = -1;
  for(const [name,pool] of sectionEntries){
    const n = norm(name);
    let s = target.includes(n) ? n.length : (n.includes(target) ? target.length : -1);
    if(/ROOKIE AUTOGRAPHS/.test(target) && name === 'ROOKIE AUTOGRAPHS') s = 100;
    if(/RETAIL ROOKIE AUTOGRAPHS/.test(target) && name === 'RETAIL ROOKIE AUTOGRAPHS') s = 110;
    if(s > score){best=pool;score=s;}
  }
  return best || basePool;
}

function pick(arr){return arr[Math.floor(Math.random()*arr.length)]}
function oddsKey(){return CONFIG[format].oddsColumn || format}
function oddRows(){return data.odds.filter(r => r.odds[oddsKey()])}
const autoRegex = new RegExp(SOURCE.config.autographPattern || 'AUTOGRAPH|AUTOGRAPHS|AUTOGRAPHED','i');
const autographSections = (SOURCE.autographSections || []).map(norm);
function isAuto(name){const target=norm(name);return autoRegex.test(name)||autographSections.some(section=>target.includes(section))}
function rarity(denom,name){
  if(/SUPERFRACTOR|LOGOMAN|TROPHY|PRINTING PLATE/.test(name)||denom>=100000)return {label:'傳奇',color:'#ff657a'};
  if(denom>=10000)return {label:'超稀有',color:'#ff8a35'};
  if(denom>=1000)return {label:'稀有',color:'#d9b6ff'};
  if(denom>=100)return {label:'特殊',color:'#61dded'};
  return {label:'平行／特卡',color:'#67e1a3'};
}
function makeHit(row,forced=false){
  const pool=poolFor(row.name), subject=pick(pool);
  const denom=row.odds[oddsKey()];
  return {...subject,set:row.name,denom,forced,auto:isAuto(row.name),...rarity(denom,row.name)};
}
function makeBase(){const s=pick(basePool);return {...s,set:SOURCE.config.baseSection,denom:null,label:'Base',color:'#8b99a8',auto:false}}

function generateBox(){
  const cfg=CONFIG[format], packs=[];
  for(let p=0;p<cfg.packs;p++){
    const hits=[];
    for(const row of oddRows()) if(Math.random()<1/row.odds[oddsKey()]) hits.push(makeHit(row));
    hits.sort((a,b)=>b.denom-a.denom);
    const kept=hits.slice(0,cfg.cards);
    while(kept.length<cfg.cards) kept.push(makeBase());
    packs.push(kept.sort(()=>Math.random()-.5));
  }
  let autos=packs.flat().filter(c=>c.auto).length;
  const autoRows=oddRows().filter(r=>isAuto(r.name));
  while(autos<cfg.guaranteedAutos && autoRows.length){
    // Conditional weighted selection: each autograph family keeps its official relative frequency.
    const weights=autoRows.map(r=>1/r.odds[oddsKey()]);
    let x=Math.random()*weights.reduce((a,b)=>a+b,0), row=autoRows[0];
    for(let i=0;i<autoRows.length;i++){x-=weights[i];if(x<=0){row=autoRows[i];break}}
    const candidates=packs.map((pack,i)=>pack.some(c=>!c.denom)?i:-1).filter(i=>i>=0);
    const pi=pick(candidates.length?candidates:packs.map((_,i)=>i));
    let ci=packs[pi].findIndex(c=>!c.denom); if(ci<0)ci=packs[pi].length-1;
    packs[pi][ci]=makeHit(row,true);autos++;
  }
  return {packs,index:0,opened:[],hits:[]};
}

function renderFormats(){
  $('#formats').innerHTML=Object.entries(CONFIG).map(([key,c])=>`<button class="format ${key===format?'active':''}" data-format="${key}"><span>${c.label}</span><small>${c.packs} 包 × ${c.cards} 張</small></button>`).join('');
  document.querySelectorAll('.format').forEach(b=>b.onclick=()=>{format=b.dataset.format;newBox()});
}
function renderSpec(){const c=CONFIG[format];$('#boxSpec').innerHTML=`<div class="spec-row"><span>每盒</span><b>${c.packs} 包</b></div><div class="spec-row"><span>每包</span><b>${c.cards} 張</b></div><div class="spec-row"><span>簽名保證</span><b>${c.guaranteedAutos?c.guaranteedAutos+' 張':'無'}</b></div><div class="spec-row"><span>機率資料</span><b>${oddRows().length} 個卡種</b></div>`;$('#packType').textContent=c.label}
function renderProgress(){const c=CONFIG[format],done=box.index,pct=done/c.packs*100;$('#packLabel').textContent=done<c.packs?`第 ${done+1} 包`:'已開完';$('#remaining').textContent=`剩餘卡包 ${c.packs-done}`;$('#progressBar').style.width=pct+'%'}
function renderSummary(){const h=box.hits;const rare=h.filter(x=>x.denom>=1000).length,autos=h.filter(x=>x.auto).length;$('#summary').innerHTML=`<div class="sum-cell"><b>${h.length}</b><small>特殊卡</small></div><div class="sum-cell"><b>${rare}</b><small>稀有+</small></div><div class="sum-cell"><b>${autos}</b><small>簽名</small></div>`;$('#hitCount').textContent=h.length}
function badges(c){return `${c.auto?'<em class="auto-badge">AUTO</em>':''}${c.rookie?'<em class="rc-badge">RC</em>':''}`}
function renderHistory(){if(!box.hits.length){$('#history').innerHTML='<div class="empty">尚未開出特殊卡</div>';return}$('#history').innerHTML=[...box.hits].sort((a,b)=>b.denom-a.denom).map(c=>`<div class="hit" style="--accent:${c.color}"><i class="hit-dot"></i><div><b>${escapeHtml(c.name)} ${badges(c)}</b><small>${escapeHtml(c.set)} · ${escapeHtml(c.team||'球隊未列')}</small></div><span class="hit-odds">1:${c.denom.toLocaleString()}</span></div>`).join('')}
function escapeHtml(s=''){return s.replace(/[&<>"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]))}
function cardHtml(c,i,total,boxMode=false){const offset=i-(total-1)/2;return `<article class="card ${c.denom?'special':''} ${c.auto?'autograph':''} ${boxMode?'box-card':''}" tabindex="0" data-card-index="${i}" aria-label="${escapeHtml(c.name)}，${escapeHtml(c.set)}${c.auto?'，簽名卡':''}" style="--i:${offset};--order:${i};--accent:${c.color};z-index:${i+1}"><div class="card-art"></div><div class="card-badges">${c.auto?'<span class="auto-card">AUTO</span>':''}${c.rookie?'<span class="rc-card">RC</span>':''}</div>${c.denom?`<span class="card-odds">1:${c.denom.toLocaleString()}</span>`:''}<div class="card-meta"><div class="card-name">${escapeHtml(c.name)}</div><div class="card-team">${escapeHtml(c.team||'球隊未列')}</div><div class="card-set">${escapeHtml(c.set)}</div></div></article>`}
function detailHtml(c){return `<div class="detail-accent" style="--accent:${c.color}"></div><div><b>${escapeHtml(c.name)} ${badges(c)}</b><span>${escapeHtml(c.team||'球隊未列')} · #${escapeHtml(c.code||'—')}</span></div><div class="detail-set"><b>${escapeHtml(c.set)}</b><span>${c.denom?`官方逐包機率 1:${c.denom.toLocaleString()}`:'基本卡'}${c.auto?' · AUTO 簽名卡':''}</span></div>`}
function bindCardDetails(cards){const detail=$('#cardDetail');document.querySelectorAll('.card').forEach(node=>{const show=()=>{const c=cards[Number(node.dataset.cardIndex)];detail.innerHTML=detailHtml(c);detail.hidden=false};node.addEventListener('mouseenter',show);node.addEventListener('focus',show)});if(cards.length){detail.innerHTML=detailHtml(cards[0]);detail.hidden=false}}
function renderCards(cards,boxMode=false){$('#packScene').classList.toggle('box-mode',boxMode);$('#cards').classList.toggle('box-results',boxMode);$('#cards').innerHTML=cards.map((c,i)=>cardHtml(c,i,cards.length,boxMode)).join('');bindCardDetails(cards)}

async function openPack(showDialog=true){
  if(busy||box.index>=CONFIG[format].packs)return;busy=true;
  const pack=box.packs[box.index];$('#cards').innerHTML='';$('#packButton').classList.add('opening');
  await new Promise(r=>setTimeout(r,430));
  $('#packButton').style.visibility='hidden';renderCards(pack);
  box.opened.push(pack);box.hits.push(...pack.filter(c=>c.denom));box.index++;
  renderProgress();renderSummary();renderHistory();
  $('#hint').textContent=pack.some(c=>c.denom)?`本包命中 ${pack.filter(c=>c.denom).length} 張特殊卡`:'本包為基本卡組合';
  await new Promise(r=>setTimeout(r,Math.min(1200,380+pack.length*90)));busy=false;
  if(box.index>=CONFIG[format].packs&&showDialog)finish();
}
async function openAll(){if(busy)return;while(box.index<CONFIG[format].packs){await openPack(false);await new Promise(r=>setTimeout(r,70))}const all=box.opened.flat().sort((a,b)=>(b.denom||0)-(a.denom||0));renderCards(all,true);$('#hint').textContent='整盒結果：依官方 1:X 由高到低排列（最稀有 → Base）';finish()}
function resetStage(){const b=$('#packButton');b.classList.remove('opening');b.style.visibility='visible';$('#packScene').classList.remove('box-mode');$('#cards').classList.remove('box-results');$('#cards').innerHTML='';$('#cardDetail').hidden=true;$('#hint').textContent='點擊卡包開始。卡片會逐張翻開。'}
function newBox(){format=format in CONFIG?format:'hobby';box=generateBox();renderFormats();renderSpec();renderProgress();renderSummary();renderHistory();resetStage()}
function finish(){const rare=box.hits.filter(c=>c.denom>=1000).length,autos=box.hits.filter(c=>c.auto).length;$('#finishStats').innerHTML=`共開出 <b>${box.hits.length}</b> 張特殊卡<br><b>${rare}</b> 張稀有以上 · <b>${autos}</b> 張簽名卡`;$('#finishDialog').showModal()}

$('#openPack').onclick=async()=>{if(box.index>0)resetStage();await openPack()};
$('#packButton').onclick=()=>$('#openPack').click();
$('#openAll').onclick=openAll;
$('#newBox').onclick=newBox;$('#newBoxTop').onclick=newBox;
$('#finishNew').onclick=()=>{$('#finishDialog').close();newBox()};
$('#finishClose').onclick=()=>$('#finishDialog').close();
document.title=`${SOURCE.config.productName} 拆盒模擬器`;
$('#brandName').textContent=SOURCE.config.productName.toUpperCase();
newBox();
