"""
The collections the pipeline reads and writes, bundled into one object.

Built once at the CLI from a :class:`PipelineConfig` (see
``infrastructure.db.repositories.from_config``) and passed down, so nothing below
``adapters/`` has to reach for a database of its own -- the database equivalent of
:class:`infrastructure.external.clients.ExternalClients`.

The fields are typed against the domain :mod:`domain.repositories` protocols, not
the concrete Mongo classes: the application layer sees only the contract. Tests
construct this with fakes instead of patching module globals, and leave the slots
a stage does not use as ``None`` -- an unexpected reach-through then fails loudly
instead of quietly opening a connection to a real database.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from domain.repositories.computations import ComputationsRepository
from domain.repositories.license_mapping import LicenseMappingRepository
from domain.repositories.pretools import PretoolsRepository
from domain.repositories.publications import PublicationRepository
from domain.repositories.raw_software import RawSoftwareRepository
from domain.repositories.similarities import SimilaritiesRepository
from domain.repositories.tools import ToolsRepository
from domain.repositories.web_availability import WebAvailabilityRepository


@dataclass(frozen=True)
class Repositories:
    alambique: Optional[RawSoftwareRepository] = None
    pretools: Optional[PretoolsRepository] = None
    tools: Optional[ToolsRepository] = None
    # Where merge writes. The live `tools` collection stays readable throughout the
    # merge -- it is where the new entries inherit their ids from -- and is only
    # replaced by this one at the end of the run.
    tools_staging: Optional[ToolsRepository] = None
    publications: Optional[PublicationRepository] = None
    license_mapping: Optional[LicenseMappingRepository] = None
    computations: Optional[ComputationsRepository] = None
    similarities: Optional[SimilaritiesRepository] = None
    web_availability: Optional[WebAvailabilityRepository] = None
