#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: se ts=4 et syn=python:

# created by: matteo.guadrini
# bb.py -- Butterfly-Backup
#
#     Copyright (C) 2018 Matteo Guadrini <matteo.guadrini@hotmail.it>
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#     Modified by Laszlo Suto Nagy (Sun)
#
"""
NAME
    Butterfly Backup - backup/restore/archive tool , agentless

DESCRIPTION
    Butterfly Backup is a simple command line wrapper of rsync for complex task, written in python

SYNOPSIS
    bb [ACTION] [OPTIONS]

    bb [-h] [--verbose] [--log] [--dry-run] [--version]
              {config,backup,restore,archive,list,export} ...

OPTIONS
    action:
      Valid action

      {config,backup,restore,archive,list,export}
                            Available actions
        config              Configuration options
        backup              Backup options
        restore             Restore options
        archive             Archive options
        list                List options
        export              Export options

EXAMPLES
    Show full help:
        O_O>$ bb --help
"""

import os
import subprocess
import multiprocessing
import utility as uty
import datetime
import yaml
import types
import logging
import dbdump
import subprocess
import traceback
import sys
import os
from functions import logger, parse_arguments, print_version, single_action, logger_init, run_in_parallel, start_process, delete_backup, RunError



if __name__ == '__main__':
    logger, loglevel = logger_init('fule-ovbck')
    version = '1.23.07.01'
    endfolder = ''
    logger.info('Eleje')
    logger.info('Loglevel: {0}'.format(logging.getLevelName(loglevel)))
    #print('Loglevel: {0}'.format(loglevel))
    global std, datetime_spec
    try:
        parser = parse_arguments()
        args = parser.parse_args()
        if args.version:
            print_version(version)
        if args.mainconfig:
            opt = vars(args)
            args = yaml.load(open(args.mainconfig), Loader=yaml.FullLoader)
            opt.update(args)
            args = types.SimpleNamespace(**opt)
        if args.dbaseconfig:
            opt = vars(args)
            args = yaml.load(open(args.dbaseconfig), Loader=yaml.FullLoader)
            opt.update(args)
            args = types.SimpleNamespace(**opt)
            #print('Mainconfig: ',args)
        if args.backuptype in ['Dump', 'All']:
            if args.dconfigdir:
                cmds = []
                aktlogs = []
                remotes = []
                allonline = True
                portmessages = []
                processzek = []
                for root, dirs, files in os.walk(args.dconfigdir):
                    for i, file in enumerate(files,0):
                        if file.endswith(args.dconfigext):
                            print('Config: ',file)
                            cfile=root+'/'+file
                            logger.info('Dump configfile: {0}'.format(cfile)                    )               
                            processz = multiprocessing.Process(target=dbdump.dbdump_async, args=(args,cfile,i))
                            processzek.append(processz)
                            processz.start()
                for processz in processzek:
                    processz.join()
        '''
        if args.backuptype in ['Pre', 'All']:
            if args.pconfigdir:
                cmds = []
                aktlogs = []
                remotes = []
                allonline = True
                portmessages = []
                processzek = []
                for root, dirs, files in os.walk(args.pconfigdir):
                    for i, file in enumerate(files,0):
                        if file.endswith(args.pconfigext):
                            print('Config: ',file)
                            cfile=root+'/'+file
                            logger.info('Dump configfile: {0}'.format(cfile)                    )               
                            processz = multiprocessing.Process(target=prersync.prersync_async, args=(args,cfile,i))
                            processzek.append(processz)
                            processz.start()
                for processz in processzek:
                    processz.join()
        '''

        #pylogfile = args.logfile if args.logfile else args.destination + '/' + 'fule-butterfly-backup.log'
        '''
        if args.loglevel:
            loglevel = args.loglevel.upper()
        else:
            loglevel = logger.DEBUG if args.verbose else logger.INFO
        '''
        #print('Loglevel: ',loglevel)
        #logger.basicConfig(level=loglevel, filename=pylogfile, format='%(asctime)s %(filename)s %(funcName)s %(lineno)d %(levelname)s: %(message)s')

        if args.backuptype in ['Rsync', 'All']:
            uty.datetime_spec=datetime.datetime.strptime(args.datetime, '%y%m%d%H%M') if args.datetime else None
            endfolder = uty.time_for_folder(False)
            
            if args.configdir:
                cmds = []
                aktlogs = []
                remotes = []
                allonline = True
                portmessages = []
                for root, dirs, files in os.walk(args.configdir):
                    for file in files:
                        if file.endswith(args.configext):
                            cfile=root+'/'+file
                            #print('Config: ',file)
                            logger.info('Rsync configfile: {0}'.format(cfile)                    )               
                            aktcmd, aktlog, online, eport = single_action(args,cfile)
                            #print('Cmd: ',aktcmd)
                            #print('Log: ',aktlog)
                            if online:
                                cmds.append(' '.join(aktcmd))
                                aktlogs.append(aktlog)
                                #print('Aktlogs: ',aktlogs)
                                aktconfig=file.partition('.')[0]
                                #print('Aktconfig in main: ',aktconfig)
                                logger.debug('Aktconfig in main: {0}'.format(aktconfig))
                                remotes.append(aktconfig)
                            else:
                                portmessages.append('The port {0} on {1} is closed or blocked!'.format(eport, args.hostname))
                                allonline = False
            else:
                single_action(args,args.configfile)
            #print('Vege cmds: ',cmds)
            #print('Vege logs: ',logs)
            #print('Vege remotes: ',remotes)
            #print('Vege: ',args)
            if cmds:
                #print('Vege cmds: ',cmds)
                #print('Vege logs: ',logs)
                #print('Vege remotes: ',remotes)
                #print('Vege: ',args)
                #exit(0)
                #print('is_last_full in main: ',is_last_full)
                rserror, rsmessages, rswarning = run_in_parallel(start_process, cmds, 8, endfolder[0:11])
                #ogger.debug('is_last_full in main: {0}'.format(is_last_full))
                if args.delold and allonline and not rserror:
                    #regiek torlese
                    dirnap = endfolder[12]
                    #print('Dirnap: ',dirnap)
                    logger.debug('Dirnap: {0}'.format(dirnap))
                    if (dirnap != 'd') and args.delold:
                        if dirnap == 'w':
                            torlonap = 'd'
                        elif dirnap == 'm':
                            torlonap = 'w'
                        elif dirnap == 'y':
                            torlonap = 'm'
                        else:
                            torlonap = ''
                        if args.mainconfig:
                            opt = vars(args)
                            args = yaml.load(open(args.mainconfig), Loader=yaml.FullLoader)
                            opt.update(args)
                            args = types.SimpleNamespace(**opt)
                            #print('Args.configdir: ',args.configdir)
                            logger.debug('Args.configdir: {0}'.format(args.configdir))
                            if args.configdir:
                                for root, dirs, files in os.walk(args.configdir):
                                    for file in files:
                                        if file.endswith(args.configext):
                                            cfile=root+'/'+file
                                            #print('Dirconfig: ',cfile)
                                            logger.debug('Dirconfig: {0}'.format(cfile))
                                            opt = vars(args)
                                            args = yaml.load(open(args.mainconfig), Loader=yaml.FullLoader)
                                            opt.update(args)
                                            args = types.SimpleNamespace(**opt)                                        
                                            opt = vars(args)
                                            args = yaml.load(open(cfile), Loader=yaml.FullLoader)
                                            opt.update(args)
                                            args = types.SimpleNamespace(**opt)
                                            if args.hostpart:
                                                hostname=args.hostname+'-'+args.hostpart
                                            else:
                                                hostname=args.hostname
                                            mentodir = args.destination + '/' + hostname
                                            #print('Mentodir: ',mentodir)
                                            logger.debug('Mentodir: {0}'.format(mentodir))
                                            remote=file.partition('.')[0]
                                            #print('Remote: ',remote)
                                            logger.debug('Remote: {0}'.format(remote))
                                            second_dir = {}
                                            for root2, dirs2, files2 in os.walk(mentodir):
                                                if root2 == mentodir:
                                                    dirs2.sort(reverse=True)
                                                    dirnum = 0
                                                    for dir in dirs2:
                                                        #print('Dir: ',dir)
                                                        logger.debug('Dir: {0}'.format(dir))                                      
                                                        if dir.rfind(dirnap) != -1:
                                                            #print('Dirkezdo: ',dir)
                                                            logger.debug('Dirkezdo: {0}'.format(dir))
                                                            dirnum += 1
                                                            if dirnum == 2:
                                                                second_dir[dirnap] = dir
                                                                #print('Second dir: ',second_dir[dirnap])
                                                                logger.debug('Second dir: {0}'.format(second_dir[dirnap]))
                                                                dirs2.sort(reverse=False)
                                                                for dir in dirs2:
                                                                    #print('Dir2: ',dir)
                                                                    logger.debug('Dir2: {0}'.format(dir))              
                                                                    if (dir.rfind(torlonap) != -1) and (dir <= second_dir[dirnap]):
                                                                        #print('Dirtorlo: ',dir)
                                                                        logger.debug('Dirtorlo: {0}'.format(dir))
                                                                        forras1 = mentodir + '/' + dir
                                                                        #print('Forras1: ',forras1)
                                                                        logger.debug('Forras1: {0}'.format(forras1))
                                                                        forras = mentodir + '/' + dir
                                                                        #print('Forras: ',forras)
                                                                        logger.debug('Forras: {0}'.format(forras))
                                                                        cel = mentodir + '/' + second_dir[dirnap] + '/'
                                                                        #print('Cel: ',cel)
                                                                        logger.debug('Cel: {0}'.format(cel))
                                                                        p=subprocess.run(['cp','-aurfT',forras,cel])
                                                                        #print('cp result: ',p)
                                                                        logger.debug('cp result: {0}'.format(str(p)))
                                                                        #shutil.copytree(forras, cel, ignore_dangling_symlinks=True, dirs_exist_ok=True)
                                                                        catalog_path = args.destination + '/' + '.catalog.cfg'
                                                                        delete_backup(catalog_path, forras1)
                                                                        akthost = os.path.basename(os.path.normpath(mentodir))
                                                                        logfile=args.logdirectory+remote+'-'+dir[:-2]+'.log'
                                                                        #print('Logfile: ',logfile)
                                                                        logger.debug('Logfile: {0}'.format(logfile))
                                                                        os.remove(logfile) if os.path.getsize(logfile) == 0 else None
                                                                        errfile=args.logdirectory+remote+'-error-'+dir[:-2]+'.log'
                                                                        #print('Errfile: ',errfile)
                                                                        logger.debug('Errfile: {0}'.format(errfile))
                                                                        os.remove(errfile) if os.path.getsize(errfile) == 0 else None
            if rserror or not allonline:
                from functools import reduce
                runmessages=portmessages+rsmessages
                runmessage = str(reduce(lambda x,y: x+"\n"+y, runmessages))
                raise RunError(runmessage)
            elif rswarning:
                from functools import reduce
                runmessages=rsmessages
                runmessage = str(reduce(lambda x,y: x+"\n"+y, runmessages))
                tmessage = 'Backup ' + endfolder[0:11] + ' end with warning: ' + runmessage                                                                    
            else:
                tmessage = 'Backup ' + endfolder[0:11] + ' OK'                                                                    
            uty.send_telegram_message(tmessage)
        #delete empty logs
        def remove_empty_logs(path):
            for (dirpath, folder_names, files) in os.walk(path):
                for filename in files:
                    file_location = dirpath + '/' + filename  #file location is location is the location of the file
                    if os.path.isfile(file_location):
                        if os.path.getsize(file_location) == 0:#Checking if the file is empty or not
                            os.remove(file_location)  #If the file is empty then it is deleted using remove method
        remove_empty_logs(args.logdirectory)
        remove_empty_logs(args.dumperror)
            
    except Exception as e:
        exception_message = str(e)
        exception_type, exception_object, exception_traceback = sys.exc_info()
        filename = exception_traceback.tb_frame.f_code.co_filename
        lines = traceback.format_exception(exception_type, exception_object, exception_traceback) # nem az exception_traceback, hanem a traceback modul
        logger.error(f"{exception_message} {exception_type} {filename}, Line {exception_traceback.tb_lineno}")
        error_lines = ""
        for line in lines:
            logger.error(line)
            error_lines += line
        error_message = f"{exception_message} {exception_type} {filename}, Line {exception_traceback.tb_lineno}"
        t_message = f"{error_message} {error_lines}"
        uty.send_telegram_message(t_message)
                                                                             