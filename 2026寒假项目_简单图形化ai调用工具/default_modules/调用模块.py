#input_quantity=004
#variable_quantity=004
#userinput=F
#showingwindow_quantity=001
#inputtingwindow_quantity=000
#setting=T
#output_quantity=002
#time_late=1
#excitedbydata=F
#name=调用模块
#kind=调用模块
#variables_name=模型选择,提示词,上下文,对话
#output_name=生成结果,更新后的上下文

import time

# 模型调用函数
def call_model(model_params, merged_params, cancel_token=None):
    """
    调用AI模型生成结果
    
    参数:
    - model_params: 模型参数，包含模型选择等
    - merged_params: 合并后的所有参数，包含提示词、设置、上下文、对话历史等
    - cancel_token: 取消令牌，用于检测是否需要取消请求
    
    返回:
    - 生成结果
    """
    # 默认参数设置
    default_params = {
        'model_source': 'lmstudio',  # 默认模型来源
        'api_key': '',  # 默认API密钥
        'model': 'gpt-3.5-turbo',  # 默认模型
        'temperature': 0.7,  # 默认温度
        'max_tokens': 1000,  # 默认最大 token 数
        'timeout': 30,  # 默认超时时间
        'delay': 0,  # 默认延迟时间
        'context': '',  # 默认上下文
        'dialogue_history': [],  # 默认对话历史
        # 本地模型默认设置
        'lmstudio_host': 'http://localhost:1234',  # LM Studio默认地址
        'lmstudio_model': 'qwen3-4b-instruct-2507-abliterated'  # 默认本地模型
    }
    
    # 合并参数
    params = {**default_params, **merged_params}
    
    # 处理model_params是字符串的情况
    if isinstance(model_params, str):
        params['model_source'] = model_params
        print(f"处理字符串模型参数: {model_params}")
    elif isinstance(model_params, dict):
        params = {**params, **model_params}
        print(f"处理字典模型参数: {model_params}")
    
    print(f"最终参数: {params}")
    
    try:
        # 检查是否需要取消
        if cancel_token and cancel_token():
            raise Exception("请求已取消")
        
        # 提取参数
        model_source = params.get('model_source', 'lmstudio')
        # 处理空模型来源
        if not model_source:
            model_source = 'lmstudio'
        prompt = params.get('prompt', '')
        api_key = params.get('api_key', '')
        context = params.get('context', '')
        dialogue_history = params.get('dialogue_history', [])
        user_dialogue = params.get('dialogue', '')
        delay = params.get('delay', 0)
        # 本地模型设置
        local_llm_host = params.get('local_llm_host', 'http://localhost:11434')
        local_llm_model = params.get('local_llm_model', 'llama2')
        
        # 类型检查和转换
        if isinstance(delay, str):
            try:
                delay = float(delay)
            except ValueError:
                delay = 0
        
        # 处理延迟
        if delay > 0:
            # 检查是否需要取消
            if cancel_token and cancel_token():
                raise Exception("请求已取消")
            time.sleep(delay)
        
        # 构建完整的上下文
        full_context = context
        if dialogue_history:
            for dialogue in dialogue_history:
                if 'user' in dialogue:
                    full_context += f"\n用户: {dialogue['user']}"
                if 'ai' in dialogue:
                    full_context += f"\nAI: {dialogue['ai']}"
        # 添加用户提交的对话内容
        if user_dialogue:
            full_context += f"\n用户对话: {user_dialogue}"
        
        # 检查是否需要取消
        if cancel_token and cancel_token():
            raise Exception("请求已取消")
        
        # 根据模型来源生成结果
        if model_source == 'ChatAPI':
            # 模拟 ChatAPI 调用
            result = f"无法调用"
        elif model_source == 'ChatGLM':
            # 模拟 ChatGLM 调用
            result = f"无法调用"
        elif model_source == 'aliyun':
            # 模拟 阿里云 调用
            result = f"无法调用"
        elif model_source == 'baidu':
            # 模拟 百度云 调用
            result = f"无法调用"
        elif model_source == 'lmstudio':
            # 真正调用 LM Studio
            try:
                import requests
                import json
                
                # 构建LM Studio API请求
                lmstudio_host = params.get('lmstudio_host', 'http://localhost:1234')
                lmstudio_model = params.get('lmstudio_model', 'qwen3-4b-instruct-2507-abliterated.q5_k_s')
                
                # 构建请求数据
                messages = [
                    {"role": "system", "content": "You are a helpful assistant."}
                ]
                
                # 获取提示词
                prompt = params.get('prompt', '')
                print(f"构建LM Studio API请求，提示词: {prompt}, 上下文: {context}, 对话历史: {dialogue_history}, 用户对话: {user_dialogue}")
                
                # 添加提示词到messages
                if prompt:
                    # 检查prompt是否为字符串
                    if isinstance(prompt, str):
                        # 如果是字符串，添加为系统消息
                        messages.append({"role": "system", "content": f"提示词: {prompt}"})
                        print(f"添加提示词系统消息: {prompt}")
                
                # 添加上下文到messages
                if context:
                    # 检查context是否为字符串
                    if isinstance(context, str):
                        # 如果是字符串，直接添加为系统消息
                        messages.append({"role": "system", "content": f"上下文信息: {context}"})
                        print(f"添加上下文系统消息: {context}")
                    # 检查context是否为对话历史列表
                    elif isinstance(context, list):
                        # 如果是列表，添加为对话历史
                        for dialogue in context:
                            if isinstance(dialogue, dict):
                                if 'user' in dialogue:
                                    messages.append({"role": "user", "content": dialogue['user']})
                                    print(f"添加用户对话历史: {dialogue['user']}")
                                if 'ai' in dialogue:
                                    messages.append({"role": "assistant", "content": dialogue['ai']})
                                    print(f"添加AI对话历史: {dialogue['ai']}")
                
                # 添加对话历史到messages
                if dialogue_history:
                    # 检查dialogue_history是否为字符串
                    if isinstance(dialogue_history, str):
                        # 如果是字符串，添加为系统消息
                        messages.append({"role": "system", "content": f"对话历史: {dialogue_history}"})
                        print(f"添加对话历史系统消息: {dialogue_history}")
                    # 检查dialogue_history是否为列表
                    elif isinstance(dialogue_history, list):
                        # 如果是列表，添加为对话历史
                        for dialogue in dialogue_history:
                            if isinstance(dialogue, dict):
                                if 'user' in dialogue:
                                    messages.append({"role": "user", "content": dialogue['user']})
                                    print(f"添加用户对话历史: {dialogue['user']}")
                                if 'ai' in dialogue:
                                    messages.append({"role": "assistant", "content": dialogue['ai']})
                                    print(f"添加AI对话历史: {dialogue['ai']}")
                
                # 添加用户提交的对话内容
                if user_dialogue:
                    messages.append({"role": "user", "content": user_dialogue})
                    print(f"添加用户对话: {user_dialogue}")
                
                print(f"最终构建的messages: {messages}")
                
                # 构建payload
                payload = {
                    "model": lmstudio_model,
                    "messages": messages,
                    "temperature": params.get('temperature', 0.7),
                    "max_tokens": params.get('max_tokens', 1000)
                }
                
                # 添加可选参数
                if 'top_p' in params:
                    payload['top_p'] = params['top_p']
                if 'top_k' in params:
                    payload['top_k'] = params['top_k']
                if 'repetition_penalty' in params:
                    payload['repetition_penalty'] = params['repetition_penalty']
                if 'presence_penalty' in params:
                    payload['presence_penalty'] = params['presence_penalty']
                if 'frequency_penalty' in params:
                    payload['frequency_penalty'] = params['frequency_penalty']
                if 'stop_words' in params and params['stop_words']:
                    payload['stop'] = [word.strip() for word in params['stop_words'].split(',')]
                if 'seed' in params and params['seed'] > 0:
                    payload['seed'] = params['seed']
                
                print(f"构建的LM Studio API请求payload: {payload}")
                
                # 检查是否需要取消
                if cancel_token and cancel_token():
                    raise Exception("请求已取消")
                
                # 发送请求
                response = requests.post(
                    f"{lmstudio_host}/v1/chat/completions",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload)
                )
                
                # 处理响应
                if response.status_code == 200:
                    response_data = response.json()
                    result = response_data['choices'][0]['message']['content']
                else:
                    result = f"调用LM Studio失败: {response.status_code} - {response.text}"
            except Exception as e:
                # 调用失败时显示具体错误信息
                result = f"调用失败: {str(e)}"
                print(f"调用LM Studio时出错: {str(e)}")
        else:
            # 未知模型来源
            result = f"无法调用"
        
        return result
    except Exception as e:
        # 错误处理
        return f"调用模型失败: {str(e)}"

