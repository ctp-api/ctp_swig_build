#!/usr/bin/env python3
"""
CTP SWIG构建脚本
使用SWIG + MSVC + Meson构建CTP Python扩展模块，并生成类型存根文件
"""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# CTP C++ API目录
ctp_source_dir = "ctp_source"

def get_platform_config():
    """获取平台特定配置"""
    system = platform.system().lower()
    
    if system == 'windows':
        return {
            'lib_suffix': '.lib',
            'dll_suffix': '.dll',
            'so_suffix': '.pyd',
            'is_windows': True,
            'is_linux': False
        }
    elif system == 'linux':
        return {
            'lib_suffix': '.a',
            'dll_suffix': '.so',
            'so_suffix': '.so',
            'is_windows': False,
            'is_linux': True
        }
    else:
        raise RuntimeError(f"不支持的操作系统: {system}")

def run_command(cmd, cwd=None, check=True):
    """运行命令并打印输出"""
    print(f"运行命令: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    if cwd:
        print(f"工作目录: {cwd}")
    
    result = subprocess.run(cmd, cwd=cwd, shell=True, 
                          capture_output=True, text=True, 
                          encoding='utf-8', errors='ignore')
    
    if result.stdout:
        print("标准输出:")
        print(result.stdout)
    
    if result.stderr:
        print("错误输出:")
        print(result.stderr)
    
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)
    
    return result

