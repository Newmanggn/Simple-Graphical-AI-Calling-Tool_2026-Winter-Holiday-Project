# Simple-Graphical-AI-Calling-Tool_2026-Winter-Holiday-Project
一个使用Python+Flask开发的简单图形化AI调用工具，支持拖拽式模块配置、连线式流程定义、一键代码转换、自定义模块、运行状态可视化等功能，让AI应用开发更简单！

注意关注“项目目前状态.txt”，以明确目前情况

这是一个高中生第一次制作这样大的项目
# 简单图形化AI调用工具

一个使用 Python + Flask + CustomTkinter 开发的图形化 AI 模型调用和流程编排工具，通过拖拽式模块配置、连线式流程定义，让 AI 应用开发更简单！

## ✨ 功能特性

- 🎨 **拖拽式模块配置** - 通过拖拽方式设置模块，每个模块有输入输出接口
- 🔗 **连线式流程定义** - 通过连线设定运行顺序、测试和数据流向
- 📝 **一键代码转换** - 将图形化编程结果一键转换为 Python 代码（基于 Python AST 的代码生成器）
- 🧩 **自定义模块支持** - 支持自定义模块并配有图形化的编程工具
- 📊 **运行状态可视化** - 连线上自动标出运行步骤，黄色圆圈显示当前运行状态
- 🎯 **多种模块类型** - 输入模块、调用模块、处理模块、输出模块等
- ⚡ **步进/连续运行** - 支持步进运行和连续运行两种模式
- 🔴⚫ **连线颜色切换** - 用户可通过双击连线切换红黑色
- 💾 **项目保存/加载** - 支持保存和加载 `.aiud` 格式的项目文件
- 🖼️ **AI 绘图支持** - 内置 Stable Diffusion 相关模块，支持文生图、图生图、遮罩重绘等
- 🖥️ **多引擎支持** - 支持 NVIDIA CUDA、AMD DML、ZLUDA、CPU 等多种计算引擎
- 📦 **虚拟环境管理** - 内置一键安装功能，支持 CUDA 和 DML 虚拟环境的自动化配置
- 🎛️ **GUI 配置面板** - 提供友好的 CustomTkinter 界面，用于配置和监控
- 🔌 **插件化架构** - 代码生成功能独立封装在 plugin/json2py.py 中，方便维护和扩展

## 🛠️ 技术栈

- **后端**: Python + Flask
- **前端**: HTML/JavaScript
- **GUI**: CustomTkinter
- **AI**: PyTorch + Diffusers + Transformers

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Windows 系统（推荐）

### 方式一：GUI 一键安装（推荐）

1. 运行 GUI 配置工具：
```bash
python app.py
```

2. 在 GUI 的「高级设置」中点击「一键安装」，根据你的显卡类型选择：
   - **仅安装 CUDA** - 如果你有 NVIDIA 显卡
   - **仅安装 DML** - 如果你有 AMD/Intel 显卡
   - **全部安装** - 安装两种环境

3. 点击「一键启动」按钮，浏览器会自动打开

### 方式二：使用 install_basic.bat（Windows）

1. 双击 `install_basic.bat` 一键安装基础依赖

2. 运行 `python app.py` 启动 GUI

3. 在 GUI 的「高级设置」中点击「一键安装」安装 AI 绘图依赖

### 方式三：手动安装

1. 安装基础依赖：
```bash
pip install flask customtkinter pillow numpy requests
```

2. 运行应用：
```bash
python app.py
```

3. 在浏览器中访问：`http://localhost:5000`

## 📖 详细文档

完整的使用说明、模块开发指南、工作流示例等详细内容请查看：

**[说明文档.md](说明文档.md)** - 完整的中文文档，包含所有功能说明、技术细节、开发指南等

## 📁 项目结构

```
.
├── app.py                      # 主应用文件（含 GUI + Flask）
├── templates/
│   └── main.html              # 前端页面
├── plugin/                    # 插件文件夹
│   └── json2py.py             # 代码生成插件（基于 Python AST）
├── default_modules/           # 内置默认模块
├── custom_modules/            # 用户自定义模块
├── auto_save/                 # 自动保存目录
├── models/                    # 模型文件夹
├── output/                    # 生成的图像输出目录
├── requirements.txt           # 依赖列表
├── install_basic.bat         # Windows 一键安装基础依赖
├── start_app.vbs             # Windows 快捷启动脚本
└── 说明文档.md                # 完整文档（中文）
```



## 💬 联系方式

如有问题或建议，欢迎提出 Issue！

