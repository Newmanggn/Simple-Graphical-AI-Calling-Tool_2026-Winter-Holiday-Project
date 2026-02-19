# AI工作流开发完整指南：.aiud文件格式与JSON结构

## 1. 文档目的
本文档旨在全面指导AI开发者和系统开发团队了解、创建和管理`.aiud`压缩包文件中的`project.json`配置文件，以便实现图形化编程的自动化和模块化开发。通过本文档，开发者可以直接生成符合规范的工作流配置，同时系统开发团队可以参考本文档开发新的默认模块。

## 2. .aiud文件结构

`.aiud`文件是一个标准的ZIP压缩包，包含以下内容：

```
.aiud文件 (ZIP压缩)
├── project.json          # 项目配置文件（必需）
└── custom_modules/       # 自定义模块文件夹（可选）
    └── 自定义模块.py      # 自定义模块文件
```

## 3. project.json文件格式

### 3.1 基本结构

```json
{
  "version": "0.1",
  "modules": [],
  "connections": [],
  "canvasSize": {
    "width": 4000,
    "height": 3000
  },
  "timestamp": "2026-02-19T12:00:00Z",
  "usedCustomModules": []
}
```

### 3.2 核心字段说明

| 字段名 | 类型 | 必需 | 说明 |
|-------|------|------|------|
| version | 字符串 | 否 | 项目文件版本号，默认"0.1" |
| modules | 数组 | 是 | 模块配置数组 |
| connections | 数组 | 是 | 连接配置数组 |
| canvasSize | 对象 | 否 | 画布大小，默认{"width": 4000, "height": 3000} |
| timestamp | 字符串 | 否 | 保存时间戳，ISO格式 |
| usedCustomModules | 数组 | 否 | 使用的自定义模块名称列表 |

## 4. 模块配置 (modules)

### 4.1 单个模块结构

```json
{
  "id": "module_1",
  "name": "user输入",
  "kind": "输入模块",
  "left": "100px",
  "top": "100px",
  "moduleData": {
    "name": "user输入",
    "params": {
      "name": "user输入",
      "kind": "输入模块",
      "input_quantity": 0,
      "output_quantity": 1,
      "showingwindow_quantity": 0,
      "inputtingwindow_quantity": 0,
      "setting": false,
      "userinput": true,
      "time_late": 0,
      "excitedbydata": false,
      "variables_name": "",
      "output_name": "output"
    }
  },
  "settings": {},
  "inputValue": ""
}
```

### 4.2 模块参数说明

| 参数名 | 类型 | 说明 | 默认值 |
|-------|------|------|-------|
| id | 字符串 | 模块唯一标识符 | 必需 |
| name | 字符串 | 模块显示名称 | 必需 |
| kind | 字符串 | 模块类型 | 必需 |
| left | 字符串 | 模块在画布上的X坐标 | 必需 |
| top | 字符串 | 模块在画布上的Y坐标 | 必需 |
| moduleData | 对象 | 模块详细数据 | 必需 |
| settings | 对象 | 模块设置参数 | {} |
| inputValue | 字符串 | 模块输入值 | "" |

### 4.3 模块类型 (kind)

支持的模块类型：
- 输入模块
- 调用模块
- 处理模块
- 输出模块
- 自定义模块

### 4.4 常见模块配置示例

#### 4.4.1 固定值输出模块

```json
{
  "id": "module_1",
  "name": "固定值输出模块",
  "kind": "处理模块",
  "left": "100px",
  "top": "100px",
  "moduleData": {
    "name": "固定值输出模块",
    "params": {
      "name": "固定值输出模块",
      "kind": "处理模块",
      "input_quantity": 0,
      "output_quantity": 1,
      "showingwindow_quantity": 0,
      "inputtingwindow_quantity": 1,
      "setting": false,
      "userinput": true,
      "time_late": 0,
      "excitedbydata": false,
      "variables_name": "",
      "output_name": "output"
    }
  },
  "settings": {
    "inputtingwindow_quantity": 1
  },
  "inputValue": "默认值"
}
```

#### 4.4.2 调用模块

