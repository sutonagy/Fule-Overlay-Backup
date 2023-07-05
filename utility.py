#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: se ts=4 et syn=python:

# created by: matteo.guadrini
# modified by: Laszlo Suto Nagy
# utility.py -- Butterfly-Backup
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

import bb as bbmain
#logger, fh, ch, logging = bbmain.logger_init('utility')

global datetime_spec

def send_telegram_message(message,token=None, chat_id=None):
    """
    Send a message to a chat_id
    :param token: token of bot
    :param chat_id: chat_id of bot
    :param message: message to send
    """
    import requests # pip install requests is necessary
    token = '6081081821:AAHL0EkjfRyTYR6H67PssyqxvHeceJ759F0' if not token else token
    chat_id = '-1001934954219' if not chat_id else chat_id # you should insert '-100' before the chat_id of the channel
    #print('telegram token: ', token)
    #print('telegram chat_id: ', chat_id)
    url = "https://api.telegram.org/bot" + token + "/sendMessage?chat_id=" + chat_id + "&text=" + message
    #print('telegram url: ', url)
    urlvalasz = requests.get(url)
    bbmain.logger.debug('Token: %s, Chat_id: %s, url: %s, requests: %s' % (token, chat_id, url, urlvalasz))

def get_today_datetime():
    """
    Get today date and time
    :return: datetime object
    """
    #print('datetime_spec: ', datetime_spec)
    bbmain.logger.debug('datetime_spec: {0}'.format(datetime_spec))
    import datetime
    if datetime_spec:
        return datetime_spec
    else:
        return datetime.datetime.now()

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


def touch(filename, times=None):
    """
    Create an empty file
    :param filename: path of file
    :param times: time creation of file
    :return:  file
    """
    import os
    # Verify folder exists
    if not os.path.exists(filename):
        # touch file
        with open(filename, 'a'):
            os.utime(filename, times)


def find_replace(filename, text_to_search, replacement_text):
    """
    Find and replace word in a text file
    :param filename: path of file
    :param text_to_search: word to search
    :param replacement_text: word to replace
    :return:  file
    """
    import fileinput

    with fileinput.FileInput(filename, inplace=True) as file:
        for line in file:
            print(line.replace(text_to_search, replacement_text), end='')


def make_dir(directory):
    """
    Create a folder
    :param directory: Path of folder
    """
    import os
    if not os.path.exists(directory):
        os.makedirs(directory)


def time_for_folder(isFull=False):
    """
    Time now() in this format: %Y_%m_%d__%H_%M
    :return: string time
    """
    from datetime import datetime
    mainap=get_today_datetime()
    folderend=mainap.strftime('%y%m%d-%H%M')
    wd=mainap.weekday()
    nap=mainap.day
    honap=mainap.month
    if isFull:
        toldalek='f'
    else:
        if wd < 6:
            toldalek='d'
        else:
            if nap < 8:
                if honap == 6:
                    toldalek='y'
                else:
                    toldalek='m'
            else:
                toldalek='w'
    folderend=folderend+'-'+toldalek
    return folderend


def time_for_log():
    """
    Time now() in this format: %Y-%m-%d %H:%M:%S
    :return: string time
    """
    import time
    return time.strftime('%Y-%m-%d %H:%M:%S')


def cleanup(path, date, days):
    """
    Delete folder to pass an first argument, when time of it is minor of certain date
    :param path: path to delete
    :param date: date passed of path
    :param days: number of days
    :return:
    """
    from shutil import rmtree
    from time import mktime
    from datetime import datetime, timedelta
    d = get_today_datetime() - timedelta(days=days)
    seconds = mktime(d.timetuple())
    date_s = mktime(string_to_time(date).timetuple())
    if date_s < seconds:
        try:
            rmtree(path)
            exitcode = 0
            return exitcode
        except OSError:
            exitcode = 1
            return exitcode


def new_id():
    """
    Generate new uuid
    :return: uuid object
    """
    import uuid
    return uuid.uuid1()


def string_to_time(string):
    """
    Convert time string into date object in this format '%Y-%m-%d %H:%M:%S'
    :param string: Time format string
    :return: time object
    """
    from datetime import datetime
    datetime_object = datetime.strptime(string, '%Y-%m-%d %H:%M:%S')
    return datetime_object


