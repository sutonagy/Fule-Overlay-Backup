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
    group_archive.add_argument('--days', '-D', help='Number of days of archive retention', dest='days',
                            action='store', type=int, default=30)
    group_archive.add_argument('--destination', '-d', help='Archive destination path', dest='destination',
                            action='store', required=True)
    # list session
    list_action = action.add_parser('list', help='List options', parents=[parent_parser])
    group_list = list_action.add_argument_group(title='List options')
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
    pylogfile = args.logfile + '-' + folderend[0:11] + '.log' if args.logfile else args.destination + '/' + 'fule-overlay-backup' + '-' + folderend[0:11] + '.log'
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
    logger.debug('Parallel remotes: {0}'.format(remotes))
    logger.debug('aktdate in parallel: {0}'.format(aktdate))
    for command, plog, remote in zip(commands, aktlogs, remotes):
        # Run the function
        # print('Parallel command: ',command)
        proc = pool.apply_async(func=fn, args=(command,aktdate,remote))
        jobs.append(proc)
        #print('Start {0} {1}'.format(args.action, plog['hostname']))
        logger.info('Start {0} {1}'.format(args.action, plog['hostname']))
        logger.info("rsync command: {0}".format(command))
        logger.info('Start process {0} on {1}'.format(args.action, plog['hostname']))

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
            logger.error('Finish process {0} on {1} with error:{2}'.format(args.action, plog['hostname'], p.get()))
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
            logger.info('Finish process {0} on {1}'.format(args.action, plog['hostname']))

    # Safely terminate the pool
    pool.close()
    pool.join()
    return rsyncerror, rmessages, rswarning
    


def start_process(command,folderend,remote=''):
    logger.debug('Remote in start_process: {0}'.format(remote))
    logfile=args.logdirectory+folderend+'-'+remote+'.log'
    logger.debug('Logfile in start_process: {0}'.format(logfile))
    logger.debug('Folderend in start_process: {0}'.format(folderend))
    errfile=args.logdirectory+folderend+'-'+remote+'.error-log'
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
    if flags.rsync:
        if os.path.exists(flags.rsync):
            command = [flags.rsync]
        else:
            logger.warning('WARNING: rsync binary {0} not exist! Set default.'.format(args.rsync))
            command = ['rsync']
    else:
        command = ['rsync']
    command.append('-ahR')
    command.append('--links')
    command.append('--partial')
    # Set verbosity
    if flags.verbose:
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
    # Set excludes
    if flags.exclude:
        for exclude in flags.exclude:
            command.append('--exclude={0}'.format(exclude))
    if flags.log:
        log_path = args.logdirectory + folderend[0:11] + '-' + host +'.rsync-log'
        command.append(
            '--log-file={0}'.format(log_path)
        )
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
        return src_list


def compose_destination(computer_name, folder):
    first_layer = os.path.join(folder, computer_name)
    folderend=endfolder[0:11]
    second_layer = os.path.join(first_layer, folderend)
    if not os.path.exists(first_layer):
        os.mkdir(first_layer)
    if not os.path.exists(second_layer):
        os.mkdir(second_layer)
    second_layer = os.path.join(second_layer, "") # Add slash to the end of the path
    logger.debug('Second layer with slash in compose destination return: {0}'.format(second_layer))
    return second_layer


def single_action(args,configfile=None):

    """
    Function to preapare one actual rsync command.
    :param args: the configurtion from the command line and the yaml files
    :param configfile: the actual yaml config file
    :return aktcmd: the actual rsync command
    :return aktlog: the actual log file
    :return online: check if the actual host's ssh and rsync ports are online
    """

    global hostname, backup_id, log_args, logs, aktlogs, rpath
    
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
        logger.error("ERROR: Only 'backup' mode works! '{0}' mode has not yet tested".format(args.action))
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
                logger.error('ERROR: The file {0} not exist!'.format(args.list))
        else:
            parser.print_usage()
            # print args
            print('For ' + PrintColor.BOLD + 'backup' + PrintColor.END + ' usage, "--help" or "-h"')
            exit(1)
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
                logger.error('The port {0} on {1} is closed or blocked!'.format(port, hostname))
                online = False
                eport = port
                continue
            logger.debug('DEBUG: After ssh port check: The port {0} on {1} is open!'.format(port, hostname_orig))
            if not uty.check_rsync(hostname_orig, rport):
                logger.error('The port {0} on {1} is closed or blocked!'.format(rport, hostname))
                online = False
                eport = rport
                continue
            logger.debug('DEBUG: After rsync port check: The port {0} on {1} is open!'.format(rport, hostname_orig))
            if not args.verbose:
                if not check_configuration(hostname_orig):
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
            # Compose command
            bck_dst, folderend = compose_destination(hostname, args.destination)
            cmd = compose_command(args, hostname, folderend)
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
            cmd.append(bck_dst)
            # Compose pull commands
            # Create a symlink for last backup
            uty.make_symlink(bck_dst, os.path.join(args.destination, hostname, 'last_backup'))
        # Start backup
        # run_in_parallel(start_process, cmds, args.parallel)
        # print('Single_action cmd: ',cmd)
        #print('Single_action log: ',log_args)
        return cmd, log_args, online, eport