```json
{
  "id": "module_2",
  "name": "调用模块",
  "kind": "调用模块",
  "left": "300px",
  "top": "100px",
  "moduleData": {
    "name": "调用模块",
    "params": {
      "name": "调用模块",
      "kind": "调用模块",
      "input_quantity": 1,
      "output_quantity": 1,
      "showingwindow_quantity": 0,
      "inputtingwindow_quantity": 0,
      "setting": true,
      "userinput": false,
      "time_late": 0,
      "excitedbydata": false,
      "variables_name": "input",
      "output_name": "output"
    }
  },
  "settings": {
    "model": "gpt-4",
    "max_tokens": 1000,
    "temperature": 0.7
  },
  "inputValue": ""
}
```

#### 4.4.3 图像输出模块

```json
{
  "id": "module_3",
  "name": "图像输出模块",
  "kind": "输出模块",
  "left": "500px",
  "top": "100px",
  "moduleData": {
    "name": "图像输出模块",
    "params": {
      "name": "图像输出模块",
      "kind": "输出模块",
      "input_quantity": 1,
      "output_quantity": 0,
      "showingwindow_quantity": 0,
      "inputtingwindow_quantity": 0,
      "setting": true,
      "userinput": false,
      "time_late": 0,
      "excitedbydata": false,
      "variables_name": "image",
      "output_name": ""
    }
  },
  "settings": {
    "auto_download": false
  },
  "inputValue": ""
}
```

## 5. 连接配置 (connections)

### 5.1 单个连接结构

```json
{
  "startModuleId": "module_1",
  "startPortIndex": 0,
  "endModuleId": "module_2",
  "endPortIndex": 0,
  "isRed": false
}
```

### 5.2 连接参数说明

| 参数名 | 类型 | 说明 | 默认值 |
|-------|------|------|-------|
| startModuleId | 字符串 | 起始模块ID | 必需 |
| startPortIndex | 整数 | 起始模块输出端口索引 | 必需 |
| endModuleId | 字符串 | 目标模块ID | 必需 |
| endPortIndex | 整数 | 目标模块输入端口索引 | 必需 |
| isRed | 布尔值 | 是否为红线（强制激活） | false |

### 5.3 连接规则

1. 每个连接必须连接一个源模块的输出端口和一个目标模块的输入端口
2. 一个输出端口可以连接到多个输入端口（一连多）
3. 一个输入端口可以接收多个输出端口的连接（多连一），此时使用最后接收到的值

## 6. 工作流示例

### 6.1 简单文本处理工作流

```json
{
  "version": "0.1",
  "modules": [
    {
      "id": "input_1",
      "name": "user输入",
      "kind": "输入模块",
      "left": "100px",
      "top": "100px",
      "moduleData": {
        "name": "user输入",
        "params": {
          "name": "user输入",
          "kind": "输入模块",
          "input_quantity": 0,
          "output_quantity": 1,
          "showingwindow_quantity": 0,
          "inputtingwindow_quantity": 0,
          "setting": false,
          "userinput": true,
          "time_late": 0,
          "excitedbydata": false,
          "variables_name": "",
          "output_name": "output"
        }
      },
      "settings": {},
      "inputValue": ""
    },
    {
      "id": "call_1",
      "name": "调用模块",
      "kind": "调用模块",
      "left": "300px",
      "top": "100px",
      "moduleData": {
        "name": "调用模块",
        "params": {
          "name": "调用模块",
          "kind": "调用模块",
          "input_quantity": 1,
          "output_quantity": 1,
          "showingwindow_quantity": 0,
          "inputtingwindow_quantity": 0,
          "setting": true,
          "userinput": false,
          "time_late": 0,
          "excitedbydata": false,
          "variables_name": "input",
          "output_name": "output"
        }
      },
      "settings": {
        "model": "gpt-3.5-turbo",
        "temperature": 0.7
      },
      "inputValue": ""
    },
    {
      "id": "output_1",
      "name": "对话输出",
      "kind": "输出模块",
      "left": "500px",
      "top": "100px",
      "moduleData": {
        "name": "对话输出",
        "params": {
          "name": "对话输出",
          "kind": "输出模块",
          "input_quantity": 1,
          "output_quantity": 0,
          "showingwindow_quantity": 0,
          "inputtingwindow_quantity": 0,
          "setting": false,
          "userinput": false,
          "time_late": 0,
          "excitedbydata": false,
          "variables_name": "input",
          "output_name": ""
        }
      },
      "settings": {},
      "inputValue": ""
    }
  ],
  "connections": [
    {
      "startModuleId": "input_1",
      "startPortIndex": 0,
      "endModuleId": "call_1",
      "endPortIndex": 0,
      "isRed": false
    },
    {
      "startModuleId": "call_1",
      "startPortIndex": 0,
      "endModuleId": "output_1",
      "endPortIndex": 0,
      "isRed": false
    }
  ],
  "canvasSize": {
    "width": 4000,
    "height": 3000
  },
  "timestamp": "2026-02-19T12:00:00Z",
  "usedCustomModules": []
}
```