# 主函数
def execute(model_params, prompt_params, context_params, dialogue_params, settings=None, cancel_token=None):
    """
    执行模块逻辑
    
    参数:
    - model_params: 模型选择（包含模型选择等）
    - prompt_params: 提示词参数
    - context_params: 上下文参数（包含对话上下文）
    - dialogue_params: 对话参数（包含用户提交给大模型的内容）
    - settings: 额外的设置参数（从前端传递的完整设置）
    - cancel_token: 取消令牌，用于检测是否需要取消请求
    
    返回:
    - 生成结果（包含更新后的上下文和本次生成结果）
    """
    # 处理空参数
    if model_params is None:
        model_params = {}
    if prompt_params is None:
        prompt_params = {}
    if context_params is None:
        context_params = {}
    if dialogue_params is None:
        dialogue_params = {}
    if settings is None:
        settings = {}
    
    print(f"执行函数参数: model_params={model_params}, prompt_params={prompt_params}, context_params={context_params}, dialogue_params={dialogue_params}, settings={settings}")
    
    # 处理字符串参数
    if isinstance(model_params, str):
        model_params = {'model_source': model_params}
        print(f"处理字符串模型参数: {model_params}")
    if isinstance(prompt_params, str):
        prompt_params = {'prompt': prompt_params}
        print(f"处理字符串提示词参数: {prompt_params}")
    if isinstance(context_params, str):
        context_params = {'context': context_params}
        print(f"处理字符串上下文参数: {context_params}")
    if isinstance(dialogue_params, str):
        dialogue_params = {'dialogue': dialogue_params}
        print(f"处理字符串对话参数: {dialogue_params}")
    
    # 合并参数
    merged_params = {**model_params, **prompt_params, **context_params, **dialogue_params, **settings}
    print(f"合并后的参数: {merged_params}")
    
    # 处理上下文参数
    if context_params:
        # 应用默认值
        if 'default_model_source' in context_params and not model_params.get('model_source'):
            merged_params['model_source'] = context_params['default_model_source']
            print(f"应用默认模型来源: {context_params['default_model_source']}")
        if 'default_prompt' in context_params and not prompt_params.get('prompt'):
            merged_params['prompt'] = context_params['default_prompt']
            print(f"应用默认提示词: {context_params['default_prompt']}")
        if 'default_context' in context_params and not context_params.get('context'):
            merged_params['context'] = context_params['default_context']
            print(f"应用默认上下文: {context_params['default_context']}")
        if 'default_dialogue' in context_params and not dialogue_params.get('dialogue_history'):
            merged_params['dialogue_history'] = context_params['default_dialogue']
            print(f"应用默认对话: {context_params['default_dialogue']}")
        
        # 处理API密钥
        if 'api_key' in context_params:
            merged_params['api_key'] = context_params['api_key']
            print(f"应用API密钥")
        
        # 处理LM Studio设置
        if 'lmstudio_host' in context_params:
            merged_params['lmstudio_host'] = context_params['lmstudio_host']
            print(f"应用LM Studio主机地址: {context_params['lmstudio_host']}")
        if 'lmstudio_model' in context_params:
            merged_params['lmstudio_model'] = context_params['lmstudio_model']
            print(f"应用LM Studio模型: {context_params['lmstudio_model']}")
    
    # 直接从settings中获取LM Studio设置
    if 'lmstudio_host' in settings:
        merged_params['lmstudio_host'] = settings['lmstudio_host']
        print(f"从settings应用LM Studio主机地址: {settings['lmstudio_host']}")
    if 'lmstudio_model' in settings:
        merged_params['lmstudio_model'] = settings['lmstudio_model']
        print(f"从settings应用LM Studio模型: {settings['lmstudio_model']}")
    if 'model_source' in settings:
        merged_params['model_source'] = settings['model_source']
        print(f"从settings应用模型来源: {settings['model_source']}")
    
    # 提取上下文
    context = merged_params.get('context', '')
    print(f"提取的上下文: {context}")
    
    # 提取对话内容（用户提交给大模型的内容）
    user_dialogue = merged_params.get('dialogue_history', '') or merged_params.get('dialogue', '')
    print(f"提取的用户对话: {user_dialogue}")
    
    # 调用模型生成结果
    result = call_model(model_params, merged_params, cancel_token)
    
    # 构建更新后的上下文
    if context:
        updated_context = f"{context}\n用户: {user_dialogue}\nAI: {result}"
    else:
        updated_context = f"用户: {user_dialogue}\nAI: {result}"
    
    # 返回两个值，分别对应两个输出端口
    # 第一个值：本次的生成结果
    # 第二个值：添加了此轮对话的上下文
    return result, updated_context