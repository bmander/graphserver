from math import floor
import struct
from typing import Any, Generator, Optional, Union

from graphserver.vincenty import vincenty


def floatrange(start: float, stop: float, step: float) -> Generator[float, None, None]:
    i = start
    while i <= stop:
        yield i
        i += step


def cons(ary: list[Any]) -> Generator[tuple[Any, Any], None, None]:
    for i in range(len(ary) - 1):
        yield ary[i], ary[i + 1]


def split_line_segment(
    lng1: float, lat1: float, lng2: float, lat2: float, max_section_length: float
) -> Generator[list[float], None, None]:
    # Split line segment defined by (x1, y1, x2, y2) into a set of points
    # (x,y,displacement) spaced less than max_section_length apart

    if lng1 == lng2 and lat1 == lat2:
        yield [lng1, lat1, 0]
        yield [lng2, lat2, 0]
        return

    street_len = vincenty(lat1, lng1, lat2, lng2)
    if street_len is None:
        raise ValueError("Vincenty calculation failed")

    n_sections = int(street_len / max_section_length) + 1

    geolen = ((lat2 - lat1) ** 2 + (lng2 - lng1) ** 2) ** 0.5
    section_len = geolen / n_sections
    street_vector = (lng2 - lng1, lat2 - lat1)
    unit_vector = [x / geolen for x in street_vector]

    for i in range(n_sections + 1):
        vec = [x * section_len * i for x in unit_vector]
        vec = [lng1 + vec[0], lat1 + vec[1], (street_len / n_sections) * i]
        yield vec


def split_line_string(
    points: list[tuple[float, float]], max_section_length: float
) -> list[tuple[float, float, float]]:
    # Split each line segment in the linestring into segment smaller than max_section_length
    split_segs = []
    for (lng1, lat1), (lng2, lat2) in cons(points):
        split_seg = list(split_line_segment(lng1, lat1, lng2, lat2, max_section_length))
        split_segs.append(split_seg)

    # String together the sub linestrings into a single linestring
    ret = []
    segstart_s = 0.0
    for i, split_seg in enumerate(split_segs):
        for x, y, s in split_seg[:-1]:
            ret.append((x, y, s + segstart_s))

        if i == len(split_segs) - 1:
            x, y, s = split_seg[-1]
            ret.append((x, y, s + segstart_s))

        segstart_s += float(split_seg[-1][2])

    return ret


class GridFloat:
    def __init__(self, basename: str) -> None:
        self._read_header(basename + ".hdr")
        self.fp = open(basename + ".flt", "rb")

    def _read_header(self, filename: str) -> None:
        fp = open(filename, "r")

        self.ncols = int(fp.readline()[14:].strip())
        self.nrows = int(fp.readline()[14:].strip())
        self.xllcorner = float(fp.readline()[14:].strip())
        self.yllcorner = float(fp.readline()[14:].strip())
        self.cellsize = float(fp.readline()[14:].strip())
        self.NODATA_value = int(fp.readline()[14:].strip())
        self.byteorder = "<" if fp.readline()[14:].strip() == "LSBFIRST" else ">"

        self.left = self.xllcorner
        self.right = self.xllcorner + (self.ncols - 1) * self.cellsize
        self.bottom = self.yllcorner
        self.top = self.yllcorner + (self.nrows - 1) * self.cellsize

    @property
    def extent(self) -> tuple[float, float, float, float]:
        return (
            self.xllcorner,
            self.yllcorner,
            self.xllcorner + self.cellsize * (self.ncols - 1),
            self.yllcorner + self.cellsize * (self.nrows - 1),
        )

    def contains(self, lng: float, lat: float) -> bool:
        return not (
            lng < self.left or lng >= self.right or lat <= self.bottom or lat > self.top
        )

    def allcells(self) -> tuple[float, ...]:
        self.fp.seek(0)
        return struct.unpack(
            "%s%df" % (self.byteorder, self.nrows * self.ncols), self.fp.read()
        )

    def extremes(self) -> tuple[float, float]:
        mem = self.allcells()
        return (min(mem), max(mem))

    def cell(self, x: int, y: int) -> float:
        position = (y * self.ncols + x) * 4
        self.fp.seek(position)
        result = struct.unpack("%sf" % (self.byteorder), self.fp.read(4))
        return float(result[0])

    def elevation(
        self, lng: float, lat: float, interpolate: bool = True
    ) -> Optional[float]:
        if lng < self.left or lng >= self.right or lat <= self.bottom or lat > self.top:
            return None

        x = (lng - self.left) / self.cellsize
        y = (self.top - lat) / self.cellsize

        ulx = int(floor(x))
        uly = int(floor(y))

        ul = self.cell(ulx, uly)
        if not interpolate:
            return ul
        ur = self.cell(ulx + 1, uly)
        ll = self.cell(ulx, uly + 1)
        lr = self.cell(ulx + 1, uly + 1)

        cellleft = x % 1
        celltop = y % 1
        um = (ur - ul) * cellleft + ul  # uppermiddle
        lm = (lr - ll) * cellleft + ll  # lowermiddle

        return (lm - um) * celltop + um

    def profile(
        self, points: list[tuple[float, float]], resolution: float = 10
    ) -> list[tuple[float, Optional[float]]]:
        return [
            (s, self.elevation(lng, lat))
            for lng, lat, s in split_line_string(points, resolution)
        ]


