import os
import shutil
from pathlib import Path
from datetime import datetime
try:
    import msvcrt  # Windows: 支持任意键退出
except Exception:
    msvcrt = None


def print_intro():
    print("===============================")
    print(" Copy4bk - 自动复制最新版本APK文件工具")
    print("===============================")
    print("主要功能：")
    print("- 从source目录下的渠道目录的release子目录中查找最新的apk文件")
    print("- apk文件名格式：butterknife-v2025.x.x-xxx.apk")
    print("- 复制到target目录下的对应渠道目录")
    print("- full渠道特殊处理：复制到target\\test目录")
    print("- 支持多目标目录一次性复制")
    print("- 复制保留文件时间戳")
    print("- 详细日志输出，便于排查")
    print("")

def read_config(config_file='copy4bk-apk.txt'):
    """
    从配置文件中读取源目录和目标目录（支持多目标目录）
    支持格式：
    1) 键值对：source=路径；target=路径（可写多行）；targets=路径1,路径2
    2) 简单格式：第一行是源目录；之后每一行都是一个目标目录
    3) 注释行配置：支持 # target=路径 clean_old=true/false 格式
    """
    if not os.path.exists(config_file):
        print(f"配置文件不存在: {config_file}")
        return None, []

    source_dir = None
    target_configs = []  # 改为存储(target_dir, config_dict)的列表

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_target = None
        current_config = {}

        for raw_line in lines:
            line = raw_line.strip()
            
            # 跳过所有注释行（以 # 开头）
            if line.startswith('#'):
                # 处理注释行中的配置：支持 # target=路径 --clean_old true 格式
                if 'target=' in line:
                    # 从注释行解析配置，例如：# target=D:\Backup1 --clean_old true
                    comment_content = line[1:].strip()  # 去掉#号
                    # 查找 target= 的位置
                    target_idx = comment_content.find('target=')
                    if target_idx >= 0:
                        # 提取 target= 后面的部分
                        target_part = comment_content[target_idx + 6:].strip()  # 跳过 'target='
                        # 查找 -- 的位置，区分路径和配置选项
                        # 支持两种格式：' --clean_old' 或 '--clean_old'（前面可能有或没有空格）
                        double_dash_idx = target_part.find('--')
                        if double_dash_idx == -1:
                            # 没有找到 --，整个就是路径（兼容旧格式）
                            current_target = target_part.strip().strip('"').strip("'")
                            current_config = {}
                            # 检查是否有旧格式的配置（clean_old=true）
                            parts = target_part.split()
                            for part in parts[1:]:  # 跳过第一个（路径）
                                if '=' in part and 'clean_old=' in part:
                                    clean_old_val = part.split('=', 1)[1].strip().lower()
                                    current_config['clean_old'] = clean_old_val == 'true'
                                    # 从路径中移除配置部分
                                    current_target = parts[0].strip().strip('"').strip("'")
                        else:
                            # 找到了 --，分割路径和配置选项
                            # 从 -- 往前找，确定路径的结束位置（跳过空格）
                            path_end = double_dash_idx
                            while path_end > 0 and target_part[path_end - 1] == ' ':
                                path_end -= 1
                            current_target = target_part[:path_end].strip().strip('"').strip("'")
                            current_config = {}
                            options_str = target_part[double_dash_idx:].strip()  # 从 -- 开始
                            # 解析配置选项
                            parts = options_str.split()
                            i = 0
                            while i < len(parts):
                                if parts[i].startswith('--'):
                                    option_name = parts[i][2:].lower()
                                    if i + 1 < len(parts):
                                        option_value = parts[i + 1].lower()
                                        if option_name == 'clean_old':
                                            current_config['clean_old'] = option_value == 'true'
                                        i += 2
                                    else:
                                        i += 1
                                elif '=' in parts[i] and 'clean_old=' in parts[i]:
                                    # 兼容旧格式
                                    clean_old_val = parts[i].split('=', 1)[1].strip().lower()
                                    current_config['clean_old'] = clean_old_val == 'true'
                                    i += 1
                                else:
                                    i += 1
                        
                        if current_target:
                            # 查找是否已有该target的配置
                            found = False
                            for idx, (td, cfg) in enumerate(target_configs):
                                if td == current_target:
                                    # 更新现有配置
                                    target_configs[idx] = (current_target, {**cfg, **current_config})
                                    found = True
                                    break
                            if not found:
                                target_configs.append((current_target, current_config.copy()))
                        current_target = None
                        current_config = {}
                # 所有注释行（无论是否包含target=）都跳过，不继续处理
                continue
            
            if not line:
                continue
            
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip().lower()
                
                if key in ['源目录', 'source', '源路径', 'a目录', 'a']:
                    # 源目录直接取value，去掉引号
                    source_dir = value.strip().strip('"').strip("'")
                elif key in ['目标目录', 'target', '目标路径', 'b目录', 'b']:
                    # 处理 target=路径 --clean_old true 格式
                    # 使用 -- 前缀来区分配置选项，避免路径包含空格时的混淆
                    value = value.strip()
                    target_path = None
                    target_config = {}
                    
                    # 查找 -- 的位置，-- 之前的都是路径，之后的是配置选项
                    # 支持两种格式：' --clean_old' 或 '--clean_old'（前面可能有或没有空格）
                    double_dash_idx = value.find('--')
                    if double_dash_idx == -1:
                        # 没有找到 --，整个value就是路径
                        target_path = value.strip().strip('"').strip("'")
                    else:
                        # 找到了 --，分割路径和配置选项
                        # 从 -- 往前找，确定路径的结束位置（跳过空格）
                        path_end = double_dash_idx
                        while path_end > 0 and value[path_end - 1] == ' ':
                            path_end -= 1
                        target_path = value[:path_end].strip().strip('"').strip("'")
                        options_str = value[double_dash_idx:].strip()  # 从 -- 开始
                        
                        # 解析配置选项，格式：--clean_old true 或 --clean_old false
                        # 也兼容旧格式 clean_old=true（向后兼容）
                        parts = options_str.split()
                        i = 0
                        while i < len(parts):
                            if parts[i].startswith('--'):
                                # 新格式：--clean_old true
                                option_name = parts[i][2:].lower()  # 去掉 --
                                if i + 1 < len(parts):
                                    option_value = parts[i + 1].lower()
                                    if option_name == 'clean_old':
                                        target_config['clean_old'] = option_value == 'true'
                                    i += 2
                                else:
                                    i += 1
                            elif '=' in parts[i]:
                                # 旧格式：clean_old=true（向后兼容）
                                option_pair = parts[i].split('=', 1)
                                option_name = option_pair[0].strip().lower()
                                option_value = option_pair[1].strip().lower()
                                if option_name == 'clean_old':
                                    target_config['clean_old'] = option_value == 'true'
                                i += 1
                            else:
                                i += 1
                    
                    if target_path:
                        # 检查是否已有该target的配置
                        found = False
                        for idx, (td, cfg) in enumerate(target_configs):
                            if td == target_path:
                                # 合并配置
                                target_configs[idx] = (target_path, {**cfg, **target_config})
                                found = True
                                break
                        if not found:
                            target_configs.append((target_path, target_config))
                elif key in ['目标目录们', '目标列表', 'targets']:
                    # 多个目标目录，逗号/分号分隔
                    parts = [p.strip() for p in value.replace('；', ';').replace('，', ',').replace(';', ',').split(',')]
                    for p in parts:
                        if p:
                            found = False
                            for idx, (td, cfg) in enumerate(target_configs):
                                if td == p:
                                    found = True
                                    break
                            if not found:
                                target_configs.append((p, {}))
            else:
                # 简单格式：第一行为源目录，其余每行为一个目标目录
                if source_dir is None:
                    source_dir = line.strip().strip('"').strip("'")
                else:
                    target_val = line.strip().strip('"').strip("'")
                    found = False
                    for idx, (td, cfg) in enumerate(target_configs):
                        if td == target_val:
                            found = True
                            break
                    if not found:
                        target_configs.append((target_val, {}))

    except Exception as e:
        print(f"读取配置文件失败: {str(e)}")
        return None, []

    # 去重并保持顺序
    dedup_configs = []
    seen = set()
    for td, cfg in target_configs:
        if td not in seen:
            dedup_configs.append((td, cfg))
            seen.add(td)

    return source_dir, dedup_configs


