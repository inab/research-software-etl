# Welcome

This is the documentation of the data processing backbone of the [Research Software Observatory](https://openebench.bsc.es/observatory/), supporting large-scale monitoring of software FAIRness in the life sciences.


The pipeline consolidates and harmonizes metadata from multiple registries and repositories, enriches it with external information, and pre-computes the FAIRsoft indicators and other metrics displayed in the Software Observatory interface.  

!!! note "At a glance"
    **Language:** Python ≥ 3.9 (tested on 3.10)  
    **Execution:** CLI (`rsetl`)  
    **Dependencies:** `pydantic`, `tenacity`, `pymongo`, ... (see [more](https://github.com/inab/research-software-etl/blob/main/requirements.txt))  
    **Database:** MongoDB  
    **Main stages:**  Transformation → Enrichment (in parallel) → Integration → Evaluation  
    **Enrichment sub-pipelines:**  SPDX · EDAM · Publications · Service availability  
    **Maintained by:** [Spanish National Bioinformatics Institute](https://github.com/inab)

## Quickstart 

Clone and install: 

```bash
git clone https://github.com/inab/research-software-etl.git
cd research-software-etl
pip install -e .
```

Each execution can run as a single stage or as part of the full workflow through the unified CLI command `rsetl`:

```bash
rsetl run
```  

Use `rsetl --help` or go to the CLI [docs](cli.md) for more information. 


##  Next steps

- [Installation & Configuration](installation.md) – Set up the environment and dependencies.
- [Main Pipeline Stages](pipeline.md) – Detailed description of each processing step.
- [Development Guide](development.md) – Learn the project’s structure and how to extend it.
- [CLI reference](cli.md) - Learn how to run the pipeline


--- 

<p align="right"><b>Next step</b> → <a href="installation/">Installation & Configuration</a></p>
