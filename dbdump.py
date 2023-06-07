#!/usr/bin/env python3
import os
import yaml
import types
import re
import traceback
 

def dbdump_async(args,configfile=None):
    import asyncio, asyncssh, sys, nest_asyncio
    nest_asyncio.apply()

    async def run_client(host):
        attempts = 0
        conn = None
        attempts_max = 10
        while attempts < attempts_max:      
            try:
                conn = await asyncio.wait_for(asyncssh.connect(host, username='rbackup', client_keys=['/etc/bb/sshkeys/rbackup.oss'], known_hosts = None,
                                                            keepalive_interval=600, keepalive_count_max=10000), timeout=6)
                break
            except Exception as exc:
                print('Attempt %d failed: %s in host: %s' % (attempts, str(exc), host))
                attempts += 1
                if attempts >= attempts_max:
                    exception_message = str(exc)
                    exception_type, exception_object, exception_traceback = sys.exc_info()
                    filename = exception_traceback.tb_frame.f_code.co_filename
                    lines = traceback.format_exception(exception_type, exception_object, exception_traceback) # nem az exception_traceback, hanem a traceback modul
                    error_lines = ""
                    for line in lines:
                        error_lines += line
                    error_message = f"{exception_message} {exception_type} {filename}, Line {exception_traceback.tb_lineno}"  
                    #print('SSH connection failed permanently: %s in host: %s' % (error_message, host))
                    sys.exit('SSH connection failed permanently: ' + str(error_message) + ' in host: ' + str(host))                    
                else:
                    print('SSH connection failed after %d attempts in host: %s' % (attempts, host))
                    continue
        return conn

    async def run_command(dbtype,host,password,server,port,user,sem,database=None,table=None):    
        async with sem:
            try:
                #print(host,server,port,database)
                conn = await run_client(host)
                dumpcommands = []
                modes = []
                if database is None:
                    sqlpath='/backup/data/%s/%s/%s' % (host,dbtype,server)
                    if not os.path.exists(sqlpath): os.makedirs(sqlpath)
                    errpath='/backup/data/%s/%s/%s/error' % (host,dbtype,server)
                    if not os.path.exists(errpath): os.makedirs(errpath)
                    if dtype == 'mysql':
                        pass
                    elif dtype == 'postgres':                  
                        dumpcommand = 'PGPASSWORD="%s" pg_dumpall -h %s -p %s -U %s --roles-only --quote-all-identifiers' % (password, server, port, user)
                        dumpcommands.append(dumpcommand)
                        modes.append('roles')
                else:
                    sqlpath='/backup/data/%s/%s/%s/%s' % (host,dbtype,server,database)
                    if not os.path.exists(sqlpath): os.makedirs(sqlpath)
                    errpath='/backup/data/%s/%s/%s/%s/error' % (host,dbtype,server,database)
                    if not os.path.exists(errpath): os.makedirs(errpath)
                    if dtype == 'mysql':
                        pass
                    elif dtype == 'postgres':
                        if table is None:
                            dumpcommand = 'PGPASSWORD="%s" pg_dump -h %s -p %s -U %s %s --schema-only --quote-all-identifiers' % (password, server, port, user, database)
                            dumpcommands.append(dumpcommand)
                            modes.append('schema')
                        else:
                            dumpcommand = 'PGPASSWORD="%s" pg_dump -h %s -p %s -U %s -d %s --table=public.%s --data-only --column-inserts --quote-all-identifiers' % (password, server, port, user, database,table)
                            dumpcommands.append(dumpcommand)
                            modes.append('data-%s' % table)
                for dumpcommand, mode in zip(dumpcommands, modes):
                    if database is None:
                        database = 'all'
                    print(dumpcommand, mode)
                    result = await conn.run(dumpcommand, stdout='%s/%s.sql' % (sqlpath,mode), stderr='%s/%s.err' % (errpath,mode), check=True)
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

    async def program(dbtype,host,user, password,server,port,include_databases,exclude_databases):
        # Run both print method and wait for them to complete (passing in asyncState)
        #print(conn)
        sem = asyncio.Semaphore(8)
        async def get_databases(host,dtype):
            print(host,dtype)
            async with await run_client(host) as conn:
                if dtype == 'mysql':
                    print('mysql -h %s --user=%s --password=%s -p %s -N  -e "show databases;"' % (server, user, password, port))
                    databases = await conn.run("mysql -h %s --user=%s --password=%s --port=%s -N  -e 'show databases;' | grep -E '[a-z]'" % (server, user, password, port), check=True)
                    #databases = await conn.run("ls", check=True)
                elif dtype == 'postgres':                  
                    databases = await conn.run("PGPASSWORD='%s' psql -h %s -p %s -U %s -l -t -z | grep -E '^ [a-z]' | awk '{print $1}'" % (password, server, port, user), check=True)
                return databases.stdout
        try:
            dbloop = asyncio.get_event_loop()
            databases = dbloop.run_until_complete(get_databases(host,dtype))
        except Exception as exc:
            exception_message = str(exc)
            exception_type, exception_object, exception_traceback = sys.exc_info()
            filename = exception_traceback.tb_frame.f_code.co_filename
            lines = traceback.format_exception(exception_type, exception_object, exception_traceback) # nem az exception_traceback, hanem a traceback modul
            error_lines = ""
            for line in lines:
                error_lines += line
            error_message = f"{exception_message} {exception_type} {filename}, Line {exception_traceback.tb_lineno}"  
            print('SSH get-databases command failed: %s in host: %s' % (error_message, host))
        async def get_tables(host,database,dtype):
            print(host,database,dtype)
            async with await run_client(host) as conn:
                if dtype == 'mysql':
                    pass
                elif dtype == 'postgres':                  
                    tables = await conn.run("PGPASSWORD='%s' psql -h %s -p %s -U %s -d %s -c '\dt' | grep -E '^ [a-z]' | awk '{print $3}'" % (password, server, port, user, database), check=True)
                return tables.stdout
        tasks = [run_command(dbtype,host,password,server,port,user,sem)]
        dbases = re.split('\n', str(databases))
        print(dbases)         
        for database in dbases:
            if database:
                runtask = True
                for exclude_database in exclude_databases:
                    for include_database in include_databases:
                        if not re.search(include_database, database) or re.search(exclude_database, database): #!!!!!!!!!!!!!!
                            runtask = False
                if runtask:
                    try:
                        tbloop = asyncio.get_event_loop()
                        tables = tbloop.run_until_complete(get_tables(host,database,dtype))
                    except (OSError, asyncssh.Error) as exc:
                        sys.exit('SSH connection failed: ' + str(exc))                    
                    tasks.extend([run_command(dbtype,host,password,server,port,user,sem,database)])
                    for table in re.split('\n', str(tables)):
                        print(table)
                        if table:
                            tasks.extend([run_command(dbtype,host,password,server,port,user,sem,database,table)])
        try:
            #print(tasks)
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
        loop.run_until_complete(program(args.dbtype,args.sshhost, args.dbuser, args.dbpassword, args.dbserver, args.dbport, args.include_databases, args.exclude_databases))
    except (OSError, asyncssh.Error) as exc:
        sys.exit('SSH connection failed: ' + str(exc))
    else:
        loop.close()

