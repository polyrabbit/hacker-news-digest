from curl_cffi import requests

# Impersonate a real Chrome (TLS/HTTP2 fingerprint and headers), as many sites reject inconsistent clients
session = requests.Session(impersonate='chrome', timeout=(10, 30), retry=1, verify=False)
