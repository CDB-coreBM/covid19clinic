

$run
$csv_file

folder='/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/RUNS/'
run='2020_05_19_OT6_KF'


Rscript -e 'library(rmarkdown);
rmarkdown::render("/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/RUNS/2020_05_19_OT7_KF/scripts/2020_05_19_test_rmarkdown.Rm_OT7.Rmd",
"html_document", output_file = "OT7_resultados.html",
output_dir="/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/RUNS/2020_05_19_OT7_KF/results/")'


smb://opn.cdb.nas.csc.es/opentrons/RUNS/2020_05_15_OT666_KF/scripts/2020_05_15_test_rmarkdown.Rm_OT666.Rmd

/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/RUNS/2020_05_14_OT4_KF/results/2020_05_14_OT4_KF_Presence Absence Result.csv


RUNS/2020_05_14_OT4_KF/results/


Rscript -e 'library(rmarkdown);
rmarkdown::render("${folder}",
"html_document", output_file = "test_resultados.html",
output_dir="/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/")
params = list(run = "teeeeeeeeeeeest")'
