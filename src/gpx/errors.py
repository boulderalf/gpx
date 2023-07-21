"""This module provices various error types."""


class InvalidGPXError(ValueError):
    """GPX is invalid."""


class ParseError(ValueError):
    """No element to parse."""


class InvalidGeoJSONError(ValueError):
    """`GeoJSON <https://geojson.org/>`_ is invalid."""


class UnsupportedGeoJSONTypeError(ValueError):
    """`GeoJSON <https://geojson.org/>`_ object type is not supported."""


class UnsupportedGeoJSONGeometryTypeError(UnsupportedGeoJSONTypeError):
    """`GeoJSON <https://geojson.org/>`_ `Geometry <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1>`_ object type is not supported."""
