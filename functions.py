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

import argparse
import configparser
import os
import subprocess
import multiprocessing
import utility as uty
import time
import datetime
import yaml
import types
import colorlog
import logging
import dbdump
from multiprocessing import Pool
#from utility import print_verbose
from shutil import rmtree
from ovbck import args, logger, remotes, endfolder, parser


class PrintColor:
    """
    Class for print string in color
    """
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def parse_arguments():
    """
    Function get arguments than specified in command line
    :return: parser
    """
    # Create a common parser
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('--verbose', '-v', help='Enable verbosity', dest='verbose', action='store_true')
    parent_parser.add_argument('--log', '-l', help='Create a log', dest='log', action='store_true')
    parent_parser.add_argument('--dry-run', '-N', help='Dry run mode', dest='dry_run', action='store_true')
    parent_parser.add_argument('--version', '-V', help='Print version', dest='version', action='store_true')
    parent_parser.add_argument('--config-file', '-F', help='Yaml config file. Do not use together with --config-dir-... and --main-config-... options', dest='configfile', action='store')
    parent_parser.add_argument('--config-dir-extension', '-X', help='Extension  for config files in configdir (.ext)', dest='configext', action='store')
    parent_parser.add_argument('--dump-config-dir-extension', '-f', help='Extension  for database dump config files in dconfigdir (.ext)', dest='dconfigext', action='store')
    parent_parser.add_argument('--config-dir', '-G', help='Config dir for yaml config files with extension defined in --config-dir-extension', dest='configdir', action='store')
    parent_parser.add_argument('--dump-config-dir', '-g', help='Config dir for dtabase dump yaml config files with extension defined in --dump-config-dir-extension', dest='dconfigdir', action='store')
    parent_parser.add_argument('--main-config-file', '-M', help='Main yaml config file for defaults', dest='mainconfig', action='store')
    parent_parser.add_argument('--dbase-config-file', '-B', help='Database dump yaml config file for defaults', dest='dbaseconfig', action='store')
    parent_parser.add_argument('--date-time', '-K', help='Set backup date and time instead of now (For testing the program only). Format: yymmddHHMM', dest='datetime', action='store')
    parent_parser.add_argument('--logfile', '-Q', help='Set python logfile', dest='logfile', action='store')
    parent_parser.add_argument('--loglevel', '-Z', help='Set python loglevel (CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET)', dest='loglevel', action='store', choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'], default='INFO')
    parent_parser.add_argument('--backuptype', '-k', help='Set which parts of backup processes will run (Dump, Rsync, Both)', dest='backuptype', action='store', choices=['Dump', 'Rsync', 'Both'], default='Both')
    parent_parser.add_argument('--console-loglevel', '-W', help='Print the log messages to the console too', dest='consolelog', action='store')
    # Create principal parser
    parser_object = argparse.ArgumentParser(prog='bb', description=PrintColor.BOLD + 'Fule Butterfly Backup'
                                            + PrintColor.END,
                                            formatter_class=argparse.RawTextHelpFormatter,
                                            epilog='''

Currently only the "backup" action is supported.
To see the backup options, use the command "bb backup -h".
In the YAML files you can use the CAPITAL letter variables from these helps in lowercase.
See the example YAML files.
The hierarchy of the options is the following. The command line options will be overwited by the main config YAML file and these will be overwited by the specific YAML files which are in the configdir with extension of configext.

Tipical usage: bb backup -M /etc/bb/bb.yaml
In bb.yaml you can define the configdir and configext options.
"
configdir: /etc/bb/hosts
configext: .yaml
"
The program will read all the YAML files in the configdir with the extension of configext (i.e. *.yaml in /etc/bb/hosts) and will merge them with the main config YAML file.

                                            ''',
                                            parents=[parent_parser])

    # Create sub_parser "action"
    action = parser_object.add_subparsers(title='action', description='Valid action', help='Available actions',
                                          dest='action')
    # config session
    config = action.add_parser('config', help='Configuration options', parents=[parent_parser])
    group_config = config.add_argument_group(title='Init configuration')
    group_config_mutually = group_config.add_mutually_exclusive_group()
    group_config_mutually.add_argument('--new', '-n', help='Generate new configuration', dest='new_conf',
                                       action='store_true')
    group_config_mutually.add_argument('--remove', '-r', help='Remove exist configuration', dest='remove_conf',
                                       action='store_true')
    group_config_mutually.add_argument('--init', '-i', help='Reset catalog file. Specify path of backup folder.',
                                       dest='init', metavar='CATALOG', action='store')
    group_config_mutually.add_argument('--delete-host', '-D', help='Delete all entry for a single HOST in catalog.',
                                       nargs=2, dest='delete', metavar=('CATALOG', 'HOST'), action='store')
    group_config_mutually.add_argument('--clean', '-c', help='Cleans the catalog if it is corrupt, '
                                                             'setting default values.',
                                       dest='clean', metavar='CATALOG', action='store')
    group_deploy = config.add_argument_group(title='Deploy configuration')
    group_deploy_mutually = group_deploy.add_mutually_exclusive_group()
    group_deploy_mutually.add_argument('--deploy', '-d', help='Deploy configuration to client: hostname or ip address',
                                       dest='deploy_host', action='store')
    group_deploy.add_argument('--user', '-u', help='User of the remote machine',
                              dest='deploy_user', action='store', default=os.getlogin())
    # backup session
    backup = action.add_parser('backup', help='Backup options', parents=[parent_parser])
    group_backup = backup.add_argument_group(title='Backup options')
    single_or_list_group = group_backup.add_mutually_exclusive_group(required=True)
    single_or_list_group.add_argument('--computer', '-c', help='Hostname or ip address to backup', dest='hostname',
                                      action='store')
    single_or_list_group.add_argument('--hostpart', '-S', help='A part of backup to split backup of one host to multiple part', dest='hostpart',
                                      action='store')
    single_or_list_group.add_argument('--list', '-L', help='File list of computers or ip addresses to backup',
                                      dest='list', action='store')
    group_backup.add_argument('--destination', '-d', help='Destination path', dest='destination', action='store',
                              required=True)
    group_backup.add_argument('--mode', '-m', help='Backup mode', dest='mode', action='store',
                              choices=['Full', 'Incremental', 'Differential', 'Mirror'], default='Incremental')
    data_or_custom = group_backup.add_mutually_exclusive_group(required=True)
    data_or_custom.add_argument('--data', '-D', help='Data of which you want to backup', dest='data', action='store',
                                choices=['User', 'Config', 'Application', 'System', 'Log'], nargs='+')
    data_or_custom.add_argument('--custom-data', '-C', help='Custom path of which you want to backup',
                                dest='customdata', action='store', nargs='+')
    group_backup.add_argument('--user', '-u', help='Login name used to log into the remote host (being backed up). Default is the current user.',
                              dest='user', action='store', default=os.getlogin())
    group_backup.add_argument('--type', '-t', help='Type of operating system to backup', dest='type', action='store',
                              choices=['Unix', 'Windows', 'MacOS'], required=True)
    group_backup.add_argument('--compress-mode', '-zc', help='Compress data', dest='compressmode', action='store')
    group_backup.add_argument('--compress-level', '-zl', help='Compress data', dest='compresslevel', action='store', type=int)
    group_backup.add_argument('--retention', '-r', help='First argument are days of backup retention. '
                                                        'Second argument is minimum number of backup retention',
                              dest='retention', action='store', nargs='*', metavar=('DAYS', 'NUMBER'), type=int)
    group_backup.add_argument('--parallel', '-p', help='Number of parallel jobs', dest='parallel', action='store',
                              type=int, default=5)
    group_backup.add_argument('--timeout', '-T', help='I/O timeout in seconds', dest='timeout', action='store',
                              type=int)
    group_backup.add_argument('--skip-error', '-e', help='Skip error', dest='skip_err', action='store_true')
    group_backup.add_argument('--rsync-path', '-R', help='Custom rsync path', dest='rsync', action='store')
    group_backup.add_argument('--bwlimit', '-b', help='Bandwidth limit in KBPS.', dest='bwlimit', action='store',
                              type=int)
    group_backup.add_argument('--ssh-port', '-P', help='Custom ssh port.', dest='port', action='store', type=int)
    group_backup.add_argument('--rsync-port', '-Y', help='Custom rsync port.', dest='rport', action='store', type=int)
    group_backup.add_argument('--exclude', '-E', help='Exclude pattern', dest='exclude', action='store', nargs='+')
    group_backup.add_argument('--start-from', '-s', help='Backup id where start a new backup', dest='sfrom',
                              action='store', metavar='ID')
    group_backup.add_argument('--delete-old-differential', '-O', help='Delete older Differential backup folders. See bb.yaml.sample!', dest='delold',
                              action='store_true')
    group_backup.add_argument('--ssh-key', '-U', help='SSH key private file for remote SSH connection. Default is ~/.ssh/id_rsa',
                              dest='sshkey', action='store')
    group_backup.add_argument('--remote-rsync-command', '-J', help='Remote rsync command (i.e. sudo rsync).',
                              dest='remotersync', action='store')
    
    # restore session
    restore = action.add_parser('restore', help='Restore options', parents=[parent_parser])
    group_restore = restore.add_argument_group(title='Restore options')
    group_restore.add_argument('--catalog', '-C', help='Folder where is catalog file', dest='catalog', action='store',
                               required=True)
    restore_id_or_last = group_restore.add_mutually_exclusive_group(required=True)
    restore_id_or_last.add_argument('--backup-id', '-i', help='Backup-id of backup', dest='id', action='store')
    restore_id_or_last.add_argument('--last', '-L', help='Last available backup', dest='last', action='store_true')
    group_restore.add_argument('--user', '-u', help="Login name used to log into the remote host "
                                                    "(where you're restoring)", dest='user',
                               action='store', default=os.getlogin())
    group_restore.add_argument('--computer', '-c', help='Hostname or ip address to perform restore', dest='hostname',
                               action='store', required=True)
    group_restore.add_argument('--type', '-t', help='Type of operating system to perform restore', dest='type',
                               action='store', choices=['Unix', 'Windows', 'MacOS'])
    group_restore.add_argument('--timeout', '-T', help='I/O timeout in seconds', dest='timeout', action='store',
                               type=int)
    group_restore.add_argument('--mirror', '-m', help='Mirror mode', dest='mirror', action='store_true')
    group_restore.add_argument('--skip-error', '-e', help='Skip error', dest='skip_err', action='store_true')
    group_restore.add_argument('--rsync-path', '-R', help='Custom rsync path', dest='rsync', action='store')
    group_restore.add_argument('--bwlimit', '-b', help='Bandwidth limit in KBPS.', dest='bwlimit', action='store',
                               type=int)
    group_restore.add_argument('--ssh-port', '-P', help='Custom ssh port.', dest='port', action='store', type=int)
    group_restore.add_argument('--rsync-port', '-Y', help='Custom rsync port.', dest='rport', action='store', type=int)
    group_restore.add_argument('--exclude', '-E', help='Exclude pattern', dest='exclude', action='store', nargs='+')
    # archive session
    archive = action.add_parser('archive', help='Archive options', parents=[parent_parser])
    group_archive = archive.add_argument_group(title='Archive options')
    group_archive.add_argument('--catalog', '-C', help='Folder where is catalog file', dest='catalog', action='store',
                               required=True)
    group_archive.add_argument('--days', '-D', help='Number of days of archive retention', dest='days',
                               action='store', type=int, default=30)
    group_archive.add_argument('--destination', '-d', help='Archive destination path', dest='destination',
                               action='store', required=True)
    # list session
    list_action = action.add_parser('list', help='List options', parents=[parent_parser])
    group_list = list_action.add_argument_group(title='List options')
    group_list.add_argument('--catalog', '-C', help='Folder where is catalog file', dest='catalog', action='store',
                            required=True)
    group_list_mutually = group_list.add_mutually_exclusive_group()
    group_list_mutually.add_argument('--backup-id', '-i', help='Backup-id of backup', dest='id', action='store')
    group_list_mutually.add_argument('--archived', '-a', help='List only archived backup', dest='archived',
                                     action='store_true')
    group_list_mutually.add_argument('--cleaned', '-c', help='List only cleaned backup', dest='cleaned',
                                     action='store_true')
    group_list_mutually.add_argument('--computer', '-H', help='List only match hostname or ip', dest='hostname',
                                     action='store')
    group_list_mutually.add_argument('--detail', '-d', help='List detail of file and folder of specific backup-id',
                                     dest='detail', action='store', metavar='ID')
    group_list.add_argument('--oneline', '-o', help='One line output', dest='oneline', action='store_true')
    # export session
    export_action = action.add_parser('export', help='Export options', parents=[parent_parser])
    group_export = export_action.add_argument_group(title='Export options')
    group_export.add_argument('--catalog', '-C', help='Folder where is catalog file', dest='catalog', action='store',
                              required=True)
    group_export_id_or_all = group_export.add_mutually_exclusive_group()
    group_export_id_or_all.add_argument('--backup-id', '-i', help='Backup-id of backup', dest='id', action='store')
    group_export_id_or_all.add_argument('--all', '-A', help='All backup', dest='all', action='store_true')
    group_export.add_argument('--destination', '-d', help='Destination path', dest='destination', action='store',
                              required=True)
    group_export.add_argument('--mirror', '-m', help='Mirror mode', dest='mirror', action='store_true')
    group_export.add_argument('--cut', '-c', help='Cut mode. Delete source', dest='cut', action='store_true')
    group_export_mutually = group_export.add_mutually_exclusive_group()
    group_export_mutually.add_argument('--include', '-I', help='Include pattern', dest='include', action='store',
                                       nargs='+')
    group_export_mutually.add_argument('--exclude', '-E', help='Exclude pattern', dest='exclude', action='store',
                                       nargs='+')
    group_export.add_argument('--timeout', '-T', help='I/O timeout in seconds', dest='timeout', action='store',
                              type=int)
    group_export.add_argument('--skip-error', '-e', help='Skip error', dest='skip_err', action='store_true')
    group_export.add_argument('--rsync-path', '-R', help='Custom rsync path', dest='rsync', action='store')
    group_export.add_argument('--bwlimit', '-b', help='Bandwidth limit in KBPS.', dest='bwlimit', action='store',
                              type=int)
    group_export.add_argument('--ssh-port', '-P', help='Custom ssh port.', dest='port', action='store', type=int)
    group_export.add_argument('--rsync-port', '-Y', help='Custom rsync port.', dest='rport', action='store', type=int)
    # Return all args
    
    return parser_object


def logger_init(loggername):

    formatter = colorlog.ColoredFormatter('{log_color} {asctime} {filename} {funcName} {lineno} {levelname}: {message}',
                                datefmt=None,
                                reset=True,
                                log_colors={
                                    'DEBUG':    'cyan',
                                    'INFO':     'light_green',
                                    'WARNING':  'yellow',
                                    'ERROR':    'bold_red',
                                    'CRITICAL': 'bold_red,bg_white',
                                },
                                secondary_log_colors={},
                                style='{'
                                )


    #logger.basicConfig(level=loglevel, filename=pylogfile, format='{log_color} {asctime} {filename} {funcName} {lineno} {levelname}: {message}', style='{')
    parser = parse_arguments()
    args = parser.parse_args()
    if args.mainconfig:
        opt = vars(args)
        args = yaml.load(open(args.mainconfig), Loader=yaml.FullLoader)
        opt.update(args)
        args = types.SimpleNamespace(**opt)
        #print('Mainconfig: ',args)
    logger = colorlog.getLogger(loggername)
    # create file handler which logs even debug messages
    # create console handler with a higher log level
    if args.consolelog:
        ch = colorlog.StreamHandler()
        ch.setFormatter(formatter)
    #ch.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    folderend=datetime.datetime.now().strftime('%y%m%d-%H%M')
    pylogfile = args.logfile + '-' + folderend[0:11] + '.log' if args.logfile else args.destination + '/' + 'fule-butterfly-backup.log'
    fh = logging.FileHandler(pylogfile)
    formatter2 = logging.Formatter('{asctime} {filename} {funcName} {lineno} {levelname}: {message}', style='{')
    fh.setFormatter(formatter2)
    if not logger.handlers: # To avoid duplicate handler and lines in log file. (It's called from utility too)
        logger.addHandler(fh)
        if args.consolelog:
            logger.addHandler(ch)
    #logger.addHandler(fh)
    # add the handlers to logger
    if args.loglevel:
        logger.setLevel(args.loglevel.upper())
    else:
        logger.setLevel(colorlog.DEBUG) if args.verbose else logger.setLevel(colorlog.INFO)
    #logger.info('loglevel: %s', args.loglevel)
    return logger, logger.level


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class RunError(Error):
    """Error if rsync run exits with error.
    """

    def __init__(self, message):
        """! InvoiceGrossamountError class initializer.
        @param message  A hibaüzenet.
        """
        self.message = message

def print_version(version):
    """
    Print version of Butterfly Backup
    :return: str
    """
    uty.print_verbose(args.verbose, 'Print version and logo')
    if args.verbose:
        print_logo()
    print(PrintColor.BOLD + 'Version: ' + PrintColor.END + version)
    exit()


def print_logo():
    """
    Print logo design
    :return: design of logo
    """
    print(
        '''
                .                   .
    .OMMMM..   .....              ...   ...MNNM$...
 .MNNNNNMM7=?..   ...            ..     ??$MMNNNNDN.
 MNNNMMNN:,:,8N:.. ...        ....   :N8,,,:MNMNMNMM.
.MMNMMM,::,,,DDD?8.....      ......+IDDD,,,:+,MMMNNM.
.MNMDN:$,,,,DDD= .?..  ..   ......??.+DDD,,,,$:MDMNM.
.MMMD::,,INN7N... ..?....   . ..$.. ...N7NN?,,,+DMDM.
 DNM7=~:.  ..8..    .:N... ...M+.    ..8..   :=+$MMD
  NI=,.  .:....M..   ..IZ?NN+O.     .M.. .~.  .,~IM.
 .,N:..+..   .?NNMNDDNZ..?NZ..7NNDNMNN8.   ..?..~M8.
   ,NND... ?D7..       .,?Z?~.       ..$D8....DDD.
     .DDNDN7....       .D???N.       .. .ONDNDD.
      ..$~N.. ,. .. .=....M....=. .  .O ..N~+..
      .??ID.M..... ....., I....... .....M.DII?.
       .?Z..   $.  ....,..?. ..... ..I. ...$I
        .8... ... ?.?O   .?~  .MM.+........O.
        ..I8N....:.N.    +??..  .N 8....NN7.
            ..NOM.. .   .I??.     ..MZN.
                         .?.


                     [GRETA OTO]
        '''
    )


def check_rsync():
    """
    Check if rsync tool is installed
    :return: string
    """
    if not uty.check_tool('rsync'):
        print(PrintColor.RED +
            'ERROR: rsync tool is required!' +
            PrintColor.END +
            """
Red-Hat/CentOS/Fedora:    yum install rsync
Debian/Ubuntu/Mint:       apt-get install rsync
Arch Linux:               aur install rsync
Mac OS X:                 install homebrew; brew install rsync
Windows:                  install Cygwin
""")
        exit()


def dry_run(message):
    """
    Check if dry run mode
    :param message: print message standard output
    :return: boolean
    """
    if args.dry_run:
        uty.print_verbose(True, message)
        return True


def run_in_parallel(fn, commands, limit, aktdate=''):
    """
    Run in parallel with limit
    :param fn: function in parallelism
    :param commands: args commands of function
    :param limit: number of parallel process
    """
    
    from pathlib import Path

    # Start a Pool with "limit" processes
    pool = Pool(processes=limit)
    jobs = []
    #folderend=endfolder if not is_last_full else endfolder[0:12] + 'f'
    #print('Parallel commands: ',commands)
    #print('Parallel aktlogs: ',aktlogs)
    #print('Parallel remotes: ',remotes)
    logger.debug('Parallel remotes: {0}'.format(remotes))
    #logger.debug('Folderend in parallel: {0}'.format(folderend))
    logger.debug('aktdate in parallel: {0}'.format(aktdate))
    for command, plog, remote in zip(commands, aktlogs, remotes):
        # Run the function
        # print('Parallel command: ',command)
        proc = pool.apply_async(func=fn, args=(command,aktdate,remote))
        jobs.append(proc)
        #print('Start {0} {1}'.format(args.action, plog['hostname']))
        logger.info('Start {0} {1}'.format(args.action, plog['hostname']))
        uty.print_verbose(args.verbose, "rsync command: {0}".format(command))
        logger.info("rsync command: {0}".format(command))
        uty.write_log(log_args['status'], plog['destination'], 'INFO', 'Start process {0} on {1}'.format(
            args.action, plog['hostname']
        ))
        logger.info('Start process {0} on {1}'.format(args.action, plog['hostname']))
        if args.action == 'backup':
            # Write catalog file
            write_catalog(catalog_path, plog['id'], 'start', uty.time_for_log())

    # Wait for jobs to complete before exiting
    while not all([p.ready() for p in jobs]):
        time.sleep(5)

    # Check exit code of command
    rmessages=[]
    rsyncerror = False
    rswarning = False
    for p, command, plog, remote in zip(jobs, commands, aktlogs, remotes):
        if p.get() != 0 and p.get() != 24:
            #print(PrintColor.RED + 'ERROR: Command {0} exit with code: {1}'.format(command, p.get()) +
                #PrintColor.END)
            logger.error('Command {0} exit with code: {1}'.format(command, p.get()))
            uty.write_log(log_args['status'], plog['destination'], 'INFO',
                            'ERROR: Command {0} exit with code: {1} on {2}'.format(command, p.get(), plog['hostname']))
            uty.write_log(log_args['status'], plog['destination'], 'ERROR',
                            'Finish process {0} on {1} with error:{2}'.format(args.action, plog['hostname'], p.get()))
            logger.error('Finish process {0} on {1} with error:{2}'.format(args.action, plog['hostname'], p.get()))
            if args.action == 'backup':
                # Write catalog file
                write_catalog(catalog_path, plog['id'], 'end', uty.time_for_log())
                write_catalog(catalog_path, plog['id'], 'status', "{0}".format(p.get()))
                if args.retention and args.skip_err:
                    # Retention policy
                    retention_policy(plog['hostname'], catalog_path, plog['destination'])
            errfile=args.logdirectory+remote+'-error-'+aktdate+'.log'
            #emessage = p.get()
            #print('emessage in paralell : ',emessage)
            #logger.debug('emessage in paralell : {0}'.format(emessage))
            if os.path.getsize(errfile) != 0:
                rmessage = 'Command {0} exit with code: {1}'.format(command, p.get()) + '\n' + Path(errfile).read_text()
                rmessages.append(rmessage)
                rsyncerror = True                
        else:
            if p.get() == 24:
                rmessage = 'Command {0} exit with code: {1}'.format(command, p.get()) + '\n' + Path(errfile).read_text()
                rmessages.append(rmessage)
                rswarning = True
                logger.warning('Warning: Command {0} end with warning: {1}'.format(command,rmessage))
                logger.warning('Finish process {0} on {1} with warning: {2}'.format(args.action, plog['hostname'], rmessage))
            #print(PrintColor.GREEN + 'SUCCESS: Command {0}'.format(command) + PrintColor.END)
            logger.info('SUCCESS: Command {0}'.format(command))
            uty.write_log(log_args['status'], plog['destination'], 'INFO',
                            'SUCCESS: Command {0} on {1}'.format(command, plog['hostname']))
            uty.write_log(log_args['status'], plog['destination'], 'INFO',
                            'Finish process {0} on {1}'.format(args.action, plog['hostname']))
            logger.info('Finish process {0} on {1}'.format(args.action, plog['hostname']))
            if args.action == 'backup':
                # Write catalog file
                write_catalog(catalog_path, plog['id'], 'end', uty.time_for_log())
                write_catalog(catalog_path, plog['id'], 'status', "{0}".format(p.get()))
                if args.retention:
                    # Retention policy
                    retention_policy(plog['hostname'], catalog_path, plog['destination'])

    # Safely terminate the pool
    pool.close()
    pool.join()
    return rsyncerror, rmessages, rswarning
    


def start_process(command,folderend,remote=''):
    """
    Start rsync commands
    :param command: rsync command
    :param remote: name of the actual yaml config file
    :return: command
    """
    
    """
    fd = get_std_out()
    if fd == 'DEVNULL':
        p = subprocess.call(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif fd == 'STDOUT':
        p = subprocess.call(command, shell=True)
    else:
        p = subprocess.call(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    """
    #print('Remote in start_process: ',remote)
    logger.debug('Remote in start_process: {0}'.format(remote))
    logfile=args.logdirectory+remote+'-'+folderend+'.log'
    #print('Logfile in start_process: ',logfile)
    logger.debug('Logfile in start_process: {0}'.format(logfile))
    #print('Folderend in start_process: ',folderend)
    logger.debug('Folderend in start_process: {0}'.format(folderend))
    errfile=args.logdirectory+remote+'-error-'+folderend+'.log'
    fo = open(logfile,'w')
    fe = open(errfile,'w')
    p = subprocess.call(command, shell=True, stdout=fo, stderr=fe)
    return p


def get_std_out():
    """
    Return stdout and stderr
    :return: string
    """
    if args.action == 'backup':
        if args.list:
            stdout = 'DEVNULL'
        elif args.hostname:
            if args.verbose:
                stdout = 'STDOUT'
            else:
                stdout = 'DEVNULL'
        else:
            stdout = 'DEVNULL'
        return stdout
    elif args.action == 'restore':
        if args.verbose:
            stdout = 'STDOUT'
        else:
            stdout = 'DEVNULL'
        return stdout
    else:
        stdout = 'STDOUT'
        return stdout


def map_dict_folder(os_name):
    """
    Mapping folder structure to dictionary
    :param os_name: Name of operating system
    :return: Dictionary folder structure
    """
    # Set an empty dictionary folders
    folders = {}
    # Check operating system
    if os_name == 'Unix':
        folders['User'] = '/home'
        folders['Config'] = '/etc'
        folders['Application'] = '/usr'
        folders['System'] = '/'
        folders['Log'] = '/var/log'
    elif os_name == 'Windows':
        folders['User'] = '/cygdrive/c/Users'
        folders['Config'] = '/cygdrive/c/ProgramData'
        folders['Application'] = "'/cygdrive/c/Program\ Files'"
        folders['System'] = '/cygdrive/c'
        folders['Log'] = '/cygdrive/c/Windows/System32/winevt'
    elif os_name == 'MacOS':
        folders['User'] = '/Users'
        folders['Config'] = '/private/etc'
        folders['Application'] = '/Applications'
        folders['System'] = '/'
        folders['Log'] = '/private/var/log'
    # Return dictionary with folder structure
    return folders


def compose_command(flags, host, folderend):
    """
    Compose rsync command for action
    :param flags: Dictionary than contains info for command
    :param host: Hostname of machine
    :return: list
    """
    
    is_last_full = False
    uty.print_verbose(args.verbose, 'Build a rsync command')
    # Set rsync binary
    if flags.rsync:
        if os.path.exists(flags.rsync):
            command = [flags.rsync]
        else:
            #print(PrintColor.YELLOW +
                  #'WARNING: rsync binary {0} not exist! Set default.'.format(args.rsync)
                  #+ PrintColor.END)
            logger.warning('WARNING: rsync binary {0} not exist! Set default.'.format(args.rsync))
            command = ['rsync']
    else:
        command = ['rsync']
    #print(catalog_path)
    catalog = read_catalog(catalog_path)
    #print(catalog)
    if flags.action == 'backup':
        # Set mode option
        if flags.mode == 'Full':
            is_last_full = True
            command.append('-ahR')
            command.append('--links')
            # Write catalog file
            write_catalog(catalog_path, backup_id, 'type', 'Full')
        elif flags.mode == 'Incremental':
            last_bck = get_last_backup(catalog)
            logger.debug('last_bck: {0}'.format(last_bck))
            if last_bck:
                command.append('-ahRu')
                command.append('--links')
                if not flags.sfrom:
                    command.append('--link-dest={0}'.format(last_bck[0]))
                    logger.debug('--link-dest={0}'.format(last_bck[0]))
                # Write catalog file
                write_catalog(catalog_path, backup_id, 'type', 'Incremental')
            else:
                is_last_full = True
                command.append('-ahR')
                command.append('--links')
                # Write catalog file
                write_catalog(catalog_path, backup_id, 'type', 'Full')
        elif flags.mode == 'Differential':
            last_full = get_last_full(catalog)
            logger.debug('Differential last_full: {0}'.format(last_full))
            if last_full:
                command.append('-ahRu')
                command.append('--links')
                if not flags.sfrom:
                    command.append('--link-dest={0}'.format(last_full[0]))
                    logger.debug('--link-dest={0}'.format(last_full[0]))
                # Write catalog file
                write_catalog(catalog_path, backup_id, 'type', 'Differential')
            else:
                is_last_full = True
                command.append('-ahR')
                command.append('--links')
                # Write catalog file
                write_catalog(catalog_path, backup_id, 'type', 'Full')
        elif flags.mode == 'Mirror':
            command.append('-ahR')
            command.append('--delete')
            # Write catalog file
            write_catalog(catalog_path, backup_id, 'type', 'Mirror')
        logger.debug('is_last_full in compose command: {0}'.format(is_last_full))
        command.append('--partial')
        # Set verbosity
        if flags.verbose:
#            command.append('-vP')
            command.append('-v')
        # Set quite mode
        if flags.skip_err:
            command.append('--quiet')
        # Set compress mode
        if flags.compressmode:
            if flags.compresslevel:
                command.append('--zc="{0}" --zl={1}'.format(flags.compressmode,flags.compresslevel))
            else:
                command.append('--zc="{0}"'.format(flags.compressmode))                
        # Set bandwidth limit
        if flags.bwlimit:
            command.append('--bwlimit={0}'.format(flags.bwlimit))
        # Set ssh custom port
        if flags.port:
            if flags.sshkey:
                command.append('-e "ssh -p {0} -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {1} -l {2}"'.format(flags.port, flags.sshkey,flags.user))
            else:
                command.append('-e "ssh -p {0} -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -l {1}"'.format(flags.port,flags.user))
        else:
            if flags.sshkey:
                command.append('-e "ssh -i {0} -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -l {1}"'.format(flags.sshkey,flags.user))
        # Set rsync custom port
        if flags.rport:
            command.append('--port={0}'.format(flags.rport))
        if flags.checksum:
            command.append('--checksum')
        if flags.remotersync:
            command.append('--rsync-path="{0}"'.format(flags.remotersync))
        # Set I/O timeout
        if flags.timeout:
            command.append('--timeout={0}'.format(flags.timeout))
        # Set dry-run mode
        if flags.dry_run:
            command.append('--dry-run')
            uty.write_log(log_args['status'], log_args['destination'], 'INFO', 'dry-run mode activate')
        # Set excludes
        if flags.exclude:
            for exclude in flags.exclude:
                command.append('--exclude={0}'.format(exclude))
        if flags.log:
            second_layer, folderend = compose_destination(host, flags.destination, is_last_full, folderend)
            #log_path = os.path.join(second_layer, 'backup.log')            
            log_path = args.logdirectory + 'rsync-' + host + '-' + folderend[0:11] + '.log'
            command.append(
                '--log-file={0}'.format(log_path)
            )
            uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'rsync log path: {0}'.format(log_path))
    elif flags.action == 'restore':
        command.append('-ahu --no-perms --no-owner --no-group')
        if flags.verbose:
