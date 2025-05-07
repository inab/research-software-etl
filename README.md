# Software metadata extraction, consolidation and evaluation

> :warning: under development. 
> Currently restructuring the whole project to align it with a clean architecture and to make it more modular and scalable.

We have developed a pipeline to **gather metadata about research software specific** to Computational Biology, **harmonize** and **integrate** it and to then be able to monitor certain features and **evaluate** their compliance with ** FAIRsoft indicators**.  [*FAIRsoft*](https://github.com/inab/FAIRsoft_indicators) are a set of research software *FAIRness* indicators, specifically devised to be assesed automatically. 

**This repository** contains the code for:

- Harmonization of raw metadata.
- Integration of pieces of metadata belonging to the same software: `integration` use case.
- Calculation of *FAIRsoft* indicators compliance and FAIRsoft scores.
- Evaluation of language models for software identity resolution.


The code for the **previos steps** can be found in the respotories specified as follows:

- Data extraction: each importer, which is responsible for extracting metadata from a specific source, has a repository of its own:
  - [Bioconda importer](https://gitlab.bsc.es/inb/elixir/software-observatory/bioconda-importer)
  - [Bioconductor importer](https://gitlab.bsc.es/inb/elixir/software-observatory/bioconductor-importer)
  - [Galaxy Toolshed importer](https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-importer)
  - [OpenEBench tools importer](https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer)
  - [OpenEBench metrics importer](https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-metrics-importer)
  - [Sourceforge importer](https://gitlab.bsc.es/inb/elixir/software-observatory/sourceforge-importer)
  - [Repositories importer](https://gitlab.bsc.es/inb/elixir/software-observatory/respositories-importer) 


## Installation 

Install the dependencies 

```
pip install -r requirements.txt
```


## Usage 

### Data transformation
This is one [use case](/src/application/use_cases/transformation/) and can be executed from the [CLI](/src/adapters/cli/transformation.py) in the following way:

```
python3 src/adapters/cli/transformation.py -l INFO
```


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
