"""
Repository protocols the application layer depends on.

These are structural ``Protocol``s -- the concrete Mongo repositories in
``infrastructure/db/mongo/`` satisfy them by shape, exactly as ``MongoDBAdapter``
satisfies ``DatabaseAdapter``. They must **not** be inherited: an inherited
``...``-bodied protocol method would silently return ``None`` where a real one is
missing; staying structural makes the same gap raise instead.

Each protocol lists only the methods the application layer actually calls, not
the full surface of the concrete class. ``application/`` imports these and the
``Repositories`` bundle from here; the ``from_config`` builder that wires the
concrete classes stays in ``infrastructure/db/repositories.py``.
"""

from domain.repositories.bundle import Repositories
from domain.repositories.computations import ComputationsRepository
from domain.repositories.license_mapping import LicenseMappingRepository
from domain.repositories.pretools import PretoolsRepository
from domain.repositories.publications import PublicationRepository
from domain.repositories.raw_software import RawSoftwareRepository
from domain.repositories.similarities import SimilaritiesRepository
from domain.repositories.tools import ToolsRepository
from domain.repositories.web_availability import WebAvailabilityRepository

__all__ = [
    "Repositories",
    "ComputationsRepository",
    "LicenseMappingRepository",
    "PretoolsRepository",
    "PublicationRepository",
    "RawSoftwareRepository",
    "SimilaritiesRepository",
    "ToolsRepository",
    "WebAvailabilityRepository",
]
