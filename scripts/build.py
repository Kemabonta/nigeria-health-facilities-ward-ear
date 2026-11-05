import pandas as pd, geopandas as gpd, numpy as np, json, re, unicodedata
from rapidfuzz import fuzz
from shapely.geometry import Point
import os; W=os.environ.get('HF_WORKDIR','./')
def norm(s):
    if s is None or (isinstance(s,float) and np.isnan(s)): return ''
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    s=re.sub(r'[^a-z0-9 ]',' ',s); return re.sub(r'\s+',' ',s).strip()
GENERIC=r'\b(primary|health|healthcare|care|centre|center|clinic|post|phc|bhc|comprehensive|basic|hospital|general|maternity|and|the|of|medical|dispensary|model|ward|community|cottage|home)\b'
def core(s): return re.sub(r'\s+',' ',re.sub(GENERIC,' ',norm(s))).strip()

# ---------- EAR wards (from PG dump, raw VIIRS >0, 1 km flare mask, 2025 pop) ----------
ear=gpd.read_parquet(W+'ear/ear_ward_2025_from_dump.parquet')
ear['ward_lga']=ear.parent_label.str.rsplit(', ',n=1).str[0]; ear['ward_state']=ear.parent_label.str.rsplit(', ',n=1).str[1]
ear=ear.rename(columns={'unit_id':'ward_id','name':'ward_name','pop_total':'ward_pop_2025','pop_lit':'ward_pop_lit_2025','ear_pct':'ward_ear_2025_pct'})
ear_m=ear.to_crs(3857)

# ---------- GRID3 v4 ----------
h=pd.read_csv(W+'raw/grid3_v4_hf.csv',low_memory=False)
h['has_coords']=h.latitude.notna()&h.longitude.notna()
gh=gpd.GeoDataFrame(h,geometry=[Point(x,y) if ok else None for x,y,ok in zip(h.longitude,h.latitude,h.has_coords)],crs=4326)

# ---------- OSM (Geofabrik extract) ----------
osm=json.load(open(W+'raw/osm_geofabrik_health.json'))
o=pd.DataFrame([{**{'osm_id':r['osm_id'],'lon':r['lon'],'lat':r['lat'],'osm_timestamp':r['ts']},**{'t_'+k:v for k,v in r['tags'].items() if k in ('name','amenity','healthcare','healthcare:speciality','operator','operator:type','operator_type','phone','contact:phone','contact:mobile','addr:full','addr:city','source','website','contact:website','opening_hours','disused','healthcare:level','health_facility:type','facility_level')}} for r in osm])
EXCL={'pharmacy','dentist','laboratory','optometrist','audiologist','psychotherapist','podiatrist','physiotherapist','speech_therapist','alternative','blood_donation','sample_collection','dialysis','counselling','rehabilitation','vaccination_centre','birthing_centre_no','yes_no'}
def osm_kind(r):
    a=r.get('t_amenity'); hc=r.get('t_healthcare')
    if a in ('pharmacy','dentist') : return 'excluded'
    if hc in EXCL and a not in ('clinic','hospital','doctors','health_post'): return 'excluded'
    if a in ('clinic','hospital','doctors','health_post') or hc in ('clinic','hospital','doctor','centre','health_post','primary','yes','birthing_centre','nurse','midwife','community_health_worker'): return 'facility'
    return 'excluded'
o['kind']=o.apply(osm_kind,axis=1)
o['has_coords']=o.lat.notna()
go=gpd.GeoDataFrame(o,geometry=[Point(x,y) if ok else None for x,y,ok in zip(o.lon,o.lat,o.has_coords)],crs=4326)

def ward_join(g):
    pts=g[g.has_coords].to_crs(3857)
    j=gpd.sjoin(pts[['geometry']],ear_m[['ward_id','geometry']],how='left',predicate='within')
    j=j[~j.index.duplicated()]
    g['ward_id']=j.ward_id.reindex(g.index)
    g['in_nigeria']=g.ward_id.notna()
    return g
gh=ward_join(gh); go=ward_join(go)

# GRID3 records lacking coords: attribute match to EAR ward via state/LGA/ward names
ear['k_full']=ear.ward_state.map(norm)+'|'+ear.ward_lga.map(norm)+'|'+ear.ward_name.map(norm)
kmap=ear.drop_duplicates('k_full').set_index('k_full').ward_id
dupk=set(ear.k_full[ear.k_full.duplicated()])
gh['k_full']=gh.state_standard.map(norm)+'|'+gh.lga_standard.map(norm)+'|'+gh.ward_standard.map(norm)
gh['ear_join_method']=np.where(gh.ward_id.notna(),'spatial (point in ward polygon)',None)
m=gh.ward_id.isna() & gh.k_full.isin(kmap.index) & ~gh.k_full.isin(dupk)
gh.loc[m,'ward_id']=gh.loc[m,'k_full'].map(kmap); gh.loc[m,'ear_join_method']='attribute (state+LGA+ward name)'
go['ear_join_method']=np.where(go.ward_id.notna(),'spatial (point in ward polygon)',None)

