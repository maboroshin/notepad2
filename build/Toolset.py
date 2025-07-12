import os.path
import glob
import json
import re
import datetime

toolset_msvc = """
    <PlatformToolset Condition="'$(VisualStudioVersion)'=='16.0'">v142</PlatformToolset>
    <PlatformToolset Condition="'$(VisualStudioVersion)'=='17.0'">v143</PlatformToolset>
""".strip('\r\n').splitlines()

toolset_llvm = """
    <PlatformToolset Condition="'$(VisualStudioVersion)'=='16.0'">LLVM_v142</PlatformToolset>
    <PlatformToolset Condition="'$(VisualStudioVersion)'=='17.0'">LLVM_v143</PlatformToolset>
""".strip('\r\n').splitlines()

def update_project_toolset(projectPath):
	with open(projectPath, encoding='utf-8') as fd:
		doc = fd.read()
	lines = []
	previous = False
	for line in doc.splitlines():
		current = '<PlatformToolset Condition=' in line
		if current:
			if not previous:
				if 'LLVM' in line:
					lines.extend(toolset_llvm)
				else:
					lines.extend(toolset_msvc)
		else:
			lines.append(line)
		previous = current

	updated = '\n'.join(lines)
	if updated != doc:
		print('update:', projectPath)
		with open(projectPath, 'w', encoding='utf-8') as fd:
			fd.write(updated)

def update_all_project_toolset():
	for path in glob.glob('VisualStudio/*.vcxproj'):
		update_project_toolset(path)
	for path in glob.glob('../locale/*/*.vcxproj'):
		update_project_toolset(path)

def update_copyright_year(path, year):
	with open(path, encoding='utf-8', newline='\n') as fd:
		doc = fd.read()
	updated = re.sub(rf'(\d{{4}}-){year - 1}', lambda m: f'{m.group(1)}{year}', doc)
	if updated != doc:
		print('update:', path)
		with open(path, 'w', encoding='utf-8', newline='\n') as fp:
			fp.write(updated)

def update_all_copyright_year():
	year = datetime.datetime.now().year
	print('update copyright year to:', year)
	for path in [
		'../doc/License.txt',
		'../matepath/doc/License.txt',
		'../matepath/src/matepath.rc',
		'../matepath/src/version.h',
		'../scintilla/License.txt',
		'../src/Notepad4.rc',
		'../src/Version.h',
		'../License.txt']:
		update_copyright_year(path, year)

	for path in glob.glob('../locale/*/*.rc'):
		update_copyright_year(path, year)

def quote_path(path):
	return f'"{path}"' if ' ' in path else path

def build_compile_commands(commands, folder, cflags, cxxflags, includes, cxx=False):
	# https://clang.llvm.org/docs/JSONCompilationDatabase.html
	folder = os.path.abspath(folder)
	with os.scandir(folder) as it:
		for entry in it:
			if not entry.is_file():
				continue
			ext = os.path.splitext(entry.name)[1]
			if ext in ('.c', '.cpp', '.cxx'):
				path = entry.path
				arguments = cxxflags[:] if cxx or ext != '.c' else cflags[:]
				arguments.extend(includes)
				arguments.append(quote_path(path))
				commands.append({
					'directory': folder,
					#'arguments': arguments,
					'command': ' '.join(arguments),
					'file': path,
				})

