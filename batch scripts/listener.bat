cd C:\Networked-data-acquisition
xcopy /s/e/Y "\\cern.ch\\dfs\\Users\\c\\cris\\Documents\\Networked-Data-Acquisition" "c:\Networked-data-acquisition\*"
start python rpc_server.py
