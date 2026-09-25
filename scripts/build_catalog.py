"""Bundle catalog JSON for file:// use and fingerprint original source PDFs."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build():
 manifest=json.loads((ROOT/'catalog.json').read_text());products=[];ids=set();sources=[]
 for entry in manifest['products']:
  product=json.loads((ROOT/entry['path']).read_text())
  assert entry['id']==product['id'] and product['id'] not in ids
  ids.add(product['id']);cfg=product['config']
  assert product['sections'][cfg['baseSection']]
  assert len({r['id'] for r in product['odds']})==len(product['odds'])
  for row in product['odds']:
   assert row['section'] in product['sections'],row
   assert all(x is None or isinstance(x,int) and x>0 for x in row['odds'].values()),row
  for f in cfg['formats'].values():
   assert f['packs']>0 and f['cards']>0
   assert any(r['odds'].get(f['oddsColumn']) for r in product['odds'])
  for source in cfg['sources']:
   path=ROOT/source['path'];assert path.is_file() and path.suffix=='.pdf'
   sources.append({'product':product['id'],'path':source['path'],'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
  products.append(product)
 assert manifest['defaultProduct'] in ids
 payload={'schemaVersion':1,'defaultProduct':manifest['defaultProduct'],'products':products}
 (ROOT/'data.js').write_text('window.SIM_CATALOG='+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+';\n')
 (ROOT/'sources-manifest.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2))
 print(f'Bundled {len(products)} products, {len(sources)} original PDFs.')
if __name__=='__main__':build()
