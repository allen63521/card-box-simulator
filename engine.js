/* Pure product-aware simulation engine. No DOM, network or global product state. */
(function(root){
  'use strict';
  const matches=(card,type)=>type==='hit'?(card.auto||card.relic):Boolean(card[type]);
  function shuffle(items,rng){for(let i=items.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[items[i],items[j]]=[items[j],items[i]]}return items}
  function weighted(rows,column,rng){let x=rng()*rows.reduce((n,r)=>n+1/r.odds[column],0);for(const row of rows){x-=1/row.odds[column];if(x<=0)return row}return rows[rows.length-1]}
  function requirements(format){return (format.guarantees||[]).flatMap(g=>Array.from({length:g.count},()=>g.type))}
  function dampingGroups(format){
    const damping=format.overGuaranteeDamping;if(!damping)return [];
    const keepExtraRate=damping.keepExtraRate??1,rareBypassDenom=damping.rareBypassDenom??Infinity;
    return (damping.groups||format.guarantees||[]).filter(g=>g.count>0).map(g=>({
      type:g.type,count:g.count,keepExtraRate:g.keepExtraRate??keepExtraRate,rareBypassDenom:g.rareBypassDenom??rareBypassDenom
    }));
  }
  // Maximum bipartite matching prevents one AUTO RELIC card satisfying two promised cards.
  function missingGuarantees(cards,requirements){
    const owner=new Map();
    function assign(req,seen){for(let i=0;i<cards.length;i++){if(seen.has(i)||!matches(cards[i],requirements[req]))continue;seen.add(i);if(!owner.has(i)||assign(owner.get(i),seen)){owner.set(i,req);return true}}return false}
    const missing=[];for(let i=0;i<requirements.length;i++)if(!assign(i,new Set()))missing.push(requirements[i]);return missing;
  }
  function applyOverGuaranteeDamping(packs,format,rng,makeBase){
    for(const group of dampingGroups(format)){
      const candidates=[];
      packs.forEach((pack,pi)=>pack.forEach((card,ci)=>{if(card.denom&&matches(card,group.type))candidates.push({pi,ci,card})}));
      if(candidates.length<=group.count)continue;
      candidates.sort((a,b)=>b.card.denom-a.card.denom);
      const keep=new Set(candidates.slice(0,group.count).map(c=>c.pi+':'+c.ci));
      for(const hit of candidates.slice(group.count)){
        const key=hit.pi+':'+hit.ci;
        if(hit.card.denom>=group.rareBypassDenom||rng()<group.keepExtraRate)keep.add(key);
      }
      for(const hit of candidates){if(!keep.has(hit.pi+':'+hit.ci))packs[hit.pi][hit.ci]=makeBase()}
    }
  }
  function generateBox(product,formatKey,rng=Math.random){
    const cfg=product.config.formats[formatKey];if(!cfg)throw Error('Unknown format: '+formatKey);
    const column=cfg.oddsColumn,rows=product.odds.filter(r=>r.odds[column]),base=product.sections[product.config.baseSection],needs=requirements(cfg);
    if(!rows.length||!base?.length)throw Error('Product data is incomplete.');
    for(const type of needs)if(!rows.some(r=>matches(r,type)))throw Error('No eligible '+type+' odds for guaranteed hit.');
    const pick=arr=>arr[Math.floor(rng()*arr.length)];
    const makeHit=(row,forced=false)=>({...pick(product.sections[row.section]),productId:product.id,rowId:row.id,set:row.name,denom:row.odds[column],auto:Boolean(row.auto),relic:Boolean(row.relic),forced});
    const makeBase=()=>({...pick(base),productId:product.id,rowId:null,set:product.config.baseSection,denom:null,auto:false,relic:false,forced:false});
    for(let attempt=0;attempt<100;attempt++){
      const packs=[];let clipped=0;
      for(let p=0;p<cfg.packs;p++){
        const hits=rows.filter(r=>rng()<1/r.odds[column]).sort((a,b)=>b.odds[column]-a.odds[column]);
        clipped+=Math.max(0,hits.length-cfg.cards);
        const cards=hits.slice(0,cfg.cards).map(r=>makeHit(r));
        while(cards.length<cfg.cards)cards.push(makeBase());
        packs.push(shuffle(cards,rng));
      }
      applyOverGuaranteeDamping(packs,cfg,rng,makeBase);
      let flat=packs.flat(),missing=missingGuarantees(flat,needs);
      const available=packs.flatMap((pack,pi)=>pack.flatMap((c,ci)=>c.denom?[]:[{pi,ci}]));
      if(available.length<missing.length)continue;
      shuffle(available,rng);
      // Re-evaluate after every added card because an auto relic may fill either requirement.
      while(missing.length){
        const row=weighted(rows.filter(r=>matches(r,missing[0])),column,rng),slot=available.pop();
        packs[slot.pi][slot.ci]=makeHit(row,true);
        flat=packs.flat();missing=missingGuarantees(flat,needs);
      }
      return {productId:product.id,formatKey,packs,index:0,opened:[],hits:[],clipped};
    }
    throw Error('Unable to generate a box with enough base-card slots for guarantees.');
  }
  const api={generateBox,missingGuarantees,requirements,matches,dampingGroups,applyOverGuaranteeDamping};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.SimEngine=api;
})(typeof window!=='undefined'?window:globalThis);
