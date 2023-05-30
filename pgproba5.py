#!/usr/bin/env python3
import multiprocessing
import urllib.request
import time
 
def weboldal_méret(url, eredmények, n):
    print(f'Letölt: {url}')
    tartalom = urllib.request.urlopen(url).read()
    print(f'{url} letöltése kész')
    eredmények[n] = len(tartalom)

def pgproba_async(host,server,port,eredmenyek,i):
    import asyncio, asyncssh, sys

    hosts = ['sasfacan.crocus.hu','mail2022.platinum.co.hu']

    async def run_client(host):
        conn = await asyncio.wait_for(asyncssh.connect(host, username='rbackup', client_keys=['/etc/bb/sshkeys/rbackup.oss'], known_hosts = None,
                                                        keepalive_interval=600, keepalive_count_max=10000),10,)

        return conn

    async def run_command(host,server,port,eredmenyek,i):    
        try:
            conn = await run_client(host)        
            result = await conn.run('pg_dump -h %s -p %s -U postgres menudb' % (server, port), stdout='backup.sql', stderr='backup.err')
            #print(result)
            eredmenyek[i] = host
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

    async def program(host,server,port,eredmenyek,i):
        # Run both print method and wait for them to complete (passing in asyncState)    
        await asyncio.gather(run_command(host,server,port,eredmenyek,i))

    # Run our program until it is complete
    loop = asyncio.get_event_loop()
    loop.run_until_complete(program(host, server, port,eredmenyek,i))
    loop.close()


if __name__ == '__main__':
    
    előtte = time.perf_counter()
    hosts = [
        'sasfacan.crocus.hu',
        #'mail2022.platinum.co.hu',
    ]
    manager = multiprocessing.Manager()
    eredmenyek = manager.list(len(hosts) * [None])
    processzek = []
    for i, host in enumerate(hosts):
        processz = multiprocessing.Process(target=pgproba_async, args=(host,'192.168.11.77','45432',eredmenyek,i))
        processzek.append(processz)
        processz.start()
    for processz in processzek:
        processz.join()
    print(eredmenyek)
    print(f'{time.perf_counter() - előtte:.3f}')
    
    #pgproba_async('sasfacan.crocus.hu','192.168.11.77','45432')