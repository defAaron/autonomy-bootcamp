"""
TODO(bootcamper): write the tests for ``src/waypoint_utils.py`` in here.

The example below covers files that parse fine: with and without ``home``,
and files with comments and blank lines in them. The rest is yours:

- Bad data: a file whose top level isn't a mapping, waypoints missing
  ``lat``, ``lon``, or ``alt``, values that aren't numbers, YAML that
  doesn't parse, and a file that isn't there.
- Out of range: latitudes past +/-90 and longitudes past +/-180 get
  rejected.
- Nothing to work with: an empty file, an empty ``waypoints`` list, and
  ``sort_clockwise_sweep`` given a list of 0 or 1 waypoints.
- ``east_north_coordinate_offset_m``: offsets you worked out yourself,
  compared with ``pytest.approx``. Never use ``==`` on meters.
- Ordering: with no ``home``, ``sort_clockwise_sweep`` goes clockwise
  starting from north.
- With a ``home``: the order starts in home's direction instead, and goes
  back to starting at north if home is right on top of the centroid.
- Two waypoints in the same direction: the closer one comes first.
- Parsing gives you frozen ``Coordinate`` objects that can't be changed.

Graded by ``warg run utils grade-tests``: pass on the real code, 90% branch
coverage, and fail on every broken copy in ``grader/mutants/``.
"""

import dataclasses

import pytest

from src.types import Coordinate
from src.waypoint_utils import (
    east_north_coordinate_offset_m,
    parse_waypoints_file,
    sort_clockwise_sweep,
)

# The helper and the test below are given to you.


def write_to_tmp_waypoints_file(tmp_path, text):
    """Write ``text`` to a YAML file and hand back its path.

    ``tmp_path`` is a pytest fixture: a fresh empty directory per test.
    """
    path = tmp_path / "waypoints.yaml"
    path.write_text(text)
    return path


