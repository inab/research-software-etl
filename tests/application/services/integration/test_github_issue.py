import json
import random
import pytest
from pprint import pprint
from src.application.services.integration.disambiguation.issues import generate_context, generate_github_issue

from tests.application.services.integration.data.data_disambiguation_original import conflicts_blocks_sets

with open('tests/application/services/integration/data/grouped_entries_no_opeb_test.json') as f:
    blocks = json.load(f)


full_conflict ={
    "disconnected": [
        {
            "id": "bioconda_recipes/ale/cmd/20180904",
            "name": "ale",
            "description": [
                "ALE: Assembly Likelihood Estimator."
            ],
            "repository": [
                {
                    "url": "https://github.com/sc932/ALE",
                    "kind": "github",
                    "source_hasAnonymousAccess": None,
                    "source_isDownloadRegistered": None,
                    "source_isFree": None,
                    "source_isRepoAccessible": None
                }
            ],
            "webpage": [
                "https://github.com/sc932/ALE"
            ],
            "source": [
                "bioconda_recipes"
            ],
            "license": [
                {
                    "name": "NCSA",
                    "url": "https://spdx.org/licenses/NCSA.html"
                }
            ],
            "authors": [],
            "publication": [],
            "documentation": [
                {
                    "type": "installation_instructions",
                    "url": "https://bioconda.github.io/recipes/ale/README.html",
                    "content": None
                },
                {
                    "type": "general",
                    "url": "https://bioconda.github.io/recipes/ale/README.html",
                    "content": None
                }
            ]
        }
    ],
    "remaining": [
        {
            "id": "biotools/ale/cmd/None",
            "name": "ale",
            "description": [
                "Automated label extraction from GEO metadata."
            ],
            "repository": [],
            "webpage": [
                "https://github.com/wrenlab/label-extraction"
            ],
            "source": [
                "biotools"
            ],
            "license": [],
            "authors": [
                {
                    "type": "Person",
                    "name": "Jonathan D. Wren",
                    "email": "jonathan-wren@omrf.org",
                    "maintainer": False,
                    "url": None,
                    "orcid": None
                },
                {
                    "type": "Person",
                    "name": "Jonathan D. Wren",
                    "email": "jdwren@gmail.com",
                    "maintainer": False,
                    "url": None,
                    "orcid": None
                }
            ],
            "publication": [
                {
                    "$oid": "67c7a9b6d3b8acd1a2f9bb26"
                }
            ],
            "documentation": [
                {
                    "type": "general",
                    "url": "https://github.com/wrenlab/label-extraction/blob/master/README.md",
                    "content": None
                }
            ]
        }
    ],
    "webpage_contents": {
        "https://github.com/wrenlab/label-extraction": {
            "README content": [
                "## ALE CLI - Automated Label Extraction Command Line Interface Tools to extract and validate labels using wrenlab's ALE. Gold standard for validation is Wrenlab's JDW manual annotations. ## REQUIREMENTS - [wrenlab](https://gitlab.com/wrenlab/wrenlab) - [metalearn](https://gitlab.com/wrenlab/metalearn) - [click](https://pypi.python.org/pypi/click) ## INSTALL python setup.py develop --user ## USAGE The following scripts should be in your $PATH and accessible from your shell ``` ale ale-validation ``` ale extracts labels from GEO. ale-validation evaluates performance against the Wrenlab gold standard for GEO data for human data (NCBI Taxon ID 9606)."
            ],
            "Repository metadata": {
                "name": "label-extraction",
                "label": [
                    "label-extraction"
                ],
                "description": [
                    "ALE Label Extraction Data and CLI Tools"
                ],
                "links": [],
                "webpage": [],
                "isDisabled": False,
                "isEmpty": False,
                "isLocked": False,
                "isPrivate": False,
                "isTemplate": False,
                "version": [],
                "license": [],
                "repository": [
                    "https://github.com/wrenlab/label-extraction"
                ],
                "topics": [],
                "operations": [],
                "authors": [
                    {
                        "name": "Cory Giles",
                        "type": "person",
                        "email": "mail@corygil.es",
                        "maintainer": False
                    },
                    {
                        "name": "Xiavan",
                        "type": "person",
                        "email": "xiavan-roopnarinesingh@omrf.org",
                        "maintainer": False
                    }
                ],
                "bioschemas": False,
                "contribPolicy": [],
                "dependencies": [],
                "documentation": [
                    {
                        "type": "readme",
                        "url": "https://github.com/wrenlab/label-extraction/blob/main/README.md"
                    }
                ],
                "download": [],
                "edam_operations": [],
                "edam_topics": [],
                "https": True,
                "input": [],
                "inst_instr": False,
                "operational": False,
                "os": [],
                "output": [],
                "publication": [],
                "semantics": {
                    "inputs": [],
                    "outputs": [],
                    "topics": [],
                    "operations": []
                },
                "source": [
                    "github"
                ],
                "src": [],
                "ssl": True,
                "tags": [],
                "test": [],
                "type": ""
            }
        },
        "https://github.com/sc932/ALE": {
            "README content": [
                "DOCUMENTATION ------------- http://portal.nersc.gov/dna/RD/Adv-Seq/ALE-doc/ This code is no longer in active development. Pull requests and bugs will be addressed as needed. Plotting -------- The authors recommend using IGV to view the output. http://www.broadinstitute.org/igv/ Just import the assembly, bam and ALE scores. You can convert the .ale file to a set of .wig files with ale2wiggle.py and IGV can read those directly. Depending on your genome size you may want to convert the .wig files to the BigWig format. LICENSE ------- /* * Copyright (C) 2010,2011,2012 Scott Clark. All rights reserved. * * Developed by: * Scott Clark * Cornell University Center for Applied Mathematics * http://cam.cornell.edu * AND * Rob Egan * Department of Energy Joint Genome Institute * http://jgi.doe.gov * * Permission is hereby granted, free of charge, to any person obtaining a * copy of this software and associated documentation files (the 'Software'), * to deal with the Software without restriction, including without limitation * the rights to use, copy, modify, merge, publish, distribute, sublicense, * and/or sell copies of the Software, and to permit persons to whom the * Software is furnished to do so, subject to the following conditions: * * 1. Redistributions of source code must retain the above copyright notice, * this list of conditions and the following disclaimers. * 2. Redistributions in binary form must reproduce the above copyright * notice, this list of conditions and the following disclaimers in the * documentation and/or other materials provided with the distribution. * 3. Neither the names of Cornell University, The Joint Genome Institute, * nor the names of its contributors may be used to endorse or promote * products derived from this Software without specific prior written * permission. * * THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE * CONTRIBUTORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER * DEALINGS WITH THE SOFTWARE. */ // For more information on the licence please see // The University of Illinois/NCSA Open Source License // http://www.opensource.org/licenses/UoI-NCSA.php INSTALL ------- http://portal.nersc.gov/dna/RD/Adv-Seq/ALE-doc/index.html#installation # # ALE comes packaged with samtools-0.1.18 Feel free to use a later version # samtools is open source (MIT license) # We would like to thank the creators for the extensive and very useful package # Requirements for plotter4.py: numpy 1.6.1 mpmath 0.17 setuptools 0.6c11 matplotlib 1.0.1 pymix 0.8 http://www.pymix.org/pymix/"
            ],
            "Repository metadata": {
                "name": "ALE",
                "label": [
                    "ALE"
                ],
                "description": [
                    "Assembly Likelihood Estimator"
                ],
                "links": [],
                "webpage": [
                    ""
                ],
                "isDisabled": False,
                "isEmpty": False,
                "isLocked": False,
                "isPrivate": False,
                "isTemplate": False,
                "version": [],
                "license": [
                    {
                        "name": "Other",
                        "url": "http://choosealicense.com/licenses/other/"
                    }
                ],
                "repository": [
                    "https://github.com/sc932/ALE"
                ],
                "topics": [],
                "operations": [],
                "authors": [
                    {
                        "name": "Rob Egan",
                        "type": "person",
                        "email": "rsegan@lbl.gov",
                        "maintainer": False
                    },
                    {
                        "name": "Eric  DEVEAUD",
                        "type": "person",
                        "email": "edeveaud@pasteur.fr",
                        "maintainer": False
                    },
                    {
                        "name": "Alexander Regueiro",
                        "type": "person",
                        "email": "alexreg@gmail.com",
                        "maintainer": False
                    },
                    {
                        "name": "Rob Egan",
                        "type": "person",
                        "email": "RSEgan@lbl.gov",
                        "maintainer": False
                    },
                    {
                        "name": "Rob Egan",
                        "type": "person",
                        "email": "github-rob@egannetworks.com",
                        "maintainer": False
                    },
                    {
                        "name": "holmrenser",
                        "type": "person",
                        "email": "rens.holmer@wur.nl",
                        "maintainer": False
                    },
                    {
                        "name": "Scott Clark",
                        "type": "person",
                        "email": "scott@scottclark.io",
                        "maintainer": False
                    },
                    {
                        "name": "Rob Egan",
                        "type": "person",
                        "email": "genepool1.nersc.gov",
                        "maintainer": False
                    },
                    {
                        "name": "Rob Egan",
                        "type": "person",
                        "email": "genepool02.nersc.gov",
                        "maintainer": False
                    },
                    {
                        "name": "Rob Egan",
                        "type": "person",
                        "email": "regan@phoebe.nersc.gov",
                        "maintainer": False
                    },
                    {
                        "name": "Rob Egan",
                        "type": "person",
                        "email": "regan@genepool04.nersc.gov",
                        "maintainer": False
                    },
                    {
                        "name": "Rob Egan",
                        "type": "person",
                        "email": "regan@dakar.jgi-psf.org",
                        "maintainer": False
                    },
                    {
                        "name": "Rob Egan",
                        "type": "person",
                        "email": "regan@regan2.local",
                        "maintainer": False
                    },
                    {
                        "name": "Scott Clark",
                        "type": "person",
                        "email": "sc932@cornell.edu",
                        "maintainer": False
                    }
                ],
                "bioschemas": False,
                "contribPolicy": [],
                "dependencies": [],
                "documentation": [],
                "download": [],
                "edam_operations": [],
                "edam_topics": [],
                "https": True,
                "input": [],
                "inst_instr": False,
                "operational": False,
                "os": [],
                "output": [],
                "publication": [],
                "semantics": {
                    "inputs": [],
                    "outputs": [],
                    "topics": [],
                    "operations": []
                },
                "source": [
                    "github"
                ],
                "src": [],
                "ssl": True,
                "tags": [],
                "test": [],
                "type": ""
            }
        }
    }
}


def test_github_issue_context_issue():

    conflict_id = "ale/cmd"
   
    context = generate_context(conflict_id, full_conflict)

    issue = generate_github_issue(context)

    assert context["id"] == "ale/cmd"
    assert "- **Name**: ale" in issue
    assert "- **ID**: bioconda_recipes/ale/cmd/20180904" in issue
    assert "- **ID**: biotools/ale/cmd/None" in issue


    
