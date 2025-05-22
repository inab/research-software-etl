from collections import Counter
from datetime import datetime
from typing import List, Tuple, Dict, Any
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

'''
USAGE:
entries = [entry['data'] for entry in my_data_list]
licenses(entries, collection="my_stats_collection")
'''


def licenses_stats(entries: List[Dict[str, Any]], collection: str):
    """
    Computes license statistics and structures data for further use.
    """
    license_summary, count_unambiguous = count_tools_per_license(entries)
    
    licenses_summary_sunburst(
        license_summary=license_summary,
        count_unambiguous=count_unambiguous,
        collection=collection
    )
    
    licenses_open_source(
        count_unambiguous=count_unambiguous,
        collection=collection
    )

def map_license(name: str) -> str:
    name_lower = name.lower()
    if 'unlicensed' in name_lower or 'unknown' in name_lower or 'unlicense' in name_lower:
        return 'unlicensed'
    elif 'agpl' in name_lower or 'affero' in name_lower:
        return 'AGPL'
    elif 'lgpl' in name_lower:
        return 'LGPL'
    elif 'gpl' in name_lower or 'gnu' in name_lower:
        return 'GPL'
    elif 'artistic' in name_lower:
        return 'Artistic'
    elif 'mit' in name_lower:
        return 'MIT'
    elif 'apache' in name_lower:
        return 'Apache'
    elif 'bsd' in name_lower:
        return 'BSD'
    elif 'afl' in name_lower:
        return 'AFL'
    elif 'CC' in name or 'creative commons' in name_lower:
        return 'CC'
    elif 'creativecommons.org' in name_lower:
        return 'not-software'
    elif 'cecill' in name_lower:
        return 'CeCILL'
    else:
        return 'other'


def count_tools_per_license(tools: List[Dict[str, Any]]) -> Tuple[Dict[str, int], Dict[str, int]]:
    coincidental_lics = []
    conflicting_lics = []
    none = 0
    not_soft = 0
    n = 0
    c = 0

    for entry in tools:
        entry = entry.get('data', {})
        n += 1
        licenses = entry.get('license', [])
        if not licenses:
            none += 1
            continue

        mapped_licenses = set()
        for license_item in licenses:
            if not license_item or not license_item['name']:
                continue
            try:
                mapped = map_license(license_item['name'])
                mapped_licenses.add(mapped)
            except Exception as e:
                print(f"Mapping failed for license {license_item['name']}: {e}")
                raise

        if 'opeb_metrics' in entry.get('source', []) and 'not-software' in mapped_licenses:
            mapped_licenses.remove('not-software')

        if len(mapped_licenses) == 0:
            none += 1
        elif len(mapped_licenses) == 1 and 'unlicensed' in mapped_licenses:
            none += 1
        elif len(mapped_licenses) == 1:
            coincidental_lics.append(mapped_licenses)
        elif len(mapped_licenses) == 2 and 'unlicensed' in mapped_licenses:
            coincidental_lics.append(mapped_licenses)
        elif len(mapped_licenses) > 1:
            conflicting_lics.append(mapped_licenses)
        else:
            none += 1

    license_summary = {
        'Total': n,
        'None': none,
        'Unambiguous': len(coincidental_lics),
        'Ambiguous': len(conflicting_lics)
    }

    list_coinc = []
    for instance in coincidental_lics:
        for lic in instance:
            if lic != 'unlicensed':
                list_coinc.append(lic)
                break

    count_unambiguous = Counter(list_coinc)
    count_unambiguous = dict(count_unambiguous)
    count_unambiguous['Open Source'] = (
        len(list_coinc) - count_unambiguous.get('other', 0)
    )

    return license_summary, count_unambiguous


def licenses_summary_sunburst(license_summary: Dict[str, int], count_unambiguous: Dict[str, int], collection: str):
    licenses_parents = {
        'Total': '',
        'None': 'Total',
        'Unambiguous': 'Total',
        'Open Source': 'Unambiguous',
        'other': 'Unambiguous',
        'Ambiguous': 'Total',
    }

    licenses_text = licenses_parents.copy()

    licenses_ids = [
        k for k in licenses_parents
        if k in license_summary or k in count_unambiguous
    ]

    license_summary['Open Source'] = count_unambiguous.get('Open Source', 0)
    data = {
        'ids': licenses_ids,
        'parents': [licenses_parents[k] for k in licenses_ids],
        'v': [license_summary.get(k, count_unambiguous.get(k, 0)) for k in licenses_ids],
        'text': [licenses_text[k] for k in licenses_ids],
    }

    print(data)

    data_sunburst = {
        'variable': 'licenses_summary_sunburst',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': data,
        'collection': collection
    }

    mongo_adapter.insert_one("computationsDev", data_sunburst)


def licenses_open_source(count_unambiguous: Dict[str, int], collection: str):
    licences_ids = ['BSD', 'GPL', 'MIT', 'Artistic', 'LGPL', 'Apache', 'CC', 'AGPL', 'CeCILL', 'AFL']
    data = {k: count_unambiguous[k] for k in licences_ids if k in count_unambiguous}

    licenses_permissive_ids = ['Artistic', 'MIT', 'Apache', 'BSD']
    licenses_copyleft_ids = ['GPL', 'LGPL', 'AGPL', 'CeCILL']
    licenses_data_ids = ['CC']

    labs = {
        'Artistic': '<a href="https://opensource.org/licenses/artistic-license">Artistic</a>',
        'MIT': '<a href="https://opensource.org/licenses/MIT">MIT</a>',
        'Apache': '<a href="https://opensource.org/licenses/apachepl.php">Apache</a>',
        'BSD': '<a href="https://www.freebsd.org/doc/en_US.ISO8859-1/articles/bsdl-gpl/article.html">BSD</a>',
        'GPL': '<a href="https://www.gnu.org/licenses/gpl-3.0.html">GPL</a>',
        'AGPL': '<a href="https://www.gnu.org/licenses/agpl-3.0.html">AGPL</a>',
        'LGPL': '<a href="https://www.gnu.org/licenses/lgpl-3.0.html">LGPL</a>',
        'CeCILL': '<a href="https://spdx.org/licenses/CECILL-C.html">CeCILL-C</a>',
        'CC': '<a href="https://creativecommons.org/licenses/">CC</a>'
    }

    result_data = {
        'licenses_permissive': [k for k in licenses_permissive_ids if k in data],
        'counts_permissive': [data[k] for k in licenses_permissive_ids if k in data],
        'labs_permissive': [labs[k] for k in licenses_permissive_ids if k in data],
        'licenses_copyleft': [k for k in licenses_copyleft_ids if k in data],
        'counts_copyleft': [data[k] for k in licenses_copyleft_ids if k in data],
        'labs_copyleft': [labs[k] for k in licenses_copyleft_ids if k in data],
        'licenses_data': [k for k in licenses_data_ids if k in data],
        'counts_data': [data[k] for k in licenses_data_ids if k in data],
        'labs_data': [labs[k] for k in licenses_data_ids if k in data],
    }

    data_open_source = {
        'variable': 'licenses_open_source',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': result_data,
        'collection': collection
    }
    
    mongo_adapter.insert_one("computationsDev", data_open_source)