def generate_compile_commands(target, avx2=False, cxx=False):
	cflags = []
	cxxflags = []
	# flags to run clang-tidy via vscode-clangd plugin, see https://clangd.llvm.org/
	defines = ['NDEBUG', '_WINDOWS', 'NOMINMAX', 'WIN32_LEAN_AND_MEAN', 'STRICT_TYPED_ITEMIDS',
		'UNICODE', '_UNICODE', '_CRT_SECURE_NO_WARNINGS', '_SCL_SECURE_NO_WARNINGS',
		'BOOST_REGEX_STANDALONE', 'NO_CXX11_REGEX',
	]
	warnings = ['-Wextra', '-Wshadow', '-Wimplicit-fallthrough', '-Wformat=2', '-Wundef', '-Wcomma']
	cxxwarn = ['-Wold-style-cast']

	target_flag = '--target=' + target
	msvc = 'msvc' in target
	if msvc:
		cflags.extend(['clang-cl.exe', target_flag, '-c', '/std:c17', '/O2'])
		cxxflags.extend(['clang-cl.exe', target_flag, '-c', '/std:c++20', '/O2', '/EHsc', '/GR-'])
		warnings.insert(0, '/W4')
	else:
		cflags.extend(['clang.exe', target_flag, '-municode', '-c', '-std=gnu17', '-O2'])
		cxxflags.extend(['clang++.exe', target_flag, '-municode', '-c', '-std=gnu++20', '-O2', '-fno-rtti'])
		warnings.insert(0, '-Wall')
	if cxx:
		cxxflags.insert(2, '/TP' if msvc else 'x c++')

	arch = target[:target.index('-')]
	if arch == 'x86_64':
		defines.append('_WIN64')
		if avx2:
			cflags.append('-march=x86-64-v3')
			cxxflags.append('-march=x86-64-v3')
			defines.extend(['_WIN32_WINNT=0x0601', 'WINVER=0x0601'])	# 7
		else:
			defines.extend(['_WIN32_WINNT=0x0600', 'WINVER=0x0600'])	# Vista
	elif arch == 'i686':
		defines.extend(['WIN32', '_WIN32_WINNT=0x0600', 'WINVER=0x0600'])	# Vista
	elif arch in ('aarch64', 'arm64'):
		defines.extend(['_WIN64', '_WIN32_WINNT=0x0A00', 'WINVER=0x0A00'])	# 10
	elif arch.startswith('arm'):
		defines.extend(['WIN32', '_WIN32_WINNT=0x0602', 'WINVER=0x0602'])	# 8

	defines = ['-D' + item for item in defines]
	cflags.extend(defines)
	cxxflags.extend(defines)
	cflags.extend(warnings)
	cxxflags.extend(warnings + cxxwarn)
	if cxx:
		cflags.extend(cxxwarn)

	config = [
		('../src', ['../scintilla/include']),
		('../scintilla/lexers', ['../include', '../lexlib']),
		('../scintilla/lexlib', ['../include']),
		('../scintilla/src', ['../include', '../lexlib']),
		('../scintilla/win32', ['../include', '../src']),
		('../matepath/src', []),
	]

	def include_path(folder, path):
		path = os.path.abspath(os.path.join(folder, path))
		return quote_path(path)

	commands = []
	for folder, includes in config:
		includes = ['-I' + include_path(folder, path) for path in includes]
		build_compile_commands(commands, folder, cflags, cxxflags, includes, cxx)

	path = '../compile_commands.json'
	print('write:', path)
	with open(path, 'w', encoding='utf-8', newline='\n') as fd:
		fd.write(json.dumps(commands, indent='\t', ensure_ascii=False))

#update_all_project_toolset()
#update_all_copyright_year()
generate_compile_commands('x86_64-pc-windows-msvc', avx2=True)
#generate_compile_commands('x86_64-pc-windows-msvc')
#generate_compile_commands('i686-pc-windows-msvc')
#generate_compile_commands('aarch64-pc-windows-msvc')
#generate_compile_commands('arm-pc-windows-msvc')
#generate_compile_commands('x86_64-w64-windows-gnu', avx2=True)
#generate_compile_commands('x86_64-w64-windows-gnu')
#generate_compile_commands('i686-w64-windows-gnu')
#generate_compile_commands('aarch64-w64-windows-gnu')
#generate_compile_commands('armv7-w64-windows-gnu')
#run-clang-tidy --quiet -j4 1>tidy.log
