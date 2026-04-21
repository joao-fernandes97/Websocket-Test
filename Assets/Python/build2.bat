@echo off
echo Building BioSignalServer...
pyinstaller --clean BioSignalServer.spec
echo Done.
pause