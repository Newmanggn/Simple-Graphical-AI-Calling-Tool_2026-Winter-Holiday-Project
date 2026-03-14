import os
import threading
import concurrent.futures
import time
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

# Flask应用代码
from flask import Flask, render_template, jsonify, request, send_from_directory
import importlib.util
import json
import zipfile
import io
import uuid
import torch
import sys
import glob
from datetime import datetime
import requests

# 创建线程池执行器，用于异步执行模块
# 最大工作线程数设置为2，避免过多线程占用资源
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# 全局停止标志，用于停止正在执行的模块
stop_execution_flag = False
# 存储正在执行的future对象，用于取消
ongoing_futures = set()

app = Flask(__name__)

# 模块文件夹路径
DEFAULT_MODULES_DIR = 'default_modules'
CUSTOM_MODULES_DIR = 'custom_modules'

# 存储加载的模块
loaded_modules = {}

# 全局张量缓存
tensor_cache = {}

# 全局模型缓存
model_cache = {}

# 解析模块文件的注释参数
def parse_module_params(file_path):
    params = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            # 读取所有注释行，直到遇到非注释行
            for line in lines:
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
            
            # 提取模块功能描述（文件最末端的三引号注释）
            content = ''.join(lines)
            # 查找文件末尾的三引号注释 - 从后往前查找
            import re
            # 先尝试匹配文件末尾的三引号注释
            # 从文件末尾开始查找，避免匹配到中间的三引号
            last_triple_quote_pos = -1
            # 查找所有的 """ 位置
            import re
            # 先找出所有三引号注释块
            pattern = re.compile(r'"""([\s\S]*?)"""', re.DOTALL)
            matches = list(pattern.finditer(content))
            # 取最后一个匹配
            last_match = None
            for m in matches:
                last_match = m
            if last_match:
                description = last_match.group(1).strip()
                if description:
                    params['description'] = description
    except Exception as e:
        print(f"解析模块文件失败: {e}")
    return params

# 从所有模块文件中读取信息并格式化为提示词文本
def collect_module_info_for_prompt():
    """收集所有模块的信息并格式化为AI提示词可用的文本"""
    module_info_text = ""
    
    # 遍历默认模块目录
    if os.path.exists(DEFAULT_MODULES_DIR):
        for filename in sorted(os.listdir(DEFAULT_MODULES_DIR)):
            if filename.endswith('.py'):
                file_path = os.path.join(DEFAULT_MODULES_DIR, filename)
                module_name = os.path.splitext(filename)[0]
                
                try:
                    # 解析模块参数
                    params = parse_module_params(file_path)
                    
                    # 添加模块名称
                    module_info_text += f"{module_name}：\n"
                    
                    # 添加配置头部信息（开头的注释）
                    if params:
                        module_info_text += "  - 配置信息：\n"
                        for key, value in params.items():
                            if key not in ['description']:
                                module_info_text += f"    - {key}: {value}\n"
                    
                    # 添加模块描述（末尾的三引号注释）
                    if 'description' in params:
                        module_info_text += "  - 详细说明：\n"
                        # 格式化描述文本，添加缩进
                        for line in params['description'].split('\n'):
                            if line.strip():
                                module_info_text += f"    {line}\n"
                    
                    module_info_text += "\n"
                except Exception as e:
                    print(f"读取模块 {module_name} 信息失败: {e}")
                    continue
    
    # 遍历自定义模块目录
    if os.path.exists(CUSTOM_MODULES_DIR):
        for filename in sorted(os.listdir(CUSTOM_MODULES_DIR)):
            if filename.endswith('.py'):
                file_path = os.path.join(CUSTOM_MODULES_DIR, filename)
                module_name = os.path.splitext(filename)[0]
                
                try:
                    # 解析模块参数
                    params = parse_module_params(file_path)
                    
                    # 添加模块名称（标注为自定义模块）
                    module_info_text += f"{module_name}（自定义模块）：\n"
                    
                    # 添加配置头部信息
                    if params:
                        module_info_text += "  - 配置信息：\n"
                        for key, value in params.items():
                            if key not in ['description']:
                                module_info_text += f"    - {key}: {value}\n"
                    
                    # 添加模块描述
                    if 'description' in params:
                        module_info_text += "  - 详细说明：\n"
                        for line in params['description'].split('\n'):
                            if line.strip():
                                module_info_text += f"    {line}\n"
                    
                    module_info_text += "\n"
                except Exception as e:
                    print(f"读取自定义模块 {module_name} 信息失败: {e}")
                    continue
    
    return module_info_text

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

def _execute_module_async(module_name, input_values, settings):
    """异步执行模块的内部函数"""
    try:
        # 确定模块文件路径
        module_path = None
        if os.path.exists(os.path.join(DEFAULT_MODULES_DIR, f'{module_name}.py')):
            module_path = os.path.join(DEFAULT_MODULES_DIR, f'{module_name}.py')
        elif os.path.exists(os.path.join(CUSTOM_MODULES_DIR, f'{module_name}.py')):
            module_path = os.path.join(CUSTOM_MODULES_DIR, f'{module_name}.py')
        
        if not module_path:
            return {'error': f'模块 {module_name} 不存在'}
        
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
                val = input_values[i]
                # 如果是张量引用，从缓存中取出
                if isinstance(val, str) and val.startswith('TENSOR_REF:'):
                    tensor_id = val[len('TENSOR_REF:'):]
                    if tensor_id in tensor_cache:
                        val = tensor_cache[tensor_id]
                # 如果是图像引用，从缓存中取出
                elif isinstance(val, str) and val.startswith('IMAGE_REF:'):
                    image_id = val[len('IMAGE_REF:'):]
                    if image_id in tensor_cache:
                        val = tensor_cache[image_id]
                # 如果是图像列表引用，从缓存中取出
                elif isinstance(val, str) and val.startswith('IMAGE_LIST_REF:'):
                    image_list_id = val[len('IMAGE_LIST_REF:'):]
                    if image_list_id in tensor_cache:
                        val = tensor_cache[image_list_id]
                prepared_inputs.append(val)
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
        print(f'接收到的settings: {settings}')
        
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
        
        # 创建取消令牌函数，检查全局停止标志
        def cancel_token():
            global stop_execution_flag
            return stop_execution_flag
        
        # 优先调用主执行函数
        main_functions = ['execute', 'run', 'process']
        for func_name in main_functions:
            if func_name in module_functions:
                try:
                    # 对于调用模块和加载图像模块，额外传递settings参数
                    if module_name == '调用模块' or module_name == '加载图像模块':
                        # 检查函数是否接受settings参数
                        import inspect
                        func = getattr(module, func_name)
                        sig = inspect.signature(func)
                        
                        if module_name == '调用模块' and 'cancel_token' in sig.parameters:
                            result = getattr(module, func_name)(*prepared_inputs, settings, cancel_token=cancel_token)
                        elif 'settings' in sig.parameters:
                            result = getattr(module, func_name)(*prepared_inputs, settings)
                        else:
                            result = getattr(module, func_name)(*prepared_inputs)
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
                    # 对于调用模块和加载图像模块，额外传递settings参数
                    if module_name == '调用模块' or module_name == '加载图像模块':
                        # 检查函数是否接受settings参数
                        import inspect
                        func = getattr(module, func_name)
                        sig = inspect.signature(func)
                        
                        if module_name == '调用模块' and 'cancel_token' in sig.parameters:
                            result = getattr(module, func_name)(*prepared_inputs, settings, cancel_token=cancel_token)
                        elif 'settings' in sig.parameters:
                            result = getattr(module, func_name)(*prepared_inputs, settings)
                        else:
                            result = getattr(module, func_name)(*prepared_inputs)
                    else:
                        result = getattr(module, func_name)(*prepared_inputs)
                    executed_function = func_name
                    break
                except Exception as e:
                    print(f'调用函数 {func_name} 失败: {e}')
                    continue
        
        if result is None:
            return {'error': f'模块 {module_name} 没有可执行的函数'}
        
        # 处理返回值
        # 确保返回值是可迭代的
        if not isinstance(result, (list, tuple)):
            result = [result]
        
        # 处理张量和图像：将PyTorch张量和PIL图像存入缓存，返回引用
        processed_result = []
        for val in result:
            # 处理包含samples字段的字典（新Latent格式）
            if isinstance(val, dict) and "samples" in val and isinstance(val["samples"], torch.Tensor):
                tensor_id = str(uuid.uuid4())
                tensor_cache[tensor_id] = val
                processed_result.append(f'TENSOR_REF:{tensor_id}')
            # 处理原始张量格式（向后兼容）
            elif isinstance(val, torch.Tensor):
                tensor_id = str(uuid.uuid4())
                tensor_cache[tensor_id] = val
                processed_result.append(f'TENSOR_REF:{tensor_id}')
            elif val is not None:
                try:
                    from PIL import Image
                    if isinstance(val, Image.Image):
                        # 是PIL图像，存入缓存
                        image_id = str(uuid.uuid4())
                        tensor_cache[image_id] = val
                        processed_result.append(f'IMAGE_REF:{image_id}')
                    elif isinstance(val, list) and len(val) > 0 and isinstance(val[0], Image.Image):
                        # 是PIL图像列表，保存为列表引用
                        image_list_id = str(uuid.uuid4())
                        tensor_cache[image_list_id] = val
                        processed_result.append(f'IMAGE_LIST_REF:{image_list_id}')
                    else:
                        processed_result.append(val)
                except ImportError:
                    processed_result.append(val)
            else:
                processed_result.append(val)
        
        # 检查返回值数量
        expected_outputs = output_quantity
        if time_late == variable_quantity:
            expected_outputs = output_quantity + 1
        
        print(f'执行模块 {module_name} 成功，调用函数: {executed_function}')
        print(f'返回值: {result}, 处理后: {processed_result}, 预期输出数量: {expected_outputs}')
        
        # 返回执行结果
        return {
            'result': processed_result,
            'output_quantity': output_quantity,
            'time_late': time_late,
            'variable_quantity': variable_quantity
        }
                
    except Exception as e:
        print(f'执行模块时出错: {e}')
        return {'error': str(e)}

