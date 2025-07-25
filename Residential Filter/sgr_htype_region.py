#!/usr/bin/env python
# coding: utf-8

# In[278]:


import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import re


# In[279]:


def broad_filter(res_cases):
    # filter out cases with irrelevant type codes
    types = ['PL_MINSP', 'PL_SSP_SM', 'PL_SSM_SM2', 'PL_CPAA', 'PL_MINPP', 'PL_MAJSP', 'PL_MAJSUP', 'PL_PPA', 'PL_MAJPP']
    filter_cases_type = res_cases[res_cases['A_TYPE'].isin(types)]

    # filter out cases with out of date status
    status = res_cases['A_STATUS'].unique()
    status = status[~np.isin(status, ['WITH', 'VOID','DEN','DISAP','EXP'])]
    filter_cases_status = filter_cases_type[filter_cases_type['A_STATUS'].isin(status)]

    # keep entries with keywords
    keywords = ['home', 'family', 'residen', 'mixed', 'mized', 'duplex', 'apartment', ' housing', 'condo', 'dwelling', 'tenant', 'affordable', 'units', 'townhouse']
    pattern = '|'.join(keywords)
    filtered_in = filter_cases_status[filter_cases_status['A_DESCRIPT'].str.contains(pattern, case=False, na=False)]

    # remove entries with certain words
    keywords_avoid = ['expand','storage']
    pattern_avoid = '|'.join(keywords_avoid)
    filtered_words = filtered_in[~filtered_in['A_DESCRIPT'].str.contains(pattern_avoid, case=False, na=False)]

    # filter out entries that were last updated over 5 years ago
    filtered_words = filtered_words.copy()
    filtered_words['A_STATUS_D'] = pd.to_datetime(filtered_words['A_STATUS_D'])
    filtered_final = filtered_words[filtered_words['A_STATUS_D'].dt.year>=2020]

    return filtered_final


# In[280]:


def normalize_for_regex(term):
    # makes it so string returns a match whether a term has spaces, dashes, both, or neither
    return re.sub(r'[-\s]+', r'\\s*-?\\s*', term)


# In[281]:


def extract_units(description):
    # remove square footage references
    description = re.sub(
        r'(\d+|\d{1,3}(,\d{3})*)(\s+[A-Za-z-]+){0,2}?\s*(SF|square feet|sq\.?\s*ft\.?|sqft)',
        '', description, flags=re.IGNORECASE
    )

    # map variations to standardized types
    term_map = {
        "home": "home", "homes": "home", "house": "home", "houses": "home",
        "duplex": "duplex", "duplexes": "duplex",
        "condo": "condo", "condominium": "condo", "condominiums": "condo", "condos": "condo", 
        "apartment": "apartment", "apartments": "apartment",
        "townhome": "townhouse", "townhomes": "townhouse",
        "townhouse": "townhouse", "townhouses": "townhouse",
        "town home": "townhouse", "town homes": "townhouse",
        "town house": "townhouse", "town houses": "townhouse",
        "multifamily": "multifamily", "multi-family": "multifamily", 
        "multi - family": "multifamily", "multi family": "multifamily",
        "mutifamily": "multifamily", "MF": "multifamily",
        "single family": "single family", "single-family": "single family", 
        "single - family": "single family", "s-f": "single family", "s - f": "single family", "s f": "single family"
    }

    modifiers = ["attached", "detached"]
    suffixes = ["units", "lots", "homes", "houses"]

    housing_pattern = "|".join([normalize_for_regex(term) for term in term_map])
    modifier_pattern = "|".join(modifiers)
    suffix_pattern = "|".join(suffixes)

    # extended match pattern to support both "qty before type" and "type before qty"
    match_pattern = rf'''
    (?:
        # Qty before type
        (?P<qty>\(?\d{{1,4}}\)?)
        (?:\s*[-+&/]?\s*)?
        (?:({modifier_pattern})\s*){{0,2}}?
        (?:\w+\s*){{0,4}}?
        (?P<type>{housing_pattern})
        (?:\s+({modifier_pattern}))?
        (?:\s+(?P<suffix>{suffix_pattern}))?

    |
        # Type before qty
        (?P<type2>{housing_pattern})
        (?:\s+({modifier_pattern}))?
        (?:\s*[-+&/]?\s*)?
        (?:\w+\s*){{0,4}}?
        (?P<qty2>\(?\d{{1,4}}\)?)
        (?:\s+(?P<suffix2>{suffix_pattern}))?

    |
        # Type with quantity in parentheses
        (?P<type3>{housing_pattern})
        (?:\s+\w+){{0,4}}?
        \(\s*(?P<qty3>\d{{1,4}})\s+(?P<suffix3>{suffix_pattern})\s*\)
    )
'''

    matches = re.finditer(match_pattern, description, flags=re.IGNORECASE | re.VERBOSE)

    result = []
    for match in matches:
        qty = match.group("qty") or match.group("qty2")
        raw_type = match.group("type") or match.group("type2")
        raw_mod = match.group(2)  # first modifier (position varies)
        raw_suffix = match.group("suffix") or match.group("suffix2")

        if not qty or not raw_type:
            continue  # skip malformed matches

        # normalize type
        norm_key = re.sub(r'[-\s]+', ' ', raw_type.lower()).strip()
        normalized_type = term_map.get(norm_key, norm_key)

        result.append((
            int(qty.strip("()")),
            raw_mod.lower() if raw_mod else None,
            normalized_type,
            raw_suffix.lower() if raw_suffix else None
        ))

    return result


