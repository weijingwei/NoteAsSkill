@echo off
chcp 65001 >nul
echo ========================================
echo  NoteAsSkill 打包脚本
echo ========================================
echo.

:: 检查 Python 环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.12
    pause
    exit /b 1
)

:: 安装 PyInstaller
echo [1/3] 安装 PyInstaller...
pip install pyinstaller -q

:: 安装依赖
echo [2/3] 安装项目依赖...
pip install -r requirements.txt -q

:: 打包
echo [3/3] 开始打包...
pyinstaller NoteAsSkill.spec --noconfirm

echo.
echo ========================================
if exist "dist\NoteAsSkill.exe" (
    echo [成功] 打包完成！
    echo 输出文件: dist\NoteAsSkill.exe
) else (
    echo [错误] 打包失败，请检查错误信息
)
echo ========================================
pause