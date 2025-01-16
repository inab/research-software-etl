# To transform the data from the github metadata api (https://github.com/inab/github-metadata-api) to the domain model

from src.core.domain.services.transformation.metadata_standardizers import MetadataStandardizer
from src.core.domain.entities.software_instance.main import instance

from pydantic import TypeAdapter, HttpUrl
from typing import Dict, Any
import logging
import re

# --------------------------------------------
# GitHub Tools Transformer
# --------------------------------------------