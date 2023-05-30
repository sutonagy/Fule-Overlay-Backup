#!/usr/bin/env python3

import asyncio, asyncssh, sys

hosts = ['sasfacan.crocus.hu','mail2022.platinum.co.hu']

async def gather_with_concurrency(n, *coros, groups=None):
    semaphore = asyncio.Semaphore(n)

    async def sem_coro(coro):
        async with semaphore:
            return await coro
    return await asyncio.gather(*(sem_coro(c) for c in coros))

async def run_client():
    conn = await asyncio.wait_for(asyncssh.connect('sasfacan.crocus.hu', username='rbackup', client_keys=['/etc/bb/sshkeys/rbackup.oss'], known_hosts = None,
                                                    keepalive_interval=600, keepalive_count_max=10000),10,)

    return conn

async def run_command():    
    try:
        conn = await run_client()        
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

async def program():
    # Run both print method and wait for them to complete (passing in asyncState)    
    await asyncio.gather(run_command())
    # await gather_with_concurrency(10, *my_coroutines)

# Run our program until it is complete
loop = asyncio.get_event_loop()
loop.run_until_complete(program())
loop.close()
