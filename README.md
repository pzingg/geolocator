# geolocator

Uses the World Waterfalls Database to get information on waterfall locations.

## locator.py

Parses WWDB information and creates waterfalls.csv file

## map_server.py

Runs the Python web server to serve up a Stadia Maps map with waterfall markers.

Main index file is waterfalls.html.
Marker data is read from map_data.json.

## static_map.py

Had to patch `textsize` in py-staticmaps .py

Had to install cairo, by first installing MSYS2 on Windows, and then:

* `pacman -S mingw-w64-x86_64-cairo`
* `python -m pip install pycairo`

For Stadia Static Maps, we only fetch one big tile (so most of py-staticmaps is not useful).
However py-staticmaps can calculate the center and zoom for us, based on the bounds of 
Markers and other objects added to the Context.