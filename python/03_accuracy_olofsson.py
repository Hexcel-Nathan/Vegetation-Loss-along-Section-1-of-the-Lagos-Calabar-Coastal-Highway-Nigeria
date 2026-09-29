"""03 - Accuracy assessment and error-adjusted areas (Section 3.6; Olofsson et al., 2014; Stehman, 2014).

300 points were drawn by gee/06 with the change map as strata (1 stable vegetation 80, 2 vegetation
loss 100, 3 vegetation gain 50, 4 stable non-vegetation 70). Each point was labelled blind as
vegetation (1) / non-vegetation (0) in 2020 (Esri Wayback) and 2026 (Wayback / PlanetScope).

Step 1 joins the blind labels to the answer key by coordinates (the pt_id field was damaged in
the export, e.g. 10 -> 1.0, so ids cannot be trusted; coordinates match exactly).
Step 2 computes, for the DS2020 map, the DS2026 map and the change map: overall, user's and
producer's accuracy with 95% CIs, and error-adjusted class areas with 95% CIs.

Inputs : data/validation/accuracy_labels.xlsx, accuracy_key.csv; data/tables/strata_areas.csv
Outputs: results/accuracy_labels_matched.csv, accuracy_summary.csv, accuracy_error_matrices.csv
"""
import sys, os, json; sys.path.insert(0, os.path.dirname(__file__))
from paths import VAL, TAB, RES
import pandas as pd, numpy as np

lab = pd.read_excel(VAL / 'accuracy_labels.xlsx')
key = pd.read_csv(VAL / 'accuracy_key.csv')
xy = key['.geo'].apply(lambda g: json.loads(g)['coordinates'])
key['lon'], key['lat'] = xy.str[0], xy.str[1]
k = lambda df: list(zip(df.lon.round(6), df.lat.round(6)))
lab['k'], key['k'] = k(lab), k(key)
d = lab.merge(key[['k', 'pt_id', 'stratum']].rename(columns={'pt_id': 'pt_id_true'}), on='k', how='inner').drop(columns='k')
d['pt_id_true'] = d.pt_id_true.astype(int)
d.to_csv(RES / 'accuracy_labels_matched.csv', index=False)
S = pd.read_csv(TAB / 'strata_areas.csv')
assert len(d)==300
d['map20']=d.stratum.isin([1,2]).astype(int); d['map26']=d.stratum.isin([1,3]).astype(int)
def rchange(a,b): return np.select([(a==1)&(b==1),(a==1)&(b==0),(a==0)&(b==1)],[1,2,3],4)
d['refchg']=rchange(d.ref2020,d.ref2026)
A=S.area_ha.sum(); W=dict(zip(S.stratum,S.area_ha/A)); nh=d.groupby('stratum').size().to_dict()
def olofsson(mapcol,refcol,classes,stratum_to_map):
    # p_ij estimated area proportions (map i, ref j); map classes are unions of strata
    # compute using strata as sampling units
    res={}
    P=np.zeros((len(classes),len(classes)))
    for h,g in d.groupby('stratum'):
        for i,ci in enumerate(classes):
            for j,cj in enumerate(classes):
                P[i,j]+=W[h]*np.mean((g[mapcol]==ci)&(g[refcol]==cj))
    OA=np.trace(P)
    # variances via stratified estimator of ratios (Stehman 2014)
    def var_total(yfun):
        v=0
        for h,g in d.groupby('stratum'):
            y=yfun(g).astype(float); v+=W[h]**2*np.var(y,ddof=1)/len(g)
        return v
    def ratio_se(yf,xf):
        R=sum(W[h]*yf(g).mean() for h,g in d.groupby('stratum'))/sum(W[h]*xf(g).mean() for h,g in d.groupby('stratum'))
        X=sum(W[h]*xf(g).mean() for h,g in d.groupby('stratum'))
        v=0
        for h,g in d.groupby('stratum'):
            y=yf(g).astype(float); x=xf(g).astype(float)
            v+=W[h]**2*(np.var(y,ddof=1)+R**2*np.var(x,ddof=1)-2*R*np.cov(y,x,ddof=1)[0,1])/len(g)
        return R,np.sqrt(v/X**2)
    oa_se=np.sqrt(var_total(lambda g:(g[mapcol]==g[refcol])))
    out=[]
    for i,c in enumerate(classes):
        ua,ua_se=ratio_se(lambda g:(g[mapcol]==c)&(g[refcol]==c),lambda g:(g[mapcol]==c))
        pa,pa_se=ratio_se(lambda g:(g[mapcol]==c)&(g[refcol]==c),lambda g:(g[refcol]==c))
        area=A*P[:,i].sum(); area_se=A*np.sqrt(var_total(lambda g:(g[refcol]==c)))
        maparea=A*P[i,:].sum()
        out.append(dict(cls=c,users=ua,users_ci=1.96*ua_se,producers=pa,producers_ci=1.96*pa_se,map_area_ha=maparea,adj_area_ha=area,adj_area_ci=1.96*area_se))
    counts=pd.crosstab(d[mapcol],d[refcol]).reindex(index=classes,columns=classes,fill_value=0)
    return OA,1.96*oa_se,pd.DataFrame(out),counts,P
res={}
for name,mc,rc,cl in [('DS2020 map','map20','ref2020',[1,0]),('DS2026 map','map26','ref2026',[1,0]),('Change 2020-2026','stratum','refchg',[1,2,3,4])]:
    OA,oaci,t,cnt,P=olofsson(mc,rc,cl,None)
    res[name]=(OA,oaci,t,cnt,P)
    print('\n',name,'OA %.3f ± %.3f'%(OA,oaci)); print(t.round(3).to_string()); print(cnt)

names = {'DS2020 map': {1: 'Vegetation', 0: 'Non-vegetation'}, 'DS2026 map': {1: 'Vegetation', 0: 'Non-vegetation'},
         'Change 2020-2026': {1: 'Stable vegetation', 2: 'Vegetation lost', 3: 'Vegetation gained', 4: 'Stable non-vegetation'}}
summ, mats = [], []
for name, (OA, oaci, t, cnt, P) in res.items():
    t = t.copy(); t.insert(0, 'map', name); t['class'] = t.cls.map(names[name]); t['overall'] = OA; t['overall_ci'] = oaci
    summ.append(t.drop(columns='cls'))
    c = cnt.rename(index=names[name], columns=names[name]); c.index.name = 'map \\ reference'
    c.insert(0, 'map', name); mats.append(c.reset_index())
pd.concat(summ).to_csv(RES / 'accuracy_summary.csv', index=False)
pd.concat(mats).to_csv(RES / 'accuracy_error_matrices.csv', index=False)
print('study-area land (ha):', round(A))
