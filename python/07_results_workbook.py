"""07 - Results workbook, part 1: Data, Summary (live Excel formulas), Regression.

Builds results/Vegetation_loss_results.xlsx from the Earth Engine panel table. The Summary sheet
recomputes the % of DS2020 vegetation lost with SUMIFS formulas, so the numbers can be checked
and the 1 ha threshold (cell Summary!D3) changed inside Excel.
Run 08 afterwards to add the accuracy, matching, DiD, event-study, fragmentation and hotspot sheets.
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from paths import TAB, RES
import pandas as pd, numpy as np, statsmodels.formula.api as smf
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import LineChart, Reference
from openpyxl.comments import Comment
SRC=TAB/'segment_zone_panel_DS2020_2026.csv'
d=pd.read_csv(SRC).sort_values(['treated','side','unit_id','year'],ascending=[False,True,True,True])
F='Arial'
def f(**k): return Font(name=F,**k)
BLUE=f(color='0000FF'); BOLD=f(bold=True); HDR=f(bold=True,color='FFFFFF')
HFILL=PatternFill('solid',fgColor='1F4E79'); YEL=PatternFill('solid',fgColor='FFFF00'); GREY=PatternFill('solid',fgColor='F2F2F2')
thin=Side(style='thin',color='BFBFBF')
wb=Workbook()
# ---------------- How it works
h=wb.active; h.title='How it works'
lines=[
('How the vegetation-loss results are calculated',BOLD),
('',None),
('1. Earth Engine produced one land-cover map per dry season (DS2020 … DS2026) and measured, for every unit (segment × zone) and year, the area of each class in m². These are the raw columns in the Data sheet (blue text).',None),
('2. a_veg2020 = area that was vegetation in DS2020.  a_veglost = area that was vegetation in DS2020 but is NOT vegetation in that year.',None),
('3. Percentage of 2020 vegetation lost (Data column V):   % lost = a_veglost ÷ a_veg2020.   It is 0 in 2020 by definition.',None),
('4. Units with less than 1 ha of vegetation in 2020 are left out (Summary!D3), because a tiny denominator gives unstable percentages. Data column U flags which units are included.',None),
('5. Summary sheet, group results: all included units in a group are pooled, i.e. total ha lost ÷ total 2020 vegetation ha (SUMIFS). This weights big units more than small ones.',None),
('6. Simple difference-in-differences (Summary sheet): change in % lost from DS2024 (last year before construction) to the average of DS2025–DS2026, for Section 1 minus the same change for the controls.',None),
('7. Regression sheet: the formal event-study and pooled difference-in-differences with unit and year fixed effects and standard errors clustered by 1 km segment. These were run in Python (statsmodels) on the same data; they are values, not live formulas.',None),
('',None),
('Zones: F = construction footprint · B1 = 0–500 m · B2 = 500 m–1 km · B3 = 1–5 km from the footprint edge.',None),
('Groups: Section 1 = treated segments T01–T47 · Control = west (CW) and east (CE) control segments.',None),
('Colour code: blue text = raw data from Earth Engine · black = formulas · yellow cell = setting you can change.',None),
('Source data: segment_zone_panel_DS2020_2026.csv exported from Earth Engine (panel_table asset), 628 units × 7 years = 4,396 rows.',None),
]
for i,(t,st) in enumerate(lines,1):
    c=h.cell(i,1,t); c.font=st or f(); c.alignment=Alignment(wrap_text=True,vertical='top')
h.column_dimensions['A'].width=130
h['A1'].font=f(bold=True,size=14)
# ---------------- Data
ds=wb.create_sheet('Data')
cols=list(d.columns)
extra=['group','veg2020_ha','veglost_ha','include','pct_veg_lost','veg_share_of_land']
ds.append(cols+extra)
for r in d.itertuples(index=False):
    ds.append(list(r))
n=len(d)+1
for i in range(2,n+1):
    ds[f'R{i}']=f'=IF(D{i}=1,"Section 1","Control")'
    ds[f'S{i}']=f'=N{i}/10000'
    ds[f'T{i}']=f'=P{i}/10000'
    ds[f'U{i}']=f"=IF(N{i}>=Summary!$D$3,1,0)"
    ds[f'V{i}']=f'=IF(N{i}>0,P{i}/N{i},"")'
    ds[f'W{i}']=f'=IF(O{i}>0,H{i}/O{i},"")'
    for c in 'ABCDEFGHIJKLMNOPQ': ds[f'{c}{i}'].font=BLUE
    for c in 'RSTUVW': ds[f'{c}{i}'].font=f()
    for c in 'GHIJKLMNOPQ': ds[f'{c}{i}'].number_format='#,##0'
    ds[f'S{i}'].number_format=ds[f'T{i}'].number_format='#,##0.00'
    ds[f'V{i}'].number_format=ds[f'W{i}'].number_format='0.0%'
for c in ds[1]: c.font=HDR; c.fill=HFILL; c.alignment=Alignment(wrap_text=True,horizontal='center')
for col,w in zip('ABCDEFGHIJKLMNOPQRSTUVW',[10,7,6,8,6,6]+[12]*11+[10,11,11,8,11,11]): ds.column_dimensions[col].width=w
ds.freeze_panes='A2'
ds['G1'].comment=Comment('All a_ columns are areas in m² measured in Earth Engine at 10 m resolution.','Claude')
ds['V1'].comment=Comment('= a_veglost ÷ a_veg2020','Claude')
# ---------------- Summary
s=wb.create_sheet('Summary')
s['A1']='Vegetation loss since DS2020 — Section 1 vs controls'; s['A1'].font=f(bold=True,size=14)
s['A3']='Minimum 2020 vegetation per unit (m²)'; s['D3']=10000; s['D3'].fill=YEL; s['D3'].font=BLUE; s['D3'].number_format='#,##0'
s['E3']='← units below this are excluded (1 ha = 10,000 m²)'
years=list(range(2020,2027))
s['A5']='% of 2020 vegetation lost'; s['A5'].font=BOLD
s.append([]) 
hdr=['Zone','Group']+[str(y) for y in years]
for j,v in enumerate(hdr,1):
    c=s.cell(6,j,v); c.font=HDR; c.fill=HFILL; c.alignment=Alignment(horizontal='center')
zones=[('F','Footprint'),('B1','0–500 m'),('B2','500 m–1 km'),('B3','1–5 km')]
r=7; rows={}
for z,zl in zones:
    for g in ['Section 1','Control']:
        s.cell(r,1,z); s.cell(r,2,g)
        for j,y in enumerate(years):
            col=3+j; L=s.cell(6,col).column_letter
            crit=f'Data!$C:$C,$A{r},Data!$R:$R,$B{r},Data!$F:$F,{y},Data!$U:$U,1'
            s.cell(r,col,f'=IFERROR(SUMIFS(Data!$P:$P,{crit})/SUMIFS(Data!$N:$N,{crit}),"")').number_format='0.0%'
        rows[(z,g)]=r; r+=1
lastpct=r-1
# DiD table
r+=1; s.cell(r,1,'Simple difference-in-differences (percentage points)').font=BOLD; r+=1
h2=['Zone','Distance','S1: 2024','S1: avg 2025–26','S1 change','Ctrl: 2024','Ctrl: avg 2025–26','Ctrl change','DiD (S1 − Ctrl)']
for j,v in enumerate(h2,1):
    c=s.cell(r,j,v); c.font=HDR; c.fill=HFILL; c.alignment=Alignment(horizontal='center',wrap_text=True)
r+=1; did_start=r
for z,zl in zones:
    a=rows[(z,'Section 1')]; b=rows[(z,'Control')]
    s.cell(r,1,z); s.cell(r,2,zl)
    s.cell(r,3,f'=G{a}'); s.cell(r,4,f'=AVERAGE(H{a}:I{a})'); s.cell(r,5,f'=D{r}-C{r}')
    s.cell(r,6,f'=G{b}'); s.cell(r,7,f'=AVERAGE(H{b}:I{b})'); s.cell(r,8,f'=G{r}-F{r}')
    s.cell(r,9,f'=(E{r}-H{r})*100')
    for c in range(3,9): s.cell(r,c).number_format='0.0%'
    s.cell(r,9).number_format='0.0;-0.0'; s.cell(r,9).font=BOLD
    r+=1
s.cell(r,1,'DiD in percentage points: e.g. 10.0 means Section 1 lost 10 percentage points more of its 2020 vegetation than the controls after construction began, relative to 2024.').font=f(italic=True)
r+=2
# hectares
s.cell(r,1,'Hectares of 2020 vegetation lost by DS2026 (included units)').font=BOLD; r+=1
for j,v in enumerate(['Zone','Distance','Section 1 (ha)','Control (ha)','S1 2020 vegetation (ha)','Control 2020 vegetation (ha)'],1):
    c=s.cell(r,j,v); c.font=HDR; c.fill=HFILL; c.alignment=Alignment(horizontal='center',wrap_text=True)
r+=1; ha0=r
for z,zl in zones:
    s.cell(r,1,z); s.cell(r,2,zl)
    for j,(g,colsrc) in enumerate([('Section 1','$T:$T'),('Control','$T:$T'),('Section 1','$S:$S'),('Control','$S:$S')]):
        s.cell(r,3+j,f'=SUMIFS(Data!{colsrc},Data!$C:$C,$A{r},Data!$R:$R,"{g}",Data!$F:$F,2026,Data!$U:$U,1)').number_format='#,##0'
    r+=1
s.cell(r,2,'Total').font=BOLD
for c in 'CDEF':
    s[f'{c}{r}']=f'=SUM({c}{ha0}:{c}{r-1})'; s[f'{c}{r}'].number_format='#,##0'; s[f'{c}{r}'].font=BOLD
s.column_dimensions['A'].width=10; s.column_dimensions['B'].width=14
for c in 'CDEFGHI': s.column_dimensions[c].width=14
s.freeze_panes='C7'
# charts
anchor_rows=[3,20,37,54]
for k,(z,zl) in enumerate(zones):
    ch=LineChart(); ch.title=f'{z} ({zl}): % of 2020 vegetation lost'; ch.height=7.5; ch.width=14
    ch.y_axis.title='% lost'; ch.y_axis.number_format='0%'; ch.x_axis.title='Dry season'
    for g in ['Section 1','Control']:
        rr=rows[(z,g)]
        ref=Reference(s,min_col=3,max_col=9,min_row=rr); ch.add_data(ref,from_rows=True,titles_from_data=False)
    ch.series[0].tx=None
    from openpyxl.chart.series import SeriesLabel
    ch.series[0].title=SeriesLabel(v='Section 1'); ch.series[1].title=SeriesLabel(v='Control')
    ch.series[0].graphicalProperties.line.solidFill='C00000'; ch.series[1].graphicalProperties.line.solidFill='2F5597'
    ch.series[1].graphicalProperties.line.dashStyle='dash'
    ch.set_categories(Reference(s,min_col=3,max_col=9,min_row=6))
    s.add_chart(ch,f'K{anchor_rows[k]}')
# ---------------- Regression (Python results)
dd=d[d.a_veg2020>=1e4].copy(); dd['y']=100*dd.a_veglost/dd.a_veg2020
rg=wb.create_sheet('Regression')
rg['A1']='Difference-in-differences with unit and year fixed effects (values computed in Python/statsmodels)'; rg['A1'].font=f(bold=True,size=13)
rg['A2']='Outcome: % of 2020 vegetation lost. Units with <1 ha 2020 vegetation excluded. Standard errors clustered by 1 km segment. Reference year for event study: DS2024.'
rg['A2'].font=f(italic=True)
row=4
for j,v in enumerate(['Zone','Term','Estimate (pp)','95% CI low','95% CI high','p-value','Units','Treated units'],1):
    c=rg.cell(row,j,v); c.font=HDR; c.fill=HFILL
row+=1
for z,zl in zones:
    sub=dd[dd.zone==z].copy()
    for k in [2021,2022,2023,2025,2026]: sub[f'e{k}']=((sub.year==k)&(sub.treated==1)).astype(int)
    m=smf.ols('y ~ e2021+e2022+e2023+e2025+e2026 + C(unit_id)+C(year)',sub).fit(cov_type='cluster',cov_kwds={'groups':sub.seg_id})
    s2=sub[sub.year>=2021].copy(); s2['post']=((s2.year>=2025)&(s2.treated==1)).astype(int)
    p=smf.ols('y ~ post + C(unit_id)+C(year)',s2).fit(cov_type='cluster',cov_kwds={'groups':s2.seg_id})
    nu=sub.unit_id.nunique(); nt=sub[sub.treated==1].unit_id.nunique()
    items=[(f'Event study DS{k}',m,f'e{k}') for k in [2021,2022,2023]]+[('DS2024 (reference)',None,None)]+[(f'Event study DS{k}',m,f'e{k}') for k in [2025,2026]]+[('Pooled DiD (post = DS2025–26)',p,'post')]
    for lab,mod,t in items:
        vals=[f'{z} ({zl})',lab]
        if mod is None: vals+=[0,None,None,None,nu,nt]
        else:
            ci=mod.conf_int().loc[t]; vals+=[round(mod.params[t],2),round(ci[0],2),round(ci[1],2),round(mod.pvalues[t],4),nu,nt]
        for j,v in enumerate(vals,1):
            c=rg.cell(row,j,v); c.font=BOLD if lab.startswith('Pooled') else f(color='0000FF') if j>2 else f()
        rg.cell(row,6).number_format='0.0000'
        row+=1
    row+=1
rg.cell(row,1,'How to read: pre-construction coefficients (DS2021–DS2023) should be close to 0 if Section 1 and controls followed the same trend before March 2024. Values far from 0 mean Section 1 was already changing differently (pre-trend).').font=f(italic=True)
for c,w in zip('ABCDEFGH',[18,32,14,12,12,10,8,13]): rg.column_dimensions[c].width=w
wb.move_sheet('Summary',offset=-1)
wb.save(RES/'Vegetation_loss_results.xlsx'); print('saved')
