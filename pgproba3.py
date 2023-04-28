#!/usr/bin/env python3

import asyncio, asyncssh, sys

async def run_client():
    conn = await asyncio.wait_for(asyncssh.connect('mail2022.platinum.co.hu', username='rbackup', client_keys=['/etc/bb/sshkeys/rbackup.oss'], known_hosts = None,
                                                    keepalive_interval=600, keepalive_count_max=10000),10,)

    return conn

async def run_command():    
    try:
        conn = await run_client()        
        result = await conn.run('systemctl status sshd.service')

        if result.exit_status == 0:
            with open('backup.sql', 'w') as f:
                f.write(result.stdout)
                f.close          
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

# Run our program until it is complete
loop = asyncio.get_event_loop()
loop.run_until_complete(program())
loop.close()