class BIL:
    def __init__(self, basename: str) -> None:
        self._read_header(basename + ".hdr")
        self.fp = open(basename + ".bil", "rb")

    def _read_header(self, filename: str) -> None:
        fp = open(filename, "r")

        raw_header = dict([x.strip().split() for x in fp.read().strip().split("\n")])

        self.byteorder = "<" if raw_header["BYTEORDER"] == "I" else ">"
        self.layout = raw_header["LAYOUT"]
        self.ncols = int(raw_header["NCOLS"])
        self.nrows = int(raw_header["NROWS"])
        self.nbands = int(raw_header["NBANDS"])
        self.nbits = int(raw_header["NBITS"])
        self.bandrowbytes = int(raw_header["BANDROWBYTES"])
        self.totalrowbytes = int(raw_header["TOTALROWBYTES"])
        self.pixeltype = raw_header["PIXELTYPE"]
        self.ulxmap = float(raw_header["ULXMAP"])
        self.ulymap = float(raw_header["ULYMAP"])
        self.xdim = float(raw_header["XDIM"])
        self.ydim = float(raw_header["YDIM"])
        self.nodata = float(raw_header["NODATA"])

        self.left = self.ulxmap
        self.right = self.ulxmap + (self.ncols - 1) * self.xdim
        self.bottom = self.ulymap - (self.nrows - 1) * self.ydim
        self.top = self.ulymap

    @property
    def extent(self) -> tuple[float, float, float, float]:
        return (self.left, self.bottom, self.right, self.top)

    def contains(self, lng: float, lat: float) -> bool:
        return not (
            lng < self.left or lng >= self.right or lat <= self.bottom or lat > self.top
        )

    def allcells(self) -> tuple[float, ...]:
        self.fp.seek(0)
        return struct.unpack(
            "%s%df" % (self.byteorder, self.nrows * self.ncols), self.fp.read()
        )

    def extremes(self) -> tuple[float, float]:
        mem = self.allcells()
        return (min(mem), max(mem))

    def cell(self, x: int, y: int) -> float:
        position = (y * self.ncols + x) * 4
        self.fp.seek(position)
        result = struct.unpack("%sf" % (self.byteorder), self.fp.read(4))
        return float(result[0])

    def elevation(
        self, lng: float, lat: float, interpolate: bool = True
    ) -> Optional[float]:
        if lng < self.left or lng >= self.right or lat <= self.bottom or lat > self.top:
            return None

        x = (lng - self.left) / self.xdim
        y = (self.top - lat) / self.ydim

        ulx = int(floor(x))
        uly = int(floor(y))

        ul = self.cell(ulx, uly)
        if not interpolate:
            return ul
        ur = self.cell(ulx + 1, uly)
        ll = self.cell(ulx, uly + 1)
        lr = self.cell(ulx + 1, uly + 1)

        cellleft = x % 1
        celltop = y % 1
        um = (ur - ul) * cellleft + ul  # uppermiddle
        lm = (lr - ll) * cellleft + ll  # lowermiddle

        return (lm - um) * celltop + um

    def profile(
        self, points: list[tuple[float, float]], resolution: float = 10
    ) -> list[tuple[float, Optional[float]]]:
        return [
            (s, self.elevation(lng, lat))
            for lng, lat, s in split_line_string(points, resolution)
        ]


class ElevationPile:
    def __init__(self) -> None:
        self.tiles: list[Union[GridFloat, BIL]] = []

    def add(self, dem_basename: str) -> None:
        base_basename = "".join(dem_basename.split(".")[0:-1])
        format = dem_basename.split(".")[-1]
        dem: Union[GridFloat, BIL]
        if format == "flt":
            dem = GridFloat(base_basename)
        elif format == "bil":
            dem = BIL(base_basename)
        else:
            raise Exception("Unknown DEM format '%s'" % format)

        self.tiles.append(dem)

    def elevation(
        self, lng: float, lat: float, interpolate: bool = True
    ) -> Optional[float]:
        for tile in self.tiles:
            if tile.contains(lng, lat):
                return tile.elevation(lng, lat, interpolate)
        return None

    def profile(
        self, points: list[tuple[float, float]], resolution: float = 10
    ) -> list[tuple[float, Optional[float]]]:
        return [
            (s, self.elevation(lng, lat))
            for lng, lat, s in split_line_string(points, resolution)
        ]