# ---------- level harmonisation ----------
TERT=r'teaching|university|federal medical cent|fmc\b|national hospital|neuro ?psychiatric|federal neuro|national orthop|specialist hospital|federal staff'
SEC=r'general hospital|cottage hospital|\bgh\b|state hospital|district hospital|specialist|comprehensive health cent'
PRIM=r'primary|phc|health cent|health post|dispensary|maternity|bhc|clinic|health clinic|mch\b'
def lvl_grid3(r):
    l=r.facility_level
    return l if l in ('Primary','Secondary','Tertiary') else 'Unknown'
def lvl_osm(r):
    n=norm(r.get('t_name')); a=r.get('t_amenity'); hc=r.get('t_healthcare'); lv=str(r.get('t_healthcare:level') or r.get('t_facility_level') or '').lower()
    if 'tert' in lv: return 'Tertiary'
    if 'second' in lv: return 'Secondary'
    if 'prim' in lv or hc=='primary': return 'Primary'
    if re.search(TERT,n): return 'Tertiary'
    if re.search(SEC,n): return 'Secondary'
    if a in ('clinic','health_post','doctors') or hc in ('clinic','health_post','centre','doctor','birthing_centre','nurse','midwife','community_health_worker') or re.search(PRIM,n): return 'Primary'
    return 'Unknown'
gh['level_harmonized']=gh.apply(lvl_grid3,axis=1)
go['level_harmonized']=go.apply(lvl_osm,axis=1)

# ---------- dedup OSM against GRID3 ----------
ghm=gh[gh.has_coords].to_crs(3857); gom=go[(go.kind=='facility')&go.has_coords].to_crs(3857)
# LGA of each point from the ward join
wlga=ear.set_index('ward_id').ward_lga; wst=ear.set_index('ward_id').ward_state
gh['lga_j']=gh.ward_id.map(wlga); go['lga_j']=go.ward_id.map(wlga)
gh_nocoord=gh[~gh.has_coords]
near=gpd.sjoin_nearest(gom[['geometry']],ghm[['geometry']],how='left',max_distance=1000,distance_col='dist_m')
cand={}
for i,row in near.iterrows():
    if pd.notna(row.index_right): cand.setdefault(i,[]).append((row.index_right,row.dist_m))
# all candidates within 250 m
buf=gom[['geometry']].copy(); buf['geometry']=buf.buffer(250)
within=gpd.sjoin(buf,ghm[['geometry']],how='inner',predicate='intersects')
res=[]
gname=gh.facility_name.map(norm); gcore=gh.facility_name.map(core)
for i,r in gom.iterrows():
    on=norm(r.t_name); oc=core(r.t_name)
    best=(None,None,0,'none')
    ids=list(within.index_right[within.index==i]) if i in within.index else []
    for j in ids:
        d=r.geometry.distance(ghm.geometry[j])
        if go.lga_j[i] is not None and gh.lga_j[j] is not None and go.lga_j[i]!=gh.lga_j[j] and d>50: continue
        sc=max(fuzz.token_set_ratio(on,gname[j]), fuzz.token_set_ratio(oc,gcore[j]) if oc and gcore[j] else 0) if on else 0
        flag=None
        if on and sc>=80 and d<=(250 if oc else 100): flag='dup_name+distance<=250m' if d>100 else 'dup_name+distance<=100m'
        elif on and sc>=60 and d<=100: flag='dup_name+distance<=100m'
        elif not on and d<=50: flag='dup_unnamed<=50m'
        if flag and (best[0] is None or sc>best[2] or (sc==best[2] and d<best[1])): best=(j,d,sc,flag)
    if best[0] is None and on and oc:
        # name-only within same LGA (<=1 km) and GRID3 records without coordinates in same LGA
        for j,d in cand.get(i,[]):
            if gh.lga_j[j]==go.lga_j[i] and fuzz.token_set_ratio(oc,gcore[j])>=90 and fuzz.ratio(on,gname[j])>=85:
                best=(j,d,fuzz.ratio(on,gname[j]),'dup_name_same_LGA<=1km')
    if best[0] is None and on and oc and go.lga_j[i] is not None:
        L=norm(go.lga_j[i]); pool=gh_nocoord[gh_nocoord.lga_standard.map(norm)==L]
        for j in pool.index:
            if fuzz.ratio(on,gname[j])>=92:
                best=(j,None,fuzz.ratio(on,gname[j]),'dup_name_GRID3_nocoord_same_LGA'); break
    res.append((i,best[0],best[1],best[2],best[3]))
mr=pd.DataFrame(res,columns=['idx','grid3_idx','dist_m','score','flag']).set_index('idx')
go['match_flag']=mr.flag.reindex(go.index)
go['matched_grid3_id']=mr.grid3_idx.reindex(go.index).map(lambda j: gh.unique_id[j] if pd.notna(j) else None)
go['match_dist_m']=mr.dist_m.reindex(go.index); go['match_score']=mr.score.reindex(go.index)
go.to_pickle(W+'work/osm_matched.pkl'); gh.to_pickle(W+'work/grid3.pkl')
print(go.match_flag.value_counts(dropna=False))
