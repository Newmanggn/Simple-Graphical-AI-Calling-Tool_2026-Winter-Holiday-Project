@echo off
chcp 65001 >nul
echo ========================================
echo   简单图形化AI调用工具 - 基础依赖安装
echo ========================================
echo.

echo [1/2] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
python --version
echo.

echo [2/2] 安装基础依赖...
pip install flask requests customtkinter pillow numpy
if %errorlevel% neq 0 (
    echo.
    echo 错误: 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)

echo.
echo ========================================
echo   基础依赖安装完成！
echo ========================================
echo.
echo 接下来你可以：
echo 1. 运行 python app.py 启动GUI配置工具
echo 2. 在GUI的「高级设置」中点击「一键安装」安装AI绘图依赖
echo.
pause
