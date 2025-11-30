@echo off
chcp 65001 >nul
echo ========================================
echo MV Production Automation Agent
echo 起動中...
echo ========================================
echo.

cd /d "%~dp0"

echo 現在のディレクトリ: %CD%
echo.

echo Streamlitアプリケーションを起動します...
echo ブラウザが自動的に開きます。
echo.
echo 停止する場合は、このウィンドウで Ctrl+C を押してください。
echo.

streamlit run app.py

pause