@app.route('/api/execute_module', methods=['POST'])
def execute_module():
    global stop_execution_flag
    try:
        data = request.json
        module_name = data.get('module_name')
        input_values = data.get('input_values', [])
        settings = data.get('settings', {})  # 获取设置界面的默认值
        
        log_message(f'收到模块执行请求: {module_name}')
        log_message(f'输入值: {input_values}')
        log_message(f'设置: {settings}')
        
        # 重置停止标志（每次新请求开始时）
        stop_execution_flag = False
        
        # 使用线程池执行器异步执行模块
        future = executor.submit(_execute_module_async, module_name, input_values, settings)
        
        # 添加到正在执行的集合中
        ongoing_futures.add(future)
        
        try:
            # 等待执行完成并获取结果，支持检查停止标志
            while not future.done():
                if stop_execution_flag:
                    future.cancel()
                    log_message(f'模块执行被取消: {module_name}')
                    return jsonify({'error': '执行已被用户取消'}), 499
                import time
                time.sleep(0.1)
            
            result = future.result()
        finally:
            # 从正在执行的集合中移除
            try:
                ongoing_futures.remove(future)
            except:
                pass
        
        # 检查是否有错误
        if 'error' in result:
            log_message(f'模块执行失败: {result["error"]}')
            return jsonify(result), 400 if '不存在' in result['error'] else 500
        
        log_message(f'模块执行成功: {module_name}')
        log_message(f'执行结果: {result}')
        
        # 返回执行结果
        return jsonify(result)
                
    except Exception as e:
        log_message(f'执行模块时出错: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/save_project', methods=['POST'])
def save_project():
    try:
        # 获取项目数据
        data = request.json
        project_data = data.get('project_data')
        
        log_message('收到项目保存请求')
        
        if not project_data:
            log_message('项目数据为空')
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
        
        log_message(f'项目保存成功: {file_path}')
        return jsonify({'success': True, 'message': '项目保存成功', 'file_path': file_path})
                
    except Exception as e:
        log_message(f'保存项目时出错: {e}')
        return jsonify({'error': str(e)}), 500

# 提供静态文件服务，用于显示和下载生成的图像
@app.route('/output/&lt;path:filename&gt;')
def serve_output_file(filename):
    output_dir = 'output'
    # 确保output文件夹存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return send_from_directory(output_dir, filename)

@app.route('/api/get_image_base64', methods=['GET'])
def get_image_base64():
    """
    获取缓存中图像的base64数据
    """
    try:
        image_ref = request.args.get('image_ref', '')
        if not image_ref:
            return jsonify({'error': '缺少image_ref参数'}), 400
        
        print(f'获取图像base64: {image_ref}')
        
        if image_ref not in tensor_cache:
            return jsonify({'error': '图像引用不存在'}), 404
        
        image_data = tensor_cache[image_ref]
        
        from PIL import Image
        import io
        import base64
        
        images_to_convert = []
        if isinstance(image_data, list):
            images_to_convert = image_data
        elif isinstance(image_data, Image.Image):
            images_to_convert = [image_data]
        
        if not images_to_convert:
            return jsonify({'error': '没有有效的图像数据'}), 400
        
        # 只转换第一张图片（显示用）
        img = images_to_convert[0]
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image_base64': f'data:image/png;base64,{img_str}',
            'image_count': len(images_to_convert)
        }), 200
        
    except Exception as e:
        print(f'获取图像base64失败: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

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
        endpoint = '/api/v1/models'
        
        print(f'调用LM Studio API: {host}{endpoint}')
        
        # 调用LM Studio API获取模型列表
        response = requests.get(f'{host}{endpoint}')
        
        print(f'API响应状态码: {response.status_code}')
        print(f'API响应内容: {response.text}')
        
        if not response.ok:
            return jsonify({'error': f'调用LM Studio API失败: {response.status_code} - {response.text}'}), 400
        
        data = response.json()
        print(f'解析后的响应数据: {data}')
        
        # 处理不同的响应格式
        models = []
        if isinstance(data, list):
            # 直接返回模型列表的格式
            models = data
            print(f'直接使用列表格式: {len(models)}个模型')
        elif 'data' in data:
            # 嵌套在data字段中的格式
            models = data.get('data', [])
            print(f'使用data字段格式: {len(models)}个模型')
        elif 'models' in data:
            # 嵌套在models字段中的格式
            models = data.get('models', [])
            print(f'使用models字段格式: {len(models)}个模型')
        else:
            print(f'未识别的响应格式，尝试直接使用: {data}')
            models = [data] if data else []
        
        # 提取模型ID列表
        model_list = []
        for model in models:
            model_id = model.get('key') or model.get('id') or model.get('name') or model.get('model') or model.get('model_id')
            if model_id:
                model_list.append(model_id)
        print(f'最终提取的模型列表: {model_list}')
        
        return jsonify({'models': model_list}), 200
        
    except Exception as e:
        print(f'获取LM Studio模型列表失败: {e}')
        return jsonify({'error': f'获取模型列表失败: {str(e)}'}), 500

@app.route('/api/save_cache', methods=['POST'])
def save_cache():
    """
    保存界面缓存
    """
    try:
        # 获取缓存数据
        data = request.json
        cache_data = data.get('cache_data')
        
        if not cache_data:
            return jsonify({'error': '缓存数据为空'}), 400
        
        # 确保缓存文件夹存在
        cache_dir = os.path.join('auto_save', 'cache')
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        # 使用固定文件名
        cache_file = os.path.join(cache_dir, 'cache.json')
        
        # 保存缓存数据
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        print(f'缓存保存成功: {cache_file}')
        return jsonify({'success': True, 'message': '缓存保存成功', 'file_path': cache_file})
                
    except Exception as e:
        print(f'保存缓存失败: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/load_cache', methods=['GET'])
def load_cache():
    """
    加载最新的界面缓存
    """
    try:
        # 确保缓存文件夹存在
        cache_dir = os.path.join('auto_save', 'cache')
        if not os.path.exists(cache_dir):
            return jsonify({'error': '缓存文件夹不存在'}), 404
        
        # 使用固定文件名
        cache_file = os.path.join(cache_dir, 'cache.json')
        if not os.path.exists(cache_file):
            return jsonify({'error': '缓存文件不存在'}), 404
        
        # 读取缓存数据
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        print(f'缓存加载成功: {cache_file}')
        return jsonify({'success': True, 'cache_data': cache_data, 'file_path': cache_file})
                
    except Exception as e:
        print(f'加载缓存失败: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear_cache', methods=['POST'])
def clear_cache():
    """
    清除界面缓存
    """
    try:
        cache_dir = os.path.join('auto_save', 'cache')
        cache_file = os.path.join(cache_dir, 'cache.json')
        
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f'缓存已清除: {cache_file}')
            return jsonify({'success': True, 'message': '缓存已清除'})
        else:
            print('缓存文件不存在，无需清除')
            return jsonify({'success': True, 'message': '缓存文件不存在'})
                
    except Exception as e:
        print(f'清除缓存失败: {e}')
        return jsonify({'error': str(e)}), 500

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