### 6.2 文本到图像工作流

```json
{
  "version": "0.1",
  "modules": [
    {
      "id": "input_1",
      "name": "user输入",
      "kind": "输入模块",
      "left": "100px",
      "top": "100px",
      "moduleData": {
        "name": "user输入",
        "params": {
          "name": "user输入",
          "kind": "输入模块",
          "input_quantity": 0,
          "output_quantity": 1,
          "showingwindow_quantity": 0,
          "inputtingwindow_quantity": 0,
          "setting": false,
          "userinput": true,
          "time_late": 0,
          "excitedbydata": false,
          "variables_name": "",
          "output_name": "output"
        }
      },
      "settings": {},
      "inputValue": "一只可爱的小猫"
    },
    {
      "id": "clip_1",
      "name": "CLIP文本编码器加载模块",
      "kind": "处理模块",
      "left": "100px",
      "top": "200px",
      "moduleData": {
        "name": "CLIP文本编码器加载模块",
        "params": {
          "name": "CLIP文本编码器加载模块",
          "kind": "处理模块",
          "input_quantity": 0,
          "output_quantity": 1,
          "showingwindow_quantity": 0,
          "inputtingwindow_quantity": 0,
          "setting": false,
          "userinput": false,
          "time_late": 0,
          "excitedbydata": false,
          "variables_name": "",
          "output_name": "output"
        }
      },
      "settings": {},
      "inputValue": ""
    },
    {
      "id": "encode_1",
      "name": "正面提示词编码模块",
      "kind": "处理模块",
      "left": "300px",
      "top": "150px",
      "moduleData": {
        "name": "正面提示词编码模块",
        "params": {
          "name": "正面提示词编码模块",
          "kind": "处理模块",
          "input_quantity": 2,
          "output_quantity": 1,
          "showingwindow_quantity": 0,
          "inputtingwindow_quantity": 0,
          "setting": false,
          "userinput": false,
          "time_late": 0,
          "excitedbydata": false,
          "variables_name": "text,clip",
          "output_name": "output"
        }
      },
      "settings": {},
      "inputValue": ""
    },
    {
      "id": "latent_1",
      "name": "空Latent张量生成模块",
      "kind": "处理模块",
      "left": "300px",
      "top": "300px",
      "moduleData": {
        "name": "空Latent张量生成模块",
        "params": {
          "name": "空Latent张量生成模块",
          "kind": "处理模块",
          "input_quantity": 0,
          "output_quantity": 1,
          "showingwindow_quantity": 0,
          "inputtingwindow_quantity": 0,
          "setting": true,
          "userinput": false,
          "time_late": 0,
          "excitedbydata": false,
          "variables_name": "",
          "output_name": "output"
        }
      },
      "settings": {
        "width": 512,
        "height": 512
      },
      "inputValue": ""
    },
    {
      "id": "sampler_1",
      "name": "K采样器模块",
      "kind": "处理模块",
      "left": "500px",
      "top": "200px",
      "moduleData": {
        "name": "K采样器模块",
        "params": {
          "name": "K采样器模块",
          "kind": "处理模块",
          "input_quantity": 2,
          "output_quantity": 1,
          "showingwindow_quantity": 0,
          "inputtingwindow_quantity": 0,
          "setting": true,
          "userinput": false,
          "time_late": 0,
          "excitedbydata": false,
          "variables_name": "latent,prompt",
          "output_name": "output"
        }
      },
      "settings": {
        "steps": 20,
        "cfg": 7.0
      },
      "inputValue": ""
    },
    {
      "id": "vae_1",
      "name": "VAE解码器加载模块",
      "kind": "处理模块",
      "left": "500px",
      "top": "350px",
      "moduleData": {
        "name": "VAE解码器加载模块",
        "params": {
          "name": "VAE解码器加载模块",
          "kind": "处理模块",
          "input_quantity": 0,
          "output_quantity": 1,
          "showingwindow_quantity": 0,
          "inputtingwindow_quantity": 0,
          "setting": false,
          "userinput": false,
          "time_late": 0,
          "excitedbydata": false,
          "variables_name": "",
          "output_name": "output"
        }
      },
      "settings": {},
      "inputValue": ""
    },
    {
      "id": "decode_1",
      "name": "VAE解码模块",
      "kind": "处理模块",
      "left": "700px",
      "top": "250px",
      "moduleData": {
        "name": "VAE解码模块",
        "params": {
          "name": "VAE解码模块",
          "kind": "处理模块",
          "input_quantity": 2,
          "output_quantity": 1,
          "showingwindow_quantity": 0,
          "inputtingwindow_quantity": 0,
          "setting": false,
          "userinput": false,
          "time_late": 0,
          "excitedbydata": false,
          "variables_name": "latent,vae",
          "output_name": "output"
        }
      },
      "settings": {},
      "inputValue": ""
    },
    {
      "id": "image_1",
      "name": "图像输出模块",
      "kind": "输出模块",
      "left": "900px",
      "top": "250px",
      "moduleData": {
        "name": "图像输出模块",
        "params": {
          "name": "图像输出模块",
          "kind": "输出模块",
          "input_quantity": 1,
          "output_quantity": 0,
          "showingwindow_quantity": 0,
          "inputtingwindow_quantity": 0,
          "setting": true,
          "userinput": false,
          "time_late": 0,
          "excitedbydata": false,
          "variables_name": "image",
          "output_name": ""
        }
      },
      "settings": {
        "auto_download": false
      },
      "inputValue": ""
    }
  ],
  "connections": [
    {
      "startModuleId": "input_1",
      "startPortIndex": 0,
      "endModuleId": "encode_1",
      "endPortIndex": 0,
      "isRed": false
    },
    {
      "startModuleId": "clip_1",
      "startPortIndex": 0,
      "endModuleId": "encode_1",
      "endPortIndex": 1,
      "isRed": false
    },
    {
      "startModuleId": "encode_1",
      "startPortIndex": 0,
      "endModuleId": "sampler_1",
      "endPortIndex": 1,
      "isRed": false
    },
    {
      "startModuleId": "latent_1",
      "startPortIndex": 0,
      "endModuleId": "sampler_1",
      "endPortIndex": 0,
      "isRed": false
    },
    {
      "startModuleId": "sampler_1",
      "startPortIndex": 0,
      "endModuleId": "decode_1",
      "endPortIndex": 0,
      "isRed": false
    },
    {
      "startModuleId": "vae_1",
      "startPortIndex": 0,
      "endModuleId": "decode_1",
      "endPortIndex": 1,
      "isRed": false
    },
    {
      "startModuleId": "decode_1",
      "startPortIndex": 0,
      "endModuleId": "image_1",
      "endPortIndex": 0,
      "isRed": false
    }
  ],
  "canvasSize": {
    "width": 4000,
    "height": 3000
  },
  "timestamp": "2026-02-19T12:00:00Z",
  "usedCustomModules": []
}
```

