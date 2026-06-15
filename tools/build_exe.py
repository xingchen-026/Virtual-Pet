"""一键打包桌宠为单文件 exe（PyInstaller onefile）。

用法：
    pip install pyinstaller            # 仅打包需要，非运行期依赖
    python tools/build_exe.py         # 产物在 dist/VirtualPet.exe

打包策略（详见 config/settings.py 的路径拆分与 ensure_user_data）：
* 只读资源（assets 全部、behavior/desktop/moderation 配置、ai_config 模板）打进 exe；
* 运行期可写数据（存档/日志/user_config/skin_config/用户皮肤）首次运行播种到 exe 旁；
* 绝不打包本地 config/ai_config.json（含真实 API Key，已被 skip-worktree 屏蔽）。

用 PyInstaller CLI 而非手写 .spec：跨版本更稳，--add-data 分隔符按平台自动取 os.pathsep。
"""

import os
import sys

import PyInstaller.__main__

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from make_icon import make_icon  # noqa: E402

SEP = os.pathsep  # Windows 为 ';'，*nix 为 ':'

# 只读资源（源路径相对 ROOT -> exe 内目标目录）。
# 注意：只列读取用的配置与模板，绝不含真实 ai_config.json / user_config.json。
_DATAS = [
    ("assets", "assets"),
    ("config/behavior_config.json", "config"),
    ("config/desktop_config.json", "config"),
    ("config/moderation.json", "config"),
    ("config/ai_config.template.json", "config"),
]

# pystray 与 pyttsx3 的平台后端用动态导入加载，PyInstaller 静态分析发现不了，需显式声明
_HIDDEN = [
    "pystray._win32",
    "pyttsx3.drivers",
    "pyttsx3.drivers.sapi5",
    "comtypes",
    "comtypes.client",
    "comtypes.stream",
]

# 排除体积大且非运行期必需的库，避免误打进 exe 让体积暴涨。
# scipy 仅用于皮肤网格切分的可选碎片剔除（spritesheet 已做缺失降级）；
# 其余为常见的科学计算/绘图/测试库，桌宠运行用不到。
_EXCLUDES = [
    "scipy", "matplotlib", "pandas", "IPython", "notebook",
    "pytest", "sphinx", "setuptools",
]


def build() -> None:
    os.chdir(ROOT)
    icon = make_icon()

    args = [
        "main.py",
        "--name=VirtualPet",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--icon={icon}",
    ]
    for src, dest in _DATAS:
        args.append(f"--add-data={src}{SEP}{dest}")
    for mod in _HIDDEN:
        args.append(f"--hidden-import={mod}")
    for mod in _EXCLUDES:
        args.append(f"--exclude-module={mod}")

    print("PyInstaller args:\n  " + "\n  ".join(args))
    PyInstaller.__main__.run(args)
    print("\n打包完成 -> dist/VirtualPet.exe")


if __name__ == "__main__":
    build()
