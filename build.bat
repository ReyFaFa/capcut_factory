@echo off
chcp 65001 > nul
echo ============================================
echo CapCut Factory - EXE Build Script
echo ============================================
echo.

:: PyInstaller check
echo [1/4] PyInstaller 확인 중...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller가 설치되지 않았습니다. 설치 중...
    pip install pyinstaller
    if errorlevel 1 (
        echo 오류: PyInstaller 설치 실패
        pause
        exit /b 1
    )
) else (
    echo PyInstaller가 이미 설치되어 있습니다.
)
echo.

:: Clean previous build
echo [2/4] 이전 빌드 파일 정리 중...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist capcut_factory.spec del /q capcut_factory.spec
echo 정리 완료
echo.

:: Build EXE
echo [3/4] EXE 파일 빌드 중...
echo 잠시만 기다려주세요 (약 30초~1분 소요)...
pyinstaller --onefile ^
    --windowed ^
    --name="CapCut_Factory" ^
    --icon=NONE ^
    --clean ^
    capcut_factory.py

if errorlevel 1 (
    echo 오류: 빌드 실패
    pause
    exit /b 1
)
echo.

:: Result check
echo [4/4] 빌드 완료!
echo.
echo ============================================
if exist "dist\CapCut_Factory.exe" (
    echo ✓ EXE 파일 생성 성공!
    echo.
    echo 파일 위치: dist\CapCut_Factory.exe
    echo.
    echo 이제 exe 파일을 실행하면 됩니다.
) else (
    echo ✗ EXE 파일 생성 실패
    echo dist 폴더를 확인해주세요.
)
echo ============================================
echo.

pause
