"""
This module provides a Track object to contain GPX tracks - an ordered list of
points describing a path.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator, Literal

from lxml import etree

from .element import Element
from .link import Link
from .track_segment import TrackSegment
from .types import Latitude, Longitude
from .utils import CustomJSONEncoder, filter_geojson_properties
from .waypoint import Waypoint


class Track(Element):
    """A track class for the GPX data format.

    A track represents an ordered list of points describing a path.

    Args:
        element: The track XML element. Defaults to `None`.
    """

    def __init__(self, element: etree._Element | None = None) -> None:
        super().__init__(element)

        #: GPS name of track.
        self.name: str | None = None

        #: GPS comment for track.
        self.cmt: str | None = None

        #: User description of track.
        self.desc: str | None = None

        #: Source of data. Included to give user some idea of reliability and
        #: accuracy of data.
        self.src: str | None = None

        #: Links to external information about track.
        self.links: list[Link] = []

        #: GPS track number.
        self.number: int | None = None

        #: Type (classification) of track.
        self.type: str | None = None

        #: A Track Segment holds a list of Track Points which are logically
        #: connected in order. To represent a single GPS track where GPS
        #: reception was lost, or the GPS receiver was turned off, start a new
        #: Track Segment for each continuous span of track data.
        self.trksegs: list[TrackSegment] = []
        self.segments = self.trksegs  #: Alias of :attr:`trksegs`.

        if self._element is not None:
            self._parse()

    def __getitem__(self, index: int) -> TrackSegment:
        """Returns the track segment at the given index."""
        return self.trksegs[index]

    def __len__(self) -> int:
        """Returns the number of track segments."""
        return len(self.trksegs)

    def __iter__(self) -> Iterator[TrackSegment]:
        """Iterates over the track segments."""
        yield from self.trksegs

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
        # GPS track number
        if (number := self._element.find("number", namespaces=self._nsmap)) is not None:
            self.number = int(number.text)
        # track type (classification)
        if (_type := self._element.find("type", namespaces=self._nsmap)) is not None:
            self.type = _type.text

        # segments
        for trkseg in self._element.iterfind("trkseg", namespaces=self._nsmap):
            self.trksegs.append(TrackSegment(trkseg))

    def _build(self, tag: str = "trk") -> etree._Element:
        track = super()._build(tag)

        if self.name is not None:
            name = etree.SubElement(track, "name", nsmap=self._nsmap)
            name.text = self.name

        if self.cmt is not None:
            cmt = etree.SubElement(track, "cmt", nsmap=self._nsmap)
            cmt.text = self.cmt

        if self.desc is not None:
            desc = etree.SubElement(track, "desc", nsmap=self._nsmap)
            desc.text = self.desc

        if self.src is not None:
            src = etree.SubElement(track, "src", nsmap=self._nsmap)
            src.text = self.src

        for link in self.links:
            track.append(link._build())

        if self.number is not None:
            number = etree.SubElement(track, "number", nsmap=self._nsmap)
            number.text = str(self.number)

        if self.type is not None:
            _type = etree.SubElement(track, "type", nsmap=self._nsmap)
            _type.text = self.type

        for segment in self.trksegs:
            track.append(segment._build())

        return track

    @property
    def _geojson_bounds(
        self,
    ) -> (
        tuple[Longitude, Latitude, Longitude, Latitude]
        | tuple[Longitude, Latitude, Decimal, Longitude, Latitude, Decimal]
    ):
        """The GeoJSON-compatible bounds.

        The bounds are of the form (minlon, minlat, minele (alt), maxlon,
        maxlat, maxele (alt)], where ele is optional.
        """
        min_lat, min_lon, max_lat, max_lon = self.bounds

        # possibly include elevation bounds
        if any(
            trkpt.ele is not None for trkseg in self.trksegs for trkpt in trkseg.trkpts
        ):
            # determine elevation bounds
            min_ele = min(
                trkpt.ele
                for trkseg in self.trksegs
                for trkpt in trkseg.trkpts
                if trkpt.ele is not None
            )
            max_ele = max(
                trkpt.ele
                for trkseg in self.trksegs
                for trkpt in trkseg.trkpts
                if trkpt.ele is not None
            )
            return min_lon, min_lat, min_ele, max_lon, max_lat, max_ele

        return min_lon, min_lat, max_lon, max_lat

    @classmethod
    def from_geojson(cls, geojson: dict[str, Any]) -> Track:  # noqa: C901
        trk = cls()

        if geojson["type"] == "MultiLineString":
            for segment_coordinates in geojson["coordinates"]:
                trkseg = TrackSegment()
                for coordinates in segment_coordinates:
                    trkseg.trkpts.append(
                        Waypoint._geojson_from_coordinates(*coordinates)
                    )
                trk.trksegs.append(trkseg)
            return trk
        elif (
            geojson["type"] == "Feature"
            and geojson["geometry"]["type"] == "MultiLineString"
        ):
            if "coordinatesProperties" in geojson["properties"]:
                for segment_coordinates, segment_properties in zip(
                    geojson["geometry"]["coordinates"],
                    geojson["properties"]["coordinatesProperties"],
                ):
                    trkseg = TrackSegment()

                    for coordinates, properties in zip(
                        segment_coordinates, segment_properties
                    ):
                        # create the track point and set the coordinates
                        trkpt = Waypoint._geojson_from_coordinates(*coordinates)

                        # set the properties
                        trkpt._geojson_parse_properties(properties)

                        # add the route point to the route
                        trkseg.trkpts.append(trkpt)

                    trk.trksegs.append(trkseg)
            else:
                for segment_coordinates in geojson["geometry"]["coordinates"]:
                    trkseg = TrackSegment()

                    for coordinates in segment_coordinates:
                        trkseg.trkpts.append(
                            Waypoint._geojson_from_coordinates(*coordinates)
                        )

                    trk.trksegs.append(trkseg)

            # set the properties
            if (name := geojson["properties"].get("name")) is not None:
                trk.name = name

            if (cmt := geojson["properties"].get("cmt")) is not None:
                trk.cmt = cmt

            if (desc := geojson["properties"].get("desc")) is not None:
                trk.desc = desc

            if (src := geojson["properties"].get("src")) is not None:
                trk.src = src

            for link in geojson["properties"].get("links", []):
                trk.links.append(Link.from_dict(link))

            if (number := geojson["properties"].get("number")) is not None:
                trk.number = number

            if (type := geojson["properties"].get("type")) is not None:
                trk.type = type

            return trk
        else:
            raise ValueError(
                f"Unsupported GeoJSON object type: {geojson['geometry']['type'] if geojson['type'] == 'Feature' else geojson['type']}. Should be either a `MultiLineString` or a `Feature` object."
            )

    def to_geojson(
        self, type: Literal["MultiLineString", "Feature"] = "Feature"
    ) -> dict[str, Any]:
        """Convert the track to a `GeoJSON <https://geojson.org/>`_ object.

        By default, the track is converted to a GeoJSON `Feature` object instead
        of a `MultiLineString` object. This way, we can add additional
        properties (i.e. metadata) to the GeoJSON object.

        Args:
            type: The type of GeoJSON object to create. Defaults to `Feature`.

        Returns:
            The GeoJSON object.
        """
        # construct the coordinates
        coordinates = [
            [trkpt._geojson_coordinates for trkpt in trkseg.trkpts]
            for trkseg in self.trksegs
        ]

        # construct the `MultiLineString` geometry
        multilinestring_geojson = {
            "type": "MultiLineString",
            "bbox": self._geojson_bounds,
            "coordinates": coordinates,
        }

        if type == "MultiLineString":
            return multilinestring_geojson

        # construct the properties
        properties: dict[str, Any] = {
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
        coordinates_properties = [
            [trkpt._geojson_properties for trkpt in trkseg.trkpts]
            for trkseg in self.trksegs
        ]
        if any([any(cp) for cp in coordinates_properties]):
            properties["coordinatesProperties"] = coordinates_properties

        # construct the `Feature` object
        feature_geojson = {
            "type": "Feature",
            "geometry": multilinestring_geojson,
        }

        if properties:
            feature_geojson["properties"] = properties

        return feature_geojson

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """Represents the track as a GeoJSON-like `MultiLineString` object.

        Implements the `__geo_interface__` protocol -- a GeoJSON-like
        protocol for geo-spatial (GIS) vector data. See the
        `__geo_interface__ specification <https://gist.github.com/sgillies/2217756>`_
        for more details.
        """
        return self.to_geojson(type="MultiLineString")

    def to_geojson_file(
        self,
        geojson_file: str | Path,
        type: Literal["MultiLineString", "Feature"] = "Feature",
    ) -> None:
        """Convert the track to a `GeoJSON <https://geojson.org/>`_ file.

        By default, the track is converted to a GeoJSON `Feature` object instead
        of a `MultiLineString` object. This way, we can add additional
        properties (i.e. metadata) to the GeoJSON object.

        Args:
            geojson_file: The file to write the GeoJSON object to.
            type: The type of GeoJSON object to create. Defaults to `Feature`.
        """
        with open(geojson_file, "w", encoding="utf-8") as fh:
            json.dump(self.to_geojson(type=type), fh, indent=4, cls=CustomJSONEncoder)

    @property
    def bounds(self) -> tuple[Latitude, Longitude, Latitude, Longitude]:
        """The bounds of the track."""
        return (
            min(trkpt.lat for trkseg in self.trksegs for trkpt in trkseg),
            min(trkpt.lon for trkseg in self.trksegs for trkpt in trkseg),
            max(trkpt.lat for trkseg in self.trksegs for trkpt in trkseg),
            max(trkpt.lon for trkseg in self.trksegs for trkpt in trkseg),
        )

    @property
    def total_distance(self) -> float:
        """The total distance of the track (in metres)."""
        return sum(trkseg.total_distance for trkseg in self.trksegs)

    distance = total_distance  #: Alias of :attr:`total_distance`.

    @property
    def total_duration(self) -> timedelta:
        """The total duration of the track (in seconds)."""
        return sum([trkseg.total_duration for trkseg in self.trksegs], timedelta())

    duration = total_duration  #: Alias of :attr:`total_duration`.

    @property
    def moving_duration(self) -> timedelta:
        """The moving duration of the track.

        The moving duration is the total duration with a
        speed greater than 0.5 km/h.
        """
        return sum([trkseg.moving_duration for trkseg in self.trksegs], timedelta())

    @property
    def avg_speed(self) -> float:
        """The average speed of the track (in metres / second)."""
        return self.total_distance / self.total_duration.total_seconds()

    speed = avg_speed  #: Alias of :attr:`avg_speed`.

    @property
    def avg_moving_speed(self) -> float:
        """The average moving speed of the track (in metres / second)."""
        return self.total_distance / self.moving_duration.total_seconds()

    @property
    def max_speed(self) -> float:
        """The maximum speed of the track (in metres / second)."""
        return max(trkseg.max_speed for trkseg in self.trksegs)

    @property
    def min_speed(self) -> float:
        """The minimum speed of the track (in metres / second)."""
        return min(trkseg.min_speed for trkseg in self.trksegs)

    @property
    def speed_profile(self) -> list[tuple[datetime, float]]:
        """The speed profile of the track.

        The speed profile is a list of (timestamp, speed) tuples.
        """
        profile = []
        for trkseg in self.trksegs:
            profile += trkseg.speed_profile
        return profile

    @property
    def avg_elevation(self) -> Decimal:
        """The average elevation (in metres)."""
        _eles = [
            trkpt.ele
            for trkseg in self.trksegs
            for trkpt in trkseg
            if trkpt.ele is not None
        ]
        return sum(_eles, Decimal("0")) / len(_eles)

    elevation = avg_elevation  #: Alias of :attr:`avg_elevation`.

    @property
    def max_elevation(self) -> Decimal:
        """The maximum elevation of the track (in metres)."""
        return max(trkseg.max_elevation for trkseg in self.trksegs)

    @property
    def min_elevation(self) -> Decimal:
        """The minimum elevation of the track (in metres)."""
        return min(trkseg.min_elevation for trkseg in self.trksegs)

    @property
    def diff_elevation(self) -> Decimal:
        """The difference in elevation of the track (in metres)."""
        return self.max_elevation - self.min_elevation

    @property
    def total_ascent(self) -> Decimal:
        """The total ascent of the track (in metres)."""
        return sum([trkseg.total_ascent for trkseg in self.trksegs], Decimal("0"))

    @property
    def total_descent(self) -> Decimal:
        """The total descent of the track (in metres)."""
        return abs(sum([trkseg.total_descent for trkseg in self.trksegs], Decimal("0")))

    @property
    def elevation_profile(self) -> list[tuple[float, Decimal]]:
        """The elevation profile of the track.

        The elevation profile is a list of (distance, elevation) tuples.
        """
        distance = 0.0
        profile = []
        if self.trksegs[0]._points_with_ele[0].ele is not None:
            profile.append((distance, self.trksegs[0]._points_with_ele[0].ele))
        for trkseg in self.trksegs:
            for i, point in enumerate(trkseg._points_with_ele[1:], 1):
                if point.ele is not None:
                    distance += trkseg._points_with_ele[i - 1].distance_to(point)
                    profile.append((distance, point.ele))
        return profile
