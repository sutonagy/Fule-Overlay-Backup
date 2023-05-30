#!/usr/bin/env python3
import asyncio
import aiohttp
import time
 
async def weboldal_méret(url):
    print(f'Letölt: {url}')
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as válasz:
            tartalom = await válasz.text()
            print(f'{url} letöltése kész')
            return len(tartalom)
 
async def main():
    weboldalak = [
        'http://faragocsaba.hu/python',
        'https://www.python.org/',
        'https://www.w3schools.com/python/',
        'https://www.tutorialspoint.com/python/',
        'https://www.pythontutorial.net/',
    ]
    feladatok = []
    for weboldal in weboldalak:
        feladatok.append(asyncio.create_task(weboldal_méret(weboldal)))
    eredmények = []
    for feladat in feladatok:
        eredmények.append(await feladat)
    print(eredmények)
 
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
előtte = time.perf_counter()
asyncio.run(main())
print(f'{time.perf_counter() - előtte:.3f}')
