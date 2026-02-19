from flask import Flask, render_template, jsonify, request, send_from_directory
import os
import importlib.util
import json
import zipfile
import io
from datetime import datetime

app = Flask(__name__)

# 模块文件夹路径
DEFAULT_MODULES_DIR = 'default_modules'
CUSTOM_MODULES_DIR = 'custom_modules'

# 存储加载的模块
loaded_modules = {}

# 解析模块文件的注释参数
def parse_module_params(file_path):
    params = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # 读取所有注释行，直到遇到非注释行
            for line in f:
                line = line.strip()
                if not line.startswith('#'):
                    break
                
                # 处理普通参数
                if '=' in line and not line.startswith('#variables_name=') and not line.startswith('#output_name='):
                    key_value = line[1:].split('=', 1)
                    if len(key_value) == 2:
                        key = key_value[0]
                        value = key_value[1]
                        # 转换布尔值
                        if value.lower() in ['t', 'true']:
                            value = True
                        elif value.lower() in ['f', 'false']:
                            value = False
                        # 转换数字
                        elif value.isdigit():
                            value = int(value)
                        params[key] = value
                # 处理变量名
                elif line.startswith('#variables_name='):
                    params['variables_name'] = line[16:]
                # 处理输出端口名称
                elif line.startswith('#output_name='):
                    params['output_name'] = line[13:]
    except Exception as e:
        print(f"解析模块文件失败: {e}")
    return params

# 加载模块
def load_modules():
    loaded_modules.clear()
    
    # 加载默认模块
    if os.path.exists(DEFAULT_MODULES_DIR):
        for filename in os.listdir(DEFAULT_MODULES_DIR):
            if filename.endswith('.py'):
                file_path = os.path.join(DEFAULT_MODULES_DIR, filename)
                module_name = os.path.splitext(filename)[0]
                params = parse_module_params(file_path)
                params['source'] = 'default'  # 添加来源信息
                loaded_modules[module_name] = params
    
    # 加载自定义模块
    if os.path.exists(CUSTOM_MODULES_DIR):
        for filename in os.listdir(CUSTOM_MODULES_DIR):
            if filename.endswith('.py'):
                file_path = os.path.join(CUSTOM_MODULES_DIR, filename)
                module_name = os.path.splitext(filename)[0]
                params = parse_module_params(file_path)
                params['source'] = 'custom'  # 添加来源信息
                loaded_modules[module_name] = params

# 初始化时加载模块
load_modules()

@app.route('/')
def index():
    return render_template('main.html')

@app.route('/api/modules')
def get_modules():
    # 重新加载模块，确保包含最新的自定义模块
    load_modules()
    return jsonify(loaded_modules)

@app.route('/api/refresh_modules')
def refresh_modules():
    load_modules()
    return jsonify(loaded_modules)

