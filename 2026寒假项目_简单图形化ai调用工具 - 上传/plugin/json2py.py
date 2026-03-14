#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 工作流转 Python 代码插件
使用简单可靠的字符串拼接方式生成代码
"""

import os
import json


def topological_sort(modules, connections):
    """
    拓扑排序算法，计算模块执行顺序
    """
    module_ids = [m.get('id') for m in modules]
    
    if not module_ids:
        return []
    
    in_degree = {mid: 0 for mid in module_ids}
    adjacency = {mid: [] for mid in module_ids}
    
    for conn in connections:
        start_id = conn.get('startModuleId')
        end_id = conn.get('endModuleId')
        
        if start_id in module_ids and end_id in module_ids:
            adjacency[start_id].append(end_id)
            in_degree[end_id] += 1
    
    temp_in_degree = in_degree.copy()
    
    queue = [mid for mid in module_ids if temp_in_degree[mid] == 0]
    result = []
    
    while queue:
        node = queue.pop(0)
        result.append(node)
        
        for neighbor in adjacency[node]:
            temp_in_degree[neighbor] -= 1
            if temp_in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    for mid in module_ids:
        if mid not in result:
            result.append(mid)
    
    return result


def read_module_file(module_name, default_modules_dir, custom_modules_dir):
    """
    读取模块文件
    """
    module_path = None
    
    if os.path.exists(os.path.join(default_modules_dir, f'{module_name}.py')):
        module_path = os.path.join(default_modules_dir, f'{module_name}.py')
    elif os.path.exists(os.path.join(custom_modules_dir, f'{module_name}.py')):
        module_path = os.path.join(custom_modules_dir, f'{module_name}.py')
    
    if module_path and os.path.exists(module_path):
        with open(module_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    return None


def extract_module_code(source_code):
    """
    从模块源代码中提取有用的代码部分
    去除顶部配置注释和底部说明文档
    """
    lines = source_code.split('\n')
    result_lines = []
    in_docstring = False
    
    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('#') and '=' in stripped and not stripped.startswith('#variables_name') and not stripped.startswith('#output_name'):
            continue
        
        if stripped.startswith('"""') or stripped.startswith("'''"):
            in_docstring = not in_docstring
            continue
        
        if not in_docstring:
            result_lines.append(line)
    
    return '\n'.join(result_lines)