@app.route('/api/get_default_paths', methods=['GET'])
def get_default_paths():
    """
    获取默认路径配置
    """
    try:
        settings_file = os.path.join(os.getcwd(), "gui_settings.json")
        default_model_path = os.path.join(os.getcwd(), "models")
        default_image_path = os.path.join(os.getcwd(), "auto_save")
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_model_path = settings.get("模型文件夹路径", default_model_path)
                    saved_image_path = settings.get("默认图片保存路径", default_image_path)
                    return jsonify({
                        'success': True,
                        'default_model_path': saved_model_path,
                        'default_image_path': saved_image_path
                    }), 200
            except Exception as e:
                print(f'读取设置文件失败: {e}')
        
        return jsonify({
            'success': True,
            'default_model_path': default_model_path,
            'default_image_path': default_image_path
        }), 200
        
    except Exception as e:
        print(f'获取默认路径失败: {e}')
        return jsonify({'error': f'获取默认路径失败: {str(e)}'}), 500

@app.route('/api/get_default_model_path', methods=['GET'])
def get_default_model_path():
    """
    获取默认模型文件夹路径（兼容旧接口）
    """
    try:
        settings_file = os.path.join(os.getcwd(), "gui_settings.json")
        default_path = os.path.join(os.getcwd(), "models")
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_path = settings.get("模型文件夹路径", default_path)
                    return jsonify({
                        'success': True,
                        'default_path': saved_path
                    }), 200
            except Exception as e:
                print(f'读取设置文件失败: {e}')
        
        return jsonify({
            'success': True,
            'default_path': default_path
        }), 200
        
    except Exception as e:
        print(f'获取默认路径失败: {e}')
        return jsonify({'error': f'获取默认路径失败: {str(e)}'}), 500

@app.route('/api/stop_execution', methods=['POST'])
def stop_execution():
    """
    停止当前正在执行的所有模块，并清空显存
    """
    global stop_execution_flag
    stop_execution_flag = True
    
    # 取消所有正在执行的future
    for future in ongoing_futures:
        try:
            future.cancel()
        except:
            pass
    
    # 清空张量缓存
    tensor_cache.clear()
    print('已清空张量缓存')
    
    # 清空模型缓存
    model_cache.clear()
    print('已清空模型缓存')
    
    # 释放PyTorch显存
    try:
        if torch and torch.cuda.is_available():
            torch.cuda.empty_cache()
            print('已释放CUDA显存')
    except Exception as e:
        print(f'释放CUDA显存失败: {e}')
    
    print('收到停止执行请求并已清空显存')
    return jsonify({'success': True, 'message': '已发送停止信号并清空显存'}), 200

@app.route('/api/get_engine_setting', methods=['GET'])
def get_engine_setting():
    """
    获取当前设置的生成引擎
    """
    try:
        settings_file = os.path.join(os.getcwd(), "gui_settings.json")
        default_engine = "CPU"
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_engine = settings.get("生成引擎", default_engine)
                    return jsonify({
                        'success': True,
                        'engine': saved_engine
                    }), 200
            except Exception as e:
                print(f'读取生成引擎设置失败: {e}')
        
        return jsonify({
            'success': True,
            'engine': default_engine
        }), 200
        
    except Exception as e:
        print(f'获取生成引擎设置失败: {e}')
        return jsonify({'error': f'获取生成引擎设置失败: {str(e)}'}), 500


@app.route('/api/get_vae_setting', methods=['GET'])
def get_vae_setting():
    """
    获取当前设置的使用 CPU 运行 VAE
    """
    try:
        settings_file = os.path.join(os.getcwd(), "gui_settings.json")
        default_vae = False
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_vae = settings.get("使用 CPU 运行 VAE", default_vae)
                    return jsonify({
                        'success': True,
                        'use_cpu_for_vae': saved_vae
                    }), 200
            except Exception as e:
                print(f'读取使用 CPU 运行 VAE 设置失败: {e}')
        
        return jsonify({
            'success': True,
            'use_cpu_for_vae': default_vae
        }), 200
        
    except Exception as e:
        print(f'获取使用 CPU 运行 VAE 设置失败: {e}')
        return jsonify({'error': f'获取使用 CPU 运行 VAE 设置失败: {str(e)}'}), 500


@app.route('/api/scan_models', methods=['POST'])
def scan_models():
    """
    扫描指定文件夹中的模型文件
    """
    try:
        data = request.json
        folder_path = data.get('folder_path', '')
        
        if not folder_path:
            return jsonify({'error': '文件夹路径不能为空'}), 400
        
        print(f'扫描模型文件夹: {folder_path}')
        
        # 检查文件夹是否存在
        if not os.path.exists(folder_path):
            return jsonify({'error': '文件夹不存在'}), 404
        
        # 扫描模型文件
        model_files = []
        patterns = [
            os.path.join(folder_path, "**", "*.safetensors"),
            os.path.join(folder_path, "**", "*.ckpt"),
            os.path.join(folder_path, "**", "*.bin")
        ]
        
        for pattern in patterns:
            files = glob.glob(pattern, recursive=True)
            model_files.extend(files)
        
        print(f'找到的模型文件: {model_files}')
        
        return jsonify({
            'success': True,
            'model_files': model_files
        }), 200
        
    except Exception as e:
        print(f'扫描模型文件失败: {e}')
        return jsonify({'error': f'扫描模型文件失败: {str(e)}'}), 500

