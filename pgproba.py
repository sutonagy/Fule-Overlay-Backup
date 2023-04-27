#!/usr/bin/env python3

import gzip
from plumbum.cmd import pg_dump
with gzip.open('backup.gz', 'wb') as f:
   (pg_dump["-h", "localhost", "-U", "postgres", "Arpad48-50"] > f)
()