def check_dependencies():
    """检查必要的依赖项"""
    print("检查依赖项...")
    
    # 检查SWIG
    try:
        run_command(['swig', '-version'])
        print("✓ SWIG已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("❌ SWIG未找到，请安装SWIG并添加到PATH")
    
    # 检查Meson
    try:
        run_command(['meson', '--version'])
        print("✓ Meson已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("❌ Meson未找到，请使用 'pip install meson' 安装")
    
def setup_build_directory(build_dir="build"):
    """设置构建目录"""
    build_path = Path(build_dir)
    
    if build_path.exists():
        print(f"清理现有构建目录: {build_path}")
        try:
            shutil.rmtree(build_path)
        except PermissionError:
            print("⚠ 无法删除构建目录，可能有文件正在使用中")
            print("请手动删除build目录或关闭相关程序后重试")
            raise
    
    print(f"创建构建目录: {build_path}")
    build_path.mkdir(exist_ok=True)
    
    return build_path

def configure_meson(build_dir):
    """配置Meson构建"""
    print("配置Meson构建...")
    
    platform_config = get_platform_config()
    cmd = ['meson', 'setup', build_dir, '--backend=ninja']
    
    # 平台特定配置
    if platform_config['is_windows']:
        cmd.extend(['--vsenv'])  # 使用Visual Studio环境
    elif platform_config['is_linux']:
        # Linux特定配置可以在这里添加
        pass
    
    run_command(cmd)
    print("✓ Meson配置完成")

def build_project(build_dir):
    """编译项目"""
    print("编译项目...")
    print("注意：编译过程中可能出现大量字符编码警告，这是正常现象。")
    print("      由于CTP接口文件非常大，编译过程中CPU使用率会飙升到很高（可能达到100%），")
    print("      这是正常现象，因为SWIG需要处理大量的C++代码生成Python绑定。")
    print("      编译时间可能需要一分钟，请耐心等待。")
    
    cmd = ['meson', 'compile', '-C', build_dir, '--verbose']
    try:
        run_command(cmd)
        print("✓ 项目编译完成")
    except subprocess.CalledProcessError as e:
        print(f"编译失败，错误码: {e.returncode}")
        print("常见解决方案:")
        print("1. 确保安装了Visual Studio 2022或更新版本")
        print("2. 检查CTP库文件是否存在且路径正确")
        print("3. 检查Python开发环境是否完整")
        raise

def install_project(build_dir):
    """安装项目"""
    print("安装项目...")
    
    cmd = ['meson', 'install', '-C', build_dir]
    run_command(cmd)
    
    # 手动复制SWIG生成的Python文件
    copy_swig_python_files(build_dir)
    
    # 重命名pyd文件，在文件名前加下划线，这样做的目的是让SWIG生成的Python模块能够正确导入带下划线的底层C扩展模块。
    rename_pyd_files()
    
    # 复制运行时依赖的DLL文件
    copy_runtime_dlls()
    
    print("✓ 项目安装完成")

def copy_swig_python_files(build_dir):
    """复制SWIG生成的Python文件到ctp_api目录"""
    print("复制SWIG生成的Python文件到ctp_api目录...")
    
    # 使用ctp_api目录作为目标
    project_root = Path.cwd()
    ctp_dir = project_root / 'ctp_api'
    
    build_path = Path(build_dir)
    modules = ['thostmduserapi', 'thosttraderapi']
    
    for module in modules:
        # 查找构建目录中的Python文件
        py_file = build_path / f"{module}.py"
        if py_file.exists():
            dst = ctp_dir / f"{module}.py"
            shutil.copy2(py_file, dst)
            print(f"✓ 复制 {py_file} -> {dst}")
        else:
            print(f"⚠ 未找到 {py_file}")

def rename_pyd_files():
    """重命名扩展模块文件，在文件名前加下划线，并删除旧文件"""
    platform_config = get_platform_config()
    so_suffix = platform_config['so_suffix']
    
    print("重命名扩展模块文件，在文件名前添加下划线...")
    
    project_root = Path.cwd()
    ctp_dir = project_root / 'ctp_api'
    
    if not ctp_dir.exists():
        print(f"⚠ CTP目录不存在: {ctp_dir}")
        return
    
    modules = ['thostmduserapi', 'thosttraderapi']
    
    for module in modules:
        # 查找包含版本号的扩展模块文件
        so_files = list(ctp_dir.glob(f"{module}.cp*{so_suffix}"))
        
        for so_file in so_files:
            # 构造新的文件名（在原文件名前加下划线）
            old_name = so_file.name
            new_name = '_' + old_name
            new_path = ctp_dir / new_name
            
            try:
                # 如果目标文件已存在，先删除
                if new_path.exists():
                    new_path.unlink()
                    print(f"✓ 删除已存在的文件: {new_name}")
                
                # 重命名文件
                so_file.rename(new_path)
                print(f"✓ 重命名 {old_name} -> {new_name}")
            except Exception as e:
                print(f"⚠ 重命名 {old_name} 失败: {e}")
        
        # 删除不需要的库文件（如果存在）
        platform_config = get_platform_config()
        lib_suffix = platform_config['lib_suffix']
        lib_files = list(ctp_dir.glob(f"{module}.cp*{lib_suffix}"))
        for lib_file in lib_files:
            try:
                lib_file.unlink()
                print(f"✓ 删除不需要的文件: {lib_file.name}")
            except Exception as e:
                print(f"⚠ 删除 {lib_file.name} 失败: {e}")
    
    # 清理可能存在的旧pyd和lib文件
    cleanup_old_files(ctp_dir, modules)

def copy_runtime_dlls():
    """复制运行时依赖的动态库文件到ctp_api目录"""
    platform_config = get_platform_config()
    dll_suffix = platform_config['dll_suffix']
    
    print(f"复制运行时依赖的动态库文件到ctp_api目录...")
    
    project_root = Path.cwd()
    ctp_api_dir = project_root / 'ctp_api'
    ctp_source_dir = project_root / 'ctp_source'
    
    dll_files = [
        f'thostmduserapi_se{dll_suffix}',
        f'thosttraderapi_se{dll_suffix}'
    ]
    
    for dll_file in dll_files:
        src = ctp_source_dir / dll_file
        if src.exists():
            dst = ctp_api_dir / dll_file
            shutil.copy2(src, dst)
            print(f"✓ 复制 {src} -> {dst}")
        else:
            print(f"⚠ 未找到 {src}")

def cleanup_old_files(ctp_dir, modules):
    """清理旧的扩展模块和库文件"""
    platform_config = get_platform_config()
    so_suffix = platform_config['so_suffix']
    lib_suffix = platform_config['lib_suffix']
    
    print("清理旧的扩展模块和库文件...")
    
    for module in modules:
        # 删除不带下划线的旧扩展模块文件
        old_so_files = list(ctp_dir.glob(f"{module}.cp*{so_suffix}"))
        for old_file in old_so_files:
            try:
                old_file.unlink()
                print(f"✓ 删除旧文件: {old_file.name}")
            except Exception as e:
                print(f"⚠ 删除 {old_file.name} 失败: {e}")
        
        # 删除所有库文件（包括带下划线的）
        all_lib_files = list(ctp_dir.glob(f"*{module}*{lib_suffix}"))
        for old_file in all_lib_files:
            try:
                old_file.unlink()
                print(f"✓ 删除不需要的文件: {old_file.name}")
            except Exception as e:
                print(f"⚠ 删除 {old_file.name} 失败: {e}")

def generate_stubs():
    """生成类型存根文件"""
    print("在ctp_api目录中生成类型存根文件...")
    
    # 首先检查stubgen是否可用
    try:
        result = run_command(['stubgen', '--version'], check=False)
        if result.returncode != 0:
            print("⚠ stubgen未正确安装，正在安装mypy...")
            install_result = run_command([sys.executable, '-m', 'pip', 'install', 'mypy'], check=False)
            if install_result.returncode != 0:
                print("⚠ mypy安装失败，跳过存根文件生成")
                print("   请手动运行: pip install mypy")
                return False
    except Exception as e:
        print(f"⚠ 检查stubgen时出错: {e}")
        print("尝试安装mypy...")
        try:
            install_result = run_command([sys.executable, '-m', 'pip', 'install', 'mypy'], check=False)
            if install_result.returncode != 0:
                print("⚠ mypy安装失败，跳过存根文件生成")
                return False
        except Exception as install_e:
            print(f"⚠ 安装mypy时出错: {install_e}")
            return False
    
    try:
        # 使用ctp_api目录
        project_root = Path.cwd()
        ctp_dir = project_root / 'ctp_api'
        
        if not ctp_dir.exists():
            print(f"⚠ CTP目录不存在: {ctp_dir}")
            return False
        
        # 为每个模块生成存根
        modules = ['thostmduserapi', 'thosttraderapi']
        success_count = 0
        
        for module in modules:
            # 查找包含版本号的pyd文件（已重命名，文件名前有下划线）
            pyd_files = list(ctp_dir.glob(f"_{module}.cp*.pyd"))
            
            if pyd_files:
                print(f"为 {module} 生成存根文件...")
                
                try:
                    # 使用stubgen命令生成存根文件
                    # 临时添加项目根目录到Python路径，确保能找到ctp包
                    original_path = sys.path.copy()
                    if str(project_root) not in sys.path:
                        sys.path.insert(0, str(project_root))
                    
                    # 使用 stubgen -m ctp_api._thostmduserapi -o . 的格式
                    stub_cmd = [
                        'stubgen',
                        '-m', f'ctp_api._{module}',  # 使用带下划线的模块名
                        '-o', '.'
                    ]
                    
                    result = run_command(stub_cmd, cwd=str(project_root), check=False)
                    
                    # 恢复Python路径
                    sys.path = original_path
                    
                    if result.returncode == 0:
                        # 检查是否生成了存根文件
                        # stubgen会在ctp目录下生成_thostmduserapi.pyi，我们需要重命名为thostmduserapi.pyi
                        generated_stub = ctp_dir / f"_{module}.pyi"
                        target_stub = ctp_dir / f"{module}.pyi"
                        
                        if generated_stub.exists():
                            # 重命名文件（去掉前缀下划线）
                            if target_stub.exists():
                                target_stub.unlink()  # 删除已存在的文件
                            generated_stub.rename(target_stub)
                            print(f"✓ {module} 存根文件生成完成: {target_stub}")
                            success_count += 1
                        else:
                            print(f"⚠ {module} 存根文件生成但未在预期位置找到")
                    else:
                        print(f"⚠ {module} 存根文件生成失败，返回码: {result.returncode}")
                        if result.stderr:
                            print(f"   错误信息: {result.stderr.strip()}")
                        
                except Exception as e:
                    print(f"⚠ {module} 存根文件生成时出错: {e}")
            else:
                print(f"⚠ 未找到 _{module}.pyd 文件")
        
        if success_count > 0:
            print(f"✓ 成功生成 {success_count}/{len(modules)} 个存根文件")
            return True
        else:
            print("⚠ 没有成功生成任何存根文件")
            print("手动生成命令（在项目根目录执行）:")
            for module in modules:
                print(f"  stubgen -m ctp_api._{module} -o .")
            return False
    
    except Exception as e:
        print(f"⚠ 存根文件生成出错: {e}")
        return False


def copy_dlls_to_build(build_dir):
    """复制动态库文件到构建目录"""
    platform_config = get_platform_config()
    dll_suffix = platform_config['dll_suffix']
    
    print("复制动态库文件...")
    
    dll_files = [
        f'ctp_source/thostmduserapi_se{dll_suffix}',
        f'ctp_source/thosttraderapi_se{dll_suffix}'
    ]
    
    build_ctp_dir = Path(build_dir) / 'ctp_source'
    build_ctp_dir.mkdir(exist_ok=True)
    
    for dll_file in dll_files:
        src = Path(dll_file)
        if src.exists():
            dst = build_ctp_dir / src.name
            shutil.copy2(src, dst)
            print(f"✓ 复制 {src} -> {dst}")
        else:
            print(f"⚠ 未找到 {dll_file}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='CTP SWIG构建脚本')
    parser.add_argument('--build-dir', default='build', 
                       help='构建目录 (默认: build)')
    parser.add_argument('--clean', action='store_true',
                       help='清理构建目录')
    parser.add_argument('--no-stubs', action='store_true',
                       help='跳过生成存根文件')
    parser.add_argument('--configure-only', action='store_true',
                       help='仅配置，不编译')
    
    args = parser.parse_args()
    
    try:
        print("=== CTP SWIG构建脚本 ===")
        
        # 检查依赖项
        check_dependencies()
        
        # 设置构建目录
        build_dir = setup_build_directory(args.build_dir)
        
        # 复制DLL文件
        copy_dlls_to_build(build_dir)
        
        # 配置Meson
        configure_meson(str(build_dir))
        
        if args.configure_only:
            print("✓ 仅配置模式，构建配置完成")
            return
        
        # 编译项目
        build_project(str(build_dir))
        
        # 安装项目
        install_project(str(build_dir))
        
        # 生成存根文件
        stub_success = False
        if not args.no_stubs:
            stub_success = generate_stubs()
        
        print("\n=== 构建完成 ===")
        print("模块已生成在ctp_api目录中")
        print("可以使用以下方式导入CTP模块:")
        print("  import ctp_api.thostmduserapi")
        print("  import ctp_api.thosttraderapi")
        print("\n生成的文件:")
        print("  ctp_api/_thostmduserapi.cp*.pyd - 行情API模块")
        print("  ctp_api/_thosttraderapi.cp*.pyd - 交易API模块")
        print("  ctp_api/thostmduserapi.py - SWIG生成的Python接口")
        print("  ctp_api/thosttraderapi.py - SWIG生成的Python接口")
        
        if not args.no_stubs:
            if stub_success:
                print("  ctp_api/thostmduserapi.pyi - 类型存根文件 ✓")
                print("  ctp_api/thosttraderapi.pyi - 类型存根文件 ✓")
            else:
                print("  ctp_api/thostmduserapi.pyi - 类型存根文件 ❌")
                print("  ctp_api/thosttraderapi.pyi - 类型存根文件 ❌")
        else:
            print("  类型存根文件生成已跳过")
        
    except Exception as e:
        print(f"\n❌ 构建失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
