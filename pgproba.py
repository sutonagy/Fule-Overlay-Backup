#!/usr/bin/env python3

import gzip
from plumbum.cmd import pg_dump
with open(w'backup.sql') as f:
#with gzip.open('backup.gz', 'wb') as f:
   (pg_dump["-h", "localhost", "-U", "postgres", "postgres"] > f)
()