#            command.append('-vP')
            command.append('-v')
            # Set quite mode
        if flags.skip_err:
            command.append('--quiet')
        # Set I/O timeout
        if flags.timeout:
            command.append('--timeout={0}'.format(flags.timeout))
        # Set mirror mode
        if flags.mirror:
            command.append('--delete')
            command.append('--ignore-times')
        # Set bandwidth limit
        if flags.bwlimit:
            command.append('--bwlimit={0}'.format(flags.bwlimit))
        # Set ssh custom port
        if flags.port:
            command.append('--rsh "ssh -p {0}"'.format(flags.port))
        # Set rsync custom port
        if flags.rport:
            command.append('--port={0}'.format(flags.rport))
        # Set dry-run mode
        if flags.dry_run:
            command.append('--dry-run')
            uty.write_log(log_args['status'], log_args['destination'], 'INFO', 'dry-run mode activate')
        # Set excludes
        if flags.exclude:
            for exclude in flags.exclude:
                command.append('--exclude={0}'.format(exclude))
        if flags.log:
            log_path = os.path.join(rpath, 'restore.log')
            command.append(
                '--log-file={0}'.format(log_path)
            )
            uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'rsync log path: {0}'.format(log_path))
    elif flags.action == 'export':
        command.append('-ahu --no-perms --no-owner --no-group')
        if flags.verbose:
