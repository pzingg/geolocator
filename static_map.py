import staticmaps
import s2sphere
import typing
import requests
import io
import pathlib
import os
import sys
from PIL import Image as PIL_Image  # type: ignore
from PIL import ImageDraw as PIL_ImageDraw  # type: ignore

GITHUB_URL = "https://github.com/flopp/py-staticmaps"
LIB_NAME = "py-staticmaps"
VERSION = "0.4.0"

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

def latlng_to_string(latlng: s2sphere.LatLng):
    return f"{latlng.lat().degrees},{latlng.lng().degrees}"

def stadia_color(color: staticmaps.Color) -> str:
    s = color.hex_rgb()
    # Strip off the #
    return s[1:]

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
        url = url + ''.join([f"&m={latlng_to_string(marker.latlng())},,{stadia_color(marker._color)}" for marker in context._objects if isinstance(marker, staticmaps.Marker)])

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

    image = PIL_Image.new("RGBA", (width, height))
    draw = PIL_ImageDraw.Draw(image)

    image_data = fetch_stadia(context, api_key, context._cache_dir, center, zoom, width, height)
    if image_data is None:
        return image

    tile_img = PIL_Image.open(io.BytesIO(image_data))
    image.paste(tile_img)

    return image

provider = 'stadia'
frankfurt = staticmaps.create_latlng(50.110644, 8.682092)
newyork = staticmaps.create_latlng(40.712728, -74.006015)

context = staticmaps.Context()
context.add_object(staticmaps.Line([frankfurt, newyork], color=staticmaps.BLUE, width=4))
context.add_object(staticmaps.Marker(frankfurt, color=staticmaps.GREEN, size=12))
context.add_object(staticmaps.Marker(newyork, color=staticmaps.RED, size=12))

if provider == 'osm':
    context.set_cache_dir("C:\\Users\\Rachel\\Documents\\GitHub\\geolocator\\cache")
    context.set_tile_provider(staticmaps.tile_provider_OSM)

    # render non-anti-aliased png
    image = context.render_pillow(800, 500)
    image.save("frankfurt_newyork_osm.pillow.png")

    # render anti-aliased png (this only works if pycairo is installed)
    # image = context.render_cairo(800, 500)
    # image.write_to_png("frankfurt_newyork.cairo.png")

    # render svg
    # svg_image = context.render_svg(800, 500)
    # with open("frankfurt_newyork.svg", "w", encoding="utf-8") as f:
    #    svg_image.write(f, pretty=True)

if provider == 'stadia':
    with open('api_key.txt', 'r') as f:
        api_key = f.readline().strip()

    context.set_cache_dir(None)
    # context.set_cache_dir("C:\\Users\\Rachel\\Documents\\GitHub\\geolocator\\cache")
    p = SingleTileProvider('Maps (C) StadiaMaps (C) StamenDesign, Data (C) OpenStreetMap.org contributor', 800, 500)
    context.set_tile_provider(p)

    # render non-anti-aliased png
    image = render_stadia(context, api_key, p._width, p._height)
    image.save("frankfurt_newyork_stadia.pillow.png")
