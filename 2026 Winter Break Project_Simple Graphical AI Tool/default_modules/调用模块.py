#input_quantity=004
#variable_quantity=006
#userinput=F
#showingwindow_quantity=001
#inputtingwindow_quantity=000
#setting=T
#output_quantity=002
#time_late=1
#excitedbydata=F
#name=调用模块
#kind=调用模块
#variables_name=模型选择,提示词,上下文,对话,服务商,模型ID,API密钥
#output_name=生成结果,更新后的上下文

import time
import json
import os

# 加载服务商配置
def load_service_providers():
    """
    加载Service_provider.json配置文件
    """
    service_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Service_provider.json")
    if os.path.exists(service_file):
        try:
            with open(service_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载Service_provider.json失败: {str(e)}")
            return {"service_providers": []}
    return {"service_providers": []}

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
        'service_provider': 'OpenAI',  # 默认服务商
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
        service_provider = params.get('service_provider', 'OpenAI')
        
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
        if model_source == 'lmstudio':
            # 真正调用 LM Studio
            try:
                import requests
                
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
                timeout = params.get('timeout', 30)
                response = requests.post(
                    f"{lmstudio_host}/v1/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=timeout
                )
                
                # 处理响应
                if response.status_code == 200:
                    response_data = response.json()
                    if 'choices' in response_data and len(response_data['choices']) > 0:
                        choice = response_data['choices'][0]
                        if 'message' in choice and 'content' in choice['message']:
                            result = choice['message']['content']
                        else:
                            result = f"响应格式错误: {response_data}"
                    else:
                        result = f"响应格式错误: {response_data}"
                else:
                    result = f"调用LM Studio失败: {response.status_code} - {response.text}"
            except Exception as e:
                # 调用失败时显示具体错误信息
                result = f"调用失败: {str(e)}"
                print(f"调用LM Studio时出错: {str(e)}")
        elif model_source == 'api':
            # 调用外部API
            try:
                import requests
                
                # 加载服务商配置
                service_config = load_service_providers()
                providers = service_config.get('service_providers', [])
                
                # 查找选中的服务商
                selected_provider = None
                for provider in providers:
                    if provider.get('name') == service_provider:
                        selected_provider = provider
                        break
                
                if not selected_provider:
                    return f"服务商 {service_provider} 未找到"
                
                # 获取API配置
                base_url = selected_provider.get('base_url')
                model = params.get('model', '')
                api_key = params.get('api_key', '')
                
                if not base_url:
                    return f"服务商 {service_provider} 未配置API地址"
                if not model:
                    return "请输入模型ID"
                if not api_key:
                    return "请输入API密钥"
                
                # 构建请求数据
                messages = [
                    {"role": "system", "content": "You are a helpful assistant."}
                ]
                
                # 添加提示词到messages
                if prompt:
                    if isinstance(prompt, str):
                        messages.append({"role": "system", "content": f"提示词: {prompt}"})
                
                # 添加上下文到messages
                if context:
                    if isinstance(context, str):
                        messages.append({"role": "system", "content": f"上下文信息: {context}"})
                    elif isinstance(context, list):
                        for dialogue in context:
                            if isinstance(dialogue, dict):
                                if 'user' in dialogue:
                                    messages.append({"role": "user", "content": dialogue['user']})
                                if 'ai' in dialogue:
                                    messages.append({"role": "assistant", "content": dialogue['ai']})
                
                # 添加对话历史到messages
                if dialogue_history:
                    if isinstance(dialogue_history, list):
                        for dialogue in dialogue_history:
                            if isinstance(dialogue, dict):
                                if 'user' in dialogue:
                                    messages.append({"role": "user", "content": dialogue['user']})
                                if 'ai' in dialogue:
                                    messages.append({"role": "assistant", "content": dialogue['ai']})
                
                # 添加用户对话
                if user_dialogue:
                    messages.append({"role": "user", "content": user_dialogue})
                
                # 构建payload
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": params.get('temperature', 0.7),
                    "max_tokens": params.get('max_tokens', 1000)
                }
                
                # 构建headers
                headers = {
                    "Content-Type": "application/json"
                }
                
                # 根据服务商设置API密钥
                if service_provider == 'OpenAI':
                    headers["Authorization"] = f"Bearer {api_key}"
                    endpoint = f"{base_url}/chat/completions"
                elif service_provider == 'Anthropic':
                    headers["x-api-key"] = api_key
                    headers["anthropic-version"] = "2023-06-01"
                    # 转换为Anthropic格式
                    payload = {
                        "model": model,
                        "messages": messages,
                        "temperature": params.get('temperature', 0.7),
                        "max_tokens": params.get('max_tokens', 1000)
                    }
                    endpoint = f"{base_url}/messages"
                elif service_provider == 'Google Gemini':
                    headers["Content-Type"] = "application/json"
                    # 转换为Gemini格式
                    contents = []
                    for msg in messages:
                        role = msg["role"]
                        content = msg["content"]
                        if role == "user":
                            contents.append({"role": "user", "parts": [{"text": content}]})
                        elif role == "assistant":
                            contents.append({"role": "model", "parts": [{"text": content}]})
                    payload = {
                        "contents": contents,
                        "temperature": params.get('temperature', 0.7),
                        "max_output_tokens": params.get('max_tokens', 1000)
                    }
                    endpoint = f"{base_url}/models/{model}:generateContent?key={api_key}"
                else:
                    # 默认OpenAI格式
                    headers["Authorization"] = f"Bearer {api_key}"
                    endpoint = f"{base_url}/chat/completions"
                
                print(f"构建API请求，服务商: {service_provider}, 端点: {endpoint}, 模型: {model}")
                print(f"请求数据: {payload}")
                
                # 检查是否需要取消
                if cancel_token and cancel_token():
                    raise Exception("请求已取消")
                
                # 发送请求
                timeout = params.get('timeout', 30)
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                
                # 处理响应
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # 根据服务商解析响应
                    if service_provider == 'Google Gemini':
                        # Gemini格式
                        if 'candidates' in response_data and len(response_data['candidates']) > 0:
                            candidate = response_data['candidates'][0]
                            if 'content' in candidate and 'parts' in candidate['content']:
                                parts = candidate['content']['parts']
                                content = ''.join([part.get('text', '') for part in parts])
                                result = content
                            else:
                                result = f"响应格式错误: {response_data}"
                        else:
                            result = f"响应格式错误: {response_data}"
                    elif service_provider == 'Anthropic':
                        # Anthropic格式
                        if 'content' in response_data and len(response_data['content']) > 0:
                            content_block = response_data['content'][0]
                            if 'text' in content_block:
                                result = content_block['text']
                            else:
                                result = f"响应格式错误: {response_data}"
                        else:
                            result = f"响应格式错误: {response_data}"
                    else:
                        # OpenAI格式
                        if 'choices' in response_data and len(response_data['choices']) > 0:
                            choice = response_data['choices'][0]
                            if 'message' in choice and 'content' in choice['message']:
                                result = choice['message']['content']
                            else:
                                result = f"响应格式错误: {response_data}"
                        else:
                            result = f"响应格式错误: {response_data}"
                else:
                    result = f"API调用失败: {response.status_code} - {response.text}"
            except Exception as e:
                result = f"API调用失败: {str(e)}"
                print(f"调用API时出错: {str(e)}")
        else:
            # 未知模型来源
            result = f"无法调用"
        
        return result
    except Exception as e:
        # 错误处理
        return f"调用模型失败: {str(e)}"

