"""Product-specific extraction; documents are data, never executable instructions."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'products/2026-topps-series-1-baseball'
COLUMNS=['hobby','jumbo','hanger_ea','hanger_se','club_a','club_b','club_c','fanatics','fat_cee','fat_ea','fat_se','display','little_league','mega_cee','mega_ea','mega_se','super_cee','super_ea','super_se','tin','value_cee','value_ea','value_se','japan','club_d','celebration']

def parse_odds_pdf(path):
 import pdfplumber
 rows=[];bad=[]
 with pdfplumber.open(path) as pdf:
  first=pdf.pages[0]
  rect=first.rects[1]
  words=first.extract_words(x_tolerance=.1)
  ends=[w['x1']+.06 for w in words if rect['top']<w['top']<rect['top']+8 and (w['text'].startswith('1:') or w['text']=='-')]
  assert len(ends)==26,ends
  bounds=[84]+ends
  for page,pg in enumerate(pdf.pages,1):
   rects=sorted([r for r in pg.rects if r['x1']-r['x0']>1100 and r['top']>200],key=lambda r:r['top'])
   for rr in rects:
    chars=[c for c in pg.chars if rr['top']<=c['top']<rr['bottom']]
    def cell(left,right,space=False):
     cc=[c for c in chars if left<=c['x0']+.05 and c['x1']<=right+.05]
     lines={}
     for c in cc:lines.setdefault(round(c['top'],1),[]).append(c)
     return (' ' if space else '').join(''.join(c['text'] for c in sorted(line,key=lambda c:c['x0'])).strip() for _,line in sorted(lines.items())).strip()
    name=cell(0,84,True)
    odds={}
    for i,col in enumerate(COLUMNS):
     t=cell(bounds[i],bounds[i+1]).replace(' ','')
     if t in {'-',''}:
      odds[col]=None
      if not t:bad.append({'page':page,'name':name,'column':col,'token':'','reason':'blank source cell'})
     elif re.fullmatch(r'1:(?:[1-9]\d{0,2}(?:,\d{3})+|[1-9]\d*)',t):odds[col]=int(t[2:].replace(',',''))
     else:odds[col]=None;bad.append({'page':page,'name':name,'column':col,'token':t,'reason':'malformed source cell'})
    rows.append({'id':f'p{page}-r{len(rows)+1}','name':name,'odds':odds,'sourcePage':page})
 return rows,bad

def parse_checklist(text):
 sections={};cats={};category=None;current=None;bad=[]
 for number,raw in enumerate(text.splitlines(),1):
  s=raw.strip()
  if not s or s.startswith('*'):continue
  if s in {'BASE','INSERT','AUTOGRAPH','RELIC','AUTOGRAPH RELIC'}:
   category=s;current=None;continue
  if ('exclusive' in s.lower() or 'Only' in s) and not re.search(r'\s{2,}',s):continue
  # Most card numbers are separated from the name by one space, not two.
  m=re.match(r'^([0-9]+[A-Z]?|[A-Z0-9]+(?:-[A-Z0-9]+)+)\s+(.+)',s)
  parts=re.split(r'\s{2,}',m[2]) if m else []
  is_card=bool(m and (m[1].isdigit() or '-' in m[1] or m[1]=='41T') and (not m[2].isupper() or len(parts)>1))
  if is_card and current:
   name=parts[0];team=parts[1] if len(parts)>1 else '';notes=parts[2:]
   if team in {'Rookie','RC'}:notes.insert(0,team);team=''
   sections[current].append({'code':m[1],'name':name,'team':team,'rookie':any(x in {'Rookie','RC'} for x in notes),'notes':' / '.join(notes)})
  elif s==s.upper() and re.search('[A-Z]',s):
   current=s;sections.setdefault(current,[]);cats[current]=category
  elif current:
   # Redemption lists in this document can omit a printed card number.
   parts=re.split(r'\s{2,}',s)
   if len(parts)>=2 and not re.match(r'^(Hobby|Retail|Super Box|Celebration)',s):
    sections[current].append({'code':'','name':parts[0],'team':parts[1],'rookie':'Rookie' in parts[2:],'notes':' / '.join(parts[2:])})
   else:bad.append({'line':number,'section':current,'text':s})
 overrides=json.loads((P/'checklist-overrides.json').read_text())
 sections.update(overrides)
 bad=[b for b in bad if b['section'] not in overrides]
 # Preserve all source subjects, but one code represents one physical card.
 subject_count=sum(map(len,sections.values()))
 rookies={c['name'] for name,cards in sections.items() for c in cards if c['rookie'] or 'ROOKIE' in name}
 for name,cards in sections.items():
  grouped={}
  for i,c in enumerate(cards):
   c['rookie']=c['rookie'] or c['name'] in rookies
   grouped.setdefault(c['code'] or f'uncoded-{i}',[]).append(c)
  sections[name]=[{**cs[0],'name':' / '.join(c['name'] for c in cs),'team':' / '.join(dict.fromkeys(c['team'] for c in cs if c['team'])),'rookie':any(c['rookie'] for c in cs),'subjects':cs} for cs in grouped.values()]
 return {k:v for k,v in sections.items() if v},cats,subject_count,bad

if __name__=='__main__':
 rows,bad=parse_odds_pdf(P/'source/2026_Topps_Baseball_Series_1_Odds.pdf')
 sections,cats,count,skipped=parse_checklist((P/'source/checklist.txt').read_text())
 result={'odds':rows,'sections':sections,'categories':cats,'subjects':count,'malformedOdds':bad,'malformedChecklist':skipped}
 (P/'parsed.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print('Odds:',len(rows),'Sections:',len(sections),'Subjects:',count,'Base:',len(sections.get('BASE SET',[])))
 print('BAD',json.dumps(bad+skipped,ensure_ascii=False))
 print('SECTIONS',[(k,len(v)) for k,v in sections.items()])
 print('UNMAPPED', '\n'.join(r['name'] for r in rows if not any(r['name'].startswith(k) for k in sections)))