# One test, three files. ``parametrize`` runs the test body once per
# ``(text, expected)`` pair, and ``ids`` names each run so a failure tells you
# which file broke.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            """
            home: {lat: 1, lon: 2, alt: 3}
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
        (
            """
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
              - {lat: 7, lon: 8, alt: 9}
            """,
            (None, [Coordinate(4, 5, 6), Coordinate(7, 8, 9)]),
        ),
        (
            """
            # a lap

            home: {lat: 1, lon: 2, alt: 3}

            waypoints:
              # first leg
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
    ],
    ids=["home-and-waypoints", "no-home", "comments-and-blank-lines"],
)
def test_parse_waypoints_file_success(tmp_path, text, expected):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    assert parse_waypoints_file(path) == expected


# parse_waypoints_file: empty or valid files with no waypoints

@pytest.mark.parametrize(
    "text",
    [
        "",
        "# only a comment\n",
        "waypoints: []\n",
        "waypoints:\n",
        "# no data\nhome:\nwaypoints:\n",
    ],
    ids=[
        "empty-file",
        "comment-only",
        "empty-list",
        "empty-waypoints",
        "empty-home-and-waypoints",
    ],
)
def test_parse_waypoints_file_empty(tmp_path, text):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    assert parse_waypoints_file(path) == (None, [])


@pytest.mark.parametrize(
    ("text", "expected_home"),
    [
        (
            "home: {lat: 1, lon: 2, alt: 3}\nwaypoints: []\n",
            Coordinate(1, 2, 3),
        ),
        (
            "home: {lat: 1, lon: 2, alt: 3}\n",
            Coordinate(1, 2, 3),
        ),
    ],
    ids=["home-with-empty-list", "home-without-waypoints-key"],
)
def test_parse_waypoints_file_home_without_waypoints(
    tmp_path, text, expected_home
):
    path = write_to_tmp_waypoints_file(tmp_path, text)

    home, waypoints = parse_waypoints_file(path)

    assert home == expected_home
    assert waypoints == []


# parse_waypoints_file: malformed YAML and invalid data

@pytest.mark.parametrize(
    "text",
    [
        "- {lat: 1, lon: 2, alt: 3}\n",
        "waypoints: {lat: 1, lon: 2, alt: 3}\n",
        'waypoints: "not a list"\n',
        "waypoints:\n  - 42\n",
        'waypoints:\n  - "not a mapping"\n',
        "home: 7\nwaypoints: []\n",
        'home: "not a mapping"\nwaypoints: []\n',
        "waypoints: [unclosed\n",
        "waypoints:\n  - {lat: , lon: 5, alt: 6}\n",
        "q3ji340asjd\n",
    ],
    ids=[
        "top-level-is-list",
        "waypoints-is-mapping",
        "waypoints-is-string",
        "waypoint-is-number",
        "waypoint-is-string",
        "home-is-number",
        "home-is-string",
        "invalid-yaml",
        "invalid-coordinate-value",
        "invalid-top-level-scalar",
    ],
)
def test_parse_waypoints_file_bad_structure_raises(tmp_path, text):
    path = write_to_tmp_waypoints_file(tmp_path, text)

    with pytest.raises(ValueError):
        parse_waypoints_file(path)


@pytest.mark.parametrize(
    "text",
    [
        "waypoints:\n  - {lon: 2, alt: 3}\n",
        "waypoints:\n  - {lat: 1, alt: 3}\n",
        "waypoints:\n  - {lat: 1, lon: 2}\n",
        "home: {lon: 2, alt: 3}\nwaypoints: []\n",
        "home: {lat: 1, alt: 3}\nwaypoints: []\n",
        "home: {lat: 1, lon: 2}\nwaypoints: []\n",
    ],
    ids=[
        "waypoint-missing-lat",
        "waypoint-missing-lon",
        "waypoint-missing-alt",
        "home-missing-lat",
        "home-missing-lon",
        "home-missing-alt",
    ],
)
def test_parse_waypoints_file_missing_coordinate_raises(tmp_path, text):
    path = write_to_tmp_waypoints_file(tmp_path, text)

    with pytest.raises(ValueError):
        parse_waypoints_file(path)


@pytest.mark.parametrize(
    "text",
    [
        'waypoints:\n  - {lat: "abc", lon: 2, alt: 3}\n',
        'waypoints:\n  - {lat: 1, lon: "abc", alt: 3}\n',
        "waypoints:\n  - {lat: 1, lon: 2, alt: [3]}\n",
        'home: {lat: "abc", lon: 2, alt: 3}\nwaypoints: []\n',
        'home: {lat: 1, lon: 2, alt: "abc"}\nwaypoints: []\n',
    ],
    ids=[
        "waypoint-lat-not-numeric",
        "waypoint-lon-not-numeric",
        "waypoint-alt-not-numeric",
        "home-lat-not-numeric",
        "home-alt-not-numeric",
    ],
)
def test_parse_waypoints_file_non_numeric_values_raise(tmp_path, text):
    path = write_to_tmp_waypoints_file(tmp_path, text)

    with pytest.raises(ValueError):
        parse_waypoints_file(path)


def test_parse_waypoints_file_missing_file_raises(tmp_path):
    path = tmp_path / "does-not-exist.yaml"

    with pytest.raises(OSError):
        parse_waypoints_file(path)


# parse_waypoints_file: coordinate ranges

@pytest.mark.parametrize(
    ("lat", "lon"),
    [
        (90.1, 0),
        (-90.1, 0),
        (100, 0),
        (0, 180.1),
        (0, -180.1),
    ],
    ids=[
        "lat-above-90",
        "lat-below-minus-90",
        "lat-100",
        "lon-above-180",
        "lon-below-minus-180",
    ],
)
def test_parse_waypoints_file_out_of_range_raises(tmp_path, lat, lon):
    path = write_to_tmp_waypoints_file(
        tmp_path,
        f"waypoints:\n  - {{lat: {lat}, lon: {lon}, alt: 0}}\n",
    )

    with pytest.raises(ValueError):
        parse_waypoints_file(path)


@pytest.mark.parametrize(
    ("lat", "lon"),
    [
        (90, 180),
        (-90, -180),
    ],
    ids=["maximum-boundaries", "minimum-boundaries"],
)
def test_parse_waypoints_file_range_limits_are_inclusive(
    tmp_path, lat, lon
):
    path = write_to_tmp_waypoints_file(
        tmp_path,
        f"waypoints:\n  - {{lat: {lat}, lon: {lon}, alt: 0}}\n",
    )

    assert parse_waypoints_file(path) == (
        None,
        [Coordinate(lat, lon, 0)],
    )


@pytest.mark.parametrize(
    ("lat", "lon"),
    [
        (91, 0),
        (-91, 0),
        (0, 181),
        (0, -181),
    ],
    ids=[
        "home-lat-above-90",
        "home-lat-below-minus-90",
        "home-lon-above-180",
        "home-lon-below-minus-180",
    ],
)
def test_parse_waypoints_file_home_out_of_range_raises(
    tmp_path, lat, lon
):
    path = write_to_tmp_waypoints_file(
        tmp_path,
        f"home: {{lat: {lat}, lon: {lon}, alt: 0}}\n"
        "waypoints: []\n",
    )

    with pytest.raises(ValueError):
        parse_waypoints_file(path)


def test_parsed_coordinates_are_frozen(tmp_path):
    path = write_to_tmp_waypoints_file(
        tmp_path,
        "waypoints:\n  - {lat: 1, lon: 2, alt: 3}\n",
    )

    _, waypoints = parse_waypoints_file(path)

    with pytest.raises(dataclasses.FrozenInstanceError):
        waypoints[0].lat = 5.0


# east_north_coordinate_offset_m

METERS_PER_MILLIDEGREE = 111.1951


@pytest.mark.parametrize(
    ("from_lat", "from_lon", "to_lat", "to_lon", "expected_east", "expected_north"),
    [
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        (0.0, 0.0, 0.001, 0.0, 0.0, METERS_PER_MILLIDEGREE),
        (0.0, 0.0, -0.001, 0.0, 0.0, -METERS_PER_MILLIDEGREE),
        (0.0, 0.0, 0.0, 0.001, METERS_PER_MILLIDEGREE, 0.0),
        (0.0, 0.0, 0.0, -0.001, -METERS_PER_MILLIDEGREE, 0.0),
        (
            0.0, 0.0, 0.001, 0.001,
            METERS_PER_MILLIDEGREE, METERS_PER_MILLIDEGREE,
        ),
        (60.0, 0.0, 60.0, 0.001, METERS_PER_MILLIDEGREE / 2, 0.0),
        (60.0, 0.0, 60.0, -0.001, -METERS_PER_MILLIDEGREE / 2, 0.0),
        (0.0, 0.0, 0.002, 0.0, 0.0, 2 * METERS_PER_MILLIDEGREE),
    ],
    ids=[
        "same-coordinate",
        "north",
        "south",
        "east-at-equator",
        "west-at-equator",
        "northeast",
        "east-at-60-degrees",
        "west-at-60-degrees",
        "two-millidegrees-north",
    ],
)
def test_east_north_coordinate_offset_m(
    from_lat,
    from_lon,
    to_lat,
    to_lon,
    expected_east,
    expected_north,
):
    east, north = east_north_coordinate_offset_m(
        from_lat, from_lon, to_lat, to_lon
    )

    assert east == pytest.approx(expected_east, abs=0.01)
    assert north == pytest.approx(expected_north, abs=0.01)


# sort_clockwise_sweep: empty and single-waypoint cases

def test_sort_empty_list():
    assert sort_clockwise_sweep([]) == []


def test_sort_single_waypoint():
    only = Coordinate(1.0, 2.0, 3.0)

    assert sort_clockwise_sweep([only]) == [only]


# sort_clockwise_sweep: clockwise ordering

NORTH = Coordinate(0.001, 0.0, 10)
EAST = Coordinate(0.0, 0.001, 10)
SOUTH = Coordinate(-0.001, 0.0, 10)
WEST = Coordinate(0.0, -0.001, 10)


def test_sort_without_home_starts_north_and_goes_clockwise():
    shuffled = [WEST, SOUTH, NORTH, EAST]

    assert sort_clockwise_sweep(shuffled) == [
        NORTH, EAST, SOUTH, WEST
    ]


def test_sort_with_home_starts_in_homes_direction():
    home = Coordinate(0.0, 0.005, 0)
    shuffled = [WEST, SOUTH, NORTH, EAST]

    assert sort_clockwise_sweep(shuffled, home) == [
        EAST, SOUTH, WEST, NORTH
    ]


def test_sort_with_home_on_centroid_starts_north():
    home = Coordinate(0.0, 0.0, 0)
    shuffled = [WEST, SOUTH, NORTH, EAST]

    assert sort_clockwise_sweep(shuffled, home) == [
        NORTH, EAST, SOUTH, WEST
    ]


def test_sort_same_bearing_closer_first():
    near = Coordinate(0.001, 0.0, 10)
    far = Coordinate(0.002, 0.0, 10)
    south = Coordinate(-0.003, 0.0, 10)

    assert sort_clockwise_sweep([far, south, near]) == [
        near, far, south
    ]


def test_sort_does_not_modify_input():
    original = [WEST, SOUTH, NORTH, EAST]
    expected = original.copy()

    sort_clockwise_sweep(original)

    assert original == expected


def test_sort_realistic_geographic_coordinates():
    north = Coordinate(43.001, -79.0, 10)
    east = Coordinate(43.0, -78.999, 20)
    south = Coordinate(42.999, -79.0, 30)
    west = Coordinate(43.0, -79.001, 40)

    assert sort_clockwise_sweep(
        [south, west, east, north]
    ) == [north, east, south, west]


def test_sort_multiple_waypoints_in_same_direction():
    far = Coordinate(0.002, 0.0, 10)
    near = Coordinate(0.001, 0.0, 20)
    east = Coordinate(0.0, 0.001, 30)
    west = Coordinate(0.0, -0.001, 40)
    south = Coordinate(-0.003, 0.0, 50)

    assert sort_clockwise_sweep(
        [far, near, east, west, south]
    ) == [near, far, east, south, west]


def test_sort_with_home_north_of_centroid():
    far = Coordinate(0.002, 0.0, 10)
    near = Coordinate(0.001, 0.0, 20)
    east = Coordinate(0.0, 0.001, 30)
    west = Coordinate(0.0, -0.001, 40)
    south = Coordinate(-0.003, 0.0, 50)
    home = Coordinate(0.001, 0.0, 60)

    assert sort_clockwise_sweep(
        [far, near, east, west, south], home
    ) == [near, far, east, south, west]