def time_to_string(date):
    """
    Convert date into string object in this format '%Y-%m-%d %H:%M:%S'
    :param date: Date object
    :return: string
    """
    from datetime import datetime
    string = datetime.strftime(date, '%Y-%m-%d %H:%M:%S')
    return string


def make_symlink(source, destination):
    """
    Make a symbolic link
    :param source: Source path of symbolic link
    :param destination: Destination path of symbolic link
    """
    import os
    try:
        if os.path.exists(destination):
            os.unlink(destination)
        os.symlink(source, destination)
    except OSError:
        print(PrintColor.YELLOW + "WARNING: MS-DOS file system doesn't support symlink file." + PrintColor.END)


def list_from_string(string):
    """
    Cast string in list
    :param string: Input string must be transform in list
    :return: list
    """
    # Convert string to list separated with comma
    return_list = string.split(',')
    return return_list


def confirm(message):
    """
    Ask user to enter Y or N (case-insensitive).
    :return: True if the answer is Y.
    :rtype: bool
    """
    answer = ""
    while answer not in ["y", "n"]:
        answer = input("{0} To continue [Y/N]? ".format(message)).lower()
    return answer == "y"


def check_tool(name):
    """
    Check tool is installed
    :param name: name of the tool
    :return: boolean
    """
    from shutil import which
    return which(name) is not None


def check_ssh(ip, port=22):
    """
    Test ssh connection
    :param ip: ip address or hostname of machine
    :param port: ssh port (default is 22)
    """
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        #print(PrintColor.YELLOW + 'Waiting for port {0} on host {1} ...'.format(port, ip)
                #+ PrintColor.END)
        bbmain.logger.debug('Waiting for port {0} on host {1} ...'.format(port, ip))
        s.settimeout(60)
        #s.connect((ip, port))
        result=s.connect_ex((ip, port))
        s.settimeout(None)
        s.shutdown(2)
        #print(PrintColor.GREEN + 'The port {0} on {1} is open!'.format(port, ip)
                #+ PrintColor.END)
        bbmain.logger.debug('The port {0} on {1} is open!'.format(port, ip))
        return True if result == 0 else False
    except socket.error:
        return False


def check_rsync(ip, port=873):
    """
    Test rsync connection
    :param ip: ip address or hostname of machine
    :param port: rsync port (default is 873)
    """
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        #print(PrintColor.YELLOW + 'Waiting for port {0} on host {1} ...'.format(port, ip)
                #+ PrintColor.END)
        bbmain.logger.debug('Waiting for port {0} on host {1} ...'.format(port, ip))
        s.settimeout(60)
        #s.connect((ip, port))
        result=s.connect_ex((ip, port))
        s.settimeout(None)
        s.shutdown(2)
        #print(PrintColor.GREEN + 'The port {0} on {1} is open!'.format(port, ip)
                #+ PrintColor.END)
        bbmain.logger.debug('The port {0} on {1} is open!'.format(port, ip))
        return True if result == 0 else False
    except socket.error:
        return False


def archive(path, date, days, destination):
    """
    Archive entire folder in a zip file
    :param path: path than would archive in a zip file
    :param date: date passed of path
    :param days: number of days
    :param destination: destination of zip file
    :return: boolean
    """
    import shutil
    import os
    from time import mktime
    from datetime import datetime, timedelta

    d = get_today_datetime - timedelta(days=days)
    seconds = mktime(d.timetuple())
    date_s = mktime(string_to_time(date).timetuple())
    if date_s < seconds:
        if os.path.exists(path):
            if os.path.exists(destination):
                try:
                    archive_from = os.path.dirname(path)
                    archive_to = os.path.basename(path.strip(os.sep))
                    final_dest = os.path.join(destination, os.path.basename(os.path.dirname(path)))
                    if not os.path.exists(final_dest):
                        os.mkdir(final_dest)
                    os.chdir(final_dest)
                    name = os.path.basename(path)
                    shutil.make_archive(name, 'zip', archive_from, archive_to)
                    exitcode = 0
                    return exitcode
                except OSError:
                    exitcode = 1
                    return exitcode
        else:
            print(PrintColor.RED + "ERROR: The path {0} is not exist.".format(path) + PrintColor.END)
