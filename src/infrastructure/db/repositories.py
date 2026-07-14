"""
The collections the pipeline reads and writes, bundled into one object.

Built once at the CLI from a :class:`PipelineConfig` and passed down, so nothing
below ``adapters/`` has to reach for the mongo singleton -- the database
equivalent of :class:`infrastructure.external.clients.ExternalClients`.

Tests construct this with fakes instead of patching module globals, and leave
the slots a stage does not use as ``None``: an unexpected reach-through then
fails loudly instead of quietly opening a connection to a real database.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from infrastructure.config import PipelineConfig
from infrastructure.db.database_adapter import DatabaseAdapter
from infrastructure.db.mongo.license_mapping_repository import LicenseMappingRepository
from infrastructure.db.mongo.mongo_adapter import MongoDBAdapter
from infrastructure.db.mongo.publications_repository import MongoPublicationRepository
from infrastructure.db.mongo.raw_software_repository import RawSoftwareMetadataRepository
from infrastructure.db.mongo.standardized_software_repository import PretoolsRepository
from infrastructure.db.mongo.tools_repository import ToolsRepository


@dataclass(frozen=True)
class Repositories:
    alambique: Optional[RawSoftwareMetadataRepository] = None
    pretools: Optional[PretoolsRepository] = None
    tools: Optional[ToolsRepository] = None
    # Where merge writes. The live `tools` collection stays readable throughout the
    # merge -- it is where the new entries inherit their ids from -- and is only
    # replaced by this one at the end of the run.
    tools_staging: Optional[ToolsRepository] = None
    publications: Optional[MongoPublicationRepository] = None
    license_mapping: Optional[LicenseMappingRepository] = None

    @classmethod
    def from_config(
        cls, config: PipelineConfig, db: Optional[DatabaseAdapter] = None
    ) -> "Repositories":
        """
        Wire every repository over one adapter.

        ``MongoDBAdapter`` holds its client in a class attribute and connects on
        first use, so building an adapter here costs nothing and opens no
        connection until a stage actually reads or writes.
        """
        db = db or MongoDBAdapter()
        return cls(
            alambique=RawSoftwareMetadataRepository(db, config.alambique_collection),
            pretools=PretoolsRepository(db, config.pretools_collection),
            tools=ToolsRepository(db, config.tools_collection),
            tools_staging=ToolsRepository(db, config.tools_staging_collection),
            publications=MongoPublicationRepository(db, config.publications_collection),
            license_mapping=LicenseMappingRepository(
                db, config.licenses_mapping_collection
            ),
        )