def generate_python_code_from_workflow(workflow_data, default_modules_dir, custom_modules_dir):
    """
    从工作流数据生成 Python 代码
    
    参数:
    - workflow_data: 工作流字典，包含 modules 和 connections
    - default_modules_dir: 默认模块文件夹路径
    - custom_modules_dir: 自定义模块文件夹路径
    
    返回:
    - 生成的 Python 代码字符串
    """
    modules = workflow_data.get('modules', [])
    connections = workflow_data.get('connections', [])
    
    module_map = {m.get('id'): m for m in modules}
    
    execution_order = topological_sort(modules, connections)
    
    code_parts = []
    
    code_parts.append('#!/usr/bin/env python3')
    code_parts.append('# -*- coding: utf-8 -*-')
    code_parts.append('"""')
    code_parts.append('图形化编程生成的Python代码')
    code_parts.append('')
    code_parts.append('功能: 根据图形化编程工作流自动生成的代码')
    code_parts.append('"""')
    code_parts.append('')
    
    code_parts.append('import os')
    code_parts.append('import json')
    code_parts.append('import time')
    code_parts.append('import requests')
    code_parts.append('')
    
    module_id_to_func = {}
    module_id_to_name = {}
    
    added_modules = set()
    
    for module_id in execution_order:
        module = module_map.get(module_id, {})
        module_data = module.get('moduleData', {})
        module_name = module_data.get('name')
        module_display_name = module.get('name', 'unknown')
        
        if not module_name or module_id in added_modules:
            continue
        
        module_source = read_module_file(module_name, default_modules_dir, custom_modules_dir)
        
        if module_source:
            code_parts.append(f'# ========== 模块: {module_display_name} ==========')
            
            func_name = f'execute_{module_id.replace("-", "_")}'
            module_id_to_func[module_id] = func_name
            module_id_to_name[module_id] = module_name
            
            lines = module_source.split('\n')
            processed_lines = []
            in_config = True
            
            for line in lines:
                stripped = line.strip()
                
                if in_config:
                    if stripped.startswith('#') and '=' in stripped:
                        continue
                    elif stripped and not stripped.startswith('#'):
                        in_config = False
                
                if not in_config or not stripped.startswith('#') or '=' not in stripped:
                    processed_lines.append(line)
            
            module_code = '\n'.join(processed_lines)
            
            new_code_lines = []
            in_main = False
            
            for line in module_code.split('\n'):
                stripped = line.strip()
                if stripped.startswith('if __name__'):
                    in_main = True
                    continue
                if in_main:
                    continue
                new_code_lines.append(line)
            
            module_code = '\n'.join(new_code_lines)
            
            def find_execute_function_name(source):
                lines = source.split('\n')
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('def '):
                        func_name = stripped.split('(')[0][4:].strip()
                        if func_name in ['execute', 'run', 'process', 'main']:
                            return func_name
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('def '):
                        func_name = stripped.split('(')[0][4:].strip()
                        if not func_name.startswith('_'):
                            return func_name
                return None
            
            target_func_name = find_execute_function_name(module_code)
            
            if target_func_name:
                module_code = module_code.replace(f'def {target_func_name}(', f'def {func_name}(')
            
            code_parts.append(module_code)
            code_parts.append('')
            
            added_modules.add(module_id)
        else:
            code_parts.append(f'# ========== 模块: {module_display_name} (默认实现) ==========')
            func_name = f'execute_{module_id.replace("-", "_")}'
            module_id_to_func[module_id] = func_name
            module_id_to_name[module_id] = module_name
            
            code_parts.append(f'def {func_name}():')
            code_parts.append('    return None')
            code_parts.append('')
            
            added_modules.add(module_id)
    
    code_parts.append('# ========== 主函数 ==========')
    code_parts.append('')
    
    user_input_modules = []
    fixed_value_modules = []
    
    for module_id in execution_order:
        module = module_map.get(module_id, {})
        module_display_name = module.get('name', '')
        
        if module_display_name == 'user输入':
            user_input_modules.append(module_id)
        elif module_display_name == '固定值输出模块':
            fixed_value_modules.append(module_id)
    
    main_args = []
    for i, mid in enumerate(user_input_modules):
        main_args.append(f'user_input_{i+1}')
    for i, mid in enumerate(fixed_value_modules):
        main_args.append(f'fixed_value_{i+1}')
    
    if main_args:
        code_parts.append(f'def main({", ".join(main_args)}):')
    else:
        code_parts.append('def main():')
    
    code_parts.append('    module_outputs = {}')
    code_parts.append('')
    
    user_input_idx = 1
    fixed_value_idx = 1
    
    for module_id in execution_order:
        module = module_map.get(module_id, {})
        module_display_name = module.get('name', '')
        module_data = module.get('moduleData', {})
        params = module_data.get('params', {})
        input_quantity = params.get('input_quantity', 0)
        
        func_name = module_id_to_func.get(module_id)
        
        if module_display_name == 'user输入':
            code_parts.append(f'    # 模块: {module_display_name}')
            code_parts.append(f'    result_{module_id.replace("-", "_")} = {func_name}()')
            code_parts.append(f'    if not isinstance(result_{module_id.replace("-", "_")}, (list, tuple)):')
            code_parts.append(f'        result_{module_id.replace("-", "_")} = [result_{module_id.replace("-", "_")}]')
            code_parts.append(f'    module_outputs["{module_id}"] = result_{module_id.replace("-", "_")}')
            code_parts.append('')
            user_input_idx += 1
        
        elif module_display_name == '固定值输出模块':
            code_parts.append(f'    # 模块: {module_display_name}')
            code_parts.append(f'    _fixed_value = fixed_value_{fixed_value_idx}')
            code_parts.append(f'    result_{module_id.replace("-", "_")} = {func_name}()')
            code_parts.append(f'    if not isinstance(result_{module_id.replace("-", "_")}, (list, tuple)):')
            code_parts.append(f'        result_{module_id.replace("-", "_")} = [result_{module_id.replace("-", "_")}]')
            code_parts.append(f'    module_outputs["{module_id}"] = result_{module_id.replace("-", "_")}')
            code_parts.append('')
            fixed_value_idx += 1
        
        else:
            code_parts.append(f'    # 模块: {module_display_name}')
            
            call_args = []
            
            for i in range(input_quantity):
                found = False
                for conn in connections:
                    if conn.get('endModuleId') == module_id and conn.get('endPortIndex') == i:
                        start_module_id = conn.get('startModuleId')
                        start_port_idx = conn.get('startPortIndex', 0)
                        call_args.append(f'module_outputs["{start_module_id}"][{start_port_idx}]')
                        found = True
                        break
                if not found:
                    call_args.append('None')
            
            args_str = ', '.join(call_args)
            code_parts.append(f'    result_{module_id.replace("-", "_")} = {func_name}({args_str})')
            code_parts.append(f'    if not isinstance(result_{module_id.replace("-", "_")}, (list, tuple)):')
            code_parts.append(f'        result_{module_id.replace("-", "_")} = [result_{module_id.replace("-", "_")}]')
            code_parts.append(f'    module_outputs["{module_id}"] = result_{module_id.replace("-", "_")}')
            code_parts.append('')
    
    if execution_order:
        last_module_id = execution_order[-1]
        code_parts.append(f'    return module_outputs["{last_module_id}"]')
    else:
        code_parts.append('    return None')
    
    code_parts.append('')
    
    code_parts.append('# ========== 示例调用 ==========')
    code_parts.append('')
    code_parts.append("if __name__ == '__main__':")
    
    example_args = []
    for i in range(len(user_input_modules)):
        example_args.append(f"'用户输入{i+1}'")
    for i in range(len(fixed_value_modules)):
        example_args.append(f"'固定值{i+1}'")
    
    args_str = ', '.join(example_args)
    code_parts.append(f'    result = main({args_str})')
    code_parts.append("    print('执行结果:', result)")
    
    return '\n'.join(code_parts)


if __name__ == '__main__':
    print('JSON2Py 插件已加载')

