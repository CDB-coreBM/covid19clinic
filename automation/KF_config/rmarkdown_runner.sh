#!/bin/bash
# set path to watch
run=$1
folder='/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/RUNS/'

rscript=`find ${folder}${run} -name '*.Rmd' -print0 | xargs -r0 echo | cut -d '/' -f10`
Rscript -e 'library(rmarkdown);
rmarkdown::render("'${folder}${run}'/scripts/'${rscript}'",
"html_document", output_file = "'${run}'_resultados.html",
output_dir="'$folder${run}'/results/")'

echo ${rscript}' executed for run '${run}
