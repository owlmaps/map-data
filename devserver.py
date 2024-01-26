from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys
import os


class CORSRequestHandler(SimpleHTTPRequestHandler):

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', '*')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header(
            'Cache-Control', 'no-store, no-cache, must-revalidate')
        return super(CORSRequestHandler, self).end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()


web_dir = os.path.join(os.path.dirname(__file__), 'data')
os.chdir(web_dir)
host = sys.argv[1] if len(sys.argv) > 2 else '0.0.0.0'
port = int(sys.argv[len(sys.argv)-1]) if len(sys.argv) > 1 else 8000

print(f'Listening on {host}:{port}')
httpd = HTTPServer((host, port), CORSRequestHandler)
httpd.serve_forever()