def get_latest_apk_in_release(release_dir):
    """
    获取release目录中最新版本的apk文件
    文件名格式：butterknife-v2025.x.x-xxx.apk
    返回最新修改的apk文件路径，如果不存在则返回None
    """
    import re
    
    if not os.path.exists(release_dir):
        return None
    
    # 匹配文件名格式：butterknife-v2025.x.x-xxx.apk
    pattern = re.compile(r'^butterknife-v2025\.\d+\.\d+-.+\.apk$', re.IGNORECASE)
    
    apk_files = []
    for item in os.listdir(release_dir):
        item_path = os.path.join(release_dir, item)
        if os.path.isfile(item_path) and pattern.match(item):
            apk_files.append(item_path)
    
    if not apk_files:
        return None
    
    # 按修改时间排序，获取最新修改的文件
    files_with_time = [(f, os.path.getmtime(f)) for f in apk_files]
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    # 返回最新修改的文件
    return files_with_time[0][0]


def get_latest_files_in_dir(source_dir):
    """
    获取目录中最新版本的文件
    返回修改时间最新的文件列表
    """
    files = []
    if not os.path.exists(source_dir):
        return files
    
    for item in os.listdir(source_dir):
        item_path = os.path.join(source_dir, item)
        if os.path.isfile(item_path):
            files.append(item_path)
    
    if not files:
        return []
    
    # 按修改时间排序，获取最新修改的文件时间
    files_with_time = [(f, os.path.getmtime(f)) for f in files]
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    # 获取最新修改时间
    latest_time = files_with_time[0][1]
    
    # 返回所有具有最新修改时间的文件（可能有多个文件在同一时间修改）
    latest_files = [f for f, t in files_with_time if t == latest_time]
    
    return latest_files


