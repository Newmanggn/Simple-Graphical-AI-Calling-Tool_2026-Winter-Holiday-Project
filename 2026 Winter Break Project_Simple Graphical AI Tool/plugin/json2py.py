#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 工作流转 Python 代码插件
基于 Python AST 的代码生成器
"""

import os
import ast
import astor


def topological_sort(modules, connections):
    """
    拓扑排序算法，计算模块执行顺序
    """
    module_ids = [m.get('id') for m in modules]
    
    # 构建依赖图
    dependencies = {}
    dependents = {}
    
    for module_id in module_ids:
        dependencies[module_id] = []
        dependents[module_id] = []
    
    for conn in connections:
        start_id = conn.get('startModuleId')
        end_id = conn.get('endModuleId')
        
        if start_id in dependencies and end_id in dependencies:
            if start_id not in dependencies[end_id]:
                dependencies[end_id].append(start_id)
            if end_id not in dependents[start_id]:
                dependents[start_id].append(end_id)
    
    # Kahn算法
    in_degree = {}
    for module_id in module_ids:
        in_degree[module_id] = len(dependencies.get(module_id, []))
    
    queue = []
    for module_id in module_ids:
        if in_degree.get(module_id, 0) == 0:
            queue.append(module_id)
    
    result = []
    while queue:
        module_id = queue.pop(0)
        result.append(module_id)
        
        for dependent_id in dependents.get(module_id, []):
            in_degree[dependent_id] -= 1
            if in_degree[dependent_id] == 0:
                queue.append(dependent_id)
    
    return result


def parse_module_params(module_path):
    """
    解析模块参数
    """
    params = {}
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#'):
                    line = line[1:].strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # 尝试转换为数字
                        if value.isdigit():
                            params[key] = int(value)
                        elif value.replace('.', '', 1).isdigit():
                            params[key] = float(value)
                        else:
                            params[key] = value
    except Exception:
        pass
    return params


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
    
    # 1. 第一步：收集模块信息并建立索引
    module_map = {}
    for module in modules:
        module_id = module.get('id')
        module_map[module_id] = module
    
    # 2. 第二步：拓扑排序，计算执行顺序
    execution_order = topological_sort(modules, connections)
    
    # 3. 第三步：构建AST节点
    body = []
    
    # 添加文件头
    body.append(ast.Expr(
        value=ast.Constant(value='图形化编程生成的Python代码\n\n功能: 根据图形化编程工作流自动生成的代码')
    ))
    
    # 模块ID到变量名的映射 - 直接用序号，简单且安全
    module_id_to_var = {}
    for idx, module_id in enumerate(execution_order):
        var_name = f'module_{idx + 1}'
        module_id_to_var[module_id] = var_name
    
    # 4. 第四步：收集所有需要的模块源代码并提取execute函数
    # 先记录哪些模块已经被添加，避免重复
    added_module_files = set()
    module_func_map = {}  # 模块ID -> 函数名
    
    for module_id in execution_order:
        module = module_map.get(module_id, {})
        module_data = module.get('moduleData', {})
        module_file_name = module_data.get('name')
        
        if not module_file_name:
            continue
        
        # 读取模块源代码
        module_source = None
        module_path = None
        
        if os.path.exists(os.path.join(default_modules_dir, f'{module_file_name}.py')):
            module_path = os.path.join(default_modules_dir, f'{module_file_name}.py')
        elif os.path.exists(os.path.join(custom_modules_dir, f'{module_file_name}.py')):
            module_path = os.path.join(custom_modules_dir, f'{module_file_name}.py')
        
        if module_path and os.path.exists(module_path):
            with open(module_path, 'r', encoding='utf-8') as f:
                module_source = f.read()
        
        if module_source:
            # 解析模块源代码，提取execute函数
            try:
                tree = ast.parse(module_source)
                
                # 查找execute函数
                execute_func = None
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == 'execute':
                        execute_func = node
                        break
                
                if execute_func:
                    # 重命名函数
                    func_name = f'execute_{module_id_to_var[module_id]}'
                    execute_func.name = func_name
                    module_func_map[module_id] = func_name
                    
                    # 只添加一次这个模块的代码
                    if module_file_name not in added_module_files:
                        # 添加模块注释
                        body.append(ast.Expr(
                            value=ast.Constant(value=f'模块: {module.get("name", "unknown")}')
                        ))
                        
                        # 添加这个函数到AST
                        body.append(execute_func)
                        added_module_files.add(module_file_name)
            
            except Exception as e:
                print(f'解析模块 {module_file_name} 失败: {e}')
    
    # 5. 第五步：生成全局设置变量
    for module_id in execution_order:
        module = module_map.get(module_id, {})
        settings = module.get('settings', {})
        
        if settings:
            module_data = module.get('moduleData', {})
            params = module_data.get('params', {})
            variables_name = params.get('variables_name', '')
            input_quantity = params.get('input_quantity', 0)
            
            var_names = [v.strip() for v in variables_name.split(',') if v.strip()]
            setting_names = var_names[input_quantity:] if input_quantity < len(var_names) else []
            
            var_name = module_id_to_var.get(module_id, 'module')
            
            # 生成设置变量
            setting_entries = list(settings.items())
            for idx, (key, value) in enumerate(setting_entries):
                param_name = None
                if idx < len(setting_names):
                    param_name = setting_names[idx]
                else:
                    param_name = key.replace(' ', '_').replace('-', '_')
                
                if param_name:
                    safe_param_name = param_name.replace(' ', '_').replace('-', '_')
                    setting_var_name = f'SETTING_{var_name}_{safe_param_name}'
                    
                    # 处理值
                    ast_value = None
                    if isinstance(value, str):
                        lower_value = value.lower()
                        if lower_value == 'true':
                            ast_value = ast.Constant(value=True)
                        elif lower_value == 'false':
                            ast_value = ast.Constant(value=False)
                        else:
                            ast_value = ast.Constant(value=value)
                    elif isinstance(value, bool):
                        ast_value = ast.Constant(value=value)
                    elif isinstance(value, int):
                        ast_value = ast.Constant(value=value)
                    elif isinstance(value, float):
                        ast_value = ast.Constant(value=value)
                    else:
                        ast_value = ast.Constant(value=str(value))
                    
                    body.append(ast.Assign(
                        targets=[ast.Name(id=setting_var_name, ctx=ast.Store())],
                        value=ast_value
                    ))
    
    # 6. 第六步：生成主函数
    main_args = []
    
    # 收集用户输入和固定值输出模块作为参数
    user_input_idx = 1
    fixed_value_idx = 1
    
    for module_id in execution_order:
        module = module_map.get(module_id, {})
        module_name = module.get('name', '')
        
        if module_name == 'user输入':
            arg_idx = len([m for m in main_args if m.arg.startswith('user_input')]) + 1
            main_args.append(ast.arg(arg=f'user_input_{arg_idx}', annotation=None))
        elif module_name == '固定值输出模块':
            arg_idx = len([m for m in main_args if m.arg.startswith('fixed_value')]) + 1
            main_args.append(ast.arg(arg=f'fixed_value_{arg_idx}', annotation=None))
    
    main_body = []
    
    # 添加 module_outputs 字典
    main_body.append(ast.Assign(
        targets=[ast.Name(id='module_outputs', ctx=ast.Store())],
        value=ast.Dict(keys=[], values=[])
    ))
    
    # 处理用户输入和固定值输出模块
    user_input_idx = 1
    fixed_value_idx = 1
    
    for module_id in execution_order:
        module = module_map.get(module_id, {})
        module_name = module.get('name', '')
        
        if module_name == 'user输入':
            main_body.append(ast.Assign(
                targets=[
                    ast.Subscript(
                        value=ast.Name(id='module_outputs', ctx=ast.Load()),
                        slice=ast.Constant(value=module_id),
                        ctx=ast.Store()
                    )
                ],
                value=ast.List(
                    elts=[ast.Name(id=f'user_input_{user_input_idx}', ctx=ast.Load())],
                    ctx=ast.Load()
                )
            ))
            user_input_idx += 1
        elif module_name == '固定值输出模块':
            main_body.append(ast.Assign(
                targets=[
                    ast.Subscript(
                        value=ast.Name(id='module_outputs', ctx=ast.Load()),
                        slice=ast.Constant(value=module_id),
                        ctx=ast.Store()
                    )
                ],
                value=ast.List(
                    elts=[ast.Name(id=f'fixed_value_{fixed_value_idx}', ctx=ast.Load())],
                    ctx=ast.Load()
                )
            ))
            fixed_value_idx += 1
    
    # 按顺序调用模块
    for module_id in execution_order:
        module = module_map.get(module_id, {})
        module_name = module.get('name', '')
        
        if module_name in ('user输入', '固定值输出模块'):
            continue
        
        func_name = module_func_map.get(module_id)
        if not func_name:
            continue
        
        # 收集输入参数
        module_data = module.get('moduleData', {})
        params = module_data.get('params', {})
        input_quantity = params.get('input_quantity', 0)
        variable_quantity = params.get('variable_quantity', 0)
        variables_name = params.get('variables_name', '')
        
        var_names = [v.strip() for v in variables_name.split(',') if v.strip()]
        
        call_args = []
        
        # 处理输入端口
        for i in range(input_quantity):
            # 找到连接到这个端口的连接
            found = False
            for conn in connections:
                if conn.get('endModuleId') == module_id and conn.get('endPortIndex') == i:
                    start_module_id = conn.get('startModuleId')
                    start_port_idx = conn.get('startPortIndex', 0)
                    
                    call_args.append(
                        ast.Subscript(
                            value=ast.Subscript(
                                value=ast.Name(id='module_outputs', ctx=ast.Load()),
                                slice=ast.Constant(value=start_module_id),
                                ctx=ast.Load()
                            ),
                            slice=ast.Constant(value=start_port_idx),
                            ctx=ast.Load()
                        )
                    )
                    found = True
                    break
            
            if not found:
                call_args.append(ast.Constant(value=None))
        
        # 处理设置参数
        var_name = module_id_to_var.get(module_id, 'module')
        setting_entries = list(module.get('settings', {}).items())
        
        for i in range(input_quantity, variable_quantity):
            param_idx = i - input_quantity
            param_name = None
            if i < len(var_names):
                param_name = var_names[i]
            elif param_idx < len(setting_entries):
                param_name = setting_entries[param_idx][0]
            
            if param_name:
                safe_param_name = param_name.replace(' ', '_').replace('-', '_')
                setting_var_name = f'SETTING_{var_name}_{safe_param_name}'
                call_args.append(ast.Name(id=setting_var_name, ctx=ast.Load()))
            else:
                call_args.append(ast.Constant(value=None))
        
        # 生成调用语句
        result_var = f'result_{module_id_to_var.get(module_id, "module")}'
        
        main_body.append(ast.Assign(
            targets=[ast.Name(id=result_var, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Name(id=func_name, ctx=ast.Load()),
                args=call_args,
                keywords=[]
            )
        ))
        
        # 处理返回值：如果不是list/tuple，包装成list
        main_body.append(ast.If(
            test=ast.UnaryOp(
                op=ast.Not(),
                operand=ast.Call(
                    func=ast.Name(id='isinstance', ctx=ast.Load()),
                    args=[
                        ast.Name(id=result_var, ctx=ast.Load()),
                        ast.Tuple(
                            elts=[
                                ast.Name(id='list', ctx=ast.Load()),
                                ast.Name(id='tuple', ctx=ast.Load())
                            ],
                            ctx=ast.Load()
                        )
                    ],
                    keywords=[]
                )
            ),
            body=[
                ast.Assign(
                    targets=[ast.Name(id=result_var, ctx=ast.Store())],
                    value=ast.List(
                        elts=[ast.Name(id=result_var, ctx=ast.Load())],
                        ctx=ast.Load()
                    )
                )
            ],
            orelse=[]
        ))
        
        # 存储到 module_outputs
        main_body.append(ast.Assign(
            targets=[
                ast.Subscript(
                    value=ast.Name(id='module_outputs', ctx=ast.Load()),
                    slice=ast.Constant(value=module_id),
                    ctx=ast.Store()
                )
            ],
            value=ast.Name(id=result_var, ctx=ast.Load())
        ))
    
    # 返回最后一个模块的输出
    if execution_order:
        last_module_id = execution_order[-1]
        main_body.append(ast.Return(
            value=ast.Subscript(
                value=ast.Name(id='module_outputs', ctx=ast.Load()),
                slice=ast.Constant(value=last_module_id),
                ctx=ast.Load()
            )
        ))
    else:
        main_body.append(ast.Return(value=ast.Constant(value=None)))
    
    # 添加主函数
    main_func = ast.FunctionDef(
        name='main',
        args=ast.arguments(
            args=main_args,
            posonlyargs=[],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[]
        ),
        body=main_body,
        decorator_list=[],
        returns=None
    )
    body.append(main_func)
    
    # 7. 第七步：添加示例调用
    example_args = []
    for arg in main_args:
        arg_name = arg.arg
        if arg_name.startswith('user_input'):
            example_args.append(ast.Constant(value=f'用户输入{arg_name.split("_")[-1]}'))
        elif arg_name.startswith('fixed_value'):
            example_args.append(ast.Constant(value=f'固定值{arg_name.split("_")[-1]}'))
    
    if_body = []
    if_body.append(ast.Assign(
        targets=[ast.Name(id='result', ctx=ast.Store())],
        value=ast.Call(
            func=ast.Name(id='main', ctx=ast.Load()),
            args=example_args,
            keywords=[]
        )
    ))
    if_body.append(ast.Expr(
        value=ast.Call(
            func=ast.Name(id='print', ctx=ast.Load()),
            args=[
                ast.Constant(value='执行结果:'),
                ast.Name(id='result', ctx=ast.Load())
            ],
            keywords=[]
        )
    ))
    
    if_stmt = ast.If(
        test=ast.Compare(
            left=ast.Name(id='__name__', ctx=ast.Load()),
            ops=[ast.Eq()],
            comparators=[ast.Constant(value='__main__')]
        ),
        body=if_body,
        orelse=[]
    )
    body.append(if_stmt)
    
    # 构建完整的Module
    module = ast.Module(body=body, type_ignores=[])
    
    # 补全位置信息
    ast.fix_missing_locations(module)
    
    # 生成源代码
    try:
        source_code = astor.to_source(module)
    except ImportError:
        # 如果没有 astor，就用简单的方法
        import io
        import contextlib
        
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ast.dump(module, indent=2)
        source_code = buf.getvalue()
    
    return source_code


if __name__ == '__main__':
    # 测试代码
    print('JSON2Py 插件已加载')
