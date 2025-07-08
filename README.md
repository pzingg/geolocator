# geolocator

Uses the World Waterfalls Database to get information on waterfall locations.

## locator.py

Parses WWDB information and creates waterfalls.csv file

## map_server.py

Runs the Python web server to serve up a Stadia Maps map with waterfall markers.

Main index file is waterfalls.html.
Marker data is read from map_data.json.
