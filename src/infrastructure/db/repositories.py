"""
Builder for the :class:`Repositories` bundle.

The bundle dataclass itself lives in :mod:`domain.repositories`, typed against the
domain protocols. This module is the infrastructure-side builder: it imports the
concrete Mongo repository classes and wires them over one adapter, returning a
domain ``Repositories``. Keeping the wiring here is what lets the application layer
depend on the protocols alone -- ``application/`` never names a Mongo class.

Assigning each concrete repository into a protocol-typed field is also where mypy
checks, for free, that the concrete classes still satisfy the protocols.
"""

from __future__ import annotations

from typing import Optional

from domain.repositories import Repositories
from infrastructure.config import PipelineConfig
from infrastructure.db.database_adapter import DatabaseAdapter
from infrastructure.db.mongo.computations_repository import ComputationsRepository
from infrastructure.db.mongo.embeddings_repository import EmbeddingsRepository
from infrastructure.db.mongo.license_mapping_repository import LicenseMappingRepository
from infrastructure.db.mongo.mongo_adapter import MongoDBAdapter
from infrastructure.db.mongo.publications_repository import MongoPublicationRepository
from infrastructure.db.mongo.raw_software_repository import (
    RawSoftwareMetadataRepository,
)
from infrastructure.db.mongo.similarities_repository import SimilaritiesRepository
from infrastructure.db.mongo.standardized_software_repository import PretoolsRepository
from infrastructure.db.mongo.tools_repository import ToolsRepository
from infrastructure.db.mongo.web_availability_repository import (
    WebAvailabilityRepository,
)

__all__ = ["Repositories", "from_config"]


def from_config(
    config: PipelineConfig, db: Optional[DatabaseAdapter] = None
) -> Repositories:
    """
    Wire every repository over one adapter.

    ``MongoDBAdapter`` holds its client in a class attribute and connects on first
    use, so building an adapter here costs nothing and opens no connection until a
    stage actually reads or writes.
    """
    db = db or MongoDBAdapter()
    return Repositories(
        alambique=RawSoftwareMetadataRepository(db, config.alambique_collection),
        pretools=PretoolsRepository(db, config.pretools_collection),
        tools=ToolsRepository(db, config.tools_collection),
        tools_staging=ToolsRepository(db, config.tools_staging_collection),
        publications=MongoPublicationRepository(db, config.publications_collection),
        license_mapping=LicenseMappingRepository(
            db, config.licenses_mapping_collection
        ),
        computations=ComputationsRepository(db, config.computations_collection),
        similarities=SimilaritiesRepository(db, config.similarities_collection),
        embeddings=EmbeddingsRepository(db, config.embeddings_collection),
        web_availability=WebAvailabilityRepository(
            db, config.web_availability_collection
        ),
    )