# 主函数
def execute(model_params, prompt_params, context_params, dialogue_params, service_params=None, model_id_params=None, api_key_params=None, settings=None, cancel_token=None):
    """
    执行模块逻辑
    
    参数:
    - model_params: 模型选择（包含模型选择等）
    - prompt_params: 提示词参数
    - context_params: 上下文参数（包含对话上下文）
    - dialogue_params: 对话参数（包含用户提交给大模型的内容）
    - service_params: 服务商参数（API模式下的服务商选择）
    - model_id_params: 模型ID参数（API模式下的模型ID）
    - api_key_params: API密钥参数（API模式下的API密钥）
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
    if service_params is None:
        service_params = {}
    if model_id_params is None:
        model_id_params = {}
    if api_key_params is None:
        api_key_params = {}
    if settings is None:
        settings = {}
    
    print(f"执行函数参数: model_params={model_params}, prompt_params={prompt_params}, context_params={context_params}, dialogue_params={dialogue_params}, service_params={service_params}, model_id_params={model_id_params}, api_key_params={api_key_params}, settings={settings}")
    
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
    if isinstance(service_params, str):
        service_params = {'service_provider': service_params}
        print(f"处理字符串服务商参数: {service_params}")
    if isinstance(model_id_params, str):
        model_id_params = {'model': model_id_params}
        print(f"处理字符串模型ID参数: {model_id_params}")
    if isinstance(api_key_params, str):
        api_key_params = {'api_key': api_key_params}
        print(f"处理字符串API密钥参数: {api_key_params}")
    
    # 合并参数
    merged_params = {**model_params, **prompt_params, **context_params, **dialogue_params, **service_params, **model_id_params, **api_key_params, **settings}
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
        if 'default_service_provider' in context_params and not service_params.get('service_provider'):
            merged_params['service_provider'] = context_params['default_service_provider']
            print(f"应用默认服务商: {context_params['default_service_provider']}")
        if 'default_model' in context_params and not model_id_params.get('model'):
            merged_params['model'] = context_params['default_model']
            print(f"应用默认模型ID: {context_params['default_model']}")
        if 'default_api_key' in context_params and not api_key_params.get('api_key'):
            merged_params['api_key'] = context_params['default_api_key']
            print(f"应用默认API密钥")
        
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
    
    # 直接从settings中获取设置
    if 'lmstudio_host' in settings:
        merged_params['lmstudio_host'] = settings['lmstudio_host']
        print(f"从settings应用LM Studio主机地址: {settings['lmstudio_host']}")
    if 'lmstudio_model' in settings:
        merged_params['lmstudio_model'] = settings['lmstudio_model']
        print(f"从settings应用LM Studio模型: {settings['lmstudio_model']}")
    if 'model_source' in settings:
        merged_params['model_source'] = settings['model_source']
        print(f"从settings应用模型来源: {settings['model_source']}")
    if 'service_provider' in settings:
        merged_params['service_provider'] = settings['service_provider']
        print(f"从settings应用服务商: {settings['service_provider']}")
    if 'model' in settings:
        merged_params['model'] = settings['model']
        print(f"从settings应用模型ID: {settings['model']}")
    if 'api_key' in settings:
        merged_params['api_key'] = settings['api_key']
        print(f"从settings应用API密钥")
    
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