## 5. 生成规则与最佳实践

### 5.1 模块ID生成
- 模块ID必须唯一
- 建议使用有意义的命名，如`input_1`、`call_2`等
- 避免使用特殊字符和空格

### 5.2 坐标设置
- 模块坐标应合理分布，避免重叠
- 建议使用相对坐标，如`100px`、`200px`
- 水平间距建议为200px，垂直间距建议为150px

### 5.3 连接规则
- 确保连接的模块ID存在
- 端口索引应在有效范围内（从0开始）
- 红线(`isRed: true`)用于强制激活目标模块，适用于需要立即执行的场景

### 5.4 模块配置
- 根据模块类型设置正确的`input_quantity`和`output_quantity`
- 输入模块的`input_quantity`应为0
- 输出模块的`output_quantity`应为0
- 为模块添加适当的`variables_name`和`output_name`

### 5.5 布局最佳实践
1. 按照数据流向从左到右排列模块
2. 相关模块放在相近位置，便于连线和查看
3. 留出足够的空间用于连线，避免连线交叉过多
4. 为复杂工作流使用模块化布局，按功能分组

### 5.6 配置优化
1. 为每个模块设置合理的默认值，减少用户配置工作量
2. 使用描述性的模块名称和端口标签，便于理解数据流向
3. 对于复杂工作流，可使用缓存模块减少重复计算
4. 合理使用延迟执行(`time_late`)功能，优化执行顺序