@app.route('/api/execute_module', methods=['POST'])
def execute_module():
    try:
        data = request.json
        module_name = data.get('module_name')
        input_values = data.get('input_values', [])
        settings = data.get('settings', {})  # 获取设置界面的默认值
        
        # 确定模块文件路径
        module_path = None
        if os.path.exists(os.path.join(DEFAULT_MODULES_DIR, f'{module_name}.py')):
            module_path = os.path.join(DEFAULT_MODULES_DIR, f'{module_name}.py')
        elif os.path.exists(os.path.join(CUSTOM_MODULES_DIR, f'{module_name}.py')):
            module_path = os.path.join(CUSTOM_MODULES_DIR, f'{module_name}.py')
        
        if not module_path:
            return jsonify({'error': f'模块 {module_name} 不存在'}), 404
        
        # 解析模块参数
        module_params = parse_module_params(module_path)
        input_quantity = module_params.get('input_quantity', 0)
        variable_quantity = module_params.get('variable_quantity', 0)
        output_quantity = module_params.get('output_quantity', 0)
        time_late = module_params.get('time_late', 0)
        
        # 准备输入变量
        # 前input_quantity个变量来自输入端口
        # 剩余变量和默认值来自设置界面
        prepared_inputs = []
        
        # 获取变量名列表
        variable_names = []
        if 'variables_name' in module_params:
            variable_names = [name.strip() for name in module_params['variables_name'].split(',')]
        
        # 处理输入端口变量
        for i in range(input_quantity):
            if i < len(input_values):
                prepared_inputs.append(input_values[i])
            else:
                # 从设置中获取默认值
                var_name = variable_names[i] if i < len(variable_names) else f'var{i}'
                # 对于判断模块，设置默认值为1
                if module_name == '判断' and var_name == '判断':
                    prepared_inputs.append(settings.get(var_name, 1))
                else:
                    prepared_inputs.append(settings.get(var_name))
        
        # 处理剩余变量（如果有）
        for i in range(input_quantity, variable_quantity):
            var_name = variable_names[i] if i < len(variable_names) else f'var{i}'
            # 对于判断模块，设置默认值为1
            if module_name == '判断' and var_name == '判断':
                prepared_inputs.append(settings.get(var_name, 1))
            else:
                prepared_inputs.append(settings.get(var_name))
        
        print(f'准备好的输入变量: {prepared_inputs}')
        
        # 加载模块
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 自动发现模块中的执行函数
        # 查找模块中定义的所有函数
        module_functions = []
        for name in dir(module):
            # 排除内置函数和私有函数
            if not name.startswith('_') and callable(getattr(module, name)):
                module_functions.append(name)
        
        # 尝试调用模块中的函数
        result = None
        executed_function = None
        
        # 创建取消令牌函数（使用更可靠的方式）
        def cancel_token():
            return False  # 暂时返回False，因为Flask的request对象没有connection属性
        
        # 优先调用主执行函数
        main_functions = ['execute', 'run', 'process']
        for func_name in main_functions:
            if func_name in module_functions:
                try:
                    # 对于调用模块，额外传递settings参数和cancel_token
                    if module_name == '调用模块':
                        # 检查函数是否接受cancel_token参数
                        import inspect
                        func = getattr(module, func_name)
                        sig = inspect.signature(func)
                        if 'cancel_token' in sig.parameters:
                            result = getattr(module, func_name)(*prepared_inputs, settings, cancel_token=cancel_token)
                        else:
                            result = getattr(module, func_name)(*prepared_inputs, settings)
                    else:
                        result = getattr(module, func_name)(*prepared_inputs)
                    executed_function = func_name
                    break
                except Exception as e:
                    print(f'调用主函数 {func_name} 失败: {e}')
                    continue
        
        # 如果没有主执行函数，尝试调用模块中的第一个函数
        if result is None and module_functions:
            for func_name in module_functions:
                try:
                    # 对于调用模块，额外传递settings参数和cancel_token
                    if module_name == '调用模块':
                        # 检查函数是否接受cancel_token参数
                        import inspect
                        func = getattr(module, func_name)
                        sig = inspect.signature(func)
                        if 'cancel_token' in sig.parameters:
                            result = getattr(module, func_name)(*prepared_inputs, settings, cancel_token=cancel_token)
                        else:
                            result = getattr(module, func_name)(*prepared_inputs, settings)
                    else:
                        result = getattr(module, func_name)(*prepared_inputs)
                    executed_function = func_name
                    break
                except Exception as e:
                    print(f'调用函数 {func_name} 失败: {e}')
                    continue
        
        if result is None:
            return jsonify({'error': f'模块 {module_name} 没有可执行的函数'}), 400
        
        # 处理返回值
        # 确保返回值是可迭代的
        if not isinstance(result, (list, tuple)):
            result = [result]
        
        # 检查返回值数量
        expected_outputs = output_quantity
        if time_late == variable_quantity:
            expected_outputs = output_quantity + 1
        
        print(f'执行模块 {module_name} 成功，调用函数: {executed_function}')
        print(f'返回值: {result}, 预期输出数量: {expected_outputs}')
        
        # 返回执行结果
        return jsonify({
            'result': result,
            'output_quantity': output_quantity,
            'time_late': time_late,
            'variable_quantity': variable_quantity
        })
                
    except Exception as e:
        print(f'执行模块时出错: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/save_project', methods=['POST'])
