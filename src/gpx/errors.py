"""This module provices various error types."""


class InvalidGPXError(ValueError):
    """GPX is invalid."""


class ParseError(ValueError):
    """No element to parse."""


class InvalidGeoJSONError(ValueError):
    """`GeoJSON <https://geojson.org/>`_ is invalid."""


class UnsupportedGeoJSONTypeError(ValueError):
    """`GeoJSON <https://geojson.org/>`_ object type is not supported."""
