#!/usr/bin/env python3
import os
import yaml
import types
import re
 

def dbdump_async(args,configfile=None):
    import asyncio, asyncssh, sys

    async def run_client(host):
        try:
            conn = await asyncio.wait_for(asyncssh.connect(host, username='rbackup', client_keys=['/etc/bb/sshkeys/rbackup.oss'], known_hosts = None,
                                                        keepalive_interval=600, keepalive_count_max=10000), timeout=6)
        except (OSError, asyncssh.Error) as exc:
            sys.exit('SSH connection failed: ' + str(exc))
        return conn

    async def run_command(host,password,server,port,sem,database=None):    
        async with sem:
            try:
                #print(host,server,port,database)
                conn = await run_client(host)
                dumpcommands = []
                modes = []
                if database is None:
                    sqlpath='/backup/data/%s/%s' % (host,server)
                    if not os.path.exists(sqlpath): os.makedirs(sqlpath)
                    if dtype == 'mysql':
                        pass
                    elif dtype == 'postgres':                  
                        dumpcommand = 'PGPASSWORD="%s" pg_dumpall -h %s -p %s -U postgres --roles-only --quote-all-identifiers' % (password, server, port)
                        dumpcommands.append(dumpcommand)
                        modes.append('roles')
                else:
                    sqlpath='/backup/data/%s/%s/%s' % (host,server,database)
                    if not os.path.exists(sqlpath): os.makedirs(sqlpath)
                    if dtype == 'mysql':
                        pass
                    elif dtype == 'postgres':
                        dumpcommand = 'PGPASSWORD="%s" pg_dump -h %s -p %s -U postgres %s --schema-only --quote-all-identifiers' % (password, server, port, database)
                        dumpcommands.append(dumpcommand)
                        modes.append('schema')
                        dumpcommand = 'PGPASSWORD="%s" pg_dump -h %s -p %s -U postgres %s --data-only --column-inserts --quote-all-identifiers' % (password, server, port, database)
                        dumpcommands.append(dumpcommand)
                        modes.append('data')
                for dumpcommand, mode in zip(dumpcommands, modes):
                    if database is None:
                        database = 'all'
                    print(dumpcommand, mode)
                    result = await conn.run(dumpcommand, stdout='%s/%s-%s.sql' % (sqlpath,database,mode), stderr='/backup/data/%s-%s-%s-%s.err' % (host,server,database,mode), check=True)
                    #print(database, result)
                    if result.exit_status == 0:
                        pass
                        #print(result.stdout, end='')                        
                    else:
                        print(result.stderr, end='', file=sys.stderr)
                        print('Program exited with status %d' % result.exit_status,
                            file=sys.stderr)
            except Exception as ex:
                print(ex)      

    async def program(host,password,server,port,include_databases,exclude_databases):
        # Run both print method and wait for them to complete (passing in asyncState)
        #print(conn)
        sem = asyncio.Semaphore(8)
        with await run_client(host) as conn:
            if dtype == 'mysql':
                pass
            elif dtype == 'postgres':                  
                databases = await conn.run("PGPASSWORD='%s' psql -h %s -p %s -U postgres -l -t -z | grep -E '^ [a-z]' | awk '{print $1}'" % (password, server, port), check=True)
                databases = databases.stdout
        tasks = [run_command(host,password,server,port,sem)]
        dbases = re.split('\n', str(databases))
        print(dbases)         
        for database in dbases:
            runtask = True
            for exclude_database in exclude_databases:
                for include_database in include_databases:
                    if not re.search(include_database, database) or re.search(exclude_database, database):
                        runtask = False
            if runtask:
                print(host,server,database)
                tasks.append([run_command(host,password,server,port,sem,database)])
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as ex:
            print(ex)

    # Run our program until it is complete
    global dtype
    dtype=''
    try:
        if configfile:
            opt = vars(args)
            args = yaml.load(open(args.mainconfig), Loader=yaml.FullLoader)
            opt.update(args)
            args = types.SimpleNamespace(**opt)        
            opt = vars(args)
            args = yaml.load(open(configfile), Loader=yaml.FullLoader)
            opt.update(args)
            args = types.SimpleNamespace(**opt)
            #print(args)
            dtype = args.dbtype
        loop = asyncio.get_event_loop()
        loop.run_until_complete(program(args.sshhost, args.dbpassword, args.dbserver, args.dbport, args.include_databases, args.exclude_databases))
    except (OSError, asyncssh.Error) as exc:
        sys.exit('SSH connection failed: ' + str(exc))
    else:
        loop.close()

