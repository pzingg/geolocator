from http.server import HTTPServer, BaseHTTPRequestHandler

class MapServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/waterfalls.html'
        try:
            file_to_open = open(self.path[1:]).read()
            self.send_response(200)
        except:
            print(f"File {self.path[1:]} not found")
            file_to_open = "File not found"
            self.send_response(404)
        self.end_headers()
        self.wfile.write(bytes(file_to_open, 'utf-8'))

httpd = HTTPServer(('localhost', 8080), MapServer)
httpd.serve_forever()