def ask_replace_file(file_name):
    """
    交互式询问是否替换已存在的文件
    回车或任意非Esc的键：替换
    Esc：跳过
    """
    try:
        print(f"  文件已存在: {file_name}，是否替换？(回车=替换, Esc=跳过): ", end='', flush=True)
        if msvcrt is not None:
            # Windows环境
            key = msvcrt.getch()
            # 处理Windows的字节输入
            if isinstance(key, bytes):
                char_code = ord(key) if len(key) == 1 else key[0]
                if char_code == 27:  # Esc键
                    print('Esc')
                    return False  # 跳过
                elif char_code == 13 or char_code == 10:  # 回车或换行
                    print('回车')
                    return True  # 替换
                else:
                    char = chr(char_code) if 32 <= char_code <= 126 else ''
                    if char:
                        print(char)
                    return True  # 其他键都替换
            else:
                # 如果是整数（字符码）
                if key == 27:  # Esc键
                    print('Esc')
                    return False  # 跳过
                elif key == 13 or key == 10:  # 回车或换行
                    print('回车')
                    return True  # 替换
                else:
                    char = chr(key) if 32 <= key <= 126 else ''
                    if char:
                        print(char)
                    return True  # 其他键都替换
        else:
            # 非Windows环境
            import sys
            import tty
            import termios
            
            try:
                # 保存终端设置
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
                if ord(ch) == 27:  # Esc键
                    print('Esc')
                    return False  # 跳过
                elif ord(ch) == 13 or ord(ch) == 10:  # 回车或换行
                    print('回车')
                    return True  # 替换
                else:
                    print(ch)
                    return True  # 其他键都替换
            except Exception:
                # 如果无法使用raw模式，回退到input
                user_input = input().strip()
                if user_input.lower() == 'esc' or user_input == '\x1b':  # Esc的字符串表示
                    return False  # 跳过
                else:
                    return True  # 替换
    except Exception as e:
        print(f"\n输入处理错误: {e}，默认替换")
        return True


def clean_old_files(target_subdir, latest_file_names):
    """
    清理目标子目录中的旧文件，只保留最新的文件
    latest_file_names: 最新文件的文件名列表
    """
    if not target_subdir.exists() or not target_subdir.is_dir():
        return
    
    deleted_count = 0
    for file_path in target_subdir.iterdir():
        if file_path.is_file():
            file_name = file_path.name
            # 如果该文件不在最新文件列表中，删除它
            if file_name not in latest_file_names:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    print(f"  已删除旧文件: {file_name}")
                except Exception as e:
                    print(f"  删除旧文件失败 {file_name}: {str(e)}")
    
    if deleted_count > 0:
        print(f"  共删除 {deleted_count} 个旧文件")


