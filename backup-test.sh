#!/usr/bin/env bash
rm -rf /backup/rsync/
mkdir -p /backup/rsync/log
cd Fule-Butterfly-Backup
git pull https://github.com/sutonagy/Fule-Butterfly-Backup.git
#python3 bb.py -M /etc/bb/bb.yaml -K 2304011307
#python3 bb.py -M /etc/bb/bb.yaml -K 2304021308
#python3 bb.py -M /etc/bb/bb.yaml -K 2304031309
#python3 bb.py -M /etc/bb/bb.yaml -K 2304041310
#python3 bb.py -M /etc/bb/bb.yaml -K 2304091311
#python3 bb.py -M /etc/bb/bb.yaml -K 2304131312
#python3 bb.py -M /etc/bb/bb.yaml -K 2304161313
python3 bb.py -M /etc/bb/bb.yaml
#python3 -m pdb bb.py -M /etc/bb/bb.yaml
