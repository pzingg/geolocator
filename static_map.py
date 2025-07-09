import staticmaps
import s2sphere
import typing
import requests
import json
import io
import pathlib
import os
import sys
from PIL import Image as PIL_Image  # type: ignore
from PIL import ImageDraw as PIL_ImageDraw  # type: ignore

GITHUB_URL = "https://github.com/flopp/py-staticmaps"
LIB_NAME = "py-staticmaps"
VERSION = "0.4.0"

# PROVIDER = "osm"
PROVIDER = "stadia"
BOUNDS = "51.0,-126.0 31.5,-113.0"
WIDTH = 22 * 72
HEIGHT = 28 * 72
STADIA_ZOOM = 6
LIGHT_ORANGE = staticmaps.Color(0xFF, 0xD5, 0x80)

class SingleTileProvider():
    def __init__(self, attribution: str, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self._attribution = attribution
    
    def attribution(self):
        return self._attribution

    def tile_size(self) -> int:
        return max(self._width, self._height) 

    def max_zoom(self) -> int:
        return 24


class LabeledMarker(staticmaps.Marker):
    def __init__(self, latlng: s2sphere.LatLng, color: staticmaps.Color = staticmaps.RED, size: int = 10, label: typing.Optional[str] = None) -> None:
        staticmaps.Marker.__init__(self, latlng, color, size)
        self._label = label

def latlng_to_string(latlng: s2sphere.LatLng):
    return f"{latlng.lat().degrees},{latlng.lng().degrees}"

def stadia_color(color: staticmaps.Color) -> str:
    s = color.hex_rgb()
    # Strip off the #
    return s[1:]

def stadia_marker(marker: LabeledMarker) -> str:
    lat = marker.latlng().lat().degrees
    lng = marker.latlng().lng().degrees
    color = stadia_color(marker._color)
    style = "stamen_terrain_sm"
    label = marker._label[:1]
    return f"&m={lat},{lng},{style},{color},{label}"

def add_markers(context: staticmaps.Context, json_file):
    with open(json_file, 'r') as f:
        markers = json.load(f)
    for marker in markers:
        latlng = staticmaps.create_latlng(marker['lat_lng'][0], marker['lat_lng'][1])
        obj = LabeledMarker(latlng, color=LIGHT_ORANGE, size=4, label=marker['name'])
        context.add_object(obj)

def fetch_stadia(context: staticmaps.Context, api_key: str, cache_dir: str, center: s2sphere.LatLng, zoom: int, width: int, height: int) -> typing.Optional[bytes]:
    user_agent = f"Mozilla/5.0+(compatible; {LIB_NAME}/{VERSION}; {GITHUB_URL})"

    file_name = None
    if cache_dir is not None:
        file_name = os.path.join(cache_dir, 'stadia-terrain', str(zoom), '1', '1.png')
        if os.path.isfile(file_name):
            with open(file_name, "rb") as f:
                data = f.read()
                print(f"read {len(data)} cached tile bytes")
                return data

    c = latlng_to_string(center)
    url = f"https://tiles.stadiamaps.com/static/stamen_terrain.png?api_key={api_key}&size={width}x{height}&center={c}&zoom={zoom}"

    if context._objects is not None:
        url = url + ''.join([stadia_marker(marker) for marker in context._objects if isinstance(marker, LabeledMarker)])

    print(f"cache file {file_name}")
    print(f"url {url}")
    res = requests.get(url, headers={"user-agent": user_agent})
    if res.status_code == 200:
        data = res.content
    else:
        print(f"fetch -> {res.status_code}")
        raise RuntimeError("fetch {} yields {}".format(url, res.status_code))

    if file_name is not None:
        print(f"caching {len(data)} tile bytes to {file_name}")
        pathlib.Path(os.path.dirname(file_name)).mkdir(parents=True, exist_ok=True)
        with open(file_name, "wb") as f:
            f.write(data)
    else:
        print(f"downloaded {len(data)} tile bytes")

    return data

def render_stadia(context: staticmaps.Context, api_key: str, width: int, height: int) -> PIL_Image:
    """Render context using PILLOW

    :param width: width of static map
    :type width: int
    :param height: height of static map
    :type height: int
    :return: pillow image
    :rtype: PIL_Image
    :raises RuntimeError: raises runtime error if map has no center and zoom
    """
    center, zoom = context.determine_center_zoom(width, height)
    if center is None or zoom is None:
        raise RuntimeError("Cannot render map without center/zoom.")

    # We'll override
    center = context._bounds.get_center()
    zoom = STADIA_ZOOM

    image = PIL_Image.new("RGBA", (width, height))
    draw = PIL_ImageDraw.Draw(image)

    image_data = fetch_stadia(context, api_key, context._cache_dir, center, zoom, width, height)
    if image_data is None:
        return image

    tile_img = PIL_Image.open(io.BytesIO(image_data))
    image.paste(tile_img)

    return image


context = staticmaps.Context()
add_markers(context, "C:\\Users\\Rachel\\Documents\\GitHub\\geolocator\\map_data.json")
bounds = staticmaps.parse_latlngs2rect(BOUNDS)
print(f"bounds: {bounds}")
context.add_bounds(bounds)

if PROVIDER == 'osm':
    context.set_cache_dir("C:\\Users\\Rachel\\Documents\\GitHub\\geolocator\\cache")
    context.set_tile_provider(staticmaps.tile_provider_OSM)

    # render non-anti-aliased png
    image = context.render_pillow(WIDTH, HEIGHT)
    image.save("pacific_waterfalls_osm.pillow.png")

    # render anti-aliased png (this only works if pycairo is installed)
    image = context.render_cairo(WIDTH, HEIGHT)
    image.write_to_png("pacific_waterfalls.cairo.png")

    # render svg
    svg_image = context.render_svg(WIDTH, HEIGHT)
    with open("pacific_waterfalls.svg", "w", encoding="utf-8") as f:
        svg_image.write(f, pretty=True)

if PROVIDER == 'stadia':
    with open('api_key.txt', 'r') as f:
        api_key = f.readline().strip()

    context.set_cache_dir(None)
    # context.set_cache_dir("C:\\Users\\Rachel\\Documents\\GitHub\\geolocator\\cache")
    p = SingleTileProvider('Maps (C) StadiaMaps (C) StamenDesign, Data (C) OpenStreetMap.org contributor', WIDTH, HEIGHT)
    context.set_tile_provider(p)

    # render non-anti-aliased png
    image = render_stadia(context, api_key, p._width, p._height)
    image.save("pacific_waterfalls_stadia.pillow.png")
