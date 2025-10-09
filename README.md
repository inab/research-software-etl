# Software metadata extraction, consolidation and evaluation

Pipeline to **gather metadata about research software specific** to Life Sciences, **harmonize** and **integrate** it and to then be able to monitor certain features and **evaluate** their compliance with [*FAIRsoft*](https://github.com/inab/FAIRsoft_indicators) indicators, set of research software *FAIRness* indicators, specifically devised to be assesed automatically. 

**This repository** contains the code for:

- Normalization of raw metadata to a common data model.
- Enrichment of metadata.
  - SPDX license mapping.
  - EDAM format normalization.
  - Contributor classification.
  - Harvesting of auxiliary metadata on publications from Europe PMC and Semantic Scholar.
- Integration of pieces of metadata belonging to the same software. This involves blcoking, conflict identification, disambiguation and merging of blocks.
- Calculation of FAIRsoft indicators compliance and FAIRsoft scores.
- Calculation of statistcs on several aspects of software in the dataset.


The code for the **previos steps** can be found in the respotories specified as follows:

- Data extraction: each importer, which is responsible for extracting metadata from a specific source, has a repository of its own:
  - [Bioconda importer](https://gitlab.bsc.es/inb/elixir/software-observatory/bioconda-importer)
  - [Bioconductor importer](https://gitlab.bsc.es/inb/elixir/software-observatory/bioconductor-importer)
  - [Galaxy Toolshed importer](https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-importer)
  - [OpenEBench tools importer](https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer)
  - [OpenEBench metrics importer](https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-metrics-importer)
  - [Sourceforge importer](https://gitlab.bsc.es/inb/elixir/software-observatory/sourceforge-importer)
  - [GitHub importer](https://github.com/inab/github-importer) 


## Installation 

Install the dependencies 

```
pip install -r requirements.txt
```


## Usage 

### Data transformation 

This step transform the metadata from different sources into the model described in `domain.models.software_instance.instace`. The records pushed to the datase are of the form of `domain.models.software_instance.database_entries.PretoolsEntryModel`.  

In addition, publication metadata is pulled into a different database collection specific of publications (of the form `domain.models.publication.publication.Publication`). The entries pushed follow the form `domain.models.software_instance.database_entries.PublicationEntryModel`.

This step can be executed from the [CLI](/src/adapters/cli/transformation.py) in the following way:

```
python3 src/adapters/cli/transformation.py -l INFO
```

Example of real script for this step: `scripts/transformation/transform_bioconductor.sh`. 


### Publications enrichment

This step adds metadata from Europe PMC and Semantic Scholar to the records in the publications database collection. The specific script to run the enrichment is `aplication/services/enrich_publications/enrich.py`. Details fior databse connection must be stored in environment variables: MONGO_HOST, MONGO_PORT, MONGO_USER, MONGO_PWD, MONGO_AUTH_SRC, MONGO_DB. 


### Data integration 

Full integration requires the execution of the following steps: 

1. Blocking.
  - Script: `adapters/cli/integration/group_and_recovery.py`
  - Example of script of real execution: `scripts/group_and_recovery.sh`.
  - This step performs the blocking of records (see `blocking_criteria.md` for details on blocking). 
  - And additional "recovery" step is performed. It consists in the merging of blocks with shared links of any kind and same name.
  - See example for complete script used to run this use case: `conflict_detection.sh`
  - Normalized data is pulled from the database, connection details must be stored in enviroment variables. 
    - MONGO_HOST, MONGO_PORT, MONGO_USER, MONGO_PWD, MONGO_AUTH_SRC, MONGO_DB
  - Blocks are stored in a file (`--grouped-entries-file`)

2. Removal of useless records (optional). 
  - Script: `scripts/remove_opeb_metrics.py` 
  - This step removes records from OpenEBench "metrics". This step is not necessary but speeds up the pocess. 
  - Why removing these records? Becasue these records are very numerous but provide no information, since their value lies in the publications data, that is saved in a difeferent database collection at the normalization step. These records remain as part as the dataset for *historical* reasons and should be removed from the normalized dataset in future development. 
  - Input and output paths are hardcoded in the script. Manually modify it to process the correct file of blocks and output to the desired path.

3. Conflict detection 
  - Script: `adapters/cli/integration/conflict_detection.py`
  - Example of script of real execution: `scripts/conflict_detection.sh`.
  - Potentially wrong blocks using the criteria in `conflict_detection.md`
  - This steps generates a file of conflicts to be disambiguate in next steps. 

4. Simplification of blocks.
  - Script: `script/simplify_grouped_entries.py`
  - Modify the script to process your bocks file. 
  - This step is needed to prepare the blocks file for next steps. 
  - This step will be incorporated in the blocking step in future developments.

5. Convert to JSONL.
  - Script: `script/json_to_jsonl.py`
  - Modify the script to process your files. 
  - Files that need conversion are: 
    - conflicts
    - simplified blocks
  - This step will be incorporated in the appropriate steps in future developments.

6. Disambiguation.
  - Script: `adapters/cli/integration/disambiguation.py`
  - Example of script of real execution: `script/disambiguation.sh`.
  - In this step, the conflicts identified in the previous "conflict detection" stage are resolved through a combination of automated and manual procedures.
  - A rescue heuristic is first applied to reduce false positives in the conflict set. Records initially marked as disconnected are re-evaluated, and those sharing both a name and source (e.g., registry) with an accepted group member are merged. This step enables the recovery of plausible matches that lack repository links but are likely to refer to the same software based on consistent naming and metadata fields.
  - After refinement, the remaining conflicts are processed using a hybrid resolution approach. A large language model-based agreement proxy is employed to assess the semantic similarity of metadata fields, README content, and associated webpages.
  - Conflicts automatically resolved by the model are marked as completed, while ambiguous cases are escalated to human reviewers through structured GitHub issues. This ensures transparent decision-making and integration through GitHub Actions.
  - This step requires GitHub and Gitlab tokens as well as OpenRouter and HuggingFace API keys. These are provided as enviroment variables.
    - GITHUB_TOKEN, GITLAB_TOKEN, OPENROUTER_API_KEY and HUGGINGFACE_API_KEY

7. Add human disambiguation. 
  - Script: `adapters/cli/integration/update_disambiguation_after_human_resoltion.py`
  - Pull from git before running this step so `human_annotations/human_conflicts_log.jsonl` is updated eith annotators decisions.
  - Example of script of real execution: `scripts/update_disambiguation_after_human_resoltion.sh`.

8. Merge.
  - Script: `adapters/cli/integration/merge_entries.py`
  - Example of script of real execution: `script/merge_entries.sh`
  - Records in blocks are merged and pushed to the database. Records pushed to the database are of the form of `domain.models.software_instance.database_entries.ToolsEntryModel`.


## Data storage
During the whole process, metadata is stored in a Mongo Database (INB Mongo `oeb-research-software`). The database connection is configured through environment variables. 

## Development 

### Testing 

To run tests, go to the root directory of this repository and use:

```bash
PYTHONPATH=$(pwd) pytest -v -s tests/
``` 

The previous command will run all tests except the ones marked as "manual". To run tests marked as "manual" use: 

```bash
PYTHONPATH=$(pwd) pytest -v -s -m manual tests/
```


### Logging 

To add loggings, use:

```python
import logging 

logger = logging.getLogger("rs-etl-pipeline")
```

The logger configuration can be found in `src/infrastructure/logging_config.py`. `INFO` logs are writen to terminal and all the rest to a file (`re_etl_pipeline.log`)
