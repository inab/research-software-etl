import pytest
from dotenv import load_dotenv
load_dotenv()
from src.application.use_cases.transformation.main import process_publications 

def test_process_publications_with_publications_biotools():
    entry = {
        '_id': 'biotools/genehub-gepis/web/None',
        '@last_updated_at': '2024-02-28T17:12:44.881Z',
        '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/commit/45aa662604db6427c289c97ac24cfba730b78f72',
        '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/pipelines/120779',
        'data': {
        '@timestamp': '2024-02-27T02:27:44.490333Z',
        'alt_ids': [],
        'confidence': 'ultimate',
        'contacts': [],
        'credits': [],
        'description': 'Tool for inferring human and mouse gene expression patterns based on normalized EST abundance in various normal and cancerous tissues.',
        'languages': [],
        'name': 'GeneHub-GEPIS',
        'os': [],
        'publications': [ { 'pmid': '15073007' }, { 'pmid': '17545196' } ],
        'repositories': [],
        'semantics': {
            'inputs': [],
            'operations': [
            'http://edamontology.org/operation_0313',
            'http://edamontology.org/operation_3463',
            'http://edamontology.org/operation_0314',
            'http://edamontology.org/operation_2495',
            'http://edamontology.org/operation_0315'
            ],
            'outputs': [],
            'topics': [
            'http://edamontology.org/topic_3512',
            'http://edamontology.org/topic_0203',
            'http://edamontology.org/topic_2640',
            'http://edamontology.org/topic_2815',
            'http://edamontology.org/topic_3337'
            ]
        },
        'tags': [],
        'validated': 1,
        'web': {
            'homepage': 'http://www.cgl.ucsf.edu/Research/genentech/genehub-gepis/'
        },
        '@id': 'https://openebench.bsc.es/monitor/tool/biotools:genehub-gepis/web/www.cgl.ucsf.edu',
        '@nmsp': 'biotools',
        '@type': 'web',
        '@label': 'genehub-gepis',
        '@version': None,
        '@license': 'https://creativecommons.org/licenses/by/4.0/',
        '@data_source': 'biotools',
        '@source_url': 'https://openebench.bsc.es/monitor/tool/biotools:genehub-gepis/web/www.cgl.ucsf.edu'
        },
        '@data_source': 'biotools',
        '@created_at': '2024-02-28T17:01:16.918Z',
        '@created_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/commit/e2b685b10889a328a0d038d4fca92f5306a20736',
        '@created_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/pipelines/120778'
    }
    source = "biotools"
    result = process_publications(entry, source)
    print(f"Resulting IDs: {result}")
    assert len(result) > 0




def test_process_publications_with_publications_bioconda_recipes():
    entry = {
        '_id': 'bioconda_recipes/bioconductor-genomicfiles/lib/1.38.0',
        '@last_updated_at': '2024-08-12T20:56:31.175Z',
        '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/biconda-importer/-/commit/7e2de24b5140b991f1aa4e288aae9298c01c03c8',
        '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/biconda-importer/-/pipelines/152332',
        'data': {
        'package': { 'name': 'bioconductor-genomicfiles', 'version': '1.38.0' },
        'source': {
            'url': [
            'https://bioconductor.org/packages/3.18/bioc/src/contrib/GenomicFiles_1.38.0.tar.gz',
            'https://bioconductor.org/packages/3.18/bioc/src/contrib/Archive/GenomicFiles/GenomicFiles_1.38.0.tar.gz',
            'https://bioarchive.galaxyproject.org/GenomicFiles_1.38.0.tar.gz',
            'https://depot.galaxyproject.org/software/bioconductor-genomicfiles/bioconductor-genomicfiles_1.38.0_src_all.tar.gz'
            ],
            'md5': '7a58dc35c19ed34afe95d505d15db3f4'
        },
        'build': {
            'number': '0',
            'rpaths': [ 'lib/R/lib/', 'lib/' ],
            'run_exports': '',
            'noarch': 'generic'
        },
        'requirements': {
            'host': [
            'bioconductor-biocgenerics >=0.48.0,<0.49.0',
            'bioconductor-biocparallel >=1.36.0,<1.37.0',
            'bioconductor-genomeinfodb >=1.38.0,<1.39.0',
            'bioconductor-genomicalignments >=1.38.0,<1.39.0',
            'bioconductor-genomicranges >=1.54.0,<1.55.0',
            'bioconductor-iranges >=2.36.0,<2.37.0',
            'bioconductor-matrixgenerics >=1.14.0,<1.15.0',
            'bioconductor-rsamtools >=2.18.0,<2.19.0',
            'bioconductor-rtracklayer >=1.62.0,<1.63.0',
            'bioconductor-s4vectors >=0.40.0,<0.41.0',
            'bioconductor-summarizedexperiment >=1.32.0,<1.33.0',
            'bioconductor-variantannotation >=1.48.0,<1.49.0',
            'r-base'
            ],
            'run': [
            'bioconductor-biocgenerics >=0.48.0,<0.49.0',
            'bioconductor-biocparallel >=1.36.0,<1.37.0',
            'bioconductor-genomeinfodb >=1.38.0,<1.39.0',
            'bioconductor-genomicalignments >=1.38.0,<1.39.0',
            'bioconductor-genomicranges >=1.54.0,<1.55.0',
            'bioconductor-iranges >=2.36.0,<2.37.0',
            'bioconductor-matrixgenerics >=1.14.0,<1.15.0',
            'bioconductor-rsamtools >=2.18.0,<2.19.0',
            'bioconductor-rtracklayer >=1.62.0,<1.63.0',
            'bioconductor-s4vectors >=0.40.0,<0.41.0',
            'bioconductor-summarizedexperiment >=1.32.0,<1.33.0',
            'bioconductor-variantannotation >=1.48.0,<1.49.0',
            'r-base'
            ]
        },
        'test': { 'commands': [ '`$R -e "library(GenomicFiles)"`' ] },
        'about': {
            'home': 'https://bioconductor.org/packages/3.18/bioc/html/GenomicFiles.html',
            'license': 'Artistic-2.0',
            'summary': 'Distributed computing by file or by range',
            'description': "This package provides infrastructure for parallel computations distributed 'by file' or 'by range'. User defined MAPPER and REDUCER functions provide added flexibility for data combination and manipulation."
        },
        'extra': {
            'identifiers': [ 'biotools:genomicfiles', 'doi:10.1038/nmeth.3252' ],
            'parent_recipe': {
            'name': 'bioconductor-genomicfiles',
            'path': 'recipes/bioconductor-genomicfiles',
            'version': '1.16.0'
            }
        },
        'name': 'bioconductor-genomicfiles',
        'version': '1.38.0',
        '@type': 'lib'
        },
        '@data_source': 'bioconda_recipes',
        '@created_at': '2024-02-28T15:34:12.909Z',
        '@created_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/biconda-importer/-/commit/96e7639eab516a89f6a7ddece0252c16aef1491f',
        '@created_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/biconda-importer/-/pipelines/120716'
    }
    source = "bioconda_recipes"
    result = process_publications(entry, source)
    print(f"Resulting IDs: {result}")
    assert len(result) > 0