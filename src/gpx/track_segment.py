"""
This module provides a TrackSegment object to contain GPX track segments - an ordered list of
points describing a path.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Literal, overload

from lxml import etree

from .element import Element
from .errors import InvalidGeoJSONError, UnsupportedGeoJSONTypeError
from .mixins import PointsMutableSequenceMixin, PointsStatisticsMixin
from .typing import GeoJSONFeature, GeoJSONLineString, SupportsGeoInterface
from .utils import CustomJSONEncoder
from .waypoint import Waypoint


class TrackSegment(Element, PointsMutableSequenceMixin, PointsStatisticsMixin):
    """A track segment class for the GPX data format.

    A Track Segment holds a list of Track Points which are logically connected
    in order. To represent a single GPS track where GPS reception was lost, or
    the GPS receiver was turned off, start a new Track Segment for each
    continuous span of track data.

    Args:
        element: The track segment XML element. Defaults to `None`.
    """

    def __init__(self, element: etree._Element | None = None) -> None:
        super().__init__(element)

        #: A Track Point holds the coordinates, elevation, timestamp, and
        #: metadata for a single point in a track.
        self.trkpts: list[Waypoint] = []
        self.points = self.trkpts  #: Alias of :attr:`trkpts`.

        if self._element is not None:
            self._parse()

    def _parse(self) -> None:
        super()._parse()

        # assertion to satisfy mypy
        assert self._element is not None

        # track points
        for trkpt in self._element.iterfind("trkpt", namespaces=self._nsmap):
            self.trkpts.append(Waypoint(trkpt))

    def _build(self, tag: str = "trkseg") -> etree._Element:
        track_segment = super()._build(tag)

        for _trkpt in self.trkpts:
            track_segment.append(_trkpt._build(tag="trkpt"))

        return track_segment

    @classmethod
    def from_geojson(
        cls, context: GeoJSONLineString | GeoJSONFeature | SupportsGeoInterface
    ) -> TrackSegment:
        """Create a track segment from a `GeoJSON <https://geojson.org/>`_
        `LineString <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.4>`_ object,
        a `Feature <https://datatracker.ietf.org/doc/html/rfc7946#section-3.2>`_ object or from an
        object which implements the `__geo_interface__` protocol -- a
        GeoJSON-like protocol for geo-spatial (GIS) vector data. See the
        `__geo_interface__ specification <https://gist.github.com/sgillies/2217756>`_
        for more details.

        Args:
            context: A `GeoJSON <https://geojson.org/>`_ `LineString <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.4>`_ object, a `Feature <https://datatracker.ietf.org/doc/html/rfc7946#section-3.2>`_ object or an object which implements the `__geo_interface__` protocol.

        Returns:
            The track segment.

        Raises:
            InvalidGeoJSONError: If the GeoJSON object is not a valid GeoJSON object.
            UnsupportedGeoJSONTypeError: If the GeoJSON object type is unsupported.
        """
        # create a new TrackSegment object
        trkseg = cls()

        if isinstance(context, SupportsGeoInterface):
            geojson = context.__geo_interface__
        else:
            geojson = context

        if isinstance(geojson, dict) and "type" in geojson:
            if geojson["type"] == "LineString":
                for coordinates in geojson["coordinates"]:
                    trkseg.trkpts.append(
                        Waypoint._geojson_from_coordinates(*coordinates)
                    )
                return trkseg
            elif (
                geojson["type"] == "Feature"
                and geojson["geometry"]["type"] == "LineString"
            ):
                if (
                    "properties" in geojson
                    and "coordinatesProperties" in geojson["properties"]
                ):
                    for coordinates, properties in zip(
                        geojson["geometry"]["coordinates"],
                        geojson["properties"]["coordinatesProperties"],
                    ):
                        # create the track segment point and set the coordinates
                        trkpt = Waypoint._geojson_from_coordinates(*coordinates)

                        # set the properties
                        trkpt._geojson_parse_properties(properties)

                        # add the track point to the track segment
                        trkseg.trkpts.append(trkpt)
                else:
                    for coordinates in geojson["geometry"]["coordinates"]:
                        trkseg.trkpts.append(
                            Waypoint._geojson_from_coordinates(*coordinates)
                        )

                return trkseg
            else:
                raise UnsupportedGeoJSONTypeError(
                    f"The GeoJSON object type is unsupported: {geojson['type']}. Should be either a `LineString` object or a `Feature` object containing a `LineString` geometry."
                )
        else:
            raise InvalidGeoJSONError(
                "The GeoJSON object is invalid. Should be a either a GeoJSON `LineString` object or a GeoJSON `Feature` object containing a `LineString` geometry."
            )

    @classmethod
    def from_geojson_file(cls, geojson_file: str | Path) -> TrackSegment:
        """Create a track segment from a `GeoJSON <https://geojson.org/>`_ file.

        Args:
            geojson_file: The file containing the GeoJSON data.

        Returns:
            The track segment.

        Raises:
            InvalidGeoJSONError: If the GeoJSON object is not a valid GeoJSON object.
            UnsupportedGeoJSONTypeError: If the GeoJSON object type is unsupported.
        """
        with open(geojson_file, encoding="utf-8") as fh:
            geojson = json.load(fh, parse_float=Decimal)

        return cls.from_geojson(geojson)

    @overload
    def to_geojson(self, type: Literal["LineString"]) -> GeoJSONLineString:
        ...

    @overload
    def to_geojson(self, type: Literal["Feature"] = ...) -> GeoJSONFeature:
        ...

    def to_geojson(
        self, type: Literal["LineString", "Feature"] = "Feature"
    ) -> GeoJSONLineString | GeoJSONFeature:
        """Convert the track segment to a `GeoJSON <https://geojson.org/>`_
        object.

        By default, the track segment is converted to a GeoJSON `Feature <https://datatracker.ietf.org/doc/html/rfc7946#section-3.2>`_ object
        instead of a `LineString <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.4>`_ object. This way, we can add additional
        properties (i.e. metadata) to the GeoJSON object.

        Args:
            type: The type of GeoJSON object to create. Defaults to `Feature`.

        Returns:
            The GeoJSON object.
        """
        # construct the coordinates
        coordinates = [trkpt._geojson_coordinates for trkpt in self.trkpts]

        # construct the `LineString` geometry
        linestring_geojson: GeoJSONLineString = {
            "type": "LineString",
            "bbox": self._geojson_bounds,
            "coordinates": coordinates,
        }

        if type == "LineString":
            return linestring_geojson

        # construct the properties
        properties = {}

        # add the coordinates properties (if any)
        coordinates_properties = [trkpt._geojson_properties for trkpt in self.trkpts]
        if any(coordinates_properties):
            properties["coordinatesProperties"] = coordinates_properties

        # construct the `Feature <https://datatracker.ietf.org/doc/html/rfc7946#section-3.2>`_ object
        feature_geojson: GeoJSONFeature = {
            "type": "Feature",
            "geometry": linestring_geojson,
        }

        if properties:
            feature_geojson["properties"] = properties

        return feature_geojson

    def to_geojson_file(
        self,
        geojson_file: str | Path,
        type: Literal["LineString", "Feature"] = "Feature",
    ) -> None:
        """Convert the track segment to a `GeoJSON <https://geojson.org/>`_ file.

        By default, the track segment is converted to a GeoJSON `Feature <https://datatracker.ietf.org/doc/html/rfc7946#section-3.2>`_ object
        instead of a `LineString <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.4>`_ object. This way, we can add additional
        properties (i.e. metadata) to the GeoJSON object.

        Args:
            geojson_file: The file to write the GeoJSON object to.
            type: The type of GeoJSON object to create. Defaults to `Feature`.
        """
        with open(geojson_file, "w", encoding="utf-8") as fh:
            json.dump(self.to_geojson(type=type), fh, indent=4, cls=CustomJSONEncoder)

    @property
    def __geo_interface__(self) -> GeoJSONLineString:
        """Represents the track segment as a GeoJSON-like `LineString <https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.4>`_ object.

        Implements the `__geo_interface__` protocol -- a GeoJSON-like protocol for geo-spatial (GIS) vector data. See the `__geo_interface__ specification <https://gist.github.com/sgillies/2217756>`_ for more details.
        """
        return self.to_geojson(type="LineString")
