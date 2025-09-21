import pandas as pd
import re
import numpy as np

def normalize_for_regex(term):
    return re.sub(r'[-\s]+', r'\\s*-?\\s*', term)

def extract_units(description):
    if pd.isna(description) or description == '':
        return []

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

def filter_excel():

    df = pd.read_excel('../data/parcels_20250730_wDevs_working.xlsx', sheet_name='Parcels_4TableJoin')

    # only filter developments with descriptions to analyze
    has_description = df['description'].notna() & (df['description'] != '')
    df_with_desc = df[has_description].copy()

    df_with_desc['match_results'] = df_with_desc['description'].apply(extract_units)
    housing_counts = df_with_desc['match_results'].apply(fill_types)

    # add housing counts to dataframe
    filtered_final = pd.concat([df_with_desc, housing_counts], axis=1)

    housing_types = ['sf_detached', 'sf_attached', 'duplex/triplex', 'multifamily', 'condo']
    totals = {}

    for h_type in housing_types:
        total = filtered_final[h_type].sum()
        developments_with_type = (filtered_final[h_type] > 0).sum()
        totals[h_type] = {
            'total_units': int(total),
            'developments': int(developments_with_type)
        }

    total_units = sum(totals[h_type]['total_units'] for h_type in housing_types)

    output_cols = ['REID', 'Case_Number', 'project_name', 'description'] + housing_types
    output_df = filtered_final[output_cols].copy()

    has_housing = filtered_final[housing_types].sum(axis=1) > 0
    housing_developments = output_df[has_housing].copy()

    housing_developments.to_csv('../outputs/Residential Filter/resdev_itre.csv', index=False)

    return totals, housing_developments


def main():

    excel_totals, detailed_df = filter_excel()

if __name__ == "__main__":
    main()