def save_project():
    try:
        # 获取项目数据
        data = request.json
        project_data = data.get('project_data')
        
        if not project_data:
            return jsonify({'error': '项目数据为空'}), 400
        
        # 确保auto_save文件夹存在
        auto_save_dir = 'auto_save'
        if not os.path.exists(auto_save_dir):
            os.makedirs(auto_save_dir)
        
        # 生成文件名
        timestamp = datetime.now().isoformat()[:19].replace(':', '-').replace('T', '-')
        filename = f'ai_tool_project_{timestamp}.aiud'
        file_path = os.path.join(auto_save_dir, filename)
        
        # 创建zip文件
        with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加project.json文件
            zipf.writestr('project.json', json.dumps(project_data, indent=2, ensure_ascii=False))
            
            # 添加自定义模块文件夹
            used_custom_modules = project_data.get('usedCustomModules', [])
            for module_name in used_custom_modules:
                # 查找自定义模块文件
                module_file = os.path.join('custom_modules', f'{module_name}.py')
                if os.path.exists(module_file):
                    # 添加自定义模块文件到zip中
                    zipf.write(module_file, f'custom_modules/{module_name}.py')
        
        print(f'项目保存成功: {file_path}')
        return jsonify({'success': True, 'message': '项目保存成功', 'file_path': file_path})
                
    except Exception as e:
        print(f'保存项目时出错: {e}')
        return jsonify({'error': str(e)}), 500

# 提供静态文件服务，用于显示和下载生成的图像
@app.route('/output/<path:filename>')
def serve_output_file(filename):
    output_dir = 'output'
    # 确保output文件夹存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return send_from_directory(output_dir, filename)

@app.route('/api/get_lmstudio_models', methods=['GET'])
def get_lmstudio_models():
    """
    获取LM Studio的模型列表
    通过后端代理来避免CORS错误
    """
    try:
        import requests
        
        # 从请求参数中获取LM Studio的主机地址
        host = request.args.get('host', 'http://localhost:1234')
        endpoint = '/v1/models'
        
        # 调用LM Studio API获取模型列表
        response = requests.get(f'{host}{endpoint}', timeout=10)
        
        if not response.ok:
            return jsonify({'error': f'调用LM Studio API失败: {response.status_code} - {response.text}'}), 400
        
        data = response.json()
        models = data.get('data', [])
        
        # 提取模型ID列表
        model_list = []
        for model in models:
            model_id = model.get('id') or model.get('name') or model.get('model')
            if model_id:
                model_list.append(model_id)
        
        return jsonify({'models': model_list}), 200
        
    except Exception as e:
        print(f'获取LM Studio模型列表失败: {e}')
        return jsonify({'error': f'获取模型列表失败: {str(e)}'}), 500

@app.route('/api/restart', methods=['POST'])
def restart_server():
    """
    重启服务器
    """
    try:
        import subprocess
        import sys
        import os
        
        print('收到重启请求，正在准备重启服务器...')
        
        # 获取当前脚本的路径
        script_path = os.path.abspath(__file__)
        
        # 构建重启命令
        # 使用pythonw.exe来在后台运行，避免控制台窗口
        python_exe = sys.executable
        
        # 启动一个新的进程来重启服务器
        # 使用subprocess.Popen来在后台运行
        subprocess.Popen([python_exe, script_path])
        
        # 返回重启成功的消息
        return jsonify({'message': '服务器正在重启...'}), 200
        
    except Exception as e:
        print(f'重启服务器失败: {e}')
        return jsonify({'error': f'重启服务器失败: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
