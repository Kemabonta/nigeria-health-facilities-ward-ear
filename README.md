# Nigeria Health Facilities, Combined Layer with 2025 Ward Electricity Access (v1.0)

A national, deduplicated point layer of health facilities in Nigeria (72,008 records), built on GRID3 NGA Health Facilities v4.0 and supplemented with OpenStreetMap facilities that GRID3 does not contain. Every facility is joined to its ward and to the ward's 2025 electricity access rate (EAR), estimated from raw NOAA/EOG VIIRS night-time lights.

Author: **Tam Kemabonta** (Entric). Version 1.0, 3 November 2026.

## Contents

| Path | Description |
|---|---|
| `data/nigeria_health_facilities_combined_v1.0.csv` | Combined facility layer (all records, incl. those without coordinates) |
| `data/nigeria_health_facilities_combined_v1.0.geojson.zip` | Same, as zipped GeoJSON (records without coordinates have null geometry) |
| `data/ward_ear_2025_with_facility_counts.csv` | Ward EAR 2025 table (9,307 wards) with facility and primary-facility counts |
| `data/phc_by_ward_ear_band_national.csv` | Primary-level facilities by ward EAR band, national |
| `data/phc_by_ward_ear_band_state.csv` | Primary-level facilities by ward EAR band and state |
| `data/phc_in_wards_ear_below_25pct.csv` | Primary-level facilities in wards with EAR below 25% |
| `data/facility_counts_by_state.csv`, `data/source_comparison.csv`, `data/merge_summary.csv` | Summary tables |
| `figures/nigeria_phc_ward_ear_2025.png/.pdf` | National map: primary-level facilities over the ward EAR choropleth |
| `scripts/` | Reference build scripts (paths refer to the author's build environment) |

## Sources

| Source | Records | Primary-level | % with valid coordinates in Nigeria | License |
|---|---|---|---|---|
| GRID3 NGA - Health Facilities v4.0 (CIESIN, Columbia University) | 70,235 | 49,761 | 83.1 | CC BY 4.0 |
| OpenStreetMap health features (Geofabrik Nigeria extract) | 7,957 | 4,475 | 98.9 | ODbL 1.0 (share-alike) |
| of which clinic/hospital/doctors/health post (pharmacy, dentist, lab excluded) | 6,367 | 4,475 | 98.7 | ODbL 1.0 |
| HOT OSM Health Facilities export on HDX (hotosm_nga_health_facilities) | 7,822 |  |  | ODbL 1.0 |
| WHO / KEMRI-Wellcome public health facilities in sub-Saharan Africa (Maina et al. 2019) |  |  |  | CC BY 4.0 (HDX listing) |
| Nigeria Health Facility Registry (NHFR), hfr.health.gov.ng |  |  |  | Not stated publicly |
| eHealth Africa Nigeria health facilities (HDX "nigeria-health-facilities") |  |  |  | CC BY 4.0 (HDX listing) |

- **GRID3 NGA - Health Facilities v4.0**: CIESIN, Columbia University (2026), https://doi.org/10.7916/pjpv-9q55, CC BY 4.0. Integrates NHFR 2024/2026, NPHCDA and GRID3 v2 inputs.
- **OpenStreetMap**: © OpenStreetMap contributors, Geofabrik Nigeria extract (3 Nov 2026), ODbL 1.0.
- **Ward boundaries**: GRID3 NGA - Operational Wards v4.0, CIESIN, CC BY-SA 4.0.
- **Night-time lights**: Earth Observation Group, Payne Institute, Colorado School of Mines, VIIRS Nighttime Lights (VNL) v2 annual composites, https://eogdata.mines.edu/products/vnl/.
- WHO/KEMRI (Maina et al. 2019), the Nigeria Health Facility Registry and the eHealth Africa HDX file were evaluated but could not be downloaded on 3 Nov 2026, so they are not in this release.

## Method

1. **Base layer.** All 70,235 GRID3 v4.0 records are kept, including 11,706 without coordinates (`has_coords = False`).
2. **OSM extraction.** OSM nodes, ways and relations tagged `amenity` = clinic, hospital, doctors or health_post, or any `healthcare=*`, were taken from the Geofabrik extract. Pharmacies, dentists, laboratories and similar were excluded. Ways use the mean of their node coordinates.
3. **Deduplication (merge).** Each OSM facility was compared with GRID3 points within 250 m. It is a duplicate if: token-set name similarity is 80 or more and the distance is 250 m or less; or similarity is 60 or more and 100 m or less; or the OSM feature is unnamed and within 50 m. Candidates in a different LGA are skipped beyond 50 m. Names made only of generic words ("PHC", "Health Post") are capped at 100 m. Two fallbacks catch near-identical names: the nearest GRID3 point within 1 km in the same LGA, or a GRID3 record without coordinates in the same LGA (name ratio of 92 or more). Unmatched OSM facilities (1,773) were added.
4. **Level harmonisation.** GRID3 `facility_level` is kept as is (blank becomes Unknown). For OSM, the `healthcare:level` tag is used where present. Otherwise name keywords decide: teaching, university, federal medical centre or specialist hospital is Tertiary; general, cottage, state or district hospital, or comprehensive health centre, is Secondary. Failing that, clinic, health_post, doctors or PHC-type tags and names are Primary. Anything else is Unknown.
5. **Admin join.** State, LGA and ward come from a point-in-polygon join to the GRID3 operational ward polygons. GRID3 records without coordinates are joined on exact normalised state + LGA + ward names.
6. **Ward EAR 2025.** EAR is the share of a ward's 2025 population living in VIIRS VNL v2 annual 2025 grid cells with radiance **> 0** (any detectable light counts as lit). Cells within **1 km of same-year gas flares** are masked, and **2025 population** is used. EAR = lit population / total population × 100. These are raw-VIIRS values, not harmonised or calibrated values.

## Primary-level facilities by ward EAR band (national)

| Ward EAR 2025 band | Primary-level facilities | Share (%) |
|---|---|---|
| 0-10% | 24,272 | 47.8 |
| 10-25% | 3,653 | 7.2 |
| 25-50% | 4,483 | 8.8 |
| 50-75% | 3,868 | 7.6 |
| 75-100% | 13,827 | 27.2 |
| No EAR value / not joined | 675 | 1.3 |

For reference, the Federal Ministry of Health and NPHCDA cite "over 30,000" primary health care centres. GRID3 v4.0 lists 49,761 primary-level records of all ownership types, of which 41,003 are public.

## Field dictionary (`nigeria_health_facilities_combined_v1.0`)

| Field | Description |
|---|---|
| `uid` | Unique id in this dataset (NGHF_000001...) |
| `source` | GRID3 NGA Health Facilities v4.0, or OpenStreetMap (Geofabrik extract 2026-11-03) |
| `source_id` | GRID3 unique_id or OSM element id (node/way/relation) |
| `facility_name` | Facility name as in source |
| `facility_type` | GRID3 facility_type; for OSM, amenity/healthcare tag values |
| `level_source` | Level as given by the source (GRID3 facility_level; OSM healthcare:level tag if any) |
| `level_harmonized` | Primary, Secondary, Tertiary or Unknown (see Method) |
| `is_primary` | True if level_harmonized is Primary |
| `ownership` | Public / Private (GRID3; OSM operator:type where present) |
| `ownership_type` | GRID3 ownership type (State/Local/Federal Government, For Profit, ...) |
| `functional_status` | GRID3 functional status; OSM: "Unknown" or "disused tag" |
| `settlement_type` | GRID3 settlement extent type (Built-up Area, Small Settlement Area, Hamlet) |
| `rural_settlement` | Yes if settlement_type is Small Settlement Area or Hamlet; No if Built-up Area; blank otherwise |
| `nhfr_facility_code` | NHFR facility code carried by GRID3 (where available) |
| `state, lga, ward_name, ward_id` | Admin units from point-in-polygon join to GRID3 operational wards (v4 ids NGA_W4_*); for GRID3 records without coordinates, from GRID3 names |
| `src_state, src_lga, src_ward` | Admin names as given by GRID3 |
| `latitude, longitude` | WGS84 decimal degrees; blank when the source has no coordinates |
| `has_coords` | True if the record has coordinates |
| `in_nigeria` | True if the point falls inside a Nigerian ward polygon |
| `ward_ear_2025_pct` | Electricity access rate (%) of the ward, 2025 |
| `ward_pop_2025` | Ward population, 2025 |
| `ward_pop_lit_2025` | Ward population living in lit cells, 2025 |
| `ear_band` | 0-10%, 10-25%, 25-50%, 50-75%, 75-100% (lower bound inclusive) |
| `ear_join_method` | spatial (point in ward polygon) or attribute (state+LGA+ward name) |
| `match_flag` | "base (GRID3)" or "added (no GRID3 match)" |
| `grid3_input_sources` | GRID3 lineage (e.g. nhfr2024, nhfr2026, nphcda, grid3v2) |
| `grid3_issues` | GRID3 QA notes (missing xy, clustered, outside ward) |

## Known limitations

- 11,706 GRID3 records (16.7%) have no coordinates. Of these, 8,458 were placed in a ward by name matching.
- GRID3 describes its data as non-exhaustive and not validated by government. Its `grid3_issues` field flags clustered points and points outside their own ward.
- Name matching can pair facilities wrongly, or miss real duplicates, where names are similar or spelled differently.
- OSM-derived levels come from tags and names, and OSM ownership is sparse.
- Ward EAR measures detectable night-time light where people live. It does not measure the electricity supply of a specific facility.

## Privacy

The public files contain no phone numbers, contact fields or personal data. Phone and contact attributes in the sources were not carried into these files. An automated scan of `data/` for formatted Nigerian phone numbers found none.

## License

See `LICENSE`. In short: the combined facility database is under the **Open Database License (ODbL) 1.0**, because it contains OpenStreetMap data. The ward EAR table and the figures are under **CC BY-SA 4.0**, because they rely on GRID3 operational ward boundaries. Attribution to GRID3/CIESIN, OpenStreetMap contributors and EOG/Colorado School of Mines is required. Scripts are under the MIT License.

## Citation

Kemabonta, T. (2026). *Nigeria Health Facilities, Combined Layer with 2025 Ward Electricity Access* (v1.0). Entric. See `CITATION.cff`.

Please also cite: CIESIN (2026) GRID3 NGA - Health Facilities v4.0, https://doi.org/10.7916/pjpv-9q55; and © OpenStreetMap contributors.
