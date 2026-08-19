"""Catalog persistence mappings and adapters."""

from wef_backend.features.catalog.infrastructure.browse_adapter import (
    SQLAlchemyCatalogBrowseAdapter,
)
from wef_backend.features.catalog.infrastructure.map_query_adapter import (
    SQLAlchemyMapQueryAdapter,
)
from wef_backend.features.catalog.infrastructure.models import (
    CatalogBase,
    LocationRow,
    OfferRow,
)
from wef_backend.features.catalog.infrastructure.offer_detail_adapter import (
    SQLAlchemyOfferDetailAdapter,
)
from wef_backend.features.catalog.infrastructure.seed_adapter import (
    SQLAlchemyCatalogSeedAdapter,
)

__all__ = [
    "CatalogBase",
    "LocationRow",
    "OfferRow",
    "SQLAlchemyCatalogBrowseAdapter",
    "SQLAlchemyCatalogSeedAdapter",
    "SQLAlchemyMapQueryAdapter",
    "SQLAlchemyOfferDetailAdapter",
]
