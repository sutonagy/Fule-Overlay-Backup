#!/usr/bin/env python3
import threading
import urllib.request
import time
 
def weboldal_méret(url, eredmények, n):
    print(f'Letölt: {url}')
    tartalom = urllib.request.urlopen(url).read()
    print(f'{url} letöltése kész')
    eredmények[n] = len(tartalom)
 
előtte = time.perf_counter()
weboldalak = [
    'http://faragocsaba.hu/python',
    'https://www.python.org/',
    'https://www.w3schools.com/python/',
    'https://www.tutorialspoint.com/python/',
    'https://www.pythontutorial.net/',
]
eredmények = len(weboldalak) * [None]
szálak = []
for i, weboldal in enumerate(weboldalak):
    szál = threading.Thread(target=weboldal_méret, args=(weboldal, eredmények, i))
    szálak.append(szál)
    szál.start()
    time.sleep(0.01)
for szál in szálak:
    szál.join()
print(eredmények)
print(f'{time.perf_counter() - előtte:.3f}')