### 5.7 错误处理
1. 确保所有必需的模块和连线都已配置
2. 检查模块端口类型是否匹配
3. 验证模块设置是否符合要求
4. 使用JSON验证工具检查配置文件格式

## 6. 版本兼容处理

### 6.1 字段默认值
当某些字段缺失时，系统会使用以下默认值：

| 字段 | 默认值 |
|------|-------|
| version | "0.1" |
| modules | [] |
| connections | [] |
| canvasSize | {"width": 4000, "height": 3000} |
| timestamp | 当前时间的ISO格式 |
| usedCustomModules | [] |

### 6.2 模块参数默认值
| 参数 | 默认值 |
|------|-------|
| input_quantity | 0 |
| output_quantity | 0 |
| showingwindow_quantity | 0 |
| inputtingwindow_quantity | 0 |
| setting | false |
| userinput | false |
| time_late | 0 |
| excitedbydata | false |
| variables_name | "" |
| output_name | "" |

## 7. 示例模板

### 7.1 基础工作流模板

```json
{
  "version": "0.1",
  "modules": [
    {
      "id": "input_1",
      "name": "user输入",
      "kind": "输入模块",
      "left": "100px",
      "top": "100px",
      "moduleData": {
        "name": "user输入",
        "params": {
          "name": "user输入",
          "kind": "输入模块",
          "input_quantity": 0,
          "output_quantity": 1,
          "showingwindow_quantity": 0,
          "inputtingwindow_quantity": 0,
          "setting": false,
          "userinput": true,
          "time_late": 0,
          "excitedbydata": false,
          "variables_name": "",
          "output_name": "output"
        }
      },
      "settings": {},
      "inputValue": ""
    },
    {
      "id": "output_1",
      "name": "对话输出",
      "kind": "输出模块",
      "left": "300px",
      "top": "100px",
      "moduleData": {
        "name": "对话输出",
        "params": {
          "name": "对话输出",
          "kind": "输出模块",
          "input_quantity": 1,
          "output_quantity": 0,
          "showingwindow_quantity": 0,
          "inputtingwindow_quantity": 0,
          "setting": false,
          "userinput": false,
          "time_late": 0,
          "excitedbydata": false,
          "variables_name": "input",
          "output_name": ""
        }
      },
      "settings": {},
      "inputValue": ""
    }
  ],
  "connections": [
    {
      "startModuleId": "input_1",
      "startPortIndex": 0,
      "endModuleId": "output_1",
      "endPortIndex": 0,
      "isRed": false
    }
  ],
  "canvasSize": {
    "width": 4000,
    "height": 3000
  },
  "timestamp": "{{当前时间ISO格式}}",
  "usedCustomModules": []
}
```

## 8. 故障排除

### 8.1 常见错误
1. **模块ID重复**：确保每个模块的ID唯一
2. **连接端口无效**：检查端口索引是否在有效范围内
3. **模块类型不匹配**：确保模块类型与输入/输出端口数量匹配
4. **JSON格式错误**：确保生成的JSON格式正确，无语法错误
5. **.aiud文件无法导入**：确保文件是有效的ZIP压缩包，内部包含正确的project.json文件

### 8.2 调试技巧
1. 从简单的工作流开始，逐步添加复杂度
2. 使用显示模块查看中间结果
3. 检查系统日志获取详细的执行信息
4. 验证每个模块的输入和输出数据
5. 使用JSON验证工具检查配置文件格式

