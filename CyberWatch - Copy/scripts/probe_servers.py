import urllib.request
import urllib.error

urls = [
    'http://127.0.0.1:8000',
    'http://127.0.0.1:8080',
    'http://127.0.0.1:8080/index.html'
]

for url in urls:
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            print(url, r.status, r.getheader('Content-Type'))
    except Exception as e:
        print(url, 'ERROR', type(e).__name__, e)
