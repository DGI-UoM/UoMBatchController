#!/bin/bash

echo "Calling CRONSCRIPT with two dirs"
cd /cifs/DAM/Staging\ Area/ingester
/opt/ActivePython/bin/python /cifs/DAM/Staging\ Area/ingester/UoMScripts/UoM_batch_controller.py /cifs/DAM/Staging\ Area/Rare_Books_Collections/ /cifs/DAM/Staging\ Area/Rare_Books_Collections/out

echo "Script Ran!!!"