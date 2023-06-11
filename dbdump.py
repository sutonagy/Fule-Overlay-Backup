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
                attempts += 1
                #print('Attempt %d failed: %s in host: %s' % (attempts, str(exc), host))
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
                results = []
                errpath='/backup/dumperror'
                if not os.path.exists(errpath): os.makedirs(errpath)
                if database is None:
                    if dtype == 'mysql':
                        dumpcommand = "mysqldump -h %s --user=%s --password=%s --port=%s -p mysql --routines" % (server, user, password, port)
                        dumpcommands.append(dumpcommand)
                        modes.append('roles')
                    elif dtype == 'postgres':                  
                        dumpcommand = 'PGPASSWORD="%s" pg_dumpall -h %s -p %s -U %s --roles-only --quote-all-identifiers' % (password, server, port, user)
                        dumpcommands.append(dumpcommand)
                        modes.append('roles')
                else:
                    if dtype == 'mysql':
                        if table is None:
                            dumpcommand = "mysqldump -h %s --user=%s --password=%s --port=%s --routines --no-data --skip-lock-tables %s" % (server, user, password, port, database)
                            dumpcommands.append(dumpcommand)
                            modes.append('schema')
                        else:
                            dumpcommand = "mysqldump -h %s --user=%s --password=%s --port=%s --no-create-info --complete-insert --hex-blob %s %s" % (server, user, password, port, database,table)
                            dumpcommands.append(dumpcommand)
                            modes.append('data-%s' % table)
                    elif dtype == 'postgres':
                        if table is None:
                            dumpcommand = 'PGPASSWORD="%s" pg_dump -h %s -p %s -U %s %s --schema-only --quote-all-identifiers' % (password, server, port, user, database)
                            dumpcommands.append(dumpcommand)
                            modes.append('schema')
                        else:
                            dumpcommand = "PGPASSWORD='%s' pg_dump -h %s -p %s -U %s -d %s --table='public.\"%s\"' --data-only --column-inserts --quote-all-identifiers" % (password, server, port, user, database,table)
                            dumpcommands.append(dumpcommand)
                            modes.append('data-%s' % table)
                for dumpcommand, mode in zip(dumpcommands, modes):
                    if database is None:
                        database = 'all'
                    sqlpath='/backup/data/%s/%s/%s/%s' % (host,dbtype,server,database)
                    if not os.path.exists(sqlpath): os.makedirs(sqlpath)
                    #print(dumpcommand, mode)
                    result = await conn.run(dumpcommand, stdout='%s/%s.sql' % (sqlpath,mode), stderr='%s/%s-%s-%s-%s-%s.err' % (errpath,host,dbtype,server,database,mode), check=True)
                    results.append(result)
                    #print(database, result)
                    estatus = result.exit_status
                    #print('Program exited with status %d' % estatus)
                    if estatus == 0:
                        pass
                        #print(result.stdout, end='')                        
                    else:
                        print(result.stderr, end='', file=sys.stderr)
                        print('Dumpcommand exited with status %d' % estatus,
                            file=sys.stderr)
                return results
            except Exception as ex:
                print('Dumpcommand exited with error %s' % ex)
            finally:
                conn.close()

    async def program(dbtype,host,user, password,server,port,include_databases,exclude_databases):
        print(75*'-')
        print(75*'-')
        print()     
        # Run both print method and wait for them to complete (passing in asyncState)
        #print(conn)
        sem = asyncio.Semaphore(8)
        async def get_databases(host,dtype):
            #print(host,dtype)
            async with await run_client(host) as conn:
                if dtype == 'mysql':
                    #print('mysql -h %s --user=%s --password=%s -p %s -N  -e "show databases;"' % (server, user, password, port))
                    databases = await conn.run("mysql -h %s --user=%s --password=%s --port=%s -N  -e 'show databases;' | grep -E '[a-z]'" % (server, user, password, port), check=True)
                    #databases = await conn.run("ls", check=True)
                elif dtype == 'postgres':                  
                    databases = await conn.run("PGPASSWORD='%s' psql -h %s -p %s -U %s -l -t -z | grep -E '^ [a-z]' | awk '{print $1}'" % (password, server, port, user), check=True)
                conn.close()
                return databases.stdout
        try:
            dbloop = asyncio.get_event_loop()
            #dbtask = asyncio.ensure_future(get_databases(host,dtype))            
            databases = dbloop.run_until_complete(get_databases(host,dtype))
            #databases = asyncio.run(get_databases(host,dtype))
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
        #finally:
        #    dbloop.stop()
        #    dbloop.close()
        async def get_tables(host,database,dtype):
            #print(host,database,dtype)
            async with await run_client(host) as conn:
                if dtype == 'mysql':
                    running_command = "mysql -h %s --user=%s --password=%s --port=%s -N -e \"select count(*) AS tnum from information_schema.tables where table_schema = '%s';\" | grep -E '[a-z0-9]'" % (server, user, password, port, database)
                    #print(running_command)
                    tables_number = await conn.run(running_command, check=True)
                    tnumber = tables_number.stdout
                    #print('%s : %s' % (database, tnumber))
                    if int(tnumber) != 0:
                        tables = await conn.run("mysql -h %s --user=%s --password=%s --port=%s -N -e 'show tables;' %s | grep -E '[a-z]'" % (server, user, password, port, database), check=True)
                        tout = tables.stdout
                    else:
                        tout = 'xxxxxxxxxxxxxxxxxx'
                    conn.close()
                    return tout, tnumber 
                elif dtype == 'postgres':                  
                    tables = await conn.run("PGPASSWORD='%s' psql -h %s -p %s -U %s -d %s -c '\dt' | grep -E '^ [a-z]' | awk '{print $3}'" % (password, server, port, user, database), check=True)
                    conn.close()
                    return tables.stdout
        tasks = [run_command(dbtype,host,password,server,port,user,sem)]
        dbases = re.split('\n', str(databases))
        #print(dbases)         
        for database in dbases:
            if database:
                runtask = False
                exclude = False
                for exclude_database in exclude_databases:
                    if re.search(exclude_database, database):
                        #print('Exclude database pattern matched: %s, Database: %s' % (exclude_database,database))
                        exclude = True
                        break
                    else:
                        pass
                        #print('Exclude database pattern not matched: %s, Database: %s' % (exclude_database,database))
                if not exclude:
                    for include_database in include_databases:
                        if re.search(include_database, database):
                            #print('Include database pattern matched: %s, Database: %s' % (include_database,database))
                            runtask = True
                            break
                        else:
                            pass
                            #print('Include database pattern not matched: %s, Database: %s' % (include_database,database))
                #print('Database: %s is %s' % (database,runtask))
                if runtask:
                    try:
                        #tbloop = asyncio.get_event_loop()
                        #tbloop.close()
                        #tbtask = asyncio.ensure_future(get_tables(host,database,dtype))            
                        tbloop = asyncio.get_event_loop()
                        if dtype == 'mysql':
                            #tables, tables_number = tbloop.run_until_complete(tbtask)
                            tables, tables_number = tbloop.run_until_complete(get_tables(host,database,dtype))
                            #tables, tables_number = asyncio.run(get_tables(host,database,dtype))
                            #print(tables_number)
                        elif dtype == 'postgres':                        
                            #tables = tbloop.run_until_complete(tbtask)
                            #tables = asyncio.run(get_tables(host,database,dtype))
                            tables = tbloop.run_until_complete(get_tables(host,database,dtype))
                    except (OSError, asyncssh.Error) as exc:
                        print(tables_number)
                        print(int(tables_number))
                        if dtype == 'mysql':
                            print(int(tables_number))
                            if int(tables_number) == 0:
                                continue #there isn't any table in database
                            else:
                                sys.exit('SSH get_tables command failed in host %s at database %s: ' % (server,database) + str(exc))
                        else:
                            sys.exit('SSH get_tables command failed in host %s at database %s: ' % (server,database) + str(exc))
                    #finally:
                    #    tbloop.stop()
                    #    tbloop.close()
                    tasks.extend([run_command(dbtype,host,password,server,port,user,sem,database)])
                    for table in re.split('\n', str(tables)):
                        #print(table)
                        if table and table != 'xxxxxxxxxxxxxxxxxx':
                            tasks.extend([run_command(dbtype,host,password,server,port,user,sem,database,table)])
        try:
            #print(75*'-')
            #print(tasks)
            print(75*'-')
            results = await asyncio.gather(*tasks, return_exceptions=True)
            #aktresults = results
            #print(aktresults)

            for i, result in enumerate(results, 1):
                #print(f"{i}: {result}")
                #for index in range(10):
                #    print(f"{index}: {result[index]}")
                #print("The type of result is:", type(result[0]))
                result = result[0]
                if isinstance(result, Exception):
                    print('Task %d failed: %s' % (i, str(result)))
                elif result.exit_status != 0:
                    print('Task %d exited with status %s. Command: %s' % (i, result.exit_status,result.command))
                    print(result.stderr, end='')
                else:
                    print('Task %d succeeded. Command: %s' % (i,result.command))
                    print(result.stdout, end='')

                print(75*'-')
            
        except Exception as exc:
            exception_message = str(exc)
            exception_type, exception_object, exception_traceback = sys.exc_info()
            filename = exception_traceback.tb_frame.f_code.co_filename
            lines = traceback.format_exception(exception_type, exception_object, exception_traceback) # nem az exception_traceback, hanem a traceback modul
            error_lines = ""
            for line in lines:
                error_lines += line
            error_message = f"{exception_message} {exception_type} {filename}, Line {exception_traceback.tb_lineno}"  
            print('Dbdump program failed: %s in host: %s in server %s with dbtype %s' % (error_message, host, server, dbtype))

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
        loop.stop()
        loop.close()
    except KeyboardInterrupt:
        tasks = asyncio.all_tasks()
        print(tasks)
    except (OSError, asyncssh.Error) as exc:
        sys.exit('SSH dbdump connection failed: ' + str(exc))
    else:
        loop.close()