#            command.append('-vP')
            command.append('-v')
            # Set quite mode
        if flags.skip_err:
            command.append('--quiet')
        # Set I/O timeout
        if flags.timeout:
            command.append('--timeout={0}'.format(flags.timeout))
        # Set mirror mode
        if flags.mirror:
            command.append('--delete')
            command.append('--ignore-times')
        # Set cut mode
        if flags.cut:
            command.append('--remove-source-files')
        # Set includes
        if flags.include:
            for include in flags.include:
                command.append('--include={0}'.format(include))
            command.append('--exclude="*"')
        # Set excludes
        if flags.exclude:
            for exclude in flags.exclude:
                command.append('--exclude={0}'.format(exclude))
        # Set timeout
        if flags.timeout:
            command.append('--timeout={0}'.format(flags.timeout))
        # Set bandwidth limit
        if flags.bwlimit:
            command.append('--bwlimit={0}'.format(flags.bwlimit))
        # Set ssh custom port
        if flags.port:
            command.append('--rsh "ssh -p {0}"'.format(flags.port))
        # Set rsync custom port
        if flags.rport:
            command.append('--port={0}'.format(flags.rport))
        # No copy symbolic link
        if flags.all:
            command.append('--safe-links')
        # Set dry-run mode
        if flags.dry_run:
            command.append('--dry-run')
            uty.write_log(log_args['status'], log_args['destination'], 'INFO', 'dry-run mode activate')
        if flags.log:
            log_path = os.path.join(flags.catalog, 'export.log')
            command.append(
                '--log-file={0}'.format(log_path)
            )
            uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'rsync log path: {0}'.format(log_path))
    uty.print_verbose(args.verbose, 'Command flags are: {0}'.format(' '.join(command)))
    return command


