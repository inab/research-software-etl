# Software metadata extraction, consolidation and evaluation

> :warning: This branch is under development. 
> Its purpose is to restructure the whole project to align it with a clean architecture and to make it more modular and scalable.

We have developed a pipeline to **gather metadata about research software specific** to Computational Biology, **harmonize** and **integrate** it and to then be able to monitor certain features and **evaluate** their compliance with ** FAIRsoft indicators**.  [*FAIRsoft*](https://github.com/inab/FAIRsoft_indicators) are a set of research software *FAIRness* indicators, specifically devised to be assesed automatically. 

The code for the previos steps can be found in the respotories specified as follows:

- Data extraction: each importer, which is responsible for extracting metadata from a specific source, has a repository of its own:
  - [Bioconda importer](https://gitlab.bsc.es/inb/elixir/software-observatory/bioconda-importer)
  - [Bioconductor importer](https://gitlab.bsc.es/inb/elixir/software-observatory/bioconductor-importer)
  - [Galaxy Toolshed importer](https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-importer)
  - [OpenEBench tools importer](https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer)
  - [OpenEBench metrics importer](https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-metrics-importer)
  - [Sourceforge importer](https://gitlab.bsc.es/inb/elixir/software-observatory/sourceforge-importer)
  - [Repositories importer](https://gitlab.bsc.es/inb/elixir/software-observatory/respositories-importer) 

  > :exclamation: Given the complexity of the installation of the requirements of some of the importers, it is highly recommended to use the dockerized version of the different importers (in `registry.bsc.es/inb/elixir/software-observatory/`). 

- Harmonization of raw metadata: part of *FAIRsoft* package.
- Integration of pieces of metadata belonging to the same software: part of *FAIRsoft* package.
- Calculation of *FAIRsoft* indicators compliance and FAIRsoft scores: part of *FAIRsoft* package.


## Data storage
During the whole process, metadata is stored in a Mongo Database (INB Mongo `oeb-research-software`). The database connection is configured through environment variables. 

:construction:

: **TODO**: add diagram of collections.

## Data Obatained from each source


### SourceForge

| Attribute | Origin |
| --- | --- |
| name |  |
| label |  |
| description |  |
| operating_system |  |
| repository | |
| webpage |  |
| download |  |
| license |  |

### Repositories

| Attribute | Origin |
| --- | --- |
| name |  |
| version |  |
| type |  |
| download  |  |
| repository |  |
| webpage |  |
| description |  |
| source_code |  |
| language |  |
| inst_instr |  |
| authors |  |
| license |  |



### Toolshed 

| Attribute | Origin |
| --- | --- |
| name |  |
| version |  |
| type |  |
| label |  |
| dependencies |  |

| Attribute | Origin |
| --- | --- |
| name |  |
| version |  |
| type |  |
| label |  |
| description |  |
| publication | |
| documentation | |
| operating_system | |
| test | |
| input | |
| output | |

### Bioconductor 

| Attribute | Origin |
| --- | --- |
| name |  |
| version |  |
| type |  |
| label |  |
| description |  |
| webape | |
| publication | |
| download | |
| source_code | |
| operating_system | |
| license | |
| dependencies | |
| authors | |
| repository | |
| documentation | |

### Bioconda Recipes 

| Attribute | Origin |
| --- | --- |
| name |  |
| version |  |
| type |  |
| label |  |
| description |  |
| webape | |
| source_code | |
| documentation | |
| repository | |
| operating_system | |
| license | |
| publication | |
| dependencies | |
| authors | |
| test | | 

### Galaxy EU

| Attribute | Origin |
| --- | --- |


### Bio.tools 

| Attribute | Origin |
| --- | --- |

