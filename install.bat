@echo off

net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo This script requires administrator privileges.
    exit /b 1
)

for /f "tokens=* usebackq" %%i in (`powershell -NoProfile -Command ^
    "$password = Read-Host 'Enter password' -AsSecureString; [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($password))"`) do set PASSWORD=%%i

if "%PASSWORD%"=="" (
    echo Password retrieval failed or was empty.
    exit /b 1
)

set REBUILD=0
set NO_CONFIRM=0
for %%i in (%*) do (
    if /i "%%i"=="--rebuild" set REBUILD=1
    if /i "%%i"=="--no_confirm" set NO_CONFIRM=1
)

if not exist %CD%\dist\windows_service.exe (
    set REBUILD=1
)

if %REBUILD% equ 1 (
    where python >nul 2>nul || (echo Python is not installed or not in PATH. & exit /b 1)


    if exist "linkedinassistant311\Scripts\activate" (
        echo Virtual environment already exists.
    ) else (
        python -m venv linkedinassistant311
        if %ERRORLEVEL% neq 0 (
            echo Failed to create virtual environment.
            exit /b %ERRORLEVEL%
        )
    )

    call linkedinassistant311\Scripts\activate.bat
    if %ERRORLEVEL% neq 0 (
        echo Failed to activate virtual environment.
        exit /b %ERRORLEVEL%
    )

    pip install -r requirements_win.txt
    if %ERRORLEVEL% neq 0 (
        echo Failed to install requirements.
        exit /b %ERRORLEVEL%
    )

    python .\src\scripts\configure_keyring.py
    if %ERRORLEVEL% neq 0 (
        echo Failed to install Vault config keys on keyring.
        exit /b %ERRORLEVEL%
    )

    setlocal EnableDelayedExpansion

    set HIDDEN_IMPORTS=
    set COLLECT_DATA=
    set COPY_METADATA=

    for %%M in (langchain-openai langchain-groq langchain-google-genai) do (
        pip list | findstr /i "%%M" >nul 2>&1
        if !ERRORLEVEL! equ 0 (
            echo Adding %%M as hidden import
            set TEMP_NAME=%%M
            set TEMP_NAME=!TEMP_NAME:-=_%!
            set HIDDEN_IMPORTS=!HIDDEN_IMPORTS! --hidden-import !TEMP_NAME!
            set COLLECT_DATA=!COLLECT_DATA! --collect_data !TEMP_NAME!
            set COPY_METADATA=!COPY_METADATA! --copy-metadata !TEMP_NAME!
        ) else (
            echo WARNING: Installing without dynamic library %%M. Providers using this library will not be available
        )
    )

    endlocal & (
      set "HIDDEN_IMPORTS=%HIDDEN_IMPORTS%"
      set "COLLECT_DATA=%COLLECT_DATA%"
      set "COPY_METADATA=%COPY_METADATA%"
    )

    pyinstaller --hidden-import win32timezone --hidden-import pydantic.deprecated.decorator --hidden-import torch --hidden-import torchvision --hidden-import tiktoken_ext.openai_public --hidden-import tiktoken_ext --hidden-import langchain_community %HIDDEN_IMPORTS% --collect-data langchain_community --collect-data torch --collect-data torchvision --collect-data langchain --collect-data pypdf --collect-data docling --collect-data pypdfium2 --collect-data pypdfium2_raw --collect-data docling_core --collect-all chromadb --collect-data docling_parse --copy-metadata torch --copy-metadata langchain_community --copy-metadata langchain --copy-metadata torchvision --copy-metadata packaging --copy-metadata safetensors --copy-metadata regex --copy-metadata huggingface-hub --copy-metadata tokenizers --copy-metadata filelock --copy-metadata numpy --copy-metadata tqdm --copy-metadata requests --copy-metadata pyyaml --copy-metadata docling --copy-metadata pypdf --copy-metadata pypdfium2 --copy-metadata docling_core --copy-metadata docling_parse --icon %CD%\res\logo\logo.ico --log-level DEBUG --clean --noconfirm --onefile src\windows_service.py
    if %ERRORLEVEL% neq 0 (
        echo PyInstaller build failed.
        exit /b %ERRORLEVEL%
    )

    call linkedinassistant311\Scripts\deactivate.bat

    set LOCAL_APPDATA=C:\Users\%USERNAME%\AppData\Local\linkedin_assistant

    if not exist "%LOCAL_APPDATA%" (
        echo Creating Data Directory at "%LOCAL_APPDATA%"
        mkdir "%LOCAL_APPDATA%"
    )

    if %NO_CONFIRM% equ 1 (
        xcopy /E /I /Q /Y res %LOCAL_APPDATA%
    ) else (
        xcopy /E /I res %LOCAL_APPDATA%
    )

    if %ERRORLEVEL% neq 0 (
        echo Failed to copy contents of res folder.
        exit /b %ERRORLEVEL%
    )

)

echo Installing service
.\dist\windows_service.exe --username=.\%USERNAME% --password=%PASSWORD% install
if %ERRORLEVEL% neq 0 (
    echo Failed to install the service.
    exit /b %ERRORLEVEL%
)

echo Build and installation completed successfully.