@app.route('/api/get_module_source', methods=['POST'])
def get_module_source():
    """
    获取模块的完整源代码
    """
    try:
        data = request.json
        module_name = data.get('module_name')
        
        if not module_name:
            return jsonify({'error': '缺少module_name参数'}), 400
        
        # 确定模块文件路径
        module_path = None
        if os.path.exists(os.path.join(DEFAULT_MODULES_DIR, f'{module_name}.py')):
            module_path = os.path.join(DEFAULT_MODULES_DIR, f'{module_name}.py')
        elif os.path.exists(os.path.join(CUSTOM_MODULES_DIR, f'{module_name}.py')):
            module_path = os.path.join(CUSTOM_MODULES_DIR, f'{module_name}.py')
        
        if not module_path:
            return jsonify({'error': f'模块 {module_name} 不存在'}), 404
        
        # 读取模块源代码
        with open(module_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # 解析模块参数
        module_params = parse_module_params(module_path)
        
        return jsonify({
            'success': True,
            'source_code': source_code,
            'module_params': module_params
        }), 200
        
    except Exception as e:
        print(f'获取模块源代码失败: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate_code_ast', methods=['POST'])
def generate_code_ast():
    """
    基于AST的工作流Python代码生成
    """
    try:
        data = request.json
        workflow_data = data.get('workflow', {})
        
        # 导入插件
        import sys
        import os
        
        # 添加 plugin 目录到路径
        plugin_dir = os.path.join(os.path.dirname(__file__), 'plugin')
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)
        
        from json2py import generate_python_code_from_workflow
        
        # 调用插件函数
        source_code = generate_python_code_from_workflow(
            workflow_data,
            DEFAULT_MODULES_DIR,
            CUSTOM_MODULES_DIR
        )
        
        return jsonify({
            'success': True,
            'source_code': source_code
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f'AST代码生成失败: {e}')
        return jsonify({'error': str(e)}), 500


def get_engine_from_settings():
    """从 gui_settings.json 读取生成引擎设置"""
    import os
    import json
    
    settings_file = os.path.join(os.getcwd(), "gui_settings.json")
    default_engine = "CPU"
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
            # 尝试从不同的键中读取
            if "生成引擎" in settings:
                return settings["生成引擎"]
            elif "engine" in settings:
                return settings["engine"]
        except Exception:
            pass
    
    # 备份方案：从 simple_gui.py 读取
    backup_file = os.path.join(os.getcwd(), "simple_gui.py")
    if os.path.exists(backup_file):
        try:
            import ast
            with open(backup_file, "r", encoding="utf-8") as f:
                # 尝试在文件中搜索引擎设置
                content = f.read()
                if "生成引擎" in content:
                    # 简单字符串解析
                    for line in content.split('\n'):
                        if "生成引擎" in line and ":" in line:
                            engine = line.split(":", 1)[1].strip().strip('"').strip("'").strip(",")
                            if engine:
                                return engine
        except Exception:
            pass
    
    return default_engine


def check_and_restart_in_venv():
    """根据生成引擎设置选择对应的虚拟环境并重启"""
    import sys
    import os
    import subprocess
    
    # 如果已经在虚拟环境中运行，直接返回
    if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
        return False
    
    # 获取生成引擎设置
    engine = get_engine_from_settings()
    print(f"读取到的生成引擎: {engine}")
    
    # 检查虚拟环境是否存在
    project_dir = os.getcwd()
    venv_cuda = os.path.join(project_dir, "venv_cuda")
    venv_dml = os.path.join(project_dir, "venv_dml")
    
    # 根据引擎选择虚拟环境
    target_venv = None
    
    if "CUDA" in engine or "TensorRT" in engine or "ZLUDA" in engine:
        # CUDA/TensorRT/ZLUDA 使用 venv_cuda
        if os.path.exists(venv_cuda):
            target_venv = venv_cuda
    elif "DML" in engine:
        # DML 必须使用 venv_dml，不存在则弹窗提醒
        if os.path.exists(venv_dml):
            target_venv = venv_dml
        else:
            # DML 引擎但 venv_dml 不存在，弹窗提醒
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror(
                    "错误",
                    "已选择 DML 引擎，但 venv_dml 虚拟环境不存在！\n\n"
                    "请先在高级设置中点击「一键安装」，选择「仅安装 DML」或「全部安装」。"
                )
                root.destroy()
            except:
                print("错误：已选择 DML 引擎，但 venv_dml 虚拟环境不存在！")
            sys.exit(1)
    else:
        # CPU 或其他情况，按优先级选择
        if os.path.exists(venv_cuda):
            target_venv = venv_cuda
        elif os.path.exists(venv_dml):
            target_venv = venv_dml
    
    if target_venv:
        python_exe = os.path.join(target_venv, "Scripts", "python.exe")
        if os.path.exists(python_exe):
            print(f"选择虚拟环境: {target_venv}")
            print(f"正在使用虚拟环境重新启动...")
            # 使用 subprocess 启动，在 Windows 上更可靠
            subprocess.Popen([python_exe] + sys.argv, cwd=project_dir)
            return True
    
    return False

# 加载AI驱动工作流设置
def load_ai_workflow_settings():
    """加载AI驱动工作流设置"""
    settings_file = 'AI_driven_workflow_setting.json'
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f'加载AI工作流设置失败: {e}')
    # 返回默认设置
    return {
        "llm_config": {
            "provider": "local",
            "local": {
                "host": "http://localhost:1234",
                "model": ""
            },
            "api": {
                "provider": "openai",
                "api_key": "",
                "model": "gpt-4"
            }
        },
        "prompts": {
            "system_prompt": "你是一个AI工作流助手，能够根据用户需求创建工作流。你必须使用工具来实际创建工作流，不能只是描述。\n\n请按照以下步骤操作：\n1. 使用place_module工具在画布上放置所需模块\n2. 使用connect_modules工具连接模块\n3. 使用set_module_params工具设置模块参数\n\n重要要求：\n- 每次只输出一个工具调用，以纯JSON格式输出\n- 必须使用双引号，不能使用单引号\n- 不要包含任何自然语言解释\n- 工具调用后，根据反馈结果决定下一步操作\n- 完成所有操作后，输出最终的工作流描述\n\n工具使用示例：\n{\n  \"tool_calls\": [\n    {\n      \"id\": \"call_1\",\n      \"type\": \"function\",\n      \"function\": {\n        \"name\": \"place_module\",\n        \"arguments\": {\n          \"module_name\": \"user输入\",\n          \"x\": 100,\n          \"y\": 100\n        }\n      }\n    }\n  ]\n}",


            "user_prompt": "请根据以下需求创建一个工作流：{user_input}"
        },
        "tools": {
            "enabled": True,
            "list": [
                {
                    "name": "place_module",
                    "description": "在画布上放置一个模块",
                    "parameters": {
                        "module_name": "string",
                        "x": "number",
                        "y": "number"
                    }
                },
                {
                    "name": "connect_modules",
                    "description": "连接两个模块",
                    "parameters": {
                        "start_module_id": "string",
                        "start_port_index": "number",
                        "end_module_id": "string",
                        "end_port_index": "number"
                    }
                },
                {
                    "name": "set_module_params",
                    "description": "设置模块参数",
                    "parameters": {
                        "module_id": "string",
                        "params": "object"
                    }
                }
            ]
        }
    }

# 保存AI驱动工作流设置
@app.route('/api/save_ai_workflow_settings', methods=['POST'])
def save_ai_workflow_settings():
    """保存AI驱动工作流设置"""
    try:
        data = request.json
        settings = data.get('settings')
        
        if not settings:
            return jsonify({'error': '缺少settings参数'}), 400
        
        # 保存到文件
        settings_file = 'AI_driven_workflow_setting.json'
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True, 'message': '设置保存成功'}), 200
    except Exception as e:
        print(f'保存AI工作流设置失败: {e}')
        return jsonify({'error': str(e)}), 500

# 获取AI驱动工作流设置
@app.route('/api/get_ai_workflow_settings', methods=['GET'])
def get_ai_workflow_settings():
    """获取AI驱动工作流设置"""
    try:
        settings = load_ai_workflow_settings()
        return jsonify(settings), 200
    except Exception as e:
        print(f'获取AI工作流设置失败: {e}')
        return jsonify({'error': str(e)}), 500