### 8.3 验证方法
1. 使用JSON验证工具检查格式正确性
2. 确保所有必需字段都已填写
3. 检查模块ID和连接的一致性
4. 测试生成的文件是否可以正常加载
5. 验证工作流执行结果是否符合预期

## 9. 模块开发指南

### 9.1 模块结构

```python
# -*- coding: utf-8 -*-
"""
name: 模块名称
kind: 模块类型（输入模块/处理模块/输出模块/调用模块）
input_quantity: 输入端口数量
output_quantity: 输出端口数量
showingwindow_quantity: 显示窗口数量
inputtingwindow_quantity: 输入窗口数量
setting: 是否有设置界面
userinput: 是否有用户输入
"""

import json

def execute(*args, **kwargs):
    """
    模块执行函数
    参数：输入端口的数据
    返回值：输出端口的数据
    """
    # 执行逻辑
    return output_data

def get_user_input():
    """
    获取用户输入
    当userinput=True时需要实现
    """
    return "默认值"

def get_settings():
    """
    获取模块设置
    当setting=True时需要实现
    """
    return {
        "setting1": "value1",
        "setting2": "value2"
    }
```

### 9.2 模块开发步骤

1. **确定模块类型**：根据功能确定模块类型（输入/处理/输出/调用）
2. **设置模块参数**：配置端口数量、窗口数量等基本参数
3. **实现执行函数**：编写模块的核心逻辑
4. **添加用户输入**：如果需要，实现get_user_input()函数
5. **添加设置界面**：如果需要，实现get_settings()函数
6. **测试模块**：确保模块可以正常加载和执行
7. **文档化**：为模块添加详细的注释和文档

### 9.3 示例模块

#### 9.3.1 固定值输出模块

```python
# -*- coding: utf-8 -*-
"""
name: 固定值输出模块
kind: 处理模块
input_quantity: 0
output_quantity: 1
showingwindow_quantity: 0
inputtingwindow_quantity: 1
setting: false
userinput: true
"""

def execute():
    """
    执行固定值输出
    """
    return "固定值"

def get_user_input():
    """
    获取用户输入
    """
    return "默认值"
```

#### 9.3.2 简单加法模块

```python
# -*- coding: utf-8 -*-
"""
name: 加法模块
kind: 处理模块
input_quantity: 2
output_quantity: 1
showingwindow_quantity: 0
inputtingwindow_quantity: 0
setting: false
userinput: false
"""

def execute(a, b):
    """
    执行加法操作
    """
    try:
        return float(a) + float(b)
    except:
        return 0
```

#### 9.3.3 条件判断模块

```python
# -*- coding: utf-8 -*-
"""
name: 判断模块
kind: 处理模块
input_quantity: 1
output_quantity: 2
showingwindow_quantity: 0
inputtingwindow_quantity: 0
setting: false
userinput: false
"""

def execute(value):
    """
    执行判断操作
    """
    if value:
        return True, False
    else:
        return False, True
```

## 10. 总结

本文档提供了全面的指南，涵盖了以下内容：

1. **.aiud文件结构**：详细说明了工作流文件的结构和组成
2. **project.json格式**：提供了完整的配置文件格式和字段说明
3. **模块配置**：详细介绍了模块的结构、参数和配置方法
4. **连接配置**：说明了模块间连接的配置方法和规则
5. **工作流示例**：提供了简单文本处理和文本到图像的完整示例
6. **最佳实践**：分享了模块布局、配置优化和错误处理的最佳实践
7. **版本兼容性**：说明了系统的版本兼容处理机制
8. **故障排除**：提供了常见错误和调试技巧
9. **模块开发**：为开发团队提供了模块开发的详细指南和示例

通过遵循本文档的规范和最佳实践，AI和开发团队可以创建功能完整、结构清晰的工作流和模块，实现图形化编程的自动化和模块化开发。

当需要创建复杂工作流时，只需在基础模板上添加更多模块和连接，并根据具体需求配置模块参数即可。对于模块开发，遵循文档中的结构和示例，可以快速创建高质量的自定义模块。