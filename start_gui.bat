@echo off
echo Starting Game Monitor GUI...
echo.

REM Try different Python commands
python start_gui.py
if %errorlevel% neq 0 (
    echo.
    echo Trying alternative Python command...
    py start_gui.py
    if %errorlevel% neq 0 (
        echo.
        echo Trying python3...
        python3 start_gui.py
        if %errorlevel% neq 0 (
            echo.
            echo ERROR: Could not start GUI
            echo Please make sure Python is installed and in PATH
            echo.
            pause
        )
    )
)

pause