# 与LLM交互的函数（支持流式输出）
def interact_with_llm_stream(message, settings):
    """与LLM交互（流式输出）"""
    llm_config = settings.get('llm_config', {})
    provider = llm_config.get('provider', 'local')
    
    if provider == 'local':
        # 使用本地LM Studio
        local_config = llm_config.get('local', {})
        host = local_config.get('host', 'http://localhost:1234')
        model = local_config.get('model', '')
        
        try:
            # 构建请求数据
            tools = []
            if settings.get('tools', {}).get('enabled', False):
                # 格式化工具定义，符合OpenAI API要求
                raw_tools = settings.get('tools', {}).get('list', [])
                for raw_tool in raw_tools:
                    # 构建JSON Schema格式的parameters
                    parameters_schema = {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                    
                    # 处理原始参数
                    raw_params = raw_tool.get('parameters', {})
                    for param_name, param_type in raw_params.items():
                        # 转换类型名称
                        openai_type = param_type
                        if param_type == 'string':
                            openai_type = 'string'
                        elif param_type == 'number':
                            openai_type = 'number'
                        elif param_type == 'object':
                            openai_type = 'object'
                        elif param_type == 'boolean':
                            openai_type = 'boolean'
                        
                        parameters_schema['properties'][param_name] = {
                            "type": openai_type
                        }
                        parameters_schema['required'].append(param_name)
                    
                    # 构建完整的工具定义
                    formatted_tool = {
                        "type": "function",
                        "function": {
                            "name": raw_tool['name'],
                            "description": raw_tool.get('description', ''),
                            "parameters": parameters_schema
                        }
                    }
                    tools.append(formatted_tool)
            
            # 获取基础system_prompt
            base_system_prompt = settings.get('prompts', {}).get('system_prompt', '')
            
            # 自动收集模块信息
            module_info = collect_module_info_for_prompt()
            
            # 将模块信息添加到system_prompt中
            full_system_prompt = base_system_prompt
            if module_info:
                full_system_prompt += "\n\n=== 可用模块详细信息 ===\n"
                full_system_prompt += module_info
            
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": full_system_prompt},
                    {"role": "user", "content": message}
                ],
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0.7,
                "max_tokens": 1000,
                "stream": True
            }
            
            # 发送请求
            response = requests.post(
                f'{host}/v1/chat/completions', 
                headers={"Content-Type": "application/json"}, 
                json=data, 
                stream=True
            )
            response.raise_for_status()
            return response
        except Exception as e:
            print(f'与本地LLM交互失败: {e}')
            return None
    else:
        # 使用API
        api_config = llm_config.get('api', {})
        api_provider = api_config.get('provider', 'OpenAI')
        api_key = api_config.get('api_key', '')
        model = api_config.get('model', 'gpt-4')
        
        try:
            # 构建基础请求数据
            if tools is None:
                tools = []
                if settings.get('tools', {}).get('enabled', False):
                    # 格式化工具定义，符合OpenAI API要求
                    raw_tools = settings.get('tools', {}).get('list', [])
                    for raw_tool in raw_tools:
                        # 构建JSON Schema格式的parameters
                        parameters_schema = {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                        
                        # 处理原始参数
                        raw_params = raw_tool.get('parameters', {})
                        for param_name, param_type in raw_params.items():
                            # 转换类型名称
                            openai_type = param_type
                            if param_type == 'string':
                                openai_type = 'string'
                            elif param_type == 'number':
                                openai_type = 'number'
                            elif param_type == 'object':
                                openai_type = 'object'
                            elif param_type == 'boolean':
                                openai_type = 'boolean'
                            
                            parameters_schema['properties'][param_name] = {
                                "type": openai_type
                            }
                            parameters_schema['required'].append(param_name)
                        
                        # 构建完整的工具定义
                        formatted_tool = {
                            "type": "function",
                            "function": {
                                "name": raw_tool['name'],
                                "description": raw_tool.get('description', ''),
                                "parameters": parameters_schema
                            }
                        }
                        tools.append(formatted_tool)
            
            # 获取基础system_prompt
            base_system_prompt = settings.get('prompts', {}).get('system_prompt', '')
            
            # 自动收集模块信息
            module_info = collect_module_info_for_prompt()
            
            # 将模块信息添加到system_prompt中
            full_system_prompt = base_system_prompt
            if module_info:
                full_system_prompt += "\n\n=== 可用模块详细信息 ===\n"
                full_system_prompt += module_info
            
            messages = [
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": message}
            ]
            
            # 根据服务商选择不同的API配置
            if api_provider == 'OpenAI':
                # 使用OpenAI API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "stream": True
                }
                endpoint = 'https://api.openai.com/v1/chat/completions'
            elif api_provider == '火山引擎':
                # 使用火山引擎API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "stream": True
                }
                endpoint = 'https://ark.cn-beijing.volces.com/api/v3/chat/completions'
            elif api_provider == '阿里云':
                # 使用阿里云API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "stream": True
                }
                endpoint = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/gpt3.5/turbo'
            elif api_provider == '腾讯云':
                # 使用腾讯云API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "stream": True
                }
                endpoint = 'https://api.tencentcloudapi.com/v20230901/chat/completions'
            elif api_provider == 'DeepSeek':
                # 使用DeepSeek API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "stream": True
                }
                endpoint = 'https://api.deepseek.com/v1/chat/completions'
            else:
                # 默认使用OpenAI API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "stream": True
                }
                endpoint = 'https://api.openai.com/v1/chat/completions'
            
            response = requests.post(endpoint, json=data, headers=headers, stream=True)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f'与API LLM交互失败: {e}')
            return None