# In[282]:


def fill_types(match_results):
    housing_types = ['sf_detached', 'sf_attached', 'duplex/triplex', 'multifamily', 'condo']
    housing_type_dict = {
        'townhouse': 'sf_attached',
        'home': 'sf_detached', 'single family': 'sf_detached',
        'duplex': 'duplex/triplex',
        'apartment': 'multifamily', 'multifamily': 'multifamily',
        'condo': 'condo'
    }

    row_data = {h_type: 0 for h_type in housing_types}
    for group in match_results:
        quantity = group[0]
        mod = group[1]
        housing = group[2]

        if housing == 'single family' and mod == 'attached':
            row_data['sf_attached'] += quantity
        elif housing in housing_type_dict:
            row_data[housing_type_dict[housing]] += quantity

    return pd.Series(row_data)


# In[283]:


durham_dev_filename = input('Please input the name of the Durham developments shapefile: ').strip()
res_cases_raw = gpd.read_file(f'../data/{durham_dev_filename}')
res_filtered = broad_filter(res_cases_raw)
res_filtered['match_results'] = res_filtered['A_DESCRIPT'].apply(extract_units)
housing_counts = res_filtered['match_results'].apply(fill_types)
filtered_final = pd.concat([res_filtered, housing_counts], axis=1)
filtered_final = filtered_final.to_crs(epsg = 3857)


# In[284]:


# read data from Data+_2025/data/enrollment_projections/sgr_table_region_2324_20240710.xlsx in Google Drive
'''
read in SGR data -- file paths: 
the current one is from 2024 July 10th, the file is already in data and is named sgr_tables_htype_reg.xlsx
'''
sgr_filename = input('Please enter the file name which includes the table of SGRs by housing type and region: ')
sgr_data = gpd.read_file(f'../data/{sgr_filename}')
sgr_data = sgr_data[sgr_data['region']!='']


# In[285]:


# remove null values and shorten to only use relevant columns
sgr_data.rename(columns={'sgr_dps_2324_all.1': 'sgr_dps_avg_k12'}, inplace=True) # because there might be a typo in the file?
sgr_data = sgr_data[['housing_type','region','sgr_dps_avg_k12']]
sgr_data['sgr_dps_avg_k12'] = sgr_data['sgr_dps_avg_k12'].round(4)
sgr_data.set_index(['region', 'housing_type'], inplace=True)
sgr_data['sgr_dps_avg_k12'] = pd.to_numeric(sgr_data['sgr_dps_avg_k12'],errors='coerce')


# In[286]:


'''
read in shapefile to get geometries for Durham County regions from Data+_2025/QGIS/DPS shapefiles from layers in Google Drive
'''
regions = gpd.read_file(r'../data/durham_regions.geojson')[['region', 'geometry']]
regions = regions.to_crs(epsg = 3857)


# In[287]:


filtered_final = filtered_final.copy()
for i,geometry in enumerate(regions['geometry']):
    in_geometry = geometry.contains(filtered_final['geometry'])

    region = regions.loc[i,'region']
    filtered_final.loc[in_geometry,'region'] = region


