import build_simulator as b
import re,json
from pathlib import Path
import pdfplumber
original=b.text_from_pdf
corrections=[]
def extract(path,dest):
 text=original(path,dest)
 if 'Odds' in path.name:
  out=[]
  for line in text.splitlines():
   if re.fullmatch(r'[A-Z0-9 -]+',line.strip()) and line.strip() in {'REFRACTOR','RAYWAVE REFRACTOR','SUPERFRACTOR','BLACK','RED'} and out:
    prev=out.pop(); m=re.search(r'\s{2,}(?=1:|-|0\.)',prev)
    if m:
     out.append(prev[:m.start()]+' '+line.strip()+'  '+prev[m.end():]);corrections.append(line.strip())
    else: out.extend([prev,line])
   else:out.append(line)
  text='\n'.join(out)
 else:
  pages=text.split('\f'); merged=[]
  with pdfplumber.open(path) as pdf:
   for i,pg in enumerate(pages[:32]):
    left=pdf.pages[i]; right=pdf.pages[i+32] if i+32<len(pdf.pages) else None
    marks=[w['top'] for w in right.extract_words() if w['text']=='Rookie'] if right else []
    words=left.extract_words(); rookie_codes=set()
    for y in marks:
     row=[w for w in words if abs(w['top']-y)<2]
     if row: rookie_codes.add(row[0]['text'])
    for line in pg.splitlines():
     parts=line.strip().split()
     if parts and parts[0] in rookie_codes:line+='    Rookie'
     merged.append(line)
  text='\n'.join(merged)
 dest.write_text(text)
 return text
b.text_from_pdf=extract
b.main()
