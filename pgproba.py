#!/usr/bin/env python3

import gzip
from plumbum import SshMachine
remote = SshMachine("mail2022.platinum.co.hu", user = "rbackup", keyfile = "/etc/bb/sshkeys/rbackup.oss", ssh_opts = ["-o", "StrictHostKeyChecking=no"])
with gzip.open('backup.gz', 'wb') as f:
    #(ssh["rbackup@mail2022.platinum.co.hu", "-o", "StrictHostKeyChecking=no", "-i", "/etc/bb/sshkeys/rbackup.oss"] > f)
    remote['pg_dump']("-h", "localhost", "-U", "postgres", "postgres") > f
#
