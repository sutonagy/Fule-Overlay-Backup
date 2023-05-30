#!/usr/bin/env python3
import urllib.request
import time
 
def weboldal_méret(url):
    print(f'Letölt: {url}')
    tartalom = urllib.request.urlopen(url).read()
    print(f'{url} letöltése kész')
    return len(tartalom)
 
előtte = time.perf_counter()
weboldalak = [
    'http://faragocsaba.hu/python',
    'https://www.python.org/',
    'https://www.w3schools.com/python/',
    'https://www.tutorialspoint.com/python/',
    'https://www.pythontutorial.net/',
]
eredmények = []
for weboldal in weboldalak:
    eredmények.append(weboldal_méret(weboldal))
print(eredmények)
print(f'{time.perf_counter() - előtte:.3f}')
