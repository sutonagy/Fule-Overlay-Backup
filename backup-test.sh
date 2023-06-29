#!/usr/bin/env bash
rm -rf /backup/rsync/
rm -rf /backup/rsynclog/
rm -rf /backup/dump/
rm -rf /backup/dumperror/
mkdir -p /backup/rsynclog
mkdir -p /backup/rsync
cd Fule-Butterfly-Backup
git pull https://github.com/sutonagy/Fule-Butterfly-Backup.git
start=`date +%s`
#python3 bb.py -M /etc/bb/bb.yaml -K 2304011307
#python3 bb.py -M /etc/bb/bb.yaml -K 2304021308
#python3 bb.py -M /etc/bb/bb.yaml -K 2304031309
#python3 bb.py -M /etc/bb/bb.yaml -K 2304041310
#python3 bb.py -M /etc/bb/bb.yaml -K 2304091311
#python3 bb.py -M /etc/bb/bb.yaml -K 2304131312
python3 bb.py -M /etc/bb/bb.yaml
end=`date +%s`
runtime=$((end-start))
echo "Total runtime of first backup: $runtime seconds"
while true; do
    echo "Full backup lefutott. Átmásoltad a korábbi backupot és módosítottad a confokat? Ha igen, akkor nyomj egy I-t, ha nem, akkor egy N-t"
    read -rep "Mehet a következő backup? (I/N)" yn
    case $yn in
        [Ii]* ) break;;
        [Nn]* ) exit;;
        * ) echo "Válaszolj igennel (I vagy i) vagy nemmel (N vagy n).";;
    esac
done
start=`date +%s`
python3 bb.py -M /etc/bb/bb.yaml
end=`date +%s`
runtime=$((end-start))
echo "Total runtimeof second backup: $runtime seconds"
#python3 -m pdb bb.py -M /etc/bb/bb.yaml
