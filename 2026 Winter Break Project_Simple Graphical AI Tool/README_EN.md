# Simple Graphical AI Call Tool

A graphical AI model invocation and workflow orchestration tool developed with Python + Flask + CustomTkinter, making AI application development simpler through drag-and-drop module configuration and wire-based workflow definition!

## ✨ Features

- 🎨 **Drag-and-Drop Module Configuration** - Set up modules by dragging and dropping, each with input and output interfaces
- 🔗 **Wire-Based Workflow Definition** - Define execution order, testing, and data flow through connections
- 📝 **One-Click Code Conversion** - Convert graphical programming results to Python code with one click
- 🧩 **Custom Module Support** - Support custom modules with graphical programming tools
- 📊 **Running Status Visualization** - Automatically mark execution steps on wires, yellow circle shows current status
- 🎯 **Multiple Module Types** - Input modules, call modules, processing modules, output modules, etc.
- ⚡ **Step/Continuous Execution** - Support both step-by-step and continuous execution modes
- 🔴⚫ **Wire Color Switching** - Users can toggle between red and black by double-clicking wires
- 💾 **Project Save/Load** - Support saving and loading projects in `.aiud` format
- 🖼️ **AI Drawing Support** - Built-in Stable Diffusion related modules, supporting text-to-image, image-to-image, inpainting, etc.
- 🖥️ **Multi-Engine Support** - Support NVIDIA CUDA, AMD DML, ZLUDA, CPU and other computing engines
- 📦 **Virtual Environment Management** - Built-in one-click installation, supporting automated configuration of CUDA and DML virtual environments
- 🎛️ **GUI Configuration Panel** - Provides a user-friendly CustomTkinter interface for configuration and monitoring

## 🛠️ Tech Stack

- **Backend**: Python + Flask
- **Frontend**: HTML/JavaScript
- **GUI**: CustomTkinter
- **AI**: PyTorch + Diffusers + Transformers

## 🚀 Quick Start

### Requirements

- Python 3.8+
- Windows system (recommended)

### Method 1: GUI One-Click Installation (Recommended)

1. Run the GUI configuration tool:
```bash
python app.py
```

2. Click "One-Click Install" in the "Advanced Settings" of the GUI, choose according to your graphics card type:
   - **Install CUDA Only** - If you have an NVIDIA graphics card
   - **Install DML Only** - If you have an AMD/Intel graphics card
   - **Install All** - Install both environments

3. Click "One-Click Start" button, the browser will open automatically

### Method 2: Using install_basic.bat (Windows)

1. Double-click `install_basic.bat` to install basic dependencies with one click

2. Run `python app.py` to start the GUI

3. Click "One-Click Install" in the "Advanced Settings" of the GUI to install AI drawing dependencies

### Method 3: Manual Installation

1. Install basic dependencies:
```bash
pip install flask customtkinter pillow numpy requests
```

2. Run the application:
```bash
python app.py
```

3. Access in your browser: `http://localhost:5000`

## 📖 Complete Documentation

For complete usage instructions, module development guides, workflow examples, and other detailed content, please refer to:

**[说明文档.md](说明文档.md)** - Complete Chinese documentation, including all feature descriptions, technical details, development guides, etc.

## 📁 Project Structure

```
.
├── app.py                      # Main application file (GUI + Flask)
├── templates/
│   └── main.html              # Frontend page
├── default_modules/           # Built-in default modules
├── custom_modules/            # User custom modules
├── auto_save/                 # Auto-save directory
├── models/                    # Models folder
├── output/                    # Generated images output directory
├── requirements.txt           # Dependencies list
├── install_basic.bat         # Windows one-click install basic dependencies
├── start_app.vbs             # Windows quick start script
└── 说明文档.md                # Complete documentation (Chinese)
```

## 📄 License

This project is for learning and research purposes only.

## 💬 Contact

Feel free to open an Issue if you have questions or suggestions!
