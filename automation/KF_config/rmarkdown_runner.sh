

$run
$csv_file

folder='/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/RUNS/'
run='2020_05_14_OT4_KF/results/2020_05_14_OT4_KF_Presence Absence Result.csv'

Rscript -e 'library(rmarkdown);
rmarkdown::render("/home/jl/Documentos/code/covid19clinic/automation/test_rmarkdown.Rmd",
"html_document", output_file = "test_resultados.html",
output_dir="/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/")
params = list(run = "teeeeeeeeeeeest")'


/run/user/1003/gvfs/smb-share:server=opn.cdb.nas.csc.es,share=opentrons/RUNS/2020_05_14_OT4_KF/results/2020_05_14_OT4_KF_Presence Absence Result.csv


RUNS/2020_05_14_OT4_KF/results/
