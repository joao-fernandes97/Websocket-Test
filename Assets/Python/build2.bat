@echo off
echo Building BioSignalServer...
python -m PyInstaller --clean BioSignalServer.spec
echo Done.
pause