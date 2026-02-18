@echo off

echo Building BioSignalServer...

pyinstaller ^
    --clean ^
    --onefile ^
    --name "BioSignalServer" ^
    --collect-all uvicorn ^
    --collect-all fastapi ^
    --collect-all starlette ^
    --collect-all neurokit2 ^
    main.py

echo Done.
pause