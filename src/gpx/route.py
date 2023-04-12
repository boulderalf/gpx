"""
This module provides a Route object to contain GPX routes - ordered lists of
waypoints representing a series of turn points leading to a destination.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from lxml import etree

from .element import Element
from .errors import InvalidGeoJSONError, UnsupportedGeoJSONTypeError
from .link import Link
from .mixins import PointsMutableSequenceMixin, PointsStatisticsMixin
from .utils import CustomJSONEncoder, filter_geojson_properties
from .waypoint import Waypoint


class Route(Element, PointsMutableSequenceMixin, PointsStatisticsMixin):
    """A route class for the GPX data format.

    A route represents an ordered list of waypoints representing a series of
    turn points leading to a destination.

    Args:
        element: The route XML element. Defaults to `None`.
    """

    def __init__(self, element: etree._Element | None = None) -> None:
        super().__init__(element)

        #: GPS name of route.
        self.name: str | None = None

        #: GPS comment for route.
        self.cmt: str | None = None

        #: Text description of route for user. Not sent to GPS.
        self.desc: str | None = None

        #: Source of data. Included to give user some idea of reliability and
        #: accuracy of data.
        self.src: str | None = None

        #: Links to external information about the route.
        self.links: list[Link] = []

        #: GPS route number.
        self.number: int | None = None

        #: Type (classification) of route.
        self.type: str | None = None

        #: A list of route points.
        self.rtepts: list[Waypoint] = []
        self.points = self.rtepts  #: Alias of :attr:`rtepts`.

        if self._element is not None:
            self._parse()

    def _parse(self) -> None:
        super()._parse()

        # assertion to satisfy mypy
        assert self._element is not None

        # name
        if (name := self._element.find("name", namespaces=self._nsmap)) is not None:
            self.name = name.text
        # comment
        if (cmt := self._element.find("cmt", namespaces=self._nsmap)) is not None:
            self.cmt = cmt.text
        # description
        if (desc := self._element.find("desc", namespaces=self._nsmap)) is not None:
            self.desc = desc.text
        # source of data
        if (src := self._element.find("src", namespaces=self._nsmap)) is not None:
            self.src = src.text
        # links
        for link in self._element.iterfind("link", namespaces=self._nsmap):
            self.links.append(Link(link))
        # GPS route number
        if (number := self._element.find("number", namespaces=self._nsmap)) is not None:
            self.number = int(number.text)
        # track type (classification)
        if (_type := self._element.find("type", namespaces=self._nsmap)) is not None:
            self.type = _type.text

        # route points
        for rtept in self._element.iterfind("rtept", namespaces=self._nsmap):
            self.rtepts.append(Waypoint(rtept))

    def _build(self, tag: str = "rte") -> etree._Element:
        route = super()._build(tag)

        if self.name is not None:
            name = etree.SubElement(route, "name", nsmap=self._nsmap)
            name.text = self.name

        if self.cmt is not None:
            cmt = etree.SubElement(route, "cmt", nsmap=self._nsmap)
            cmt.text = self.cmt

        if self.desc is not None:
            desc = etree.SubElement(route, "desc", nsmap=self._nsmap)
            desc.text = self.desc

        if self.src is not None:
            src = etree.SubElement(route, "src", nsmap=self._nsmap)
            src.text = self.src

        for link in self.links:
            route.append(link._build())

        if self.number is not None:
            number = etree.SubElement(route, "number", nsmap=self._nsmap)
            number.text = str(self.number)

        if self.type is not None:
            _type = etree.SubElement(route, "type", nsmap=self._nsmap)
            _type.text = self.type

        for _rtept in self.rtepts:
            route.append(_rtept._build(tag="rtept"))

        return route

    @classmethod
    def from_geojson(cls, geojson: dict[str, Any]) -> Route:  # noqa: C901
        """Create a route from a `GeoJSON <https://geojson.org/>`_ object.

        Args:
            geojson: The GeoJSON object.

        Returns:
            The route.

        Raises:
            InvalidGeoJSONError: If the GeoJSON object is not a valid GeoJSON object.
            UnsupportedGeoJSONTypeError: If the GeoJSON object type is unsupported.
        """
        # create a new Route object
        rte = cls()

        if isinstance(geojson, dict) and "type" in geojson:
            if geojson["type"] == "LineString":
                for coordinates in geojson["coordinates"]:
                    rte.rtepts.append(Waypoint._geojson_from_coordinates(*coordinates))
                return rte
            elif (
                geojson["type"] == "Feature"
                and geojson["geometry"]["type"] == "LineString"
            ):
                if "coordinatesProperties" in geojson["properties"]:
                    for coordinates, properties in zip(
                        geojson["geometry"]["coordinates"],
                        geojson["properties"]["coordinatesProperties"],
                    ):
                        # create the route point and set the coordinates
                        rtept = Waypoint._geojson_from_coordinates(*coordinates)

                        # set the properties
                        rtept._geojson_parse_properties(properties)

                        # add the route point to the route
                        rte.rtepts.append(rtept)
                else:
                    for coordinates in geojson["geometry"]["coordinates"]:
                        rte.rtepts.append(
                            Waypoint._geojson_from_coordinates(*coordinates)
                        )

                # set the properties
                if (name := geojson["properties"].get("name")) is not None:
                    rte.name = name

                if (cmt := geojson["properties"].get("cmt")) is not None:
                    rte.cmt = cmt

                if (desc := geojson["properties"].get("desc")) is not None:
                    rte.desc = desc

                if (src := geojson["properties"].get("src")) is not None:
                    rte.src = src

                for link in geojson["properties"].get("links", []):
                    rte.links.append(Link.from_dict(link))

                if (number := geojson["properties"].get("number")) is not None:
                    rte.number = number

                if (type := geojson["properties"].get("type")) is not None:
                    rte.type = type

                return rte
            else:
                raise UnsupportedGeoJSONTypeError(
                    f"The GeoJSON object type is unsupported: {geojson['type']}. Should be either a `LineString` or a `Feature` object."
                )
        else:
            raise InvalidGeoJSONError(
                "The GeoJSON object is invalid. Should be a either a `LineString` or a `Feature` object."
            )

    @classmethod
    def from_geojson_file(cls, geojson_file: str | Path) -> Route:
        """Create a route from a `GeoJSON <https://geojson.org/>`_ file.

        Args:
            geojson_file: The file containing the GeoJSON data.

        Returns:
            The route.

        Raises:
            InvalidGeoJSONError: If the GeoJSON object is not a valid GeoJSON object.
            UnsupportedGeoJSONTypeError: If the GeoJSON object type is unsupported.
        """
        with open(geojson_file, encoding="utf-8") as fh:
            geojson = json.load(fh, parse_float=Decimal)

        return cls.from_geojson(geojson)

    def to_geojson(
        self, type: Literal["LineString", "Feature"] = "Feature"
    ) -> dict[str, Any]:
        """Convert the route to a `GeoJSON <https://geojson.org/>`_ object.

        By default, the route is converted to a GeoJSON `Feature` object instead
        of a `LineString` object. This way, we can add additional properties
        (i.e. metadata) to the GeoJSON object.

        Args:
            type: The type of GeoJSON object to create. Defaults to `Feature`.

        Returns:
            The GeoJSON object.
        """
        # construct the coordinates
        coordinates = [rtept._geojson_coordinates for rtept in self.rtepts]

        # construct the `LineString` geometry
        linestring_geojson = {
            "type": "LineString",
            "bbox": self._geojson_bounds,
            "coordinates": coordinates,
        }

        if type == "LineString":
            return linestring_geojson

        # construct the properties
        properties = {
            "name": self.name,
            "cmt": self.cmt,
            "desc": self.desc,
            "src": self.src,
            "links": [link.to_dict() for link in self.links],
            "number": self.number,
            "type": self.type,
        }

        # filter out `None` values and remove empty links
        properties = filter_geojson_properties(properties)

        # add the coordinates properties (if any)
        coordinates_properties = [rtept._geojson_properties for rtept in self.rtepts]
        if any(coordinates_properties):
            properties["coordinatesProperties"] = coordinates_properties

        # construct the `Feature` object
        feature_geojson = {
            "type": "Feature",
            "geometry": linestring_geojson,
            "properties": properties if properties else None,
        }

        return feature_geojson

    def to_geojson_file(
        self,
        geojson_file: str | Path,
        type: Literal["LineString", "Feature"] = "Feature",
    ) -> None:
        """Convert the route to a `GeoJSON <https://geojson.org/>`_ file.

        By default, the route is converted to a GeoJSON `Feature` object instead
        of a `LineString` object. This way, we can add additional properties
        (i.e. metadata) to the GeoJSON object.

        Args:
            geojson_file: The file to write the GeoJSON object to.
            type: The type of GeoJSON object to create. Defaults to `Feature`.
        """
        with open(geojson_file, "w", encoding="utf-8") as fh:
            json.dump(self.to_geojson(type=type), fh, indent=4, cls=CustomJSONEncoder)

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """Represents the route as a GeoJSON-like `LineString` object.

        Implements the `__geo_interface__` protocol -- a GeoJSON-like
        protocol for geo-spatial (GIS) vector data. See the
        `__geo_interface__ specification <https://gist.github.com/sgillies/2217756>`_
        for more details.
        """
        return self.to_geojson(type="LineString")
