#!/usr/bin/env bash
rm -rf /backup/data/
rm -rf /backup/dumperror/
mkdir -p /backup/rsync/log
cd Fule-Butterfly-Backup
git pull https://github.com/sutonagy/Fule-Butterfly-Backup.git
start=`date +%s`
#python3 bb.py -M /etc/bb/bb.yaml -B /etc/bb/dump.yaml -k 'Dump'
python3 bb.py -M /etc/bb/bb.yaml
end=`date +%s`
runtime=$((end-start))
echo "Total runtime: $runtime seconds"
