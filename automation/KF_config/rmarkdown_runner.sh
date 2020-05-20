#!/bin/bash
# set path to watch
DIR="/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/RUNS/"
# set path to copy the script to
target_dir="/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/RUNS/"

inotifywait -m -r -e moved_to -e create "$DIR" --format "%w%f" | while read f
folder='/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/RUNS/'
do
    echo $f
    # check if the file is a .sh file
    if [[ $f = *.csv ]]; then
      echo $f 'detected'
      run=`echo $f | cut -d '/' -f8`
      rscript=`find ${folder}${run} -name '*.Rmd' -print0 | xargs -r0 echo | cut -d '/' -f10`
      Rscript -e 'library(rmarkdown);
      rmarkdown::render("'${folder}${run}'/scripts/'${rscript}'",
      "html_document", output_file = "'${run}'_resultados.html",
      output_dir="'$folder${run}'/results/")'
      echo ${rscript}' executed for '${run}
    fi
done
