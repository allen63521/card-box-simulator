import json,re
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'app'
d=json.loads((p/'data.js').read_text()[16:-1]); secs=d['sections']
src=(p.parent/'source/checklist.txt').read_text()
raw=src.split('FANATICS AUTHENTICS REDEMPTION CARDS')[1].split('MINIONS MLB')[0]
secs['FANATICS AUTHENTICS REDEMPTION CARDS']=[{'code':'','name':a[0],'team':a[1],'rookie':False} for line in raw.splitlines() if len(a:=re.split(r'\s{2,}',line.strip()))==2]
aliases={'2025 MLB COMMISSIONER’S TROPHY':'2025 MLB COMMISSIONERS TROPHY','CHROME RADIATING ROOKIES':'TOPPS CHROME RADIATING ROOKIES','MVP BUYBACKS':'2025 CHROME MVP BUYBACKS','TOPPS CHROME CHAMPION GOLD':'TOPPS CHROME CHAMPION REFRACTORS','TOPPS CHROME ROOKIE AUTOGRAPHS':'ROOKIE AUTOGRAPHS','TOPPS CHROME RETAIL ROOKIE AUTOGRAPHS':'RETAIL ROOKIE AUTOGRAPHS','TOPPS CHROME LEGENDS AUTOGRAPHS':'CHROME LEGEND AUTOGRAPHS','TOPPS CHROME MVP BUYBACKS AUTOGRAPHS':'2025 CHROME MVP BUYBACKS AUTOGRAPHS','1991 TOPPS CHROME AUTOGRAPHS':'1991 TOPPS BASEBALL AUTOGRAPHS','2025 WORLD SERIES CHAMPIONS AUTOGRAPHS':'2025 WORLD CHAMPIONS AUTOGRAPH REFRACTOR','CLASS OF 2026 COOPERSTOWN CALLS AUTOGRAPH VARIATION':'COOPERSTOWN CALLS AUTOGRAPH VARIATION'}
mapping={**{k:k for k in secs},**aliases};unmapped=[]
for r in d['odds']:
 matches=[k for k in mapping if r['name'].startswith(k)]
 r['section']=mapping[max(matches,key=len)] if matches else d['config']['baseSection']
 if not matches:unmapped.append(r['name'])
 r['auto']=r['section'] in d['autographSections'] or 'AUTOGRAPH' in r['name']
 if r['name']=='2025 WORLD SERIES CHAMPIONS AUTOGRAPHS GOLD REFRACTOR': r['odds']['hobby']=None
# Preserve multiple subjects sharing one card code as a single multi-subject card.
subject_count=sum(map(len,secs.values()))
for name,entries in secs.items():
 if 'DUAL' not in name:continue
 grouped={}
 for e in entries: grouped.setdefault(e['code'],[]).append(e)
 secs[name]=[{'code':k,'name':' / '.join(e['name'] for e in es),'team':' / '.join(dict.fromkeys(e['team'] for e in es if e['team'])),'rookie':any(e['rookie'] for e in es)} for k,es in grouped.items()]
report=json.loads((p/'extraction-report.json').read_text())
report.update(checklistSections=len(secs),subjects=subject_count,cardEntries=sum(map(len,secs.values())),unmappedOddsFamilies=unmapped,baseCards=len(secs['BASE CARDS']),baseRookies=sum(e['rookie'] for e in secs['BASE CARDS']))
report['sourceNotes']=['PDF 第 6 頁 2025 WORLD SERIES CHAMPIONS AUTOGRAPHS GOLD REFRACTOR：Hobby 原文 1:1,2175 的千分位格式異常、Delight 原文 0.39374999999999999 非 1:X；兩格排除，其餘有效欄位保留。','跨行卡種名稱已合併；第 33–63 頁 Rookie 欄依垂直座標接回第 1–31 頁。','Fanatics odds 保留於資料，因尚未核實專屬盒型規格而未開放。','同一卡號多球員合併顯示；不同卡號的重複球員仍保留。']
report['malformedOdds'][0]['reason']='Source PDF contains invalid decimal odds (Delight) and malformed thousands separator (Hobby); both cells excluded.'
for key,c in d['config']['formats'].items():
 rows=[r for r in d['odds'] if r['odds'][key]]
 report['probabilityAudit'][key].update(publishedRows=len(rows),expectedNonBasePerPack=sum(1/r['odds'][key] for r in rows),expectedNonBasePerBox=c['packs']*sum(1/r['odds'][key] for r in rows),naturalExpectedAutosPerBox=c['packs']*sum(1/r['odds'][key] for r in rows if r['auto']))
d['audit']=report['probabilityAudit']
(p/'data.js').write_text('window.SIM_DATA='+json.dumps(d,ensure_ascii=False,separators=(',',':'))+';')
(p/'extraction-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
assert not unmapped,unmapped
print(json.dumps({k:report[k] for k in ['oddsRows','checklistSections','subjects','cardEntries','baseRookies','unmappedOddsFamilies']},ensure_ascii=False))
