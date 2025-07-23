import pandas as pd
import geopandas as gpd
import numpy as np
import re

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


def normalize_for_regex(term):
    # makes it so string returns a match whether a term has spaces, dashes, both, or neither
    return re.sub(r'[-\s]+', r'\\s*-?\\s*', term)

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

# function to fill in housing type columns in residential development dataframe
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


def main():
    filepath = input('Please input the name of Durham developments shapefile: ').strip() # use durham_developments from data folder
    res_cases_raw = gpd.read_file(f'../data/{filepath}')

    res_filtered = broad_filter(res_cases_raw)
    res_filtered['match_results'] = res_filtered['A_DESCRIPT'].apply(extract_units)
    housing_counts = res_filtered['match_results'].apply(fill_types)

    filtered_final = pd.concat([res_filtered, housing_counts], axis=1)
    filtered_final = res_filtered.to_crs('EPSG:4326')
    filtered_final.to_file('resdev_filtered.geojson', driver='GeoJSON')
    print("Finished processing. Output saved to 'resdev_filtered.geojson'.")

if __name__ == "__main__":
    main()