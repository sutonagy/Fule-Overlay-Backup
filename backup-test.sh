#!/usr/bin/env bash
rm -rf /backup/rsync/
rm -rf /backup/rsynclog/
rm -rf /backup/dump/
rm -rf /backup/dumperror/
mkdir -p /backup/rsynclog
mkdir -p /backup/rsync
cd Fule-Overlay-Backup
git pull https://github.com/sutonagy/Fule-Overlay-Backup.git
start=`date +%s`
python3 ovbck.py -M /etc/bb/bb.yaml -K 2304131312
end=`date +%s`
runtime=$((end-start))
echo "Total runtime of first backup: $runtime seconds"
while true; do
    echo "Első backup lefutott. Mehet a következő? Ha igen, akkor nyomj egy I-t, ha nem, akkor egy N-t"
    read -rep "Mehet a következő backup? (I/N)" yn
    case $yn in
        [Ii]* ) break;;
        [Nn]* ) exit;;
        * ) echo "Válaszolj igennel (I vagy i) vagy nemmel (N vagy n).";;
    esac
done
start=`date +%s`
python3 ovbck.py -M /etc/bb/bb.yaml
end=`date +%s`
runtime=$((end-start))
echo "Total runtimeof second backup: $runtime seconds"