def compose_source(action, os_name, sources):
    """
    Compose source
    :param action: command action (backup, restore, archive)
    :param os_name: Name of operating system
    :param sources: Dictionary or string than contains the paths of source
    :return: list
    """
    if action == 'backup':
        src_list = []
        # Add include to the list
        folders = map_dict_folder(os_name)
        # Write catalog file
        write_catalog(catalog_path, backup_id, 'os', os_name)
        custom = True
        if 'System' in sources:
            src_list.append(':{0}'.format(folders['System']))
            return src_list
        if 'User' in sources:
            src_list.append(':{0}'.format(folders['User']))
            custom = False
        if 'Config' in sources:
            src_list.append(':{0}'.format(folders['Config']))
            custom = False
        if 'Application' in sources:
            src_list.append(':{0}'.format(folders['Application']))
            custom = False
        if 'Log' in sources:
            src_list.append(':{0}'.format(folders['Log']))
            custom = False
        if custom:
            # This is custom data
            for custom_data in sources:
                src_list.append(':{0}'.format("'" + custom_data.replace("'", "'\\''") + "'"))
        uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                          'OS {0}; backup folder {1}'.format(os_name, ' '.join(src_list)))
        uty.print_verbose(args.verbose, 'Include this criteria: {0}'.format(' '.join(src_list)))
        return src_list


def compose_restore_src_dst(backup_os, restore_os, restore_path, is_last_full):
    """
    Compare dictionary of folder backup and restore
    :param backup_os: backup structure folders
    :param restore_os: restore structure folders
    :param restore_path: path of backup
    :return: set
    """
    # Compare folder of the backup os and restore os
    b_folders = map_dict_folder(backup_os)
    r_folders = map_dict_folder(restore_os)
    for key in b_folders.keys():
        if restore_path in b_folders[key]:
            rsrc = os.path.join(restore_path, '*')
            rdst = r_folders[key]
            if rsrc and rdst:
                return rsrc, rdst
        else:
            rsrc = restore_path
            folderend=endfolder if not is_last_full else endfolder[0:12] + 'f'
            rdst = os.path.join(r_folders['System'], 'restore_{0}'.format(folderend))
            if rsrc and rdst:
                return rsrc, rdst


def get_restore_os():
    """
    Get the operating system value on catalog by id
    :return: os value (string)
    """
    config = read_catalog(os.path.join(args.catalog, '.catalog.cfg'))
    return config.get(args.id, 'os')


def compose_destination(computer_name, folder, is_last_full, folderend=None):
    """
    Compose folder destination of backup
    :param computer_name: name of source computer
    :param folder: path of backup
    :return: string
    """
    # Create root folder of backup
    logger.debug('is_last_full in compose destination call: {0}'.format(is_last_full))
    first_layer = os.path.join(folder, computer_name)
    # Check if backup is a Mirror or not
    if args.mode != 'Mirror':
        #print('Is_last_full: {0}'.format(is_last_full))
        #print('Computer_name: {0}'.format(computer_name))
        #print('Folder: {0}'.format(folder))
        logger.debug('Folderend in compose destination call: {0}'.format(folderend))
        if not folderend:
            folderend=endfolder if not is_last_full else endfolder[0:12] + 'f'
        second_layer = os.path.join(first_layer, folderend)
    else:
        second_layer = os.path.join(first_layer, 'mirror_backup')
    if not os.path.exists(first_layer):
        os.mkdir(first_layer)
        uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                          'Create folder {0}'.format(first_layer))
    if not os.path.exists(second_layer):
        os.mkdir(second_layer)
        uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                          'Create folder {0}'.format(second_layer))
    # Write catalog file
    logger.debug('Folderend in compose destination return: {0}'.format(folderend))
    logger.debug('is_last_full in compose destination: {0}'.format(is_last_full))
    write_catalog(catalog_path, backup_id, 'path', second_layer)
    uty.print_verbose(args.verbose, 'Destination is {0}'.format(second_layer))
    second_layer = os.path.join(second_layer, "") # Add slash to the end of the path
    logger.debug('Second layer with slash in compose destination return: {0}'.format(second_layer))
    return second_layer, folderend


def get_last_full(catalog):
    """
    Get the last full
    :param catalog: configparser object
    :return: path (string), os (string)
    """
    config = catalog
    if config:
        dates = []
        for bid in config.sections():
            #logger.debug('get_last_full timestamp: {0}'.format(config.get(bid, 'timestamp')))
            #logger.debug('get_last_full timestamp_string: {0}'.format(uty.string_to_time(config.get(bid, 'timestamp'))))
            if config.has_option(bid, 'type') and config.has_option(bid, 'name'):
                logger.debug('get_last_full hostname: {0}'.format(hostname))
                if config.get(bid, 'type') == 'Full' \
                        and config.get(bid, 'name') == hostname \
                        and (not config.has_option(bid, 'cleaned') or not config.has_option(bid, 'archived')):
                    try:
                        logger.debug('get_last_full timestamp: {0}'.format(config.get(bid, 'timestamp')))
                        logger.debug('get_last_full timestamp_string: {0}'.format(uty.string_to_time(config.get(bid, 'timestamp'))))
                        dates.append(uty.string_to_time(config.get(bid, 'timestamp')))
                        logger.debug('get_last_full dates_try: {0}'.format(dates))
                    except configparser.NoOptionError:
                        #print(PrintColor.RED +
                            #"ERROR: Corrupted catalog! No found timestamp in {0}".format(bid) + PrintColor.END)
                        logger.error("ERROR: Corrupted catalog! No found timestamp in {0}".format(bid))
                        exit(2)
        logger.debug('get_last_full dates: {0}'.format(dates))
        if dates:
            last_full = uty.time_to_string(max(dates))
            logger.debug('get_last_full last_full: {0}'.format(last_full))
            if last_full:
                uty.print_verbose(args.verbose, 'Last full is {0}'.format(last_full))
                for bid in config.sections():
                    logger.debug('get_last_full type, name, timestamp: {0}, {1}, {2}'.format(config.get(bid, 'type'), config.get(bid, 'name'), config.get(bid, 'timestamp')))
                    logger.debug('get_last_full hostname_if: {0}'.format(hostname))
                    if config.get(bid, 'type') == 'Full' and config.get(bid, 'name') == hostname and config.get(bid, 'timestamp') == last_full:
                        logger.debug('get_last_full path: {0}'.format(config.get(bid, 'path')))
                        return config.get(bid, 'path'), config.get(bid, 'os')
                        #return config.get(bid, 'path')
        else:
            return False
    else:
        return False


