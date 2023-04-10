"""
This module provides a Route object to contain GPX routes - ordered lists of
waypoints representing a series of turn points leading to a destination.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from lxml import etree

from .element import Element
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
        }

        if properties:
            feature_geojson["properties"] = properties

        return feature_geojson

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """Represents the route as a GeoJSON-like `LineString` object.

        Implements the `__geo_interface__` protocol -- a GeoJSON-like
        protocol for geo-spatial (GIS) vector data. See the
        `__geo_interface__ specification <https://gist.github.com/sgillies/2217756>`_
        for more details.
        """
        return self.to_geojson(type="LineString")

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
