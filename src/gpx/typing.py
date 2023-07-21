"""This module provides static type annotations for GPX data."""
from abc import abstractmethod
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from typing_extensions import (
    Literal,  # Python 3.8+
    NotRequired,  # Python 3.11+,
    Protocol,  # Python 3.8+
    TypeAlias,  # Python 3.10+
    TypedDict,  # Python 3.8+
    runtime_checkable,  # Python 3.8+
)

#: A type alias for a `GeoJSON <https://geojson.org/>`_ `bbox <https://datatracker.ietf.org/doc/html/rfc7946#section-5>`_ array -- a :class:`~typing.Sequence` of :class:`float` or :class:`~decimal.Decimal` values.
BBox: TypeAlias = Sequence[float | Decimal]

#: A type alias for a `GeoJSON <https://geojson.org/>`_ `position <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.1>`_ array -- a :class:`~typing.Sequence` of :class:`float` or :class:`~decimal.Decimal` values.
GeoJSONPosition: TypeAlias = Sequence[float | Decimal]


class GeoJSONBase(TypedDict):
    """A base type for `GeoJSON <https://geojson.org/>`_ objects."""

    bbox: NotRequired[BBox]


class GeoJSONPoint(GeoJSONBase):
    """A `GeoJSON <https://geojson.org/>`_ `Point <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.2>`_ object."""

    type: Literal["Point"]
    coordinates: GeoJSONPosition


class GeoJSONMultiPoint(GeoJSONBase):
    """A `GeoJSON <https://geojson.org/>`_ `MultiPoint <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.3>`_ object."""

    type: Literal["MultiPoint"]
    coordinates: Sequence[GeoJSONPosition]


class GeoJSONLineString(GeoJSONBase):
    """A `GeoJSON <https://geojson.org/>`_ `LineString <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.4>`_ object."""

    type: Literal["LineString"]
    coordinates: Sequence[GeoJSONPosition]


class GeoJSONMultiLineString(GeoJSONBase):
    """A `GeoJSON <https://geojson.org/>`_ `MultiLineString <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.5>`_ object."""

    type: Literal["MultiLineString"]
    coordinates: Sequence[Sequence[GeoJSONPosition]]


class GeoJSONPolygon(GeoJSONBase):
    """A `GeoJSON <https://geojson.org/>`_ `Polygon <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.6>`_ object."""

    type: Literal["Polygon"]
    coordinates: Sequence[Sequence[GeoJSONPosition]]


class GeoJSONMultiPolygon(GeoJSONBase):
    """A `GeoJSON <https://geojson.org/>`_ `MultiPolygon <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.7>`_ object."""

    type: Literal["MultiPolygon"]
    coordinates: Sequence[Sequence[Sequence[GeoJSONPosition]]]


#: A type alias for a `GeoJSON <https://geojson.org/>`_ `Geometry <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1>`_ object.
GeoJSONGeometry: TypeAlias = (
    GeoJSONPoint
    | GeoJSONMultiPoint
    | GeoJSONLineString
    | GeoJSONMultiLineString
    | GeoJSONPolygon
    | GeoJSONMultiPolygon
)


class GeoJSONGeometryCollection(GeoJSONBase):
    """A `GeoJSON <https://geojson.org/>`_ `GeometryCollection <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.8>`_ object."""

    type: Literal["GeometryCollection"]
    geometries: Sequence[GeoJSONGeometry]


class GeoJSONFeature(GeoJSONBase):
    """A `GeoJSON <https://geojson.org/>`_ `Feature <https://datatracker.ietf.org/doc/html/rfc7946#section-3.2>`_ object."""

    type: Literal["Feature"]
    geometry: GeoJSONGeometry
    properties: NotRequired[dict[str, Any]]
    id: NotRequired[str | int]


class GeoJSONFeatureCollection(GeoJSONBase):
    """A `GeoJSON <https://geojson.org/>`_ `FeatureCollection <https://datatracker.ietf.org/doc/html/rfc7946#section-3.3>`_ object."""

    type: Literal["FeatureCollection"]
    features: Sequence[GeoJSONFeature]


#: A type alias for a `GeoJSON <https://geojson.org/>`_ object.
GeoJSON: TypeAlias = (
    GeoJSONGeometry
    | GeoJSONGeometryCollection
    | GeoJSONFeature
    | GeoJSONFeatureCollection
)


@runtime_checkable
class SupportsGeoInterface(Protocol):
    """A :class:`~typing.Protocol` for objects that support the `__geo_interface__` protocol -- a GeoJSON-like protocol for geo-spatial (GIS) vector data. See the `__geo_interface__ specification <https://gist.github.com/sgillies/2217756>`_ for more details."""

    @property
    @abstractmethod
    def __geo_interface__(self) -> GeoJSON:
        ...
