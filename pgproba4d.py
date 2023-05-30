#!/usr/bin/env python3
import multiprocessing
import urllib.request
import time
 
def weboldal_méret(url, eredmények, n):
    print(f'Letölt: {url}')
    tartalom = urllib.request.urlopen(url).read()
    print(f'{url} letöltése kész')
    eredmények[n] = len(tartalom)
 
if __name__ == '__main__':
    előtte = time.perf_counter()
    weboldalak = [
        'http://faragocsaba.hu/python',
        'https://www.python.org/',
        'https://www.w3schools.com/python/',
        'https://www.tutorialspoint.com/python/',
        'https://www.pythontutorial.net/',
    ]
    manager = multiprocessing.Manager()
    eredmények = manager.list(len(weboldalak) * [None])
    processzek = []
    for i, weboldal in enumerate(weboldalak):
        processz = multiprocessing.Process(target=weboldal_méret, args=(weboldal, eredmények, i))
        processzek.append(processz)
        processz.start()
    for processz in processzek:
        processz.join()
    print(eredmények)
    print(f'{time.perf_counter() - előtte:.3f}')
    