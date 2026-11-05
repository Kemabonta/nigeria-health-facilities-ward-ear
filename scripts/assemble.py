import pandas as pd, geopandas as gpd, numpy as np, re
import os; W=os.environ.get('HF_WORKDIR','./'); TAG='Nigeria_Health_Facilities_Combined_11-3-2026_v1.0'
gh=pd.read_pickle(W+'work/grid3.pkl'); go=pd.read_pickle(W+'work/osm_matched.pkl')
ear=gpd.read_parquet(W+'ear/ear_ward_2025_from_dump.parquet')
ear['ward_lga']=ear.parent_label.str.rsplit(', ',n=1).str[0]; ear['ward_state']=ear.parent_label.str.rsplit(', ',n=1).str[1]
ear=ear.rename(columns={'unit_id':'ward_id','name':'ward_name','pop_total':'ward_pop_2025','pop_lit':'ward_pop_lit_2025','ear_pct':'ward_ear_2025_pct'})
E=ear.drop(columns='geometry').set_index('ward_id')

A=pd.DataFrame({
 'source':'GRID3 NGA Health Facilities v4.0','source_id':gh.unique_id,
 'facility_name':gh.facility_name,'facility_type':gh.facility_type,'level_source':gh.facility_level,
 'level_harmonized':gh.level_harmonized,'ownership':gh.facility_ownership,'ownership_type':gh.facility_ownership_type,
 'functional_status':gh.functional,'settlement_type':gh.sett_ext_type,'nhfr_facility_code':gh.nhfr_facility_code,
 'src_state':gh.state_standard,'src_lga':gh.lga_standard,'src_ward':gh.ward_standard,
 'latitude':gh.latitude,'longitude':gh.longitude,'has_coords':gh.has_coords,'in_nigeria':gh.in_nigeria,
 'grid3_input_sources':gh.input_data_sources,'grid3_issues':gh.issues,
 'match_flag':'base (GRID3)','matched_grid3_id':None,'match_dist_m':np.nan,'match_score':np.nan,
 'ward_id':gh.ward_id,'ear_join_method':gh.ear_join_method,'phone_private':None,'phone_source':None})
add=go[(go.kind=='facility')&(go.match_flag=='none')]
def own(r):
    t=str(r.get('t_operator:type') or r.get('t_operator_type') or '').lower()
    if t in ('public','government') or 'state' in t or 'primary' in t: return 'Public'
    if t in ('private','ngo','religious','community','charity','private_non_profit'): return 'Private'
    return None
B=pd.DataFrame({
 'source':'OpenStreetMap (Geofabrik extract 2026-11-03)','source_id':add.osm_id,
 'facility_name':add.t_name,'facility_type':(add.t_amenity.fillna('')+'/'+add.t_healthcare.fillna('')).str.strip('/'),
 'level_source':add.get('t_healthcare:level'),'level_harmonized':add.level_harmonized,'ownership':add.apply(own,axis=1),
 'ownership_type':add.get('t_operator:type').fillna(add.get('t_operator_type')) if 't_operator:type' in add else add.get('t_operator_type'),
 'functional_status':np.where(add.get('t_disused').notna() if 't_disused' in add else False,'disused tag','Unknown'),
 'settlement_type':None,'nhfr_facility_code':None,'src_state':None,'src_lga':None,'src_ward':None,
 'latitude':add.lat,'longitude':add.lon,'has_coords':add.has_coords,'in_nigeria':add.in_nigeria,
 'grid3_input_sources':None,'grid3_issues':None,'match_flag':'added (no GRID3 match)','matched_grid3_id':None,
 'match_dist_m':np.nan,'match_score':np.nan,'ward_id':add.ward_id,'ear_join_method':add.ear_join_method,
 'phone_private':add.get('t_phone').fillna(add.get('t_contact:phone')) if 't_contact:phone' in add else add.get('t_phone'),
 'phone_source':None})
B.loc[B.phone_private.notna(),'phone_source']='https://www.openstreetmap.org/'+B.loc[B.phone_private.notna(),'source_id']
M=pd.concat([A,B],ignore_index=True)
M['ward_name']=M.ward_id.map(E.ward_name); M['lga']=M.ward_id.map(E.ward_lga); M['state']=M.ward_id.map(E.ward_state)
for c in ['ward_ear_2025_pct','ward_pop_2025','ward_pop_lit_2025']: M[c]=M.ward_id.map(E[c])
M['lga']=M.lga.fillna(M.src_lga); M['state']=M.state.fillna(M.src_state); M['ward_name']=M.ward_name.fillna(M.src_ward)
bins=[-0.001,10,25,50,75,100.001]; labs=['0-10%','10-25%','25-50%','50-75%','75-100%']
M['ear_band']=pd.cut(M.ward_ear_2025_pct,bins=bins,labels=labs).astype(str).replace('nan',None)
M['is_primary']=M.level_harmonized.eq('Primary')
M['rural_settlement']=np.where(M.settlement_type.isna(),None,np.where(M.settlement_type.isin(['Small Settlement Area','Hamlet']),'Yes','No'))
M.insert(0,'uid',['NGHF_%06d'%i for i in range(1,len(M)+1)])
M.to_pickle(W+'work/merged.pkl')
print(len(M), M.source.value_counts().to_dict(), M.ear_join_method.value_counts(dropna=False).to_dict())
print('phones in added OSM', B.phone_private.notna().sum())
