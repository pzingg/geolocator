import staticmaps
import s2sphere
import typing
import sys

with open('api_key.txt', 'r') as f:
    api_key = f.readline()

class StadiaStaticProvider(staticmaps.TileProvider):
    def __init__( self,
        name: str,
        url_pattern: str,
        api_key: typing.Optional[str] = None,
        center: typing.Optional[s2sphere.LatLng] = None,
        zoom: typing.Optional[int] = None,
        markers: typing.Optional[typing.List] = None,
        attribution: typing.Optional[str] = None,
        max_zoom: int = 24,) -> None:
        super().__init__(name, url_pattern, api_key)
        self.center = center
        self.markers = markers

    def url(self, zoom: int, x: int, y: int) -> typing.Optional[str]:
        """Return the url of the tile provider
        """
        if not self._api_key:
            print("No api key")
            return None
        if len(self._url_pattern.template) == 0:
            print("No url template")
            return None
        if (zoom < 0) or (zoom > self._max_zoom):
            print(f"Zoom {zoom} out of range")
            return None
        
        url =  self._url_pattern.substitute(c=self._center, z=self._zoom, k=self._api_key)
        if self.markers is not None:
            url = url + [f"&m={lat,lng}" for lat, lng in self.markers]
            print(f"url: {url}")
            sys.exit(1)

        return url


markers = [
    (50.110644, 8.682092),
    (40.712728, -74.006015)
]

frankfurt = staticmaps.create_latlng(50.110644, 8.682092)
newyork = staticmaps.create_latlng(40.712728, -74.006015)

context = staticmaps.Context()
context.add_object(staticmaps.Line([frankfurt, newyork], color=staticmaps.BLUE, width=4))
context.add_object(staticmaps.Marker(frankfurt, color=staticmaps.GREEN, size=12))
context.add_object(staticmaps.Marker(newyork, color=staticmaps.RED, size=12))
center, zoom = context.determine_center_zoom(800, 500)
context.set_center(center)
context.set_zoom(zoom)

print(f"api_key {api_key}")
tile_provider_StadiaTerrain = StadiaStaticProvider(
    "stadia-terrain",
    url_pattern="https://tiles.stadiamaps.com/static/stamen_terrain.png?api_key=$k",
    api_key=api_key,
    markers=markers,
    center=center,
    zoom=zoom,
    attribution="Maps (C) Stadia Maps (C) OpenMapTiles (C) OpenStreetMap.org contributors",
    max_zoom=20,
)

context.set_tile_provider(tile_provider_StadiaTerrain)

# render non-anti-aliased png
image = context.render_pillow(800, 500)
image.save("frankfurt_newyork.pillow.png")

# render anti-aliased png (this only works if pycairo is installed)
image = context.render_cairo(800, 500)
image.write_to_png("frankfurt_newyork.cairo.png")

# render svg
svg_image = context.render_svg(800, 500)
with open("frankfurt_newyork.svg", "w", encoding="utf-8") as f:
    svg_image.write(f, pretty=True)
