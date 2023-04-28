#!/usr/bin/env python3

import paramiko
host = "mail2022.platinum.co.hu"
port = 22
username = "rbackup"
# password = "password"
keyfile = "/etc/bb/sshkeys/rbackup.oss"
command = "systemctl status sshd.service"
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port=port, username=username, key_filename=keyfile)
stdin, stdout, stderr = ssh.exec_command(command)
stdin.close()
lines = stdout.readlines()
print(lines)
ssh.close()
