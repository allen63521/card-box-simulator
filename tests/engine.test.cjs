const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const E=require('../engine.js');
const root=path.join(__dirname,'..');
function rng(seed){return ()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296}}
const manifest=JSON.parse(fs.readFileSync(path.join(root,'catalog.json'),'utf8'));
const products=manifest.products.map(p=>JSON.parse(fs.readFileSync(path.join(root,p.path),'utf8')));
for(const p of products){
 const rows=new Map(p.odds.map(r=>[r.id,r]));
 for(const [key,cfg] of Object.entries(p.config.formats)){
  const random=rng(481+cfg.cards);let autos=0,relics=0;
  for(let i=0;i<1000;i++){
   const box=E.generateBox(p,key,random);assert.equal(box.packs.length,cfg.packs);
   for(const pack of box.packs){assert.equal(pack.length,cfg.cards);for(const card of pack){
    assert.equal(card.productId,p.id);
    if(card.rowId){const row=rows.get(card.rowId);assert.ok(row);assert.equal(card.denom,row.odds[cfg.oddsColumn]);assert.ok(p.sections[row.section].some(s=>s.code===card.code&&s.name===card.name));assert.equal(card.auto,row.auto);assert.equal(card.relic,row.relic)}
    else assert.ok(p.sections[p.config.baseSection].some(s=>s.code===card.code&&s.name===card.name));
   }}
   const flat=box.packs.flat();assert.deepEqual(E.missingGuarantees(flat,E.requirements(cfg)),[]);autos+=flat.filter(c=>c.auto).length;relics+=flat.filter(c=>c.relic).length;
  }
  console.log(`${p.id}/${key}: 1000 boxes PASS; mean AUTO ${(autos/1000).toFixed(3)}, RELIC ${(relics/1000).toFixed(3)}`);
 }
}
assert.equal(E.missingGuarantees([{auto:true,relic:true}],['auto','relic']).length,1);
assert.deepEqual(E.missingGuarantees([{auto:true,relic:true},{auto:true,relic:false}],['auto','relic']),[]);
const toy={id:'test',config:{baseSection:'BASE',formats:{box:{packs:1,cards:3,oddsColumn:'a',guarantees:[]}}},sections:{BASE:[{code:'1',name:'Base'}],AUTO:[{code:'A',name:'Auto'}]},odds:[{id:'hit',name:'AUTO',section:'AUTO',odds:{a:4},auto:true,relic:false}]};
const random=rng(9182);let hits=0;
for(let i=0;i<10000;i++)hits+=E.generateBox(toy,'box',random).packs.flat().filter(c=>c.auto).length;
assert.ok(Math.abs(hits/10000-.25)<.02,`1:4 empirical rate ${hits/10000}`);
toy.config.formats.box.guarantees=[{type:'auto',count:1}];
const natural=E.generateBox(toy,'box',()=>0);assert.equal(natural.packs.flat().filter(c=>c.auto).length,1);assert.equal(natural.packs.flat().filter(c=>c.forced).length,0);
const supplemented=E.generateBox(toy,'box',()=>.99);assert.equal(supplemented.packs.flat().filter(c=>c.forced).length,1);assert.equal(supplemented.packs[0].length,3);
const dampedToy={
 id:'damped',
 config:{baseSection:'BASE',formats:{box:{packs:1,cards:4,oddsColumn:'a',guarantees:[{type:'auto',count:1}],overGuaranteeDamping:{keepExtraRate:0}}}},
 sections:{BASE:[{code:'1',name:'Base'}],AUTO:[{code:'A',name:'Auto A'},{code:'B',name:'Auto B'}]},
 odds:[
  {id:'rare',name:'RARE AUTO',section:'AUTO',odds:{a:10},auto:true,relic:false},
  {id:'common',name:'COMMON AUTO',section:'AUTO',odds:{a:2},auto:true,relic:false}
 ]
};
const damped=E.generateBox(dampedToy,'box',()=>0).packs.flat();
assert.equal(damped.filter(c=>c.auto).length,1);
assert.equal(damped.find(c=>c.auto).rowId,'rare');
const series=products.find(p=>p.id.includes('series-1'));
assert.equal(series.sections['BASE SET'].length,350);
assert.ok(series.sections['BASE SET'].find(c=>c.code==='11').name.includes(' / '));
assert.equal(series.odds.find(r=>r.name==='MASCOTS').odds.celebration,2);
assert.equal(series.odds.find(r=>r.name==='BASE CARDS GOLD').odds.hobby,49);
assert.ok(series.odds.filter(r=>r.name.includes('AUTOGRAPH')).every(r=>r.auto));
assert.ok(series.odds.find(r=>r.name==='MAJOR LEAGUE MATERIAL CARDS').relic);
console.log('PASS: source mappings, distinct guarantees, per-pack frequency, no unconditional extra hits.');
