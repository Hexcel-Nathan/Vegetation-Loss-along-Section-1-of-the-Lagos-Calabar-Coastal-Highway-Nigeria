"""04 - Matching and difference-in-differences (Sections 3.7 and 4.3).

Matching : each Section 1 segment gets its 2 nearest control segments (Mahalanobis distance on
           DS2020 vegetation and built-up shares, with replacement, caliper 0.5). Segments with
           no control inside the caliper are dropped (common support). Balance = standardised
           mean differences (SMD) before/after.
Outcome  : Y = % of the unit's DS2020 vegetation that is non-vegetated in year t
           (units with < 1 ha of DS2020 vegetation excluded).
Models   : unit + year fixed effects, SE clustered by 1 km segment, for each zone (F, B1, B2, B3):
             event study  - Treated x year dummies, reference year DS2024
             pooled DiD   - Treated x Post (Post = DS2025-DS2026), estimated on DS2021-DS2026
           Three specifications: A unmatched; B matched (weights); C all segments + baseline
           covariate x year trends. Wild cluster bootstrap p-value (Rademacher, null imposed,
           499 draws) for B.

Inputs : data/tables/segment_zone_panel_DS2020_2026.csv, results/seg_cov.csv (from 02)
Outputs: results/matching_balance.csv, matched_pairs.csv, did_results.csv, event_study.csv, seg_cov_w.csv
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from paths import TAB, RES
import pandas as pd, numpy as np, statsmodels.api as sm
rng=np.random.default_rng(1)
d=pd.read_csv(TAB/'segment_zone_panel_DS2020_2026.csv')
b=pd.read_csv(RES/'seg_cov.csv')
X=['veg','built']
T=b[b.treated==1].reset_index(drop=True); C=b[b.treated==0].reset_index(drop=True)
Si=np.linalg.inv(np.cov(b[X].values.T))
D=np.array([[np.sqrt((t-c)@Si@(t-c)) for c in C[X].values] for t in T[X].values])
K,CAL=2,0.5
idx=np.argsort(D,axis=1)[:,:K]; dm=np.take_along_axis(D,idx,1); keep=dm.max(1)<=CAL
w={}; pairs=[]
for i in range(len(T)):
    if keep[i]:
        w[T.seg_id[i]]=1.0
        for j,dist in zip(idx[i],dm[i]):
            w[C.seg_id[j]]=w.get(C.seg_id[j],0)+1/K; pairs.append((T.seg_id[i],C.seg_id[j],round(dist,3)))
    else: pairs.append((T.seg_id[i],'(no match within caliper)',round(dm[i].min(),3)))
b['match_w']=b.seg_id.map(w).fillna(0)
def smdrow(v,tr,co,wt):
    sd=np.sqrt((T[v].var()+C[v].var())/2)
    return (tr[v].mean()-co[v].mean())/sd, (tr[v].mean()-np.average(co[v],weights=wt))/sd
bal=[]
tr=b[(b.treated==1)&(b.match_w>0)]; co=b[(b.treated==0)&(b.match_w>0)]
for v,lab in [('veg','Vegetation share 2020'),('built','Built-up share 2020'),('bare','Bare/sand share 2020'),('waterfrac','Water share of cell'),('elev','Mean elevation (m)'),('dcbd_km','Distance to Lagos Island CBD (km)')]:
    before=(T[v].mean()-C[v].mean())/np.sqrt((T[v].var()+C[v].var())/2)
    after=(tr[v].mean()-np.average(co[v],weights=co.match_w))/np.sqrt((T[v].var()+C[v].var())/2)
    bal.append(dict(covariate=lab,used_in_matching=('Yes' if v in X else 'No'),S1_mean_all=T[v].mean(),Ctrl_mean_all=C[v].mean(),SMD_before=before,
                    S1_mean_matched=tr[v].mean(),Ctrl_mean_matched=np.average(co[v],weights=co.match_w),SMD_after=after))
bal=pd.DataFrame(bal)

d=d[d.a_veg2020>=1e4].copy(); d['y']=100*d.a_veglost/d.a_veg2020
d=d.merge(b[['seg_id','veg','built','elev','match_w']],on='seg_id')

def fit(s,terms,wcol=None,extra=None):
    s=s.reset_index(drop=True)
    Xd=pd.get_dummies(s.unit_id,drop_first=False,dtype=float)
    Yd=pd.get_dummies(s.year,prefix='yr',drop_first=True,dtype=float)
    M=pd.concat([s[terms].astype(float),Xd,Yd]+([extra(s)] if extra else []),axis=1)
    W=s[wcol].values if wcol else None
    mod=(sm.WLS(s.y,M,weights=W) if wcol else sm.OLS(s.y,M)).fit(cov_type='cluster',cov_kwds={'groups':pd.factorize(s.seg_id)[0]})
    return mod,M,W
def cov_trends(s):  # year dummies x baseline covariates
    out={}
    for yr in sorted(s.year.unique())[1:]:
        for v in ['veg','built','elev']: out[f'{v}_x{yr}']=(s.year==yr)*s[v]
    return pd.DataFrame(out)
def wild(s,M,W,term,B=999):
    s=s.reset_index(drop=True); cl=pd.factorize(s.seg_id)[0]; G=cl.max()+1
    Mr=M.drop(columns=[term]); w=np.ones(len(s)) if W is None else W
    sw=np.sqrt(w)
    br=np.linalg.lstsq(Mr.values*sw[:,None],s.y.values*sw,rcond=None)[0]; fr=Mr.values@br; er=s.y.values-fr
    def tstat(y):
        mod=sm.WLS(y,M,weights=w).fit(cov_type='cluster',cov_kwds={'groups':cl}); return mod.tvalues[term]
    t0=tstat(s.y.values); cnt=0
    for _ in range(B):
        v=rng.choice([-1,1],G)[cl]; cnt+=abs(tstat(fr+er*v))>=abs(t0)
    return (cnt+1)/(B+1)
rows=[]; es=[]
for z,zl in [('F','Footprint'),('B1','0–500 m'),('B2','500 m–1 km'),('B3','1–5 km')]:
    for spec in ['A: Unmatched (all segments)','B: Matched (common support)','C: All segments + baseline covariate trends']:
        s=d[d.zone==z].copy()
        wcol=None; extra=None
        if spec.startswith('B'): s=s[s.match_w>0]; wcol='match_w'
        if spec.startswith('C'): extra=cov_trends
        s2=s[s.year>=2021].copy(); s2['post']=((s2.year>=2025)&(s2.treated==1)).astype(int)
        m,M,W=fit(s2,['post'],wcol,extra)
        p_boot=wild(s2,M,W,'post',B=499) if spec[0] in 'B' else np.nan
        ci=m.conf_int().loc['post']
        rows.append(dict(zone=z,distance=zl,spec=spec,estimate=m.params.post,ci_low=ci[0],ci_high=ci[1],p_cluster=m.pvalues.post,p_wild_bootstrap=p_boot,
                         treated_units=s[s.treated==1].unit_id.nunique(),control_units=s[s.treated==0].unit_id.nunique()))
        # event study
        for k in [2021,2022,2023,2025,2026]: s[f'e{k}']=((s.year==k)&(s.treated==1)).astype(int)
        me,_,_=fit(s,[f'e{k}' for k in [2021,2022,2023,2025,2026]],wcol,extra)
        for k in [2021,2022,2023,2024,2025,2026]:
            if k==2024: es.append(dict(zone=z,spec=spec,year=k,estimate=0,ci_low=0,ci_high=0))
            else:
                c=me.conf_int().loc[f'e{k}']; es.append(dict(zone=z,spec=spec,year=k,estimate=me.params[f'e{k}'],ci_low=c[0],ci_high=c[1]))
res=pd.DataFrame(rows); es=pd.DataFrame(es)
pd.set_option('display.width',250)
print(bal.round(2).to_string()); print(res.round(3).to_string()); print(es[es.spec.str.startswith('B')].round(2).to_string())
bal.to_csv(RES/'matching_balance.csv',index=False); res.to_csv(RES/'did_results.csv',index=False); es.to_csv(RES/'event_study.csv',index=False)
pd.DataFrame(pairs,columns=['treated_segment','matched_control','mahalanobis_distance']).to_csv(RES/'matched_pairs.csv',index=False)
b.to_csv(RES/'seg_cov_w.csv',index=False)
