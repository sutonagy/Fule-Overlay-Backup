#!/usr/bin/env bash
rm -rf /backup/rsync/*
mkdir -p /backup/rsync/log
cd Fule-Butterfly-Backup
git pull https://github.com/sutonagy/Fule-Butterfly-Backup.git
python3 bb.py -F /home/alma/Fule-Butterfly-Backup/setting.yml
#python3 -m pdb bb.py -F /home/alma/Fule-Butterfly-Backup/setting.yml