def get_last_backup(catalog):
    """
    Get the last available backup
    :param catalog: configparser object
    :return: path (string), os (string)
    """
    config = catalog
    dates = []
    if config:
        for bid in config.sections():
            if config.has_option(bid, 'type') and config.has_option(bid, 'name'):
                if config.get(bid, 'name') == hostname \
                        and (not config.has_option(bid, 'cleaned') or not config.has_option(bid, 'archived')):
                    try:
                        dates.append(uty.string_to_time(config.get(bid, 'timestamp')))
                    except configparser.NoOptionError:
                        print(PrintColor.RED +
                            "ERROR: Corrupted catalog! No found timestamp in {0}".format(bid) + PrintColor.END)
                        logger.error("ERROR: Corrupted catalog! No found timestamp in {0}".format(bid))
                        exit(2)
        if dates:
            dates.sort()
            last = uty.time_to_string(dates[-1])
            if last:
                for bid in config.sections():
                    if config.get(bid, 'name') == hostname and config.get(bid, 'timestamp') == last:
                        return config.get(bid, 'path'), config.get(bid, 'os')
        else:
            return False
    else:
        return False


def count_full(config, name):
    """
    Count all full (and Incremental) backup in a catalog
    :param config: configparser object
    :param name: hostname of machine
    :return: count (int)
    """
    count = 0
    if config:
        for bid in config.sections():
            if ((config.get(bid, 'type') == 'Full' or
                 config.get(bid, 'type') == 'Incremental') and
                    config.get(bid, 'name') == name):
                count += 1
    return count


def list_backup(config, name):
    """
    Count all full in a catalog
    :param config: configparser object
    :param name: hostname of machine
    :return: r_list (list)
    """
    r_list = list()
    if config:
        for bid in config.sections():
            if config.get(bid, 'name') == name:
                r_list.append(bid)
    return r_list


def read_catalog(catalog):
    """
    Read a catalog file
    :param catalog: catalog file
    :return: catalog file (configparser)
    """
    config = configparser.ConfigParser()
    file = config.read(catalog)
    if file:
        return config
    else:
        uty.print_verbose(args.verbose, 'Catalog not found! Create a new one.')
        if os.path.exists(os.path.dirname(catalog)):
            uty.touch(catalog)
            config.read(catalog)
            return config
        else:
            #print(PrintColor.RED +
                  #'ERROR: Folder {0} not exist!'.format(os.path.dirname(catalog)) + PrintColor.END)
            logger.error('ERROR: Folder {0} not exist!'.format(os.path.dirname(catalog)))
            exit(1)


def write_catalog(catalog, section, key, value):
    """
    Write catalog file
    :param catalog: path catalog file
    :param section: section of catalog file
    :param key: key of catalog file
    :param value: value of key of catalog file
    :return:
    """
    config = read_catalog(catalog)
    if not args.dry_run:
        # Add new section
        try:
            config.add_section(section)
            config.set(section, key, value)
        except configparser.DuplicateSectionError:
            config.set(section, key, value)
        # Write new section
        with open(catalog, 'w') as catalogfile:
            config.write(catalogfile)


def retention_policy(host, catalog, logpath):
    """
    Retention policy
    :param host: hostname of machine
    :param catalog: catalog file
    :param logpath: path of log file
    """
    config = read_catalog(catalog)
    full_count = count_full(config, host)
    if len(args.retention) >= 3:
        #print(PrintColor.RED + 'ERROR: The "--retention or -r" parameter must have two integers. '
                                       #'Three or more arguments specified: {}'.format(args.retention) +
              #PrintColor.END)
        logger.error('ERROR: The "--retention or -r" parameter must have two integers. ')
        return
    if args.retention[1]:
        backup_list = list_backup(config, host)[-args.retention[1]:]
    else:
        backup_list = list()
    cleanup = -1
    for bid in config.sections():
        if bid not in backup_list:
            if (config.get(bid, 'cleaned', fallback='unset') == 'unset') and (config.get(bid, 'name') == host):
                type_backup = config.get(bid, 'type')
                path = config.get(bid, 'path')
                date = config.get(bid, 'timestamp')
                if (type_backup == 'Full' or type_backup == 'Incremental') and (full_count <= 1):
                    continue
                uty.print_verbose(args.verbose, "Check cleanup this backup {0}. Folder {1}".format(bid, path))
                if not dry_run("Cleanup {0} backup folder".format(path)):
                    cleanup = uty.cleanup(path, date, args.retention[0])
                if not os.path.exists(path):
                    uty.print_verbose(args.verbose, "This folder {0} does not exist. "
                                                        "The backup has already been cleaned.".format(path))
                    cleanup = 0
                if cleanup == 0:
                    write_catalog(catalog, bid, 'cleaned', 'True')
                    print(PrintColor.GREEN + 'SUCCESS: Cleanup {0} successfully.'.format(path) +
                          PrintColor.END)
                    uty.write_log(log_args['status'], logpath, 'INFO',
                                      'Cleanup {0} successfully.'.format(path))
                elif cleanup == 1:
                    print(PrintColor.RED + 'ERROR: Cleanup {0} failed.'.format(path) +
                          PrintColor.END)
                    uty.write_log(log_args['status'], logpath, 'ERROR',
                                      'Cleanup {0} failed.'.format(path))
                else:
                    uty.print_verbose(args.verbose, "No cleanup backup {0}. Folder {1}".format(bid, path))


def archive_policy(catalog, destination):
    """
    Archive policy
    :param catalog: catalog file
    :param destination: destination pth of archive file
    """
    config = read_catalog(catalog)
    archive = -1
    for bid in config.sections():
        full_count = count_full(config, config.get(bid, 'name'))
        if (config.get(bid, 'archived', fallback='unset') == 'unset') and not \
                (config.get(bid, 'cleaned', fallback=False)):
            type_backup = config.get(bid, 'type')
            path = config.get(bid, 'path')
            date = config.get(bid, 'timestamp')
            logpath = os.path.join(os.path.dirname(path), 'general.log')
            uty.print_verbose(args.verbose, "Check archive this backup {0}. Folder {1}".format(bid, path))
            if (type_backup == 'Full') and (full_count <= 1):
                continue
            if not dry_run("Archive {0} backup folder".format(path)):
                archive = uty.archive(path, date, args.days, destination)
            if archive == 0:
                write_catalog(catalog, bid, 'archived', 'True')
                print(PrintColor.GREEN + 'SUCCESS: Archive {0} successfully.'.format(path) +
                      PrintColor.END)
                uty.write_log(log_args['status'], logpath, 'INFO',
                                  'Archive {0} successfully.'.format(path))
            elif archive == 1:
                print(PrintColor.RED + 'ERROR: Archive {0} failed.'.format(path) +
                      PrintColor.END)
                uty.write_log(log_args['status'], logpath, 'ERROR',
                                  'Archive {0} failed.'.format(path))
            else:
                uty.print_verbose(args.verbose, "No archive backup {0}. Folder {1}".format(bid, path))


def deploy_configuration(computer, user):
    """
    Deploy configuration on remote machine (run "ssh-copy-id -i pub_file -f <user>@<computer>")
    :param computer: remote computer than deploy RSA key
    :param user: remote user on computer
    """
    # Create home path
    home = os.path.expanduser('~')
    ssh_folder = os.path.join(home, '.ssh')
    # Remove private key file
    id_rsa_pub_file = os.path.join(ssh_folder, 'id_rsa.pub')
    uty.print_verbose(args.verbose, 'Public id_rsa is {0}'.format(id_rsa_pub_file))
    if not dry_run('Copying configuration to {0}'.format(computer)):
        if os.path.exists(id_rsa_pub_file):
            print('Copying configuration to' + PrintColor.BOLD + ' {0}'.format(computer) +
                  PrintColor.END + '; write the password:')
            return_code = subprocess.call('ssh-copy-id -i {0} {1}@{2}'.format(id_rsa_pub_file, user, computer),
                                          shell=True)
            uty.print_verbose(args.verbose, 'Return code of ssh-copy-id: {0}'.format(return_code))
            if return_code == 0:
                print(PrintColor.GREEN + "SUCCESS: Configuration copied successfully on {0}!".format(computer) +
                      PrintColor.END)
            else:
                print(PrintColor.RED + "ERROR: Configuration has not been copied successfully on {0}!".format(
                    computer) +
                      PrintColor.END)
        else:
            print(PrintColor.YELLOW + "WARNING: Public key ~/.ssh/id_rsa.pub is not exist" +
                  PrintColor.END)
            exit(2)


def remove_configuration():
    """
    Remove a new configuration (remove an exist RSA key pair)
    """
    # Create home path
    home = os.path.expanduser('~')
    ssh_folder = os.path.join(home, '.ssh')
    if not dry_run('Remove private id_rsa'):
        if uty.confirm('Are you sure to remove existing rsa keys?'):
            # Remove private key file
            id_rsa_file = os.path.join(ssh_folder, 'id_rsa')
            uty.print_verbose(args.verbose, 'Remove private id_rsa {0}'.format(id_rsa_file))
            if os.path.exists(id_rsa_file):
                os.remove(id_rsa_file)
            else:
                print(
                    PrintColor.YELLOW + "WARNING: Private key ~/.ssh/id_rsa is not exist" +
                    PrintColor.END)
                exit(2)
            # Remove public key file
            id_rsa_pub_file = os.path.join(ssh_folder, 'id_rsa.pub')
            uty.print_verbose(args.verbose, 'Remove public id_rsa {0}'.format(id_rsa_pub_file))
            if os.path.exists(id_rsa_pub_file):
                os.remove(id_rsa_pub_file)
            else:
                print(
                    PrintColor.YELLOW + "WARNING: Public key ~/.ssh/id_rsa.pub is not exist" +
                    PrintColor.END)
                exit(2)
            print(PrintColor.GREEN + "SUCCESS: Removed configuration successfully!" + PrintColor.END)


