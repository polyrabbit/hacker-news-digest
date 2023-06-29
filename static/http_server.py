import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler

httpd = HTTPServer(('localhost', 443), BaseHTTPRequestHandler)
httpd.socket = ssl.wrap_socket(
    httpd.socket,
    keyfile="static/localhost-key.pem",
    certfile='static/localhost.pem',
    server_side=True)
httpd.serve_forever()