# In[288]:


# function to count number of students in each row
def count_students(row): 

    htype_map = {
        'sf_detached': 'sf_detach',
        'sf_attached': 'sf_attach',
        'duplex/triplex': 'du_tri',
        'multifamily': 'mf_apt',
        'condo': 'condo'
    }

    region = row['region']

    total = 0
    for col_name, sgr_col in htype_map.items():
        count = row.get(col_name, 0)

        try:
            multiplier = sgr_data.loc[(region, sgr_col), 'sgr_dps_avg_k12']
        except KeyError:
            multiplier = 0

        total += count * multiplier

    return total


# In[289]:


filtered_final['student_gen'] = filtered_final.apply(count_students, axis=1)


# In[290]:


filtered_final[['region', 'sf_detached', 'sf_attached', 'multifamily', 'student_gen','geometry']]


# In[291]:


#read in the planning units
pu_filename = input('Please input the geodataframe with all planning units: ')
dps_pu = gpd.read_file(f'../data/{pu_filename}').rename(columns={'pu_2324_848':'pu_2324_84'})
dps_pu = dps_pu.to_crs(epsg = 3857).sort_values(by='pu_2324_84')


# In[292]:


filtered_final = filtered_final.copy()
for i,geometry in enumerate(dps_pu['geometry']):
    in_geometry = geometry.contains(filtered_final['geometry'])
    pu = dps_pu.loc[i,'pu_2324_84']
    filtered_final.loc[in_geometry,'pu_2324_84'] = pu
filtered_final = filtered_final.groupby('pu_2324_84')['student_gen'].sum().round(0).astype(int)

full_index = pd.Index(range(1, 851), dtype=float)
filtered_final = filtered_final.reindex(full_index, fill_value=0)
filtered_final.index.name = 'pu_2324_84'


# In[293]:


#loading in the current enrollment for only the 2024-25 school year
enrollment_filename = input('Please enter the file name for the file with current enrollment by planning unit by year and grade: ')
current_enrollment = gpd.read_file(f'../data/{enrollment_filename}').rename(columns={'pu_2324_848':'pu_2324_84'})
current_enrollment = current_enrollment[['pu_2324_84','grade','fall_year','basez']].replace('', 0)


# In[294]:


school_type = input('Would you like to get the enrollment projections for elementary, middle, or high schools? Enter as es, ms, or hs: ')

if school_type == 'es':
    grades = [0,1,2,3,4,5]
elif school_type == 'ms':
    grades = [6,7,8]
elif school_type == 'hs':
    grades = [9,10,11,12]

current_enrollment['pu_2324_84'] = pd.to_numeric(current_enrollment['pu_2324_84'],errors ='coerce')
current_enrollment['grade'] = pd.to_numeric(current_enrollment['grade'],errors ='coerce')
current_enrollment['fall_year'] = pd.to_numeric(current_enrollment['fall_year'],errors ='coerce')
current_enrollment['basez'] =  pd.to_numeric(current_enrollment['basez'],errors ='coerce')

current_by_type = current_enrollment[
    (current_enrollment['grade'].isin(grades)) &
    (current_enrollment['fall_year'].isin([2022,2023,2024]))
     ]

averaged_by_type = current_by_type.groupby(['pu_2324_84','grade'],as_index=False).mean()
averaged_by_type = averaged_by_type.groupby(['pu_2324_84'],as_index=False).sum().drop(columns=['grade','fall_year'])

all_pus = pd.DataFrame({'pu_2324_84': range(1,852)})
full_basez = all_pus.merge(averaged_by_type, on='pu_2324_84',how='left').fillna(0)

full_basez.loc[773,'basez'] = full_basez.loc[773,'basez'] * 30.0/81.0
full_basez.loc[850,'basez'] = full_basez.loc[773,'basez'] * 51.0/81.0
full_basez[['basez']] = full_basez[['basez']].round(0).astype(int)
#full_basez


# In[295]:


full_geo = dps_pu.merge(full_basez, on = 'pu_2324_84')[['pu_2324_84'"",'Region','geometry','basez']]
full_geo = full_geo.merge(filtered_final,on='pu_2324_84')
full_geo


# In[298]:




# In[ ]:




