#!/usr/bin/env python3
import multiprocessing
import urllib.request
import time
 
def weboldal_méret(url, eredmények, n):
    print(f'Letölt: {url}')
    tartalom = urllib.request.urlopen(url).read()
    print(f'{url} letöltése kész')
    eredmények[n] = len(tartalom)

def pgproba_async(host):
    import asyncio, asyncssh, sys

    hosts = ['sasfacan.crocus.hu','mail2022.platinum.co.hu']

    async def run_client(host):
        conn = await asyncio.wait_for(asyncssh.connect(host, username='rbackup', client_keys=['/etc/bb/sshkeys/rbackup.oss'], known_hosts = None,
                                                        keepalive_interval=600, keepalive_count_max=10000),10,)

        return conn

    async def run_command(host):    
        try:
            conn = await run_client(host)        
            result = await conn.run('pg_dump -h 192.168.11.77 -p 45432 -U postgres menudb', stdout='backup.sql', stderr='backup.err')
            #result = await conn.run('systemctl status sshd.service', stdout=sys.stdout, stderr=sys.stderr)

            if result.exit_status == 0:
                pass
                print(result.stdout, end='')                        
            else:
                print(result.stderr, end='', file=sys.stderr)
                print('Program exited with status %d' % result.exit_status,
                    file=sys.stderr)
        except Exception as ex:
            print(ex)      

    async def program(host):
        # Run both print method and wait for them to complete (passing in asyncState)    
        await asyncio.gather(run_command(host))

    # Run our program until it is complete
    loop = asyncio.get_event_loop()
    loop.run_until_complete(program(host))
    loop.close()


if __name__ == '__main__':
    """
    előtte = time.perf_counter()
    hosts = [
        'sasfacan.crocus.hu',
        'mail2022.platinum.co.hu',
    ]
    manager = multiprocessing.Manager()
    eredmények = manager.list(len(hosts) * [None])
    processzek = []
    for host in hosts:
        processz = multiprocessing.Process(target=pgproba_async, args=(host))
        processzek.append(processz)
        processz.start()
    for processz in processzek:
        processz.join()
    print(eredmények)
    print(f'{time.perf_counter() - előtte:.3f}')
    """
    pgproba_async('sasfacan.crocus.hu')