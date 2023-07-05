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
import requests
from functions import logger, parse_arguments, print_version, single_action, logger_init, run_in_parallel, start_process, delete_backup, RunError



if __name__ == '__main__':
    logger, loglevel = logger_init('fule-ovbck')
    response = requests.get("https://api.github.com/repos/sutonagy/Fule-Overlay-Backup/releases/latest")
    version = response.json()["name"]
    endfolder = ''
    logger.info('Eleje')
    logger.info('Loglevel: {0}'.format(logging.getLevelName(loglevel)))
    logger.info('Version: {0}'.format(version))
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
                rserror, rsmessages, rswarning = run_in_parallel(start_process, cmds, 8, endfolder[0:11])
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
                                                                             