# 与LLM交互的函数（非流式）
def interact_with_llm(message, settings, tools=None):
    """与LLM交互（非流式）"""
    import json
    llm_config = settings.get('llm_config', {})
    provider = llm_config.get('provider', 'local')
    
    if provider == 'local':
        # 使用本地LM Studio
        local_config = llm_config.get('local', {})
        host = local_config.get('host', 'http://localhost:1234')
        model = local_config.get('model', '')
        
        try:
            # 构建请求数据
            if tools is None:
                tools = []
                if settings.get('tools', {}).get('enabled', False):
                    # 格式化工具定义，符合OpenAI API要求
                    raw_tools = settings.get('tools', {}).get('list', [])
                    for raw_tool in raw_tools:
                        # 构建JSON Schema格式的parameters
                        parameters_schema = {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                        
                        # 处理原始参数
                        raw_params = raw_tool.get('parameters', {})
                        for param_name, param_type in raw_params.items():
                            # 转换类型名称
                            openai_type = param_type
                            if param_type == 'string':
                                openai_type = 'string'
                            elif param_type == 'number':
                                openai_type = 'number'
                            elif param_type == 'object':
                                openai_type = 'object'
                            elif param_type == 'boolean':
                                openai_type = 'boolean'
                            
                            parameters_schema['properties'][param_name] = {
                                "type": openai_type
                            }
                            parameters_schema['required'].append(param_name)
                        
                        # 构建完整的工具定义
                        formatted_tool = {
                            "type": "function",
                            "function": {
                                "name": raw_tool['name'],
                                "description": raw_tool.get('description', ''),
                                "parameters": parameters_schema
                            }
                        }
                        tools.append(formatted_tool)
            
            # 解析对话历史
            try:
                messages = json.loads(message)
            except json.JSONDecodeError:
                # 如果不是JSON，作为普通消息处理
                messages = [
                    {"role": "system", "content": settings.get('prompts', {}).get('system_prompt', '')},
                    {"role": "user", "content": message}
                ]
            
            data = {
                "model": model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            # 发送请求
            response = requests.post(
                f'{host}/v1/chat/completions', 
                headers={"Content-Type": "application/json"}, 
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f'与本地LLM交互失败: {e}')
            return {'error': str(e)}
    else:
        # 使用API
        api_config = llm_config.get('api', {})
        api_provider = api_config.get('provider', 'OpenAI')
        api_key = api_config.get('api_key', '')
        model = api_config.get('model', 'gpt-4')
        
        try:
            # 构建基础请求数据
            if tools is None:
                tools = []
                if settings.get('tools', {}).get('enabled', False):
                    # 格式化工具定义，符合OpenAI API要求
                    raw_tools = settings.get('tools', {}).get('list', [])
                    for raw_tool in raw_tools:
                        # 构建JSON Schema格式的parameters
                        parameters_schema = {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                        
                        # 处理原始参数
                        raw_params = raw_tool.get('parameters', {})
                        for param_name, param_type in raw_params.items():
                            # 转换类型名称
                            openai_type = param_type
                            if param_type == 'string':
                                openai_type = 'string'
                            elif param_type == 'number':
                                openai_type = 'number'
                            elif param_type == 'object':
                                openai_type = 'object'
                            elif param_type == 'boolean':
                                openai_type = 'boolean'
                            
                            parameters_schema['properties'][param_name] = {
                                "type": openai_type
                            }
                            parameters_schema['required'].append(param_name)
                        
                        # 构建完整的工具定义
                        formatted_tool = {
                            "type": "function",
                            "function": {
                                "name": raw_tool['name'],
                                "description": raw_tool.get('description', ''),
                                "parameters": parameters_schema
                            }
                        }
                        tools.append(formatted_tool)
            
            # 获取基础system_prompt
            base_system_prompt = settings.get('prompts', {}).get('system_prompt', '')
            
            # 自动收集模块信息
            module_info = collect_module_info_for_prompt()
            
            # 将模块信息添加到system_prompt中
            full_system_prompt = base_system_prompt
            if module_info:
                full_system_prompt += "\n\n=== 可用模块详细信息 ===\n"
                full_system_prompt += module_info
            
            messages = [
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": message}
            ]
            
            # 根据服务商选择不同的API配置
            if api_provider == 'OpenAI':
                # 使用OpenAI API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto"
                }
                endpoint = 'https://api.openai.com/v1/chat/completions'
            elif api_provider == '火山引擎':
                # 使用火山引擎API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto"
                }
                endpoint = 'https://ark.cn-beijing.volces.com/api/v3/chat/completions'
            elif api_provider == '阿里云':
                # 使用阿里云API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto"
                }
                endpoint = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/gpt3.5/turbo'
            elif api_provider == '腾讯云':
                # 使用腾讯云API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto"
                }
                endpoint = 'https://api.tencentcloudapi.com/v20230901/chat/completions'
            elif api_provider == 'DeepSeek':
                # 使用DeepSeek API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto"
                }
                endpoint = 'https://api.deepseek.com/v1/chat/completions'
            else:
                # 默认使用OpenAI API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto"
                }
                endpoint = 'https://api.openai.com/v1/chat/completions'
            
            response = requests.post(endpoint, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f'与API LLM交互失败: {e}')
            return {'error': str(e)}



# 处理AI工作流请求的API端点（非流式）
@app.route('/api/ai_workflow', methods=['POST'])
def ai_workflow():
    """处理AI工作流请求（非流式）"""
    try:
        data = request.json
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({'error': '缺少message参数'}), 400
        
        # 加载设置
        settings = load_ai_workflow_settings()
        
        # 重新加载模块，确保包含最新的模块信息
        load_modules()
        
        # 构建模块信息（简化版本，减少长度）
        modules_info = "系统中可用的模块：\n\n"
        module_count = 0
        max_modules = 10  # 限制模块数量
        
        for module_name, module_params in loaded_modules.items():
            if module_count >= max_modules:
                modules_info += f"... 等其他 {len(loaded_modules) - max_modules} 个模块\n\n"
                break
                
            name = module_params.get('name', module_name)
            kind = module_params.get('kind', '处理模块')
            input_quantity = module_params.get('input_quantity', 0)
            output_quantity = module_params.get('output_quantity', 0)
            
            # 构建简洁的模块描述
            modules_info += f"- {name} ({kind}): 输入{input_quantity}，输出{output_quantity}\n"
            module_count += 1
        
        modules_info += "\n"
        
        # 构建用户提示
        user_prompt_template = settings.get('prompts', {}).get('user_prompt', '请根据以下需求创建一个工作流：{user_input}')
        user_prompt = user_prompt_template.format(user_input=user_message)
        
        # 构建完整提示词
        full_prompt = f"{modules_info}\n{user_prompt}"
        
        # 与LLM交互
        llm_response = interact_with_llm(full_prompt, settings)
        
        if 'error' in llm_response:
            return jsonify({'error': llm_response['error']}), 500
        
        # 处理LLM响应
        return jsonify(llm_response)
        
    except Exception as e:
        print(f'处理AI工作流请求失败: {e}')
        return jsonify({'error': str(e)}), 500

# 处理工具调用的API端点
@app.route('/api/ai_workflow/tool_call', methods=['POST'])
def ai_workflow_tool_call():
    """处理工具调用"""
    try:
        data = request.json
        tool_call_id = data.get('tool_call_id')
        result = data.get('result')
        
        if not tool_call_id or not result:
            return jsonify({'error': '缺少tool_call_id或result参数'}), 400
        
        # 加载设置
        settings = load_ai_workflow_settings()
        
        # 构建工具调用结果消息（正确的格式）
        tool_result_message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps(result)
        }
        
        # 与LLM交互获取最终响应
        llm_response = interact_with_llm(json.dumps(tool_result_message), settings)
        
        if 'error' in llm_response:
            return jsonify({'error': llm_response['error']}), 500
        
        # 处理LLM响应
        return jsonify(llm_response)
        
    except Exception as e:
        print(f'处理工具调用失败: {e}')
        return jsonify({'error': str(e)}), 500

# 全局状态管理
ai_workflow_tasks = {}

# 工具定义
ai_tools = [
    {
        "type": "function",
        "function": {
            "name": "place_module",
            "description": "在画布上放置一个模块",
            "parameters": {
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "模块名称"
                    },
                    "x": {
                        "type": "number",
                        "description": "模块的X坐标"
                    },
                    "y": {
                        "type": "number",
                        "description": "模块的Y坐标"
                    }
                },
                "required": ["module_name", "x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "connect_modules",
            "description": "连接两个模块",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_module_id": {
                        "type": "string",
                        "description": "源模块ID"
                    },
                    "end_module_id": {
                        "type": "string",
                        "description": "目标模块ID"
                    },
                    "start_port_index": {
                        "type": "number",
                        "description": "源模块端口索引"
                    },
                    "end_port_index": {
                        "type": "number",
                        "description": "目标模块端口索引"
                    }
                },
                "required": ["start_module_id", "end_module_id", "start_port_index", "end_port_index"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_module_params",
            "description": "设置模块参数",
            "parameters": {
                "type": "object",
                "properties": {
                    "module_id": {
                        "type": "string",
                        "description": "模块ID"
                    },
                    "params": {
                        "type": "object",
                        "description": "模块参数"
                    }
                },
                "required": ["module_id", "params"]
            }
        }
    }
]

# 全局变量：跟踪工作流生成过程中的统计信息
global_workflow_stats = {
    'modules_added': 0,
    'connections_added': 0,
    'operations': []
}