def copy_latest_files(source_dir, target_dir, config=None):
    """
    从源目录下的渠道目录的release子目录中查找最新的apk文件，复制到目标目录的对应渠道目录中
    source\渠道\release\butterknife-v2025.x.x-xxx.apk -> target\渠道\butterknife-v2025.x.x-xxx.apk
    特殊处理：full渠道 -> target\test
    config: 目标目录的配置字典，包含 clean_old 等选项
    """
    if config is None:
        config = {}
    
    source_path = Path(source_dir)
    target_path = Path(target_dir)
    
    if not source_path.exists():
        print(f"源目录不存在: {source_dir}")
        return
    
    # 创建目标目录（如果不存在）
    target_path.mkdir(parents=True, exist_ok=True)
    
    clean_old = config.get('clean_old', False)  # 默认不清理旧文件
    
    # 遍历源目录下的每个渠道目录
    for channel_dir in source_path.iterdir():
        if channel_dir.is_dir():
            channel_name = channel_dir.name
            print(f"\n处理渠道: {channel_name}")
            
            # 进入渠道目录下的release子目录
            release_dir = channel_dir / 'release'
            
            if not release_dir.exists():
                print(f"  渠道 {channel_name} 的release目录不存在: {release_dir}")
                continue
            
            # 获取release目录中最新的apk文件
            latest_apk = get_latest_apk_in_release(str(release_dir))
            
            if not latest_apk:
                print(f"  渠道 {channel_name} 的release目录中没有找到符合条件的apk文件")
                continue
            
            file_name = os.path.basename(latest_apk)
            
            # 确定目标目录
            # full渠道特殊处理：拷贝到target\test目录
            if channel_name.lower() == 'full':
                target_channel_dir = target_path / 'test'
                print(f"  特殊处理：full渠道 -> target\\test")
            else:
                target_channel_dir = target_path / channel_name
            
            # 创建目标渠道目录
            target_channel_dir.mkdir(parents=True, exist_ok=True)
            
            target_file = target_channel_dir / file_name
            
            # 获取最新文件的文件名列表（用于清理旧文件）
            latest_file_names = [file_name]
            
            # 如果启用了清理旧文件功能，先清理旧文件
            if clean_old:
                clean_old_files(target_channel_dir, latest_file_names)
            
            # 检查目标文件是否已存在
            file_exists = target_file.exists()
            
            if file_exists:
                # 询问是否替换
                if not ask_replace_file(file_name):
                    print(f"  已跳过: {file_name}")
                    continue
            
            try:
                shutil.copy2(latest_apk, target_file)
                mod_time = datetime.fromtimestamp(os.path.getmtime(latest_apk))
                action = "已替换" if file_exists else "已复制"
                print(f"  {action}: {file_name} (修改时间: {mod_time.strftime('%Y-%m-%d %H:%M:%S')})")
                print(f"    源: {latest_apk}")
                print(f"    目标: {target_file}")
            except Exception as e:
                print(f"  复制失败 {file_name}: {str(e)}")


if __name__ == '__main__':
    def wait_for_keypress():
        try:
            if msvcrt is not None:
                print("\n按任意键退出...")
                msvcrt.getch()
                return
            # 非 Windows 兜底
            input("\n按回车键退出...")
        except Exception:
            pass

    try:
        print_intro()
        # 从配置文件读取源目录和目标目录们
        source_directory, target_directories = read_config('copy4bk-apk.txt')

        if not source_directory or not target_directories:
            print("错误：无法从配置文件读取源目录或目标目录！")
            print("\n请确保配置文件 copy4bk-apk.txt 存在且格式正确。")
        else:
            print("开始复制最新版本文件...")
            print(f"源目录: {source_directory}")
            print("目标目录配置:")
            for idx, (td, cfg) in enumerate(target_directories, 1):
                clean_old_status = "启用" if cfg.get('clean_old', False) else "禁用"
                print(f"  {idx}. {td} (清理旧文件: {clean_old_status})")

            for td, cfg in target_directories:
                print(f"\n=> 正在处理目标目录: {td}")
                clean_old_status = "启用" if cfg.get('clean_old', False) else "禁用"
                if clean_old_status == "启用":
                    print(f"  清理旧文件功能: {clean_old_status}")
                copy_latest_files(source_directory, td, cfg)

            print("\n全部目标目录处理完成！")
    finally:
        wait_for_keypress()
