# Copy4bk - 自动复制最新版本APK文件工具

一个用于自动从源目录下的渠道目录中查找最新的APK文件并复制到目标目录的 Python 工具。

## 功能特性

- 📱 **自动查找APK文件**：从source目录下的渠道目录的release子目录中查找最新的apk文件
- 🎯 **文件名格式匹配**：自动匹配文件名格式 `butterknife-v2025.x.x-xxx.apk`
- 🔍 **自动识别最新版本**：根据文件修改时间自动识别release目录中的最新apk文件
- 📁 **渠道目录映射**：自动在目标目录中创建对应的渠道目录结构
- ⚠️ **特殊渠道处理**：full渠道特殊处理，复制到`target\test`目录
- ⚙️ **配置文件驱动**：通过配置文件管理源目录和目标目录，无需修改代码
- 🕒 **保留时间戳**：复制文件时保留原始文件的修改时间
- 📝 **详细日志**：显示每个渠道的处理过程和文件复制信息
- 🗑️ **清理旧文件**：可配置为自动清理目标目录中的旧文件，只保留最新版本
- 💬 **交互式替换**：遇到相同文件时询问是否替换（回车替换，Esc跳过）
- 🎯 **独立配置**：每个目标目录可单独配置清理选项

## 目录结构说明

工具从source目录下的渠道目录中查找APK文件：

```
source/
├── chf/
│   └── release/
│       └── butterknife-v2025.1.4-chf.apk  (最新文件)
├── cyb/
│   └── release/
│       └── butterknife-v2025.1.4-cyb.apk
├── full/
│   └── release/
│       └── butterknife-v2025.1.4-full.apk  (特殊处理)
└── ...
```

复制到target目录的结构：

```
target/
├── chf/
│   └── butterknife-v2025.1.4-chf.apk
├── cyb/
│   └── butterknife-v2025.1.4-cyb.apk
├── test/                    (full渠道特殊处理)
│   └── butterknife-v2025.1.4-full.apk
└── ...
```

## 使用方法

### 1. 环境要求

- Python 3.6 或更高版本
- 无需额外依赖包（使用 Python 标准库）

### 2. 配置设置

编辑 `copy4bk.txt` 配置文件，支持单个或多个目标目录：

#### 基础配置

```txt
# 源目录配置（包含渠道目录的根目录）
source=D:\work\AndroidProjects\butter-knife2\outputs

# 目标目录配置方式1：直接在target行配置（推荐）
# 使用 --clean_old true/false 格式，路径可以包含空格，无需引号
target=D:\work\AndroidProjects\butter-knife2\target --clean_old false
target=D:\Backup\butter-knife2 --clean_old true

# 如果路径包含空格，也无需引号，因为配置选项用 -- 前缀区分
# target=D:\My Backup Folder --clean_old true

# 目标目录配置方式2：使用注释行配置
# target=D:\Backup1 --clean_old true
# target=D:\Backup2 --clean_old false
```

#### 配置选项说明

- **clean_old**: 是否清理目标子目录中的旧文件
  - `--clean_old true`: 自动删除目标子目录中不在最新文件列表中的旧文件，只保留最新版本
  - `--clean_old false`: 不清理旧文件（默认值）

#### 文件替换策略

- 如果目标文件已存在，程序会交互式询问是否替换：
  - **回车**：替换已存在的文件
  - **Esc**：跳过该文件，不替换

#### 配置示例

```txt
# 示例1：直接在target行配置选项（推荐）
source=D:\work\AndroidProjects\butter-knife2\outputs
target=D:\work\AndroidProjects\butter-knife2\target --clean_old true
target=D:\Backup\butter-knife2 --clean_old false

# 示例2：使用注释行配置
source=D:\work\AndroidProjects\butter-knife2\outputs
# target=D:\Backup1 --clean_old true
# target=D:\Backup2 --clean_old false
```

## 工作流程

1. **遍历渠道目录**：从source目录下读取所有渠道目录（如 chf、cyb、full、local、wxg、zhk 等）
2. **查找release目录**：进入每个渠道目录下的`release`子目录
3. **匹配APK文件**：查找符合文件名格式 `butterknife-v2025.x.x-xxx.apk` 的文件
4. **选择最新文件**：根据文件修改时间选择最新的apk文件
5. **复制到目标目录**：
   - 普通渠道（如chf、cyb等）→ `target\渠道名\butterknife-v2025.x.x-xxx.apk`
   - full渠道（特殊处理）→ `target\test\butterknife-v2025.x.x-full.apk`

## 文件名格式要求

工具会查找符合以下格式的APK文件：
- 文件名格式：`butterknife-v2025.x.x-xxx.apk`
- 示例：`butterknife-v2025.1.4-chf.apk`、`butterknife-v2025.1.4-full.apk`

## 特殊渠道处理

- **full渠道**：会自动复制到 `target\test` 目录，而不是 `target\full` 目录

## 运行结果

程序运行时会显示：
- 每个渠道的处理状态
- 找到的最新apk文件信息
- 文件复制状态（已复制/已替换/已跳过）
- 文件的修改时间
- 源文件路径和目标文件路径

程序结束时会显示"按任意键退出…"，便于直接双击运行后查看日志。

### 打包

使用**pyinstaller**打包成exe文件，打开**PyCharm**的`Terminal`输入：

```shell
pyinstaller --onefile --name "Copy4bk-apk" --icon app.ico main.py
```

如果需要在exe文件名中添加版本号、版权、公司等版本信息，可以使用`--version-file`参数，例如：

```shell
pyinstaller --onefile --version-file version.txt --name "Copy4bk-apk" --icon app.ico main.py
```
