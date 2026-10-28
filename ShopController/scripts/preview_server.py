"""Serve isolated sample data for UI tests; production API is never replaced on disk."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import argparse

ROOT = Path(__file__).resolve().parent.parent

class PreviewHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        name = urlparse(self.path).path
        overrides = {'/api.js': 'api.js', '/demo.js': 'demo.js', '/store-preview.html': 'store-preview.html', '/manager-preview.html': 'manager-preview.html'}
        if name in overrides:
            path = ROOT / 'preview' / overrides[name]
            if not path.is_file():
                self.send_error(404)
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8' if name.endswith('.html') else 'text/javascript; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=19173)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(PreviewHandler, directory=str(ROOT/'extension')))
    print(f'Local sample preview: http://127.0.0.1:{args.port}/popup.html?window=1', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
