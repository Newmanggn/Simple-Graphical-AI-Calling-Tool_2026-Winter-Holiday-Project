# Simple-Graphical-AI-Calling-Tool_2026-Winter-Holiday-Project
一个使用Python + Flask + CustomTkinter开发的简单图形化AI调用工具，支持拖拽式模块配置、连线式流程定义、一键代码转换、自定义模块、运行状态可视化等功能，让AI应用开发更简单！

注意关注“项目目前状态.txt”，以明确目前情况

这是一个高中生第一次制作这样大的项目

可能有人会说comfyui不是已经够好了吗，
我的想法是，在不使用comfyui的api的前提下写一个功能更强大的（当然，高中生的寒假
还是太短了）

B站专栏：https://www.bilibili.com/opus/1172650239378587687

目前，该项目被提交参加2026年师生数字素养提升实践活动

# 简单图形化AI调用工具


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

### 1. 系统要求

- **操作系统**：Windows 系统（推荐）
- **Python 版本**：Python 3.8
- **硬件要求**：
  - 基本运行：任何现代 CPU
  - AI 绘图：至少16G以上内存、8G以上显存


### 2. 安装方法
  无需安装,下载即用
  github上传的只有源码，没有环境。
  请前往  下载完整整合包

### 3. 启动和运行

1. 双击 `launcher.exe`
2. 在 GUI 界面中，完整设置，点击「一键启动」按钮
3. 系统会自动打开浏览器，显示图形化编辑界面

## 📖 详细文档

完整的使用说明、模块开发指南、工作流示例等详细内容请查看：

**[说明文档.md](2026 Winter Break Project_Simple Graphical AI Tool/说明文档.md)** - 完整的中文文档，包含所有功能说明、技术细节、开发指南等

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
├── launcher.exe              # 启动器可执行文件
└── 说明文档.md                # 完整文档（中文）
```


## 💬 联系方式

如有问题或建议，欢迎提出 Issue！

