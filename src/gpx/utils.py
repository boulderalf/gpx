"""This module contains various utility functions."""
import re
from datetime import datetime
from decimal import Decimal
from json import JSONEncoder
from typing import Any


def remove_encoding_from_string(s: str) -> str:
    """
    Removes encoding declarations (e.g. encoding="utf-8") from the string, if
    any.

    Args:
        s: The string.

    Returns:
        The string with any encoding declarations removed.
    """
    return re.sub(r"(encoding=[\"\'].+[\"\'])", "", s)


def format_datetime(dt: datetime) -> str:
    """
    Formats a datetime object to the format used in GPX files.

    Args:
        dt: The datetime object.

    Returns:
        The formatted datetime string.
    """
    return dt.isoformat(
        timespec="milliseconds" if dt.microsecond else "seconds"
    ).replace("+00:00", "Z")


class CustomJSONEncoder(JSONEncoder):
    """Custom JSON encoder."""

    def default(self, obj: Any) -> Any:
        """Convert `obj` to a JSON serializable type. Overrides the default
        `JSONEncoder`.
        """
        if isinstance(obj, datetime):
            return format_datetime(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def filter_geojson_properties(geojson_properties: dict[str, Any]) -> dict[str, Any]:
    """
    Filters out `None` values from the GeoJSON properties, as well as removing
    empty links.
    """
    # filter out `None` values
    geojson_properties = {k: v for k, v in geojson_properties.items() if v is not None}

    # remove empty links
    if not any(geojson_properties["links"]):
        geojson_properties.pop("links")

    return geojson_properties
