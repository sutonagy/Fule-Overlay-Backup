#!/usr/bin/env python3

import gzip
from plumbum.cmd import pg_dump
with open('backup.sql','w') as f:
#with gzip.open('backup.gz', 'wb') as f:
    # \n is placed to indicate EOL (End of Line)
    L = ["This is Delhi \n","This is Paris \n","This is London \n"]
    f.write("Hello \n")
    f.writelines(L)
    (pg_dump["-h", "localhost", "-U", "postgres", "postgres"] > f)  
()
