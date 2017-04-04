title Beamtuning launcher
xcopy /s/e/Y "\\cern.ch\\dfs\\Users\\c\\cris\\Documents\\Networked-Data-Acquisition\\Config files" "c:\\Networked-data-acquisition\\Config files\\*"
xcopy /s/e/Y "\\cern.ch\\dfs\\Users\\c\\cris\\Documents\\Networked-Data-Acquisition\\BeamTunes" "c:\\Networked-data-acquisition\\Config files\\BeamTunes\\*"
cd C:\Networked-data-acquisition
start python BeamlineControllerApp.py
