# FAIRsoft 

Library for the aggregation of Life Sciences software metadata and FAIR evaluation.


## Installation 
Install using [pip](https://pip.pypa.io/en/stable/):
```
pip install FAIRsoft
``` 

## Usage 

Configuration is done through environment variables. Those refering to the database where extracted and/or proccessd software metadata is stored are: 

| Name             | Description | Default | Notes |
|------------------|-------------|---------|-------|
| MONGO_HOST       |  Host of database where output will be pushed |   `localhost`        | |
| MONGO_PORT       |  Port of database where output will be pushed |   `27017`            | |
| MONGO_DB         |  Name of database where output will be pushed |   `observatory`      | |
| MONGO_USER       |  User of database where output will be pushed |   `observatory`      | |
| MONGO_PWD   |  Password of database where output will be pushed |   `observatory`      | |
| MONGO_AUTH_SRC   |  Authentication source of database where output will be pushed |   `observatory`      | |
| ALAMBIQUE |  Name of collection where importers output will be stored  |   `alambique`        | Needed for importation only |
| LICENSES_COLLECTION | Name of collection where licenses are stored | `licenses` | Needed for importation only |

| PRETOOLS      |  Name of collection where output of transformation step (harmonized version of data in ALAMBIQUE collection) will be pushed. It is also the collection from which the following step, integration, will use as source of input data |   `pretools`    | Needed for transformation and integration |
| TOOLS      |  Name of collection where output of integration  will be stored. This is the final collection os the porccess. Thus, it is the collection that can be use for the evaluation of FAIRness, calculation of statictics, etc |   `tools`        |  Needed for integration  |

## Data transformation 

Data transformation requires the environment variables DBHOST, DBPORT, DB, ALAMBIQUE and PRETOOLS (previously explained) to be set.

Execute the following command to transform data: 

```sh
FAIRsoft_transform --env-file=[env-file] -l=[log-level]
``` 
- `-e`/`--env-file` is optional. It specifies the path to the file containing the environment variables. Default is `.env`.
- `-l`/`--loglevel` is optional. It can be `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Default is `INFO`.

## Data integration
Data integration requires the environment variables DBHOST, DBPORT, DB, PRETOOLS and TOOLS (previously explained) to be set.

Execute the following command to integrate data: 

```sh
FAIRsoft_integrate --env-file=[env-file] -l=[log-level]
```
- `-e`/`--env-file` is optional. It specifies the path to the file containing the environment variables. Default is `.env`.
- `-l`/`--loglevel` is optional. It can be `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Default is `INFO`.

### FAIRsoft indicators evaluation 
FAIRness indicators evaluation requires the environment variables DBHOST, DBPORT, DB and TOOLS (previously explained) to be set. 
Additionally, FAIR is required: 
| Name             | Description | Default | Notes |
|------------------|-------------|---------|-------|
| FAIR | Name of collection where FAIRness indicators will be stored | `fair` | | 

To run the evaluation use: 

```sh
FAIRsoft_indicators_evaluation --env-file=[env-file] -l=[log-level]
```