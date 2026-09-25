"""Build the Series 1 product from bundled PDFs and explicit reviewed mappings."""
import hashlib,json,subprocess,os,shutil
from pathlib import Path
from parse_series1 import parse_odds_pdf,parse_checklist,COLUMNS
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'products/2026-topps-series-1-baseball'

def audit(data):
 return {k:{'publishedRows':len(rows:=[r for r in data['odds'] if r['odds'].get(c['oddsColumn'])]),'expectedNonBasePerPack':sum(1/r['odds'][c['oddsColumn']] for r in rows),'expectedNonBasePerBox':c['packs']*sum(1/r['odds'][c['oddsColumn']] for r in rows),'naturalExpectedAutosPerBox':c['packs']*sum(1/r['odds'][c['oddsColumn']] for r in rows if r['auto']),'naturalExpectedRelicsPerBox':c['packs']*sum(1/r['odds'][c['oddsColumn']] for r in rows if r['relic'])} for k,c in data['config']['formats'].items()}

def build():
 pdftotext=os.environ.get('PDFTOTEXT') or shutil.which('pdftotext')
 if not pdftotext:raise SystemExit('Set PDFTOTEXT to the Poppler pdftotext executable.')
 for name,output in [('2026_Topps_Series_1_Baseball_Checklist_2-23.pdf','checklist.txt'),('2026_Topps_Baseball_Series_1_Odds.pdf','odds.txt')]:
  subprocess.run([pdftotext,'-layout',str(P/'source'/name),str(P/'source'/output)],check=True)
 rows,bad=parse_odds_pdf(P/'source/2026_Topps_Baseball_Series_1_Odds.pdf')
 sections,categories,subjects,skipped=parse_checklist((P/'source/checklist.txt').read_text())
 aliases=json.loads((P/'mapping.json').read_text())
 mapping={**{k:k for k in sections},**aliases}
 for r in rows:
  matches=[k for k in mapping if r['name']==k or r['name'].startswith(k+' ')]
  if not matches:raise ValueError('Unmapped odds: '+r['name'])
  r['section']=mapping[max(matches,key=len)]
  category=categories.get(r['section'])
  r['auto']=category in {'AUTOGRAPH','AUTOGRAPH RELIC'}
  r['relic']=category in {'RELIC','AUTOGRAPH RELIC'}
  assert not ('AUTOGRAPH' in r['name'] and not r['auto']),r
 config=json.loads((P/'config.json').read_text())
 data={'id':P.name,'config':config,'sections':sections,'odds':rows,'autographSections':[k for k in sections if categories.get(k) in {'AUTOGRAPH','AUTOGRAPH RELIC'}]}
 data['audit']=audit(data)
 report={'product':config['productName'],'oddsRows':len(rows),'oddsColumns':len(COLUMNS),'checklistSections':len(sections),'subjects':subjects,'cardEntries':sum(map(len,sections.values())),'baseCards':len(sections['BASE SET']),'unmappedOddsFamilies':[],'malformedOdds':[x for x in bad if x['token']],'blankOddsCells':[x for x in bad if not x['token']],'malformedChecklist':skipped,'formats':config['formats'],'probabilityAudit':data['audit'],'notes':config['notes']}
 assert len(sections['BASE SET'])==350
 assert not report['malformedOdds'] and not skipped
 (P/'product.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 (P/'extraction-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(config['productName'],report['oddsRows'],report['checklistSections'],report['subjects'])
if __name__=='__main__':build()