# 重置工作流统计信息
def reset_workflow_stats():
    """重置工作流统计信息"""
    global global_workflow_stats
    global_workflow_stats = {
        'modules_added': 0,
        'connections_added': 0,
        'operations': []
    }

# 执行工具调用 - 工具调用执行逻辑
def execute_tool(tool_name, tool_args):
    """执行工具调用 - 实现工具调用执行逻辑"""
    # 声明全局变量
    global global_workflow_stats
    
    try:
        # 1. 定义工具契约：明确告诉AI有哪些函数可用
        available_tools = {
            'place_module': '在画布上放置一个模块',
            'connect_modules': '连接两个模块',
            'set_module_params': '设置模块参数'
        }
        
        # 检查工具是否存在
        if tool_name not in available_tools:
            return {
                'success': False,
                'error': f'未知工具: {tool_name}。可用工具: {list(available_tools.keys())}'
            }
        
        # 处理tool_args可能是字符串的情况
        if isinstance(tool_args, str):
            try:
                log_message(f'工具参数是字符串，尝试解析为JSON: {tool_args}')
                import json
                tool_args = json.loads(tool_args)
            except json.JSONDecodeError as e:
                error_msg = f'工具参数解析失败: {str(e)}'
                log_message(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
        
        log_message(f'执行工具: {tool_name}，参数: {tool_args}')
        
        # 2. 参数校验：AI返回的JSON参数必须经过代码校验
        if tool_name == 'place_module':
            # 校验必要参数
            if 'module_name' not in tool_args or 'x' not in tool_args or 'y' not in tool_args:
                return {
                    'success': False,
                    'error': 'place_module工具缺少必要参数: module_name, x, y'
                }
            
            # 3. 功能映射：place_module -> 调用画布接口生成节点
            module_name = tool_args.get('module_name')
            x = tool_args.get('x')
            y = tool_args.get('y')
            
            # 生成模块ID
            module_id = f"module_{int(time.time() * 1000)}"
            # 创建操作对象
            operation = {
                'id': f"op_{int(time.time() * 1000)}",
                'type': 'place_module',
                'args': {
                    'module_name': module_name,
                    'x': x,
                    'y': y
                },
                'module_id': module_id
            }
            
            # 更新统计信息
            global_workflow_stats['modules_added'] += 1
            global_workflow_stats['operations'].append(operation)
            
            # 4. 结果返回：将执行成功/失败的结果，塞回给AI的上下文
            return {
                'success': True,
                'module_id': module_id,
                'operation': operation,
                'message': f'成功放置模块: {module_name} 在位置 ({x}, {y})'
            }
            
        elif tool_name == 'connect_modules':
            # 校验必要参数 - 支持两种参数命名方式
            required_params = ['start_module_id', 'start_port_index', 'end_module_id', 'end_port_index']
            alt_params = ['source_module_id', 'source_port', 'target_module_id', 'target_port']
            
            # 检查是否使用的是备选参数名
            if 'source_module_id' in tool_args:
                # 转换为标准参数名
                tool_args['start_module_id'] = tool_args.pop('source_module_id')
                tool_args['start_port_index'] = tool_args.pop('source_port')
                tool_args['end_module_id'] = tool_args.pop('target_module_id')
                tool_args['end_port_index'] = tool_args.pop('target_port')
            
            # 校验参数
            for param in required_params:
                if param not in tool_args:
                    return {
                        'success': False,
                        'error': f'connect_modules工具缺少必要参数: {param}'
                    }
            
            # 3. 功能映射：connect_modules -> 调用连线接口
            # 生成连接ID
            link_id = f"link_{int(time.time() * 1000)}"
            # 创建操作对象
            # 直接使用标准参数名
            operation_args = {
                'start_module_id': tool_args.get('start_module_id'),
                'end_module_id': tool_args.get('end_module_id'),
                'start_port_index': tool_args.get('start_port_index'),
                'end_port_index': tool_args.get('end_port_index')
            }
            operation = {
                'id': f"op_{int(time.time() * 1000)}",
                'type': 'connect_modules',
                'args': operation_args,
                'link_id': link_id
            }
            
            # 更新统计信息
            global_workflow_stats['connections_added'] += 1
            global_workflow_stats['operations'].append(operation)
            
            return {
                'success': True,
                'link_id': link_id,
                'operation': operation,
                'message': f'成功连接模块 {tool_args.get("start_module_id")} 到 {tool_args.get("end_module_id")}'
            }
            
        elif tool_name == 'set_module_params':
            # 校验必要参数
            if 'module_id' not in tool_args or 'params' not in tool_args:
                return {
                    'success': False,
                    'error': 'set_module_params工具缺少必要参数: module_id, params'
                }
            
            # 3. 功能映射：set_params -> 修改节点配置
            # 创建操作对象
            operation = {
                'id': f"op_{int(time.time() * 1000)}",
                'type': 'set_module_params',
                'args': tool_args
            }
            
            # 更新统计信息
            global_workflow_stats['operations'].append(operation)
            
            return {
                'success': True,
                'operation': operation,
                'message': f'成功设置模块 {tool_args.get("module_id")} 的参数'
            }
        else:
            return {
                'success': False,
                'error': f'未知工具: {tool_name}'
            }
    except Exception as e:
        error_msg = str(e)
        log_message(f'工具执行失败: {error_msg}')
        return {
            'success': False,
            'error': error_msg
        }

# Agent循环 - 核心ReAct闭环
def agent_loop(user_prompt, task_id):
    """AI工作流Agent循环 - 实现ReAct闭环逻辑"""
    # 声明全局变量
    global global_workflow_stats
    
    # 1. 初始化
    settings = load_ai_workflow_settings()
    stream_buffer = ""
    
    # 重置工作流统计信息
    reset_workflow_stats()
    
    # 重新加载模块，确保包含最新的模块信息
    load_modules()
    
    # 模块名称映射 - 帮助AI理解常用的简化名称
    module_aliases = {
        'Checkpoint加载器': ['CheckPoint', 'checkpoint', 'Checkpoint Loader'],
        'CLIP文本编码模块': ['CLIP', 'clip', 'CLIP Encoder'],
        'CLIP文本编码器加载模块': ['CLIP Loader'],
        'VAE解码模块': ['VAE', 'vae', 'VAE Decoder'],
        'VAE图像编码模块': ['VAE Encoder'],
        'VAE解码器加载模块': ['VAE Loader'],
        'VAE重绘编码器模块': ['VAE Inpaint'],
        'K采样器模块': ['Sampler', 'K Sampler', 'sampler'],
        '空Latent张量生成模块': ['Latent', 'Empty Latent', 'latent'],
        '加载图像模块': ['Image', 'Load Image', 'image'],
        'user输入': ['User Input', 'user input'],
        '图片保存_显示模块': ['Save', 'Save Image', 'save'],
        '显示模块': ['Display', 'display'],
        '缓存模块': ['Cache', 'cache']
    }
    
    # 构建模块信息
    modules_info = "系统中可用的模块（括号内是别名，也可以使用）：\n\n"
    module_count = 0
    max_modules = 20  # 增加模块数量限制
    
    for module_name, module_params in loaded_modules.items():
        if module_count >= max_modules:
            modules_info += f"... 等其他 {len(loaded_modules) - max_modules} 个模块\n\n"
            break
            
        name = module_params.get('name', module_name)
        kind = module_params.get('kind', '处理模块')
        input_quantity = module_params.get('input_quantity', 0)
        output_quantity = module_params.get('output_quantity', 0)
        
        # 添加别名信息
        aliases = module_aliases.get(name, [])
        alias_str = f" (别名: {', '.join(aliases)})" if aliases else ""
        
        # 构建简洁的模块描述
        modules_info += f"- {name}{alias_str} ({kind}): 输入{input_quantity}，输出{output_quantity}\n"
        module_count += 1
    
    modules_info += "\n"
    modules_info += "重要提示：请使用完整的模块名称或别名来调用place_module工具！\n\n"
    
    # 构建用户提示
    user_prompt_template = settings.get('prompts', {}).get('user_prompt', '请根据以下需求创建一个工作流：{user_input}')
    user_prompt = user_prompt_template.format(user_input=user_prompt)
    
    # 构建完整提示词
    full_prompt = f"{modules_info}\n{user_prompt}"
    
    # 初始化对话历史
    conversation_history = [
        {"role": "system", "content": settings.get('prompts', {}).get('system_prompt', '')},
        {"role": "user", "content": full_prompt}
    ]
    
    # Agent循环 - ReAct闭环
    max_iterations = 20  # 增加迭代次数，确保有足够时间生成连接操作
    iteration = 0
    is_running = True
    
    while is_running and iteration < max_iterations:
        # 检查任务状态
        task_status = ai_workflow_tasks.get(task_id, {})
        if task_status.get('status') == 'stopped':
            yield json.dumps({'type': 'status', 'content': '任务已停止'})
            break
        
        iteration += 1
        
        try:
            # 2. 思考：决定下一步做什么
            log_message(f'[思考] 第{iteration}轮，分析用户请求和历史上下文')
            llm_response = interact_with_llm(json.dumps(conversation_history), settings, tools=ai_tools)
            
            if 'error' in llm_response:
                error_msg = llm_response['error']
                log_message(f'[错误] LLM交互失败: {error_msg}')
                yield json.dumps({'type': 'error', 'content': error_msg})
                break
            
            # 提取响应
            if llm_response.get('choices') and len(llm_response['choices']) > 0:
                choice = llm_response['choices'][0]
                message = choice.get('message', {})
                content = message.get('content', '')
                tool_calls = message.get('tool_calls', [])
                
                # 添加到对话历史
                conversation_history.append(message)
                
                # 3. 行动：执行决策
                if content:
                    # 流式输出文本
                    log_message(f'[行动] 生成文本内容')
                    yield json.dumps({'type': 'text', 'content': content})
                    stream_buffer += content
                
                if tool_calls:
                    for tool_call in tool_calls:
                        tool_id = tool_call.get('id')
                        tool_function = tool_call.get('function', {})
                        tool_name = tool_function.get('name')
                        tool_args = tool_function.get('arguments', {})
                        
                        # 执行工具调用
                        log_message(f'[行动] 执行工具调用: {tool_name}')
                        tool_result = execute_tool(tool_name, tool_args)
                        
                        # 4. 反馈：将工具执行结果吐回去让AI看到
                        log_message(f'[反馈] 工具执行结果: {tool_result}')
                        yield json.dumps({'type': 'tool_result', 'content': tool_result})
                        
                        # 构建工具调用结果
                        tool_result_message = {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": json.dumps(tool_result)
                        }
                        
                        # 添加到对话历史
                        conversation_history.append(tool_result_message)
                else:
                    # 没有工具调用，结束循环
                    log_message('[完成] 工作流生成完成')
                    # 返回工作流统计信息
                    global global_workflow_stats
                    yield json.dumps({
                        'type': 'workflow_stats',
                        'content': {
                            'modules_added': global_workflow_stats['modules_added'],
                            'connections_added': global_workflow_stats['connections_added'],
                            'operations': global_workflow_stats['operations']
                        }
                    })
                    yield json.dumps({'type': 'done', 'content': '工作流生成完成'})
                    is_running = False
            else:
                error_msg = 'LLM响应格式错误'
                log_message(f'[错误] {error_msg}')
                yield json.dumps({'type': 'error', 'content': error_msg})
                break
        except Exception as e:
            error_msg = str(e)
            log_message(f'[错误] Agent循环执行失败: {error_msg}')
            yield json.dumps({'type': 'error', 'content': error_msg})
            break

# 流式传输端点 - SSE协议实现
@app.route('/api/ai_workflow_stream', methods=['POST'])
def ai_workflow_stream():
    """AI工作流流式传输端点 - 实现SSE协议"""
    from flask import stream_with_context, Response
    
    try:
        log_message('收到AI工作流流式请求')
        data = request.json
        log_message(f'请求数据: {data}')
        user_message = data.get('message')
        
        if not user_message:
            log_message('缺少message参数')
            return jsonify({'error': '缺少message参数'}), 400
        
        # 生成任务ID
        task_id = f"task_{int(time.time() * 1000)}"
        log_message(f'生成任务ID: {task_id}')
        
        # 初始化任务状态
        ai_workflow_tasks[task_id] = {
            'status': 'running',
            'start_time': time.time()
        }
        log_message(f'初始化任务状态: {ai_workflow_tasks[task_id]}')
        
        # 流式生成 - 核心SSE逻辑
        def generate():
            try:
                log_message(f'开始Agent循环，任务ID: {task_id}')
                # 接入上面的agent_loop
                for token in agent_loop(user_message, task_id):
                    # 必须加上 "data: " 前缀和双换行结尾
                    # 确保yield出来的内容是字符串
                    sse_data = f'data: {token}\n\n'
                    log_message(f'生成SSE数据: {token}')
                    yield sse_data
            except Exception as e:
                log_message(f'Agent循环执行失败: {e}')
                import traceback
                traceback.print_exc()
                # 错误处理也必须遵循SSE格式
                error_token = json.dumps({"type": "error", "content": str(e)})
                yield f'data: {error_token}\n\n'
            finally:
                # 更新任务状态
                if task_id in ai_workflow_tasks:
                    ai_workflow_tasks[task_id]['status'] = 'finished'
                    log_message(f'更新任务状态为finished: {task_id}')
        
        log_message('返回流式响应')
        # 返回流式响应，设置正确的MIME类型
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
    except Exception as e:
        log_message(f'处理AI工作流流式请求失败: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# 处理AI工作流操作结果的API端点
@app.route('/api/ai_workflow/operation_result', methods=['POST'])
def ai_workflow_operation_result():
    """处理AI工作流操作结果"""
    try:
        data = request.json
        log_message(f'收到操作结果: {data}')
        return jsonify({'success': True, 'message': '操作结果已接收'})
    except Exception as e:
        log_message(f'处理操作结果失败: {e}')
        return jsonify({'error': str(e)}), 500

# 停止任务端点 - 状态与中断控制
@app.route('/api/ai_workflow_stop/<task_id>', methods=['POST'])
def ai_workflow_stop(task_id):
    """停止AI工作流任务 - 实现状态与中断控制逻辑"""
    try:
        if task_id in ai_workflow_tasks:
            # 一旦收到信号，立即修改task_status为Stopped
            ai_workflow_tasks[task_id]['status'] = 'stopped'
            log_message(f'任务已停止: {task_id}')
            return jsonify({'success': True, 'message': '任务已停止'})
        else:
            return jsonify({'error': '任务不存在'}), 404
    except Exception as e:
        error_msg = str(e)
        log_message(f'停止AI工作流任务失败: {error_msg}')
        return jsonify({'error': error_msg}), 500

# 日志记录函数
def log_message(message):
    """记录消息到日志文件"""
    import datetime
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}\n"
    
    # 写入日志文件
    with open('data.txt', 'a', encoding='utf-8') as f:
        f.write(log_entry)
    
    # 同时打印到控制台
    print(log_entry, end='')

if __name__ == '__main__':
    # 检查并在虚拟环境中重启
    if check_and_restart_in_venv():
        sys.exit(0)
    
    # 启动Flask服务器
    log_message('服务器启动中...')
    app.run(debug=False, host='0.0.0.0', port=5000)