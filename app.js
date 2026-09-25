'use strict';
const $=s=>document.querySelector(s);
const catalog=window.SIM_CATALOG;
if(!catalog?.products?.length){document.body.innerHTML='<main>卡包資料未載入，請確認 data.js 與 index.html 位於同一資料夾。</main>';throw Error('Missing catalog')}
const products=new Map(catalog.products.map(p=>[p.id,p]));
const sessions=new Map(),lastFormats=new Map();
let product=products.get(catalog.defaultProduct)||catalog.products[0],format=Object.keys(product.config.formats)[0],box,busy=false;
const escapeHtml=(s='')=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const sessionKey=()=>product.id+':'+format;
const cfg=()=>product.config.formats[format];
const oddRows=()=>product.odds.filter(r=>r.odds[cfg().oddsColumn]);
const sorted=cards=>[...cards].sort((a,b)=>(b.denom||0)-(a.denom||0));
const color=c=>!c.denom?'#8b99a8':c.denom>=100000?'#ff657a':c.denom>=10000?'#ffad60':c.denom>=1000?'#d9b6ff':c.denom>=100?'#61dded':'#67e1a3';
function badges(c){return `${c.auto?'<em class="auto-badge">AUTO</em>':''}${c.relic?'<em class="relic-badge">RELIC</em>':''}${c.rookie?'<em class="rc-badge">RC</em>':''}`}
function updateControls(){const done=box.index>=cfg().packs;$('#productSelect').disabled=busy;document.querySelectorAll('#formats button,#newBox,#newBoxTop').forEach(b=>b.disabled=busy);for(const id of ['#openPack','#openAll','#packButton'])$(id).disabled=busy||done}
function renderProduct(){
 $('#brandName').textContent=product.config.productName;
 document.title=product.config.productName+' · 拆盒模擬器';
 $('#productSelect').value=product.id;
 $('#productMeta').textContent=`${product.sections[product.config.baseSection].length} 張 Base · ${Object.keys(product.sections).length} 個系列`;
 $('#sourceLinks').innerHTML=product.config.sources.map(s=>`<a href="${escapeHtml(s.path)}" target="_blank" rel="noopener">↗ ${escapeHtml(s.label)}</a>`).join('')+`<a href="products/${escapeHtml(product.id)}/extraction-report.json" target="_blank" rel="noopener">↗ 資料稽核報告</a>`;
 $('#productNotes').innerHTML=product.config.notes.map(n=>`<li>${escapeHtml(n)}</li>`).join('');
 $('#packSeries').textContent=product.id.includes('chrome')?'CHROME':'SERIES 1';
 document.body.dataset.product=product.id;
}
function renderFormats(){
 $('#formats').innerHTML=Object.entries(product.config.formats).map(([key,c])=>`<button class="format ${key===format?'active':''}" aria-pressed="${key===format}" data-format="${key}"><span>${escapeHtml(c.label)}</span><small>${c.packs} 包 × ${c.cards} 張</small></button>`).join('');
 document.querySelectorAll('[data-format]').forEach(b=>b.onclick=()=>{if(!busy){format=b.dataset.format;activate()}});
}
function renderSpec(){
 const c=cfg(),a=product.audit[format];
 $('#boxSpec').innerHTML=`<div class="spec-row"><span>每盒主卡包</span><b>${c.packs} 包</b></div><div class="spec-row"><span>每包</span><b>${c.cards} 張</b></div><div class="spec-row"><span>最低保證</span><b>${escapeHtml(c.guaranteeLabel)}</b></div><div class="spec-row"><span>機率資料</span><b>${oddRows().length} 個卡種</b></div><div class="audit-note">自然期望／盒（截斷與補保證前）<br>特殊卡 ${a.expectedNonBasePerBox.toFixed(2)} 張 · AUTO ${a.naturalExpectedAutosPerBox.toFixed(2)} 張${a.naturalExpectedRelicsPerBox!=null?` · RELIC ${a.naturalExpectedRelicsPerBox.toFixed(2)} 張`:''}</div>`;
 $('#packType').textContent=c.label;$('#formatNotice').textContent=c.note||'依官方逐包機率，探索本盒的平行卡、特卡與簽名。';
}
function renderProgress(){const done=box.index;$('#packLabel').textContent=done<cfg().packs?`第 ${done+1} 包`:'已開完';$('#remaining').textContent=`剩餘卡包 ${cfg().packs-done}`;$('#progressBar').style.width=(done/cfg().packs*100)+'%'}
function renderSummary(){const h=box.hits;$('#summary').innerHTML=[['特殊卡',h.length],['AUTO',h.filter(c=>c.auto).length],['RELIC',h.filter(c=>c.relic).length]].map(([label,count])=>`<div class="sum-cell"><b>${count}</b><small>${label}</small></div>`).join('');$('#hitCount').textContent=h.length}
function renderHistory(){
 $('#history').innerHTML=box.hits.length?sorted(box.hits).map(c=>`<div class="hit" style="--accent:${color(c)}"><i class="hit-dot"></i><div><b>${escapeHtml(c.name)} ${badges(c)}</b><small>${escapeHtml(c.set)} · ${escapeHtml(c.team||'未列球隊')}</small></div><span class="hit-odds">1:${c.denom.toLocaleString()}</span></div>`).join(''):'<div class="empty">尚未開出特殊卡</div>';
}
function cardHtml(c,i,total,grid){return `<article class="card ${c.denom?'special':''} ${c.auto?'autograph':''} ${grid?'box-card':''}" tabindex="0" data-card-index="${i}" aria-label="${escapeHtml(c.name)}，${escapeHtml(c.set)}${c.auto?'，AUTO':''}${c.relic?'，RELIC':''}" style="--i:${i-(total-1)/2};--order:${i};--accent:${color(c)};z-index:${i+1}"><div class="card-art"></div><div class="card-badges">${c.auto?'<span class="auto-card">AUTO</span>':''}${c.relic?'<span class="relic-card">RELIC</span>':''}${c.rookie?'<span class="rc-card">RC</span>':''}</div>${c.denom?`<span class="card-odds">1:${c.denom.toLocaleString()}</span>`:''}<div class="card-meta"><div class="card-name">${escapeHtml(c.name)}</div><div class="card-team">${escapeHtml(c.team||'未列球隊')}</div><div class="card-set">${escapeHtml(c.set)}</div></div></article>`}
function detailHtml(c){return `<div class="detail-accent" style="--accent:${color(c)}"></div><div><b>${escapeHtml(c.name)} ${badges(c)}</b><span>${escapeHtml(c.team||'未列球隊')} · #${escapeHtml(c.code||'未列卡號')}</span>${c.notes?`<span>${escapeHtml(c.notes)}</span>`:''}</div><div class="detail-set"><b>${escapeHtml(c.set)}</b><span>${c.denom?`官方每包 1:${c.denom.toLocaleString()}`:'基本卡'}${c.auto?' · AUTO 簽名卡':''}${c.relic?' · RELIC 實物卡':''}${c.forced?' · 整盒保證補足':''}</span></div>`}
function renderCards(cards,boxMode=false){
 const grid=boxMode||cards.length>12;
 $('#packScene').classList.toggle('box-mode',grid);$('#cards').classList.toggle('box-results',grid);
 $('#cards').innerHTML=cards.map((c,i)=>cardHtml(c,i,cards.length,grid)).join('');
 const detail=$('#cardDetail');
 document.querySelectorAll('.card').forEach(n=>{const show=()=>{detail.innerHTML=detailHtml(cards[Number(n.dataset.cardIndex)]);detail.hidden=false};n.addEventListener('mouseenter',show);n.addEventListener('focus',show);n.addEventListener('click',show)});
 detail.hidden=!cards.length;if(cards.length)detail.innerHTML=detailHtml(cards[0]);
}
function resetStage(){const b=$('#packButton');b.classList.remove('opening');b.style.visibility='visible';$('#packScene').classList.remove('box-mode');$('#cards').classList.remove('box-results');$('#cards').innerHTML='';$('#cardDetail').hidden=true;$('#hint').textContent='點擊卡包開始。滑鼠移入、點擊或 Tab 聚焦可看完整卡片。'}
function renderBox(){renderProduct();renderFormats();renderSpec();renderProgress();renderSummary();renderHistory();resetStage();if(box.index){$('#packButton').style.visibility='hidden';const complete=box.index===cfg().packs;renderCards(complete?sorted(box.opened.flat()):box.opened.at(-1),complete);$('#hint').textContent=complete?'整盒結果：依 1:X 分母由高到低排列，最稀有 → Base。':`已恢復本盒進度：${box.index} / ${cfg().packs} 包`;}updateControls()}
function activate(){lastFormats.set(product.id,format);box=sessions.get(sessionKey());if(!box){box=SimEngine.generateBox(product,format);sessions.set(sessionKey(),box)}if($('#finishDialog').open)$('#finishDialog').close();renderBox()}
function newBox(){if(busy)return;try{box=SimEngine.generateBox(product,format);sessions.set(sessionKey(),box);$('#errorMessage').hidden=true;renderBox()}catch(e){$('#errorMessage').textContent='無法建立卡盒：'+e.message;$('#errorMessage').hidden=false}}
function finish(){renderCards(sorted(box.opened.flat()),true);$('#hint').textContent=`整盒 ${box.opened.flat().length} 張：依 1:X 分母由高到低排列，最稀有 → Base。`;$('#finishStats').innerHTML=`${escapeHtml(product.config.productName)}<br>${escapeHtml(cfg().label)} · <b>${box.opened.flat().length}</b> 張卡<br><b>${box.hits.filter(c=>c.auto).length}</b> AUTO · <b>${box.hits.filter(c=>c.relic).length}</b> RELIC<br>特殊卡共 <b>${box.hits.length}</b> 張`;$('#finishDialog').showModal();updateControls()}
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function revealNextPack({finishOnComplete=true}={}){
 resetStage();$('#packButton').classList.add('opening');
 await wait(430);
 const pack=box.packs[box.index++];box.opened.push(pack);box.hits.push(...pack.filter(c=>c.denom));$('#packButton').style.visibility='hidden';renderCards(pack);renderProgress();renderSummary();renderHistory();$('#hint').textContent=`本包 ${pack.length} 張 · ${pack.filter(c=>c.denom).length} 張特殊卡`;
 await wait(450);
 if(finishOnComplete&&box.index===cfg().packs)finish();
}
async function openPack(){
 if(busy||box.index>=cfg().packs)return;busy=true;updateControls();
 try{await revealNextPack()}finally{busy=false;updateControls()}
}
async function openAll(){
 if(busy||box.index>=cfg().packs)return;busy=true;$('#openAll').textContent='逐包開盒中...';updateControls();
 try{
  while(box.index<cfg().packs){
   await revealNextPack({finishOnComplete:false});
   if(box.index<cfg().packs)await wait(260);
  }
  finish();
 }finally{$('#openAll').textContent='逐包開完';busy=false;updateControls()}
}
$('#productCount').textContent=`${products.size} 系列`;
$('#productSelect').innerHTML=catalog.products.map(p=>`<option value="${escapeHtml(p.id)}">${escapeHtml(p.config.productName)}</option>`).join('');
$('#productSelect').onchange=()=>{if(busy)return;product=products.get($('#productSelect').value);format=lastFormats.get(product.id)||Object.keys(product.config.formats)[0];activate()};
$('#openPack').onclick=openPack;$('#packButton').onclick=openPack;$('#openAll').onclick=openAll;
$('#newBox').onclick=newBox;$('#newBoxTop').onclick=newBox;
$('#finishNew').onclick=()=>{$('#finishDialog').close();newBox()};$('#finishClose').onclick=()=>$('#finishDialog').close();
activate();
