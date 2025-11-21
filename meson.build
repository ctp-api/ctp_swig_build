project(
  'ctp-swig-build',
  'cpp',
  version : '6.7.10.1',
  license: 'MIT',
  meson_version: '>=1.9.0',
  default_options : [
    'warning_level=2',  # 警告级别
    'cpp_std=c++17',
    'buildtype=release',
    'optimization=2'
  ]
)

# 查找Python解释器和开发文件
py_mod = import('python')
py = py_mod.find_installation('python3')
py_dep = py.dependency()

# 获取编译器信息
cpp = meson.get_compiler('cpp')

# 输出构建目标系统信息
message('构建目标系统: ' + host_machine.system())

# 查找SWIG
swig = find_program('swig', required: true)

# 系统特定配置
target_system = host_machine.system()
if target_system == 'windows'
  lib_suffix = '.lib'
  dll_suffix = '.dll'
  so_suffix = '.pyd'
elif target_system == 'linux'
  lib_suffix = '.a'
  dll_suffix = '.so'
  so_suffix = '.so'
else
  error('Unsupported system: ' + target_system)
endif

# CTP C++源目录
source_dir = 'ctp_source'
# 设置包含目录
ctp_inc = include_directories(source_dir)

# 定义SWIG源文件和目标
swig_sources = [
  ['thostmduserapi.i', 'thostmduserapi'],
  ['thosttraderapi.i', 'thosttraderapi']
]

# 为每个SWIG模块生成包装代码和编译模块
foreach swig_source : swig_sources
  swig_file = swig_source[0]
  module_name = swig_source[1]
  
  # 生成SWIG包装代码
  swig_wrapper = custom_target(module_name + '_wrap',
    input : swig_file,
    output : [module_name + '_wrap.cxx', module_name + '.py'],
    command : [swig, '-threads', '-c++', '-python', 
               '-I@SOURCE_ROOT@/' + source_dir,
               '-outdir', '@OUTDIR@',
               '-o', '@OUTPUT0@',
               '@INPUT@'],
    build_by_default : true)
  
  # 设置库文件路径
  lib_name = 'thostmduserapi_se'
  if module_name == 'thosttraderapi'
    lib_name = 'thosttraderapi_se'
  endif
  
  # 系统特定的编译参数
  system_cpp_args = []
  if target_system == 'windows'
    system_cpp_args = [
      '-D_CRT_SECURE_NO_WARNINGS',
      '-D_SILENCE_CXX17_CODECVT_HEADER_DEPRECATION_WARNING',
      '/bigobj',          # 支持大文件编译
      '/wd4819',          # 禁用C4819警告（字符编码警告）
      '/wd4828',          # 禁用C4828警告（UTF-8字符无效警告）
      '/wd4267',          # 禁用size_t转换警告
      '/wd4244',          # 禁用数据类型转换警告
      '/source-charset:GB2312',  # 源文件字符集
      '/execution-charset:GB2312' # 执行字符集
    ]
  elif target_system == 'linux'
    system_cpp_args = [
      '-D_GNU_SOURCE',
      '-fPIC',
      '-Wno-unused-variable',
      '-Wno-unused-function'
    ]
  endif
  
  # 编译Python扩展模块
  py_ext = py.extension_module(module_name,
    swig_wrapper[0],  # SWIG生成的C++文件
    include_directories : ctp_inc,
    dependencies : [py_dep],
    link_args : [meson.current_source_dir() + '/'+ source_dir + '/' + lib_name + lib_suffix],
    cpp_args : system_cpp_args,
    install : true,
    install_dir : meson.current_source_dir() / 'ctp_api')
endforeach