def new_configuration():
    """
    Create a new configuration (create a RSA key pair)
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend

    if not dry_run('Generate private/public key pair'):
        # Generate private/public key pair
        uty.print_verbose(args.verbose, 'Generate private/public key pair')
        private_key = rsa.generate_private_key(backend=default_backend(), public_exponent=65537,
                                               key_size=2048)
        # Get public key in OpenSSH format
        uty.print_verbose(args.verbose, 'Get public key in OpenSSH format')
        public_key = private_key.public_key().public_bytes(serialization.Encoding.OpenSSH,
                                                           serialization.PublicFormat.OpenSSH)
        # Get private key in PEM container format
        uty.print_verbose(args.verbose, 'Get private key in PEM container format')
        pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                                        encryption_algorithm=serialization.NoEncryption())
        # Decode to printable strings
        private_key_str = pem.decode('utf-8')
        public_key_str = public_key.decode('utf-8')
        # Create home path
        home = os.path.expanduser('~')
        # Create folder .ssh
        ssh_folder = os.path.join(home, '.ssh')
        uty.print_verbose(args.verbose, 'Create folder {0}'.format(ssh_folder))
        if not os.path.exists(ssh_folder):
            os.mkdir(ssh_folder, mode=0o755)
        # Create private key file
        id_rsa_file = os.path.join(ssh_folder, 'id_rsa')
        uty.print_verbose(args.verbose, 'Create private key file {0}'.format(id_rsa_file))
        if not os.path.exists(id_rsa_file):
            with open(id_rsa_file, 'w') as id_rsa:
                os.chmod(id_rsa_file, mode=0o600)
                id_rsa.write(private_key_str)
        else:
            #print(PrintColor.YELLOW + "WARNING: Private key ~/.ssh/id_rsa exists" + PrintColor.END)
            logger.warning('Private key ~/.ssh/id_rsa exists')
            #print('If you want to use the existing key, run "bb config --deploy name_of_machine", '
                  #'otherwise to remove it, '
                  #'run "bb config --remove"')
            exit(2)
        # Create private key file
        id_rsa_pub_file = os.path.join(ssh_folder, 'id_rsa.pub')
        uty.print_verbose(args.verbose, 'Create public key file {0}'.format(id_rsa_pub_file))
        if not os.path.exists(id_rsa_pub_file):
            with open(id_rsa_pub_file, 'w') as id_rsa_pub:
                os.chmod(id_rsa_pub_file, mode=0o644)
                id_rsa_pub.write(public_key_str)
        else:
            #print(PrintColor.YELLOW + "WARNING: Public key ~/.ssh/id_rsa.pub exists" + PrintColor.END)
            logger.warning('Public key ~/.ssh/id_rsa.pub exists')
            #print('If you want to use the existing key, run "bb config --deploy name_of_machine", '
                  #'otherwise to remove it, '
                  #'run "bb config --remove"')
            exit(2)
        #print(PrintColor.GREEN + "SUCCESS: New configuration successfully created!" + PrintColor.END)
        logger.info('New configuration successfully created!')


def check_configuration(ip):
    """
    Check if configuration is correctly deployed
    :param ip: hostname of pc or ip address
    :return: output of command
    """
    from subprocess import check_output, STDOUT
    cmd = "ssh-keyscan {0}".format(ip)
    try:
        #output = check_output(["ssh-keyscan", "{0}".format(ip)], stderr=STDOUT, shell=True).decode()
        output = check_output(cmd, stderr=STDOUT, shell=True).decode().partition('\n')[0]
        logger.debug('Output of ssh-keyscan: {0}'.format(output))
        #if not out:
        #    return False
        #else:
        return True
    # except subprocess.CalledProcessError:
    except Exception as e:
        logger.error('{0}'.format(e.output.decode())) # print out the stdout messages up to the exception
        logger.error('{0}'.format(e)) # To print out the exception message
        logger.error('SSH key configuration error.') # To print out the exception message
        return False


def init_catalog(catalog):
    """
    :param catalog: catalog file
    """
    config = read_catalog(catalog)
    for cid in config.sections():
        if not os.path.exists(config[cid]['path']):
            uty.print_verbose(args.verbose, "Backup-id {0} has been removed to catalog!".format(cid))
            config.remove_section(cid)
    # Write file
    with open(catalog, 'w') as catalogfile:
        config.write(catalogfile)


def delete_host(catalog, host):
    """
    :param catalog: catalog file
    :param host: hostname or ip address
    """
    from shutil import rmtree
    config = read_catalog(catalog)
    root = os.path.join(os.path.dirname(catalog), host)
    for cid in config.sections():
        if config.get(cid, "name") == host:
            if not os.path.exists(config[cid]['path']):
                uty.print_verbose(args.verbose, "Backup-id {0} has been removed to catalog!".format(cid))
                config.remove_section(cid)
            else:
                path = config.get(cid, 'path')
                date = config.get(cid, 'timestamp')
                cleanup = uty.cleanup(path, date, 0)
                if cleanup == 0:
                    print(PrintColor.GREEN + 'SUCCESS: Delete {0} successfully.'.format(path) +
                          PrintColor.END)
                    uty.print_verbose(args.verbose, "Backup-id {0} has been removed to catalog!".format(cid))
                    config.remove_section(cid)
                elif cleanup == 1:
                    print(PrintColor.RED + 'ERROR: Delete {0} failed.'.format(path) +
                          PrintColor.END)
    rmtree(root)
    # Write file
    with open(catalog, 'w') as catalogfile:
        config.write(catalogfile)


def delete_backup(catalog, path):
    """
    :param catalog: catalog file
    :param path: path of the given backup
    """
    config = read_catalog(catalog)
    #root = os.path.join(os.path.dirname(catalog), host)
    root = path
    #print('path: {0}'.format(path))
    logger.debug('path: {0}'.format(path))
    for cid in config.sections():
        #print('cid path: {0}'.format(config.get(cid, "path")))
        logger.debug('cid path: {0}'.format(config.get(cid, "path")))
        if config.get(cid, "path") == path:
            #print('cid path in if: {0}'.format(config.get(cid, "path")))
            if not os.path.exists(config[cid]['path']):
                #print_verbose(args.verbose, "Backup-id {0} has been removed to catalog!".format(cid))
                #print("Backup-id {0} has been removed to catalog!".format(cid))
                config.remove_section(cid)
                logger.info("Backup-id {0} has been removed to catalog!".format(cid))
            else:
                path = config.get(cid, 'path')
                date = config.get(cid, 'timestamp')
                #cleanup = uty.cleanup(path, date, 0)
                #if cleanup == 0:
                #print(PrintColor.GREEN + 'SUCCESS: Delete {0} successfully.'.format(path) +
                        #PrintColor.END)
                #print_verbose(args.verbose, "Backup-id {0} has been removed to catalog!".format(cid))
                config.remove_section(cid)
                #print("Backup-id {0} has been removed to catalog!".format(cid))
                logger.info('Delete {0} successfully.'.format(path))
                #elif cleanup == 1:
                    #print(PrintColor.RED + 'ERROR: Delete {0} failed.'.format(path) +
                    #      PrintColor.END)
                    #logger.error('Delete {0} failed.'.format(path))
    rmtree(root)
    # Write file
    with open(catalog, 'w') as catalogfile:
        config.write(catalogfile)


def clean_catalog(catalog):
    """
    :param catalog: catalog file
    """
    config = read_catalog(catalog)
    uty.print_verbose(args.verbose, "Start check catalog file: {0}!".format(catalog))
    for cid in config.sections():
        uty.print_verbose(args.verbose, "Check backup-id: {0}!".format(cid))
        mod = False
        if not config.get(cid, 'type', fallback=''):
            config.set(cid, 'type', 'Incremental')
            mod = True
        if not config.get(cid, 'path', fallback=''):
            config.remove_section(cid)
            mod = True
        if not config.get(cid, 'name', fallback=''):
            config.set(cid, 'name', 'default')
            mod = True
        if not config.get(cid, 'os', fallback=''):
            config.set(cid, 'os', 'Unix')
            mod = True
        if not config.get(cid, 'timestamp', fallback=''):
            config.set(cid, 'timestamp', uty.time_for_log())
            mod = True
        if not config.get(cid, 'start', fallback=''):
            config.set(cid, 'start', uty.time_for_log())
            mod = True
        if not config.get(cid, 'end', fallback=''):
            config.set(cid, 'end', uty.time_for_log())
            mod = True
        if not config.get(cid, 'status', fallback=''):
            config.set(cid, 'status', '0')
            mod = True
        if mod:
            #print(PrintColor.YELLOW +
                  #'WARNING: The backup-id {0} has been set to default value, because he was corrupt. '
                  #'Check it!'.format(cid) + PrintColor.END)
            logger.warning('The backup-id {0} has been set to default value, because he was corrupt. '
                            'Check it!'.format(cid))
    # Write file
    with open(catalog, 'w') as catalogfile:
        config.write(catalogfile)



def single_action(args,configfile=None):

    """
    Function to preapare one actual rsync command.
    :param args: the configurtion from the command line and the yaml files
    :param configfile: the actual yaml config file
    :return aktcmd: the actual rsync command
    :return aktlog: the actual log file
    :return online: check if the actual host's ssh and rsync ports are online
    """

    global catalog_path, backup_catalog, hostname, backup_id, log_args, logs, aktlogs, rpath
    
    if configfile:
        opt = vars(args)
        args = yaml.load(open(args.mainconfig), Loader=yaml.FullLoader)
        opt.update(args)
        args = types.SimpleNamespace(**opt)        
        opt = vars(args)
        args = yaml.load(open(configfile), Loader=yaml.FullLoader)
        opt.update(args)
        args = types.SimpleNamespace(**opt)
    # Check action
    if not args.action:
        # print args
        parser.print_help()
    
    if args.action != 'backup':
        #print(PrintColor.RED +
                #"ERROR: Only 'backup' mode works! '{0}' mode has not yet tested".format(args.action) + PrintColor.END)
        logger.error("ERROR: Only 'backup' mode works! '{0}' mode has not yet tested".format(args.action))
        exit(1)
    # Check config session

    if args.action == 'config':
        if args.new_conf:
            new_configuration()
        elif args.remove_conf:
            remove_configuration()
        elif args.deploy_host:
            deploy_configuration(args.deploy_host, args.deploy_user)
        elif args.init:
            catalog_path = os.path.join(args.init, '.catalog.cfg')
            init_catalog(catalog_path)
        elif args.delete:
            catalog_path = os.path.join(args.delete[0], '.catalog.cfg')
            delete_host(catalog_path, args.delete[1])
        elif args.clean:
            catalog_path = os.path.join(args.clean, '.catalog.cfg')
            clean_catalog(catalog_path)
        else:
            parser.print_usage()
            print('For ' + PrintColor.BOLD + 'config' + PrintColor.END + ' usage, "--help" or "-h"')
            exit(1)

    # Check backup session
    if args.action == 'backup':
        # Check custom ssh port
        port = args.port if args.port else 22
        # Check custom rsync port
        rport = args.rport if args.rport else 873
        hostnames = []
        # cmds = []
        # logs = []
        logger.info('Rsync configfile: {0}, args: {1}'.format(configfile,args)                    )               
        if args.hostname:
            # Computer list
            hostnames.append(args.hostname)
        elif args.list:
            if os.path.exists(args.list):
                list_file = open(args.list, 'r').read().split()
                for line in list_file:
                    # Computer list
                    hostnames.append(line)
            else:
                #print(PrintColor.RED + 'ERROR: The file {0} not exist!'.format(args.list)
                      #+ PrintColor.END)
                logger.error('ERROR: The file {0} not exist!'.format(args.list))
        else:
            parser.print_usage()
            # print args
            print('For ' + PrintColor.BOLD + 'backup' + PrintColor.END + ' usage, "--help" or "-h"')
            exit(1)
        # print (args)
        # exit(0)
        # most csak egy hostra jo
        for hostname in hostnames:
            log_args = {}
            cmd =''
            if args.hostpart:
                hostname_orig=hostname
                hostname=hostname+'-'+args.hostpart
            else:
                hostname_orig=hostname
            online = True
            eport = None
            if not uty.check_ssh(hostname_orig, port):
                #print(PrintColor.RED + 'ERROR: The port {0} on {1} is closed!'.format(port, hostname)
                      #+ PrintColor.END)
                logger.error('The port {0} on {1} is closed or blocked!'.format(port, hostname))
                online = False
                eport = port
                continue
            logger.debug('DEBUG: After ssh port check: The port {0} on {1} is open!'.format(port, hostname_orig))
            if not uty.check_rsync(hostname_orig, rport):
                #print(PrintColor.RED + 'ERROR: The port {0} on {1} is closed!'.format(rport, hostname)
                      #+ PrintColor.END)
                logger.error('The port {0} on {1} is closed or blocked!'.format(rport, hostname))
                online = False
                eport = rport
                continue
            logger.debug('DEBUG: After rsync port check: The port {0} on {1} is open!'.format(rport, hostname_orig))
            if not args.verbose:
                if not check_configuration(hostname_orig):
                    #print(PrintColor.RED + '''ERROR: For bulk or silently backup, deploy configuration!
                            #See bb deploy --help or specify --verbose''' + PrintColor.END)
                    logger.error('For bulk or silently backup, deploy configuration! (Copy the public key to the remote host)')
                    online = False
                    continue
            # Log information's
            backup_id = '{}'.format(uty.new_id())
            log_args = {
                'id': backup_id,
                'hostname': hostname,
                'status': args.log,
                'destination': os.path.join(args.destination, hostname, 'general.log')
            }
            # print('Log_args: ',log_args)
            # logs.append(log_args)
            catalog_path = os.path.join(args.destination, '.catalog.cfg')
            backup_catalog = read_catalog(catalog_path)
            # Compose command
            #print('Compose commands: ',args)
            is_last_full = False
            if args.mode == 'Full':
                is_last_full = True
            elif args.mode == 'Incremental':
                last_bck = get_last_backup(backup_catalog)
                if not last_bck:
                    is_last_full = True
            elif args.mode == 'Differential':
                last_full = get_last_full(backup_catalog)
                if not last_full:
                    is_last_full = True
            #print('is_last_full in single_action: ',is_last_full)
            logger.debug('is_last_full in single_action: {0}'.format(is_last_full))
            bck_dst, folderend = compose_destination(hostname, args.destination, is_last_full)
            cmd = compose_command(args, hostname, folderend)
            # Check if start-from is specified
            if args.sfrom:
                if backup_catalog.has_section(args.sfrom):
                    # Check if exist path of backup
                    if os.path.exists(backup_catalog[args.sfrom]['path']):
                        cmd.append('--copy-dest={0}'.format(backup_catalog[args.sfrom]['path']))
                    else:
                        #print(PrintColor.YELLOW +
                              #'WARNING: Backup folder {0} not exist!'.format(backup_catalog[args.sfrom]['path'])
                              #+ PrintColor.END)
                        logger.warning('WARNING: Backup folder {0} not exist!'.format(backup_catalog[args.sfrom]['path']))
                else:
                    #print(PrintColor.RED +
                          #'ERROR: Backup id {0} not exist in catalog {1}!'.format(args.sfrom, args.destination)
                          #+ PrintColor.END)
                    logger.error('ERROR: Backup id {0} not exist in catalog {1}!'.format(args.sfrom, args.destination))
                    exit(1)
            uty.print_verbose(args.verbose, 'Create a folder structure for {0} os'.format(args.type))
            # Write catalog file
            write_catalog(catalog_path, backup_id, 'name', hostname)
            # Compose source
            if args.data:
                srcs = args.data
                source_list = compose_source(args.action, args.type, srcs)
            elif args.customdata:
                srcs = args.customdata
                source_list = compose_source(args.action, args.type, srcs)
            else:
                source_list = []
            # Check if hostname is localhost or 127.0.0.1
            if (hostname_orig == "localhost") or (hostname_orig == "LOCALHOST") or (hostname_orig == "127.0.0.1"):
                # Compose source with only path of folder list
               cmd.append(" ".join(source_list)[1:])
            else:
                # Compose source <user>@<hostname> format
                if not args.sshkey and not args.port:
                    cmd.append('{0}@{1}'.format(args.user, hostname_orig).__add__(" ".join(source_list)))
                else:
                    cmd.append('{0}'.format(hostname_orig).__add__(" ".join(source_list)))
            # Compose destination
            uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'Backup on folder {0}'.format(bck_dst))
            cmd.append(bck_dst)
            # Compose pull commands
            #cmds.append(' '.join(cmd))
            #print (cmds)
            # Write catalog file
            write_catalog(catalog_path, backup_id, 'timestamp', uty.time_for_log())
            # Create a symlink for last backup
            uty.make_symlink(bck_dst, os.path.join(args.destination, hostname, 'last_backup'))
        # Start backup
        # run_in_parallel(start_process, cmds, args.parallel)
        # print('Single_action cmd: ',cmd)
        #print('Single_action log: ',log_args)
        return cmd, log_args, online, eport
    # Check restore session
    if args.action == 'restore':
        # Check custom ssh port
        port = args.port if args.port else 22
        # Check custom rsync port
        rport = args.rport if args.rport else 873
        cmds = []
        logs = []
        rhost = ''
        hostname = args.hostname
        rpath = ''
        bos = ''
        ros = ''
        rfolders = ''
        if not args.type and args.id:
            args.type = get_restore_os()
        # Read catalog file
        catalog_path = os.path.join(args.catalog, '.catalog.cfg')
        restore_catalog = read_catalog(catalog_path)
        # Check if select backup-id or last backup
        if args.last:
            rhost = hostname
            last_backup = get_last_backup(restore_catalog)
            if not args.type:
                args.type = last_backup[1]
            rpath = last_backup[0]
            if os.path.exists(rpath):
                bos = last_backup[1]
                ros = args.type
                rfolders = [f.path for f in os.scandir(rpath) if f.is_dir()]
            else:
                print(PrintColor.RED + 'ERROR: Backup folder {0} not exist!'.format(rpath) +
                      PrintColor.END)
                exit(1)
        elif args.id:
            # Check catalog backup id
            if restore_catalog.has_section(args.id):
                # Check if exist path of backup
                if os.path.exists(restore_catalog[args.id]['path']):
                    rhost = hostname
                    rpath = restore_catalog[args.id]['path']
                    bos = restore_catalog[args.id]['os']
                    ros = args.type
                    rfolders = [f.path for f in os.scandir(rpath) if f.is_dir()]
                else:
                    print(PrintColor.RED +
                          'ERROR: Backup folder {0} not exist!'.format(restore_catalog[args.id]['path'])
                          + PrintColor.END)
                    exit(1)
            else:
                print(PrintColor.RED +
                      'ERROR: Backup id {0} not exist in catalog {1}!'.format(args.id, args.catalog)
                      + PrintColor.END)
                exit(1)
        # Test connection
        if not uty.check_ssh(rhost, port):
            print(PrintColor.RED + 'ERROR: The port {0} on {1} is closed or blocked!'.format(port, rhost)
                    + PrintColor.END)
            exit(1)
        if not uty.check_rsync(rhost, rport):
            print(PrintColor.RED + 'ERROR: The port {0} on {1} is closed or blocked!'.format(rport, rhost)
                    + PrintColor.END)
            exit(1)
        if not args.verbose:
            if not check_configuration(rhost):
                print(PrintColor.RED + '''ERROR: For bulk or silently backup to deploy configuration!
                                            See bb deploy --help or specify --verbose''' + PrintColor.END)
                exit(1)
        log_args = {
            'hostname': rhost,
            'status': args.log,
            'destination': os.path.join(os.path.dirname(rpath), 'general.log')
        }
        uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                          'Restore on {0}'.format(rhost))
        for rf in rfolders:
            # Append logs
            logs.append(log_args)
            # Compose command
            cmd = compose_command(args, rhost)
            # ATTENTION: permit access to anyone users
            if ros == 'Windows':
                cmd.append('--chmod=ugo=rwX')
            # Compose source and destination
            src_dst = compose_restore_src_dst(bos, ros, os.path.basename(rf), is_last_full)
            if src_dst:
                src = src_dst[0]
                # Compose source
                cmd.append(os.path.join(rpath, src))
                dst = src_dst[1]
                if (hostname == "localhost") or (hostname == "LOCALHOST") or (hostname == "127.0.0.1"):
                    # Compose destination only with path of folder
                    cmd.append('{}'.format(dst))
                else:
                    # Compose destination <user>@<hostname> format
                    cmd.append('{0}@{1}:'.format(args.user, rhost).__add__(dst))
                # Add command
                if uty.confirm("Want to do restore path {0}?".format(os.path.join(rpath, src))):
                    cmds.append(' '.join(cmd))
        # Start restore
        run_in_parallel(start_process, cmds, 1)

    # Check archive session
    if args.action == 'archive':
        # Log info
        log_args = {
            'status': args.log,
            'destination': os.path.join(args.catalog, 'archive.log')
        }
        # Read catalog file
        archive_catalog = os.path.join(args.catalog, '.catalog.cfg')
        # Archive paths
        archive_policy(archive_catalog, args.destination)

    # Check list session
    if args.action == 'list':
        # Log info
        log_args = {
            'status': args.log,
            'destination': os.path.join(args.catalog, 'backup.list')
        }
        # Read catalog file
        list_catalog = read_catalog(os.path.join(args.catalog, '.catalog.cfg'))
        # Check specified argument backup-id
        if args.id:
            if not args.oneline:
                uty.print_verbose(args.verbose, "Select backup-id: {0}".format(args.id))
                if not list_catalog.has_section(args.id):
                    print(PrintColor.RED +
                          'ERROR: Backup-id {0} not exist!'.format(args.id)
                          + PrintColor.END)
                    exit(1)
                print('Backup id: ' + PrintColor.BOLD + args.id +
                      PrintColor.END)
                print('Hostname or ip: ' + PrintColor.DARKCYAN + list_catalog[args.id]['name'] +
                      PrintColor.END)
                print('Type: ' + PrintColor.DARKCYAN + list_catalog[args.id]['type'] +
                      PrintColor.END)
                print('Timestamp: ' + PrintColor.DARKCYAN + list_catalog[args.id]['timestamp'] +
                      PrintColor.END)
                print('Start: ' + PrintColor.DARKCYAN + list_catalog[args.id]['start'] +
                      PrintColor.END)
                print('Finish: ' + PrintColor.DARKCYAN + list_catalog[args.id]['end'] +
                      PrintColor.END)
                print('OS: ' + PrintColor.DARKCYAN + list_catalog[args.id]['os'] +
                      PrintColor.END)
                print('ExitCode: ' + PrintColor.DARKCYAN + list_catalog[args.id]['status'] +
                      PrintColor.END)
                print('Path: ' + PrintColor.DARKCYAN + list_catalog[args.id]['path'] +
                      PrintColor.END)
                if list_catalog.get(args.id, 'cleaned', fallback=False):
                    print('Cleaned: ' + PrintColor.DARKCYAN + list_catalog[args.id]['cleaned'] +
                          PrintColor.END)
                elif list_catalog.get(args.id, 'archived', fallback=False):
                    print('Archived: ' + PrintColor.DARKCYAN + list_catalog[args.id]['archived'] +
                          PrintColor.END)
                else:
                    print('List: ' + PrintColor.DARKCYAN + '\n'.join(os.listdir(list_catalog[args.id]['path']))
                          + PrintColor.END)
            else:
                if not list_catalog.has_section(args.id):
                    print(PrintColor.RED +
                          'ERROR: Backup-id {0} not exist!'.format(args.id)
                          + PrintColor.END)
                    exit(1)
                print('Id: ' + PrintColor.BOLD + args.id +
                      PrintColor.END, end=' - ')
                print('Name: ' + PrintColor.DARKCYAN + list_catalog[args.id]['name'] +
                      PrintColor.END, end=' - ')
                print('Type: ' + PrintColor.DARKCYAN + list_catalog[args.id]['type'] +
                      PrintColor.END, end=' - ')
                print('Timestamp: ' + PrintColor.DARKCYAN + list_catalog[args.id]['timestamp'] +
                      PrintColor.END, end=' - ')
                print('Start: ' + PrintColor.DARKCYAN + list_catalog[args.id]['start'] +
                      PrintColor.END, end=' - ')
                print('Finish: ' + PrintColor.DARKCYAN + list_catalog[args.id]['end'] +
                      PrintColor.END, end=' - ')
                print('OS: ' + PrintColor.DARKCYAN + list_catalog[args.id]['os'] +
                      PrintColor.END, end=' - ')
                print('ExitCode: ' + PrintColor.DARKCYAN + list_catalog[args.id]['status'] +
                      PrintColor.END, end=' - ')
                print('Path: ' + PrintColor.DARKCYAN + list_catalog[args.id]['path'] +
                      PrintColor.END, end=' - ')
                if list_catalog.get(args.id, 'cleaned', fallback=False):
                    print('Cleaned: ' + PrintColor.DARKCYAN + list_catalog[args.id]['cleaned'] +
                          PrintColor.END, end=' - ')
                elif list_catalog.get(args.id, 'archived', fallback=False):
                    print('Archived: ' + PrintColor.DARKCYAN + list_catalog[args.id]['archived'] +
                          PrintColor.END, end=' - ')
                else:
                    print('List: ' + PrintColor.DARKCYAN + ' '.join(os.listdir(list_catalog[args.id]['path'])) +
                          PrintColor.END)
        elif args.detail:
            log_args['hostname'] = list_catalog[args.detail]['name']
            logs = [log_args]
            uty.print_verbose(args.verbose, "List detail of backup-id: {0}".format(args.detail))
            print('Detail of backup folder: ' + PrintColor.DARKCYAN
                  + list_catalog[args.detail]['path'] + PrintColor.END)
            print('List: ' + PrintColor.DARKCYAN + '\n'.join(os.listdir(list_catalog[args.detail]['path']))
                  + PrintColor.END)
            if log_args['status']:
                uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                  'BUTTERFLY BACKUP DETAIL (BACKUP-ID: {0} PATH: {1})'.format(
                                      args.detail, list_catalog[args.detail]['path'])
                                  )
                cmd = 'rsync --list-only -r --log-file={0} {1}'.format(log_args['destination'],
                                                                       list_catalog[args.detail]['path'])
            else:
                cmd = 'rsync --list-only -r {0}'.format(list_catalog[args.detail]['path'])
            start_process(cmd)
        elif args.archived:
            uty.print_verbose(args.verbose, "List all archived backup in catalog")
            text = 'BUTTERFLY BACKUP CATALOG (ARCHIVED)\n\n'
            uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'BUTTERFLY BACKUP CATALOG (ARCHIVED)')
            for lid in list_catalog.sections():
                if 'archived' in list_catalog[lid]:
                    uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Backup id: {0}'.format(lid))
                    uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Hostname or ip: {0}'.format(list_catalog[lid]['name']))
                    uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Timestamp: {0}'.format(list_catalog[lid]['timestamp']))
                    text += 'Backup id: {0}'.format(lid)
                    text += '\n'
                    text += 'Hostname or ip: {0}'.format(list_catalog[lid]['name'])
                    text += '\n'
                    text += 'Timestamp: {0}'.format(list_catalog[lid]['timestamp'])
                    text += '\n\n'
            uty.pager(text)
        elif args.cleaned:
            uty.print_verbose(args.verbose, "List all cleaned backup in catalog")
            text = 'BUTTERFLY BACKUP CATALOG (CLEANED)\n\n'
            uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'BUTTERFLY BACKUP CATALOG (CLEANED)')
            for lid in list_catalog.sections():
                if 'cleaned' in list_catalog[lid]:
                    uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Backup id: {0}'.format(lid))
                    uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Hostname or ip: {0}'.format(list_catalog[lid]['name']))
                    uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Timestamp: {0}'.format(list_catalog[lid]['timestamp']))
                    text += 'Backup id: {0}'.format(lid)
                    text += '\n'
                    text += 'Hostname or ip: {0}'.format(list_catalog[lid]['name'])
                    text += '\n'
                    text += 'Timestamp: {0}'.format(list_catalog[lid]['timestamp'])
                    text += '\n\n'
            uty.pager(text)
        else:
            uty.print_verbose(args.verbose, "List all backup in catalog")
            text = 'BUTTERFLY BACKUP CATALOG\n\n'
            uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'BUTTERFLY BACKUP CATALOG')
            if args.hostname:
                for lid in list_catalog.sections():
                    if list_catalog[lid]['name'] == args.hostname:
                        uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                          'Backup id: {0}'.format(lid))
                        uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                          'Hostname or ip: {0}'.format(list_catalog[lid]['name']))
                        uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                          'Timestamp: {0}'.format(list_catalog[lid]['timestamp']))
                        text += 'Backup id: {0}'.format(lid)
                        text += '\n'
                        text += 'Hostname or ip: {0}'.format(list_catalog[lid]['name'])
                        text += '\n'
                        text += 'Timestamp: {0}'.format(list_catalog[lid]['timestamp'])
                        text += '\n\n'
            else:
                for lid in list_catalog.sections():
                    uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Backup id: {0}'.format(lid))
                    uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Hostname or ip: {0}'.format(list_catalog[lid]['name']))
                    uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Timestamp: {0}'.format(list_catalog[lid]['timestamp']))
                    text += 'Backup id: {0}'.format(lid)
                    text += '\n'
                    text += 'Hostname or ip: {0}'.format(list_catalog[lid]['name'])
                    text += '\n'
                    text += 'Timestamp: {0}'.format(list_catalog[lid]['timestamp'])
                    text += '\n\n'
            uty.pager(text)

    # Check export session
    if args.action == 'export':
        cmds = list()
        # Read catalog file
        catalog_path = os.path.join(args.catalog, '.catalog.cfg')
        export_catalog = read_catalog(catalog_path)
        if os.path.exists(args.destination):
            # Check one export or all
            if args.all:
                # Log info
                log_args = {
                    'hostname': 'all_backup',
                    'status': args.log,
                    'destination': os.path.join(args.destination, 'export.log')
                }
                logs = list()
                logs.append(log_args)
                # Compose command
                uty.print_verbose(args.verbose, 'Build a rsync command')
                cmd = compose_command(args, None)
                # Add source
                cmd.append('{}'.format(os.path.join(args.catalog, '')))
                # Add destination
                cmd.append('{}'.format(args.destination))
            else:
                # Check specified argument backup-id
                if not export_catalog.has_section(args.id):
                    print(PrintColor.RED +
                          'ERROR: Backup-id {0} not exist!'.format(args.id)
                          + PrintColor.END)
                    exit(1)
                # Log info
                log_args = {
                    'hostname': export_catalog[args.id]['Name'],
                    'status': args.log,
                    'destination': os.path.join(args.destination, 'export.log')
                }
                logs = list()
                logs.append(log_args)
                # Compose command
                uty.print_verbose(args.verbose, 'Build a rsync command')
                cmd = compose_command(args, None)
                # Export
                uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                  'Export {0}. Folder {1} to {2}'.format(args.id, export_catalog[args.id]['Path'],
                                                                         args.destination))
                uty.print_verbose(args.verbose, 'Export backup with id {0}'.format(args.id))
                if os.path.exists(export_catalog[args.id]['Path']):
                    # Add source
                    cmd.append('{}'.format(export_catalog[args.id]['Path']))
                    # Add destination
                    cmd.append('{}'.format(os.path.join(args.destination, export_catalog[args.id]['Name'])))
                    uty.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Export command {0}.'.format(" ".join(cmd)))
                    # Check cut option
                    if args.cut:
                        write_catalog(os.path.join(args.catalog, '.catalog.cfg'), args.id, 'cleaned', 'True')
            # Start export
            cmds.append(' '.join(cmd))
            run_in_parallel(start_process, cmds, 1)
            if os.path.exists(os.path.join(args.destination, '.catalog.cfg')):
                # Migrate catalog to new file system
                uty.find_replace(os.path.join(args.destination, '.catalog.cfg'), args.catalog.rstrip('/'),
                                     args.destination.rstrip('/'))
        else:
            print(PrintColor.RED +
                  "ERROR: Source or destination path doesn't exist!" + PrintColor.END)
            exit(1)

