test_entries = [
    # --- Case 1: Bioconductor tool with matching GitHub entry (name slightly different) ---
    {
        "_id": 1,
        "data": {
            "name": "bioTool-X",
            "type": "tool",
            "source": ["bioconductor"],
            "repository": [{"url": "https://bioconductor.org/packages/biotool-x"}],
            "webpage": ["https://biotoolx.com"]
        }
    },
    {
        "_id": 2,
        "data": {
            "name": "BioToolX",
            "type": "tool",
            "source": ["github"],
            "source_url": "https://bioconductor.org/packages/biotool-x",
            "repository": [{"url": "https://github.com/org/biotool-x"}],
            "webpage": ["https://biotoolx.com"]
        }
    },

    # --- Case 2: Tool with the same name/type from multiple sources (should be merged) ---
    {
        "_id": 3,
        "data": {
            "name": "RNA-SeqAnalyzer",
            "type": "tool",
            "source": ["biotools"],
            "repository": [{"url": "https://github.com/org/rna-seq-analyzer"}],
            "webpage": ["https://rnaseqanalyzer.com"]
        }
    },
    {
        "_id": 4,
        "data": {
            "name": "RNA-SeqAnalyzer",
            "type": "tool",
            "source": ["galaxy"],
            "repository": [{"url": "https://github.com/org/rna-seq-analyzer"}],
            "webpage": ["https://rnaseqanalyzer.com"]
        }
    },

    # --- Case 3: Bioconductor tool with matching SourceForge entry (name slightly different) ---
    {
        "_id": 5,
        "data": {
            "name": "SeqQuant",
            "type": "tool",
            "source": ["bioconductor"],
            "repository": [{"url": "https://bioconductor.org/packages/seqquant"}],
            "webpage": ["https://seqquant.com"]
        }
    },
    {
        "_id": 6,
        "data": {
            "name": "Seq-Quantifier",
            "type": "tool",
            "source": ["sourceforge"],
            "source_url": "https://bioconductor.org/packages/seqquant",
            "repository": [{"url": "https://sourceforge.net/projects/seqquant"}],
            "webpage": ["https://seqquant.com"]
        }
    },

    # --- Case 4: Tool with identical name/type but different links (should remain separate) ---
    {
        "_id": 7,
        "data": {
            "name": "DataAnalyzer",
            "type": "tool",
            "source": ["biotools"],
            "repository": [{"url": "https://github.com/org/data-analyzer"}],
            "webpage": ["https://dataanalyzer.com"]
        }
    },
    {
        "_id": 8,
        "data": {
            "name": "DataAnalyzer",
            "type": "tool",
            "source": ["bioconductor"],
            "repository": [{"url": "https://bioconductor.org/packages/dataanalyzer"}],
            "webpage": ["https://bioconductor.org/packages/dataanalyzer"]
        }
    },

    # --- Case 5: Completely isolated tool (should remain separate) ---
    {
        "_id": 9,
        "data": {
            "name": "StandaloneTool",
            "type": "tool",
            "source": ["github"],
            "repository": [{"url": "https://github.com/org/standalone-tool"}],
            "webpage": ["https://standalonetool.com"]
        }
    }
]
