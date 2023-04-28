#!/usr/bin/env python3

import gzip
from plumbum import SshMachine
remote = SshMachine("mail2022.platinum.co.hu", user = "rbackup", keyfile = "/etc/bb/sshkeys/rbackup.oss", ssh_opts = ["-o", "StrictHostKeyChecking=no"])
print('Connected to mail2022.platinum.co.hu')
with open('backup.sql', 'w') as f:
#with gzip.open('backup.gz', 'wb') as f:
    #(ssh["rbackup@mail2022.platinum.co.hu", "-o", "StrictHostKeyChecking=no", "-i", "/etc/bb/sshkeys/rbackup.oss"] > f)
    rm_pgd = remote['pg_dump']("-h", "localhost", "-U", "postgres", "postgres")
    f.write(rm_pgd())
#
