"""This module provides a Waypoint object to contain GPX waypoints."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any, Literal

from dateutil.parser import isoparse
from lxml import etree

from .element import Element
from .errors import InvalidGeoJSONError, UnsupportedGeoJSONTypeError
from .link import Link
from .types import Degrees, DGPSStation, Fix, Latitude, Longitude
from .utils import CustomJSONEncoder, filter_geojson_properties, format_datetime


class Waypoint(Element):
    """A waypoint class for the GPX data format.

    A waypoint represents a waypoint, point of interest, or named feature on a
    map.

    Args:
        element: The waypoint XML element. Defaults to `None`.
    """

    def __init__(self, element: etree._Element | None = None) -> None:
        super().__init__(element)

        #: The latitude of the point. Decimal degrees, WGS84 datum.
        self.lat: Latitude

        #: The longitude of the point. Decimal degrees, WGS84 datum.
        self.lon: Longitude

        #: Elevation (in meters) of the point.
        self.ele: Decimal | None = None

        #: Creation/modification timestamp for element. Date and time in are in
        #: Universal Coordinated Time (UTC), not local time! Conforms to ISO
        #: 8601 specification for date/time representation. Fractional seconds
        #: are allowed for millisecond timing in tracklogs.
        self.time: datetime | None = None

        #: Magnetic variation (in degrees) at the point
        self.magvar: Degrees | None = None

        #: Height (in meters) of geoid (mean sea level) above WGS84 earth
        #: ellipsoid. As defined in NMEA GGA message.
        self.geoidheight: Decimal | None = None

        #: The GPS name of the waypoint. This field will be transferred to and
        #: from the GPS. GPX does not place restrictions on the length of this
        #: field or the characters contained in it. It is up to the receiving
        #: application to validate the field before sending it to the GPS.
        self.name: str | None = None

        #: GPS waypoint comment. Sent to GPS as comment.
        self.cmt: str | None = None

        #: A text description of the element. Holds additional information about
        #: the element intended for the user, not the GPS.
        self.desc: str | None = None

        #: Source of data. Included to give user some idea of reliability and
        #: accuracy of data. "Garmin eTrex", "USGS quad Boston North", e.g.
        self.src: str | None = None

        #: Link to additional information about the waypoint.
        self.links: list[Link] = []

        #: Text of GPS symbol name. For interchange with other programs, use the
        #: exact spelling of the symbol as displayed on the GPS. If the GPS
        #: abbreviates words, spell them out.
        self.sym: str | None = None

        #: Type (classification) of the waypoint.
        self.type: str | None = None

        #: Type of GPX fix.
        self.fix: Fix | None = None

        #: Number of satellites used to calculate the GPX fix.
        self.sat: int | None = None

        #: Horizontal dilution of precision.
        self.hdop: Decimal | None = None

        #: Vertical dilution of precision.
        self.vdop: Decimal | None = None

        #: Position dilution of precision.
        self.pdop: Decimal | None = None

        #: Number of seconds since last DGPS update.
        self.ageofdgpsdata: Decimal | None = None

        #: ID of DGPS station used in differential correction.
        self.dgpsid: DGPSStation | None = None

        if self._element is not None:
            self._parse()

    def _parse(self) -> None:  # noqa: C901
        super()._parse()

        # assertion to satisfy mypy
        assert self._element is not None

        # required
        self.lat = Latitude(self._element.get("lat"))
        self.lon = Longitude(self._element.get("lon"))

        # position info
        # elevation
        if (ele := self._element.find("ele", namespaces=self._nsmap)) is not None:
            self.ele = Decimal(ele.text)
        # time
        if (time := self._element.find("time", namespaces=self._nsmap)) is not None:
            self.time = isoparse(time.text)
        # magnetic variation
        if (magvar := self._element.find("magvar", namespaces=self._nsmap)) is not None:
            self.magvar = Degrees(magvar.text)
        # geoid height
        if (
            geoidheight := self._element.find("geoidheight", namespaces=self._nsmap)
        ) is not None:
            self.geoidheight = Decimal(geoidheight.text)

        # description info
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
        # GPS symbol name
        if (sym := self._element.find("sym", namespaces=self._nsmap)) is not None:
            self.sym = sym.text
        # waypoint type (classification)
        if (_type := self._element.find("type", namespaces=self._nsmap)) is not None:
            self.type = _type.text

        # accuracy info
        # GPX fix type
        if (fix := self._element.find("fix", namespaces=self._nsmap)) is not None:
            self.fix = Fix(fix.text)
        # number of satellites used to calculate the GPX fix
        if (sat := self._element.find("sat", namespaces=self._nsmap)) is not None:
            self.sat = int(sat.text)
        # horizontal dilution of precision
        if (hdop := self._element.find("hdop", namespaces=self._nsmap)) is not None:
            self.hdop = Decimal(hdop.text)
        # vertical dilution of precision
        if (vdop := self._element.find("vdop", namespaces=self._nsmap)) is not None:
            self.vdop = Decimal(vdop.text)
        # position dilution of precision
        if (pdop := self._element.find("pdop", namespaces=self._nsmap)) is not None:
            self.pdop = Decimal(pdop.text)
        # number of seconds since last DGPS update
        if (
            ageofdgpsdata := self._element.find("ageofdgpsdata", namespaces=self._nsmap)
        ) is not None:
            self.ageofdgpsdata = Decimal(ageofdgpsdata.text)
        # DGPS station id used in differential correction
        if (dgpsid := self._element.find("dgpsid", namespaces=self._nsmap)) is not None:
            self.dgpsid = DGPSStation(dgpsid.text)

    def _build(self, tag: str = "wpt") -> etree._Element:  # noqa: C901
        waypoint = super()._build(tag)
        waypoint.set("lat", str(self.lat))
        waypoint.set("lon", str(self.lon))

        if self.ele is not None:
            ele = etree.SubElement(waypoint, "ele", nsmap=self._nsmap)
            ele.text = str(self.ele)

        if self.time is not None:
            time = etree.SubElement(waypoint, "time", nsmap=self._nsmap)
            time.text = format_datetime(self.time)

        if self.magvar is not None:
            magvar = etree.SubElement(waypoint, "magvar", nsmap=self._nsmap)
            magvar.text = str(self.magvar)

        if self.geoidheight is not None:
            geoidheight = etree.SubElement(waypoint, "geoidheight", nsmap=self._nsmap)
            geoidheight.text = str(self.geoidheight)

        if self.name is not None:
            name = etree.SubElement(waypoint, "name", nsmap=self._nsmap)
            name.text = self.name

        if self.cmt is not None:
            cmt = etree.SubElement(waypoint, "cmt", nsmap=self._nsmap)
            cmt.text = self.cmt

        if self.desc is not None:
            desc = etree.SubElement(waypoint, "desc", nsmap=self._nsmap)
            desc.text = self.desc

        if self.src is not None:
            src = etree.SubElement(waypoint, "src", nsmap=self._nsmap)
            src.text = self.src

        for link in self.links:
            waypoint.append(link._build())

        if self.sym is not None:
            sym = etree.SubElement(waypoint, "sym", nsmap=self._nsmap)
            sym.text = self.sym

        if self.type is not None:
            _type = etree.SubElement(waypoint, "type", nsmap=self._nsmap)
            _type.text = self.type

        if self.fix is not None:
            fix = etree.SubElement(waypoint, "fix", nsmap=self._nsmap)
            fix.text = self.fix

        if self.sat is not None:
            sat = etree.SubElement(waypoint, "sat", nsmap=self._nsmap)
            sat.text = str(self.sat)

        if self.hdop is not None:
            hdop = etree.SubElement(waypoint, "hdop", nsmap=self._nsmap)
            hdop.text = str(self.hdop)

        if self.vdop is not None:
            vdop = etree.SubElement(waypoint, "vdop", nsmap=self._nsmap)
            vdop.text = str(self.vdop)

        if self.pdop is not None:
            pdop = etree.SubElement(waypoint, "pdop", nsmap=self._nsmap)
            pdop.text = str(self.pdop)

        if self.ageofdgpsdata is not None:
            ageofdgpsdata = etree.SubElement(
                waypoint, "ageofdgpsdata", nsmap=self._nsmap
            )
            ageofdgpsdata.text = str(self.ageofdgpsdata)

        if self.dgpsid is not None:
            dgpsid = etree.SubElement(waypoint, "dgpsid", nsmap=self._nsmap)
            dgpsid.text = str(self.dgpsid)

        return waypoint

    @property
    def _geojson_coordinates(
        self,
    ) -> tuple[Longitude, Latitude] | tuple[Longitude, Latitude, Decimal]:
        """The GeoJSON-compatible coordinates of the waypoint.

        The coordinates are of the form [lon, lat, ele (alt)], where ele is
        optional.
        """
        if self.ele is not None:
            return self.lon, self.lat, self.ele
        return self.lon, self.lat

    @property
    def _geojson_properties(self) -> dict[str, Any]:
        """The GeoJSON-compatible properties of the waypoint."""
        # construct the properties
        properties = {
            "time": self.time,
            "magvar": self.magvar,
            "geoidheight": self.geoidheight,
            "name": self.name,
            "cmt": self.cmt,
            "desc": self.desc,
            "src": self.src,
            "links": [link.to_dict() for link in self.links],
            "sym": self.sym,
            "type": self.type,
            "fix": self.fix,
            "sat": self.sat,
            "hdop": self.hdop,
            "vdop": self.vdop,
            "pdop": self.pdop,
            "ageofdgpsdata": self.ageofdgpsdata,
            "dgpsid": self.dgpsid,
        }

        # filter out `None` values and remove empty links
        properties = filter_geojson_properties(properties)

        return properties

    @classmethod
    def _geojson_from_coordinates(
        cls, lon: float, lat: float, ele: float | None = None
    ) -> Waypoint:
        """Create a waypoint from the given coordinates.

        Args:
            lon: The longitude of the waypoint.
            lat: The latitude of the waypoint.
            ele: The elevation of the waypoint.
        """
        wpt = cls()
        wpt.lon = Longitude(lon)
        wpt.lat = Latitude(lat)
        if ele is not None:
            wpt.ele = Decimal(ele)
        return wpt

    def _geojson_parse_properties(  # noqa: C901
        self, properties: dict[str, Any]
    ) -> None:
        if (time := properties.get("time")) is not None:
            self.time = isoparse(time)

        if (magvar := properties.get("magvar")) is not None:
            self.magvar = Degrees(magvar)

        if (geoidheight := properties.get("geoidheight")) is not None:
            self.geoidheight = Decimal(geoidheight)

        if (name := properties.get("name")) is not None:
            self.name = name

        if (cmt := properties.get("cmt")) is not None:
            self.cmt = cmt

        if (desc := properties.get("desc")) is not None:
            self.desc = desc

        if (src := properties.get("src")) is not None:
            self.src = src

        for link in properties.get("links", []):
            self.links.append(Link.from_dict(link))

        if (sym := properties.get("sym")) is not None:
            self.sym = sym

        if (type := properties.get("type")) is not None:
            self.type = type

        if (fix := properties.get("fix")) is not None:
            self.fix = Fix(fix)

        if (sat := properties.get("sat")) is not None:
            self.sat = int(sat)

        if (hdop := properties.get("hdop")) is not None:
            self.hdop = Decimal(hdop)

        if (vdop := properties.get("vdop")) is not None:
            self.vdop = Decimal(vdop)

        if (pdop := properties.get("pdop")) is not None:
            self.pdop = Decimal(pdop)

        if (ageofdgpsdata := properties.get("ageofdgpsdata")) is not None:
            self.ageofdgpsdata = Decimal(ageofdgpsdata)

        if (dgpsid := properties.get("dgpsid")) is not None:
            self.dgpsid = DGPSStation(dgpsid)

    @classmethod
    def from_geojson(cls, geojson: dict[str, Any]) -> Waypoint:
        """Create a waypoint from a `GeoJSON <https://geojson.org/>`_ object.

        Args:
            geojson: The GeoJSON object.

        Returns:
            The waypoint.

        Raises:
            InvalidGeoJSONError: If the GeoJSON object is not a valid GeoJSON object.
            UnsupportedGeoJSONTypeError: If the GeoJSON object type is unsupported.
        """
        if isinstance(geojson, dict) and "type" in geojson:
            if geojson["type"] == "Point":
                return cls._geojson_from_coordinates(*geojson["coordinates"])
            elif (
                geojson["type"] == "Feature" and geojson["geometry"]["type"] == "Point"
            ):
                # create the waypoint and set the coordinates
                wpt = cls._geojson_from_coordinates(*geojson["geometry"]["coordinates"])

                # set the properties
                wpt._geojson_parse_properties(geojson["properties"])

                return wpt
            else:
                raise UnsupportedGeoJSONTypeError(
                    f"The GeoJSON object type is unsupported: {geojson['type']}. Should be either a `Point` or a `Feature` object."
                )
        else:
            raise InvalidGeoJSONError(
                "The GeoJSON object is invalid. Should be a either a `Point` or a `Feature` object."
            )

    @classmethod
    def from_geojson_file(cls, geojson_file: str | Path) -> Waypoint:
        """Create a waypoint from a `GeoJSON <https://geojson.org/>`_ file.

        Args:
            geojson_file: The file containing the GeoJSON data.

        Returns:
            The waypoint.

        Raises:
            InvalidGeoJSONError: If the GeoJSON object is not a valid GeoJSON object.
            UnsupportedGeoJSONTypeError: If the GeoJSON object type is unsupported.
        """
        with open(geojson_file, encoding="utf-8") as fh:
            geojson = json.load(fh, parse_float=Decimal)

        return cls.from_geojson(geojson)

    def to_geojson(
        self, type: Literal["Point", "Feature"] = "Feature"
    ) -> dict[str, Any]:
        """Convert the waypoint to a `GeoJSON <https://geojson.org/>`_ object.

        By default, the waypoint is converted to a GeoJSON `Feature` object
        instead of a `Point` object. This way, we can add additional properties
        (i.e. metadata) to the GeoJSON object.

        Args:
            type: The type of GeoJSON object to create. Defaults to `Feature`.

        Returns:
            The GeoJSON object.
        """
        # construct the coordinates
        coordinates = self._geojson_coordinates

        # construct the `Point` geometry
        point_geojson = {
            "type": "Point",
            "coordinates": coordinates,
        }

        if type == "Point":
            return point_geojson

        # construct the properties
        properties = self._geojson_properties

        # construct the `Feature` object
        feature_geojson = {
            "type": "Feature",
            "geometry": point_geojson,
            "properties": properties if properties else None,
        }

        return feature_geojson

    def to_geojson_file(
        self, geojson_file: str | Path, type: Literal["Point", "Feature"] = "Feature"
    ) -> None:
        """Convert the waypoint to a `GeoJSON <https://geojson.org/>`_ file.

        By default, the waypoint is converted to a GeoJSON `Feature` object
        instead of a `Point` object. This way, we can add additional properties
        (i.e. metadata) to the GeoJSON object.

        Args:
            geojson_file: The file to write the GeoJSON object to.
            type: The type of GeoJSON object to create. Defaults to `Feature`.
        """
        with open(geojson_file, "w", encoding="utf-8") as fh:
            json.dump(self.to_geojson(type=type), fh, indent=4, cls=CustomJSONEncoder)

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """Represents the waypoint as a GeoJSON-like `Point` object.

        Implements the `__geo_interface__` protocol -- a GeoJSON-like
        protocol for geo-spatial (GIS) vector data. See the
        `__geo_interface__ specification <https://gist.github.com/sgillies/2217756>`_
        for more details.
        """
        return self.to_geojson(type="Point")

    def distance_to(self, other: Waypoint, radius: int = 6_378_137) -> float:
        """Returns the distance to the other waypoint (in metres) using a simple
        spherical earth model (haversine formula).

        Args:
            other: The other waypoint.
            radius: The radius of the earth (defaults to 6,378,137 metres).

        Returns:
            The distance to the other waypoint (in metres).

        Adapted from: https://github.com/chrisveness/geodesy/blob/33d1bf53c069cd7dd83c6bf8531f5f3e0955c16e/latlon-spherical.js#L187-L205
        """
        R = radius
        φ1, λ1 = radians(self.lat), radians(self.lon)
        φ2, λ2 = radians(other.lat), radians(other.lon)
        Δφ = φ2 - φ1
        Δλ = λ2 - λ1
        a = sin(Δφ / 2) * sin(Δφ / 2) + cos(φ1) * cos(φ2) * sin(Δλ / 2) * sin(Δλ / 2)
        δ = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * δ

    def duration_to(self, other: Waypoint) -> timedelta:
        """Returns the duration to the other waypoint.

        Args:
            other: The other waypoint.

        Returns:
            The duration to the other waypoint.
        """
        if self.time is None or other.time is None:
            return timedelta()
        return other.time - self.time

    def speed_to(self, other: Waypoint) -> float:
        """Returns the speed to the other waypoint (in metres per second).

        Args:
            other: The other waypoint.

        Returns:
            The speed to the other waypoint (in metres per second).
        """
        return self.distance_to(other) / self.duration_to(other).total_seconds()

    def gain_to(self, other: Waypoint) -> Decimal:
        """Returns the elevation gain to the other waypoint (in metres).

        Args:
            other: The other waypoint.

        Returns:
            The elevation gain to the other waypoint (in metres).
        """
        if self.ele is None or other.ele is None:
            return Decimal("0.0")
        return other.ele - self.ele

    def slope_to(self, other: Waypoint) -> Decimal:
        """Returns the slope to the other waypoint (in percent).

        Args:
            other: The other waypoint.

        Returns:
            The slope to the other waypoint (in percent).
        """
        return self.gain_to(other) / Decimal(self.distance_to(other)) * 100
