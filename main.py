"""桌面虚拟宠物程序入口。

启动流程（由 Game.__init__ / Game.run 内部按顺序完成）：

    程序启动 -> 加载配置（desktop_config / behavior_config）
        -> 加载宠物数据（JSON 存档，缺失或损坏则使用默认值）
        -> 初始化桌面窗口（DesktopManager：无边框/透明/置顶/初始位置）
        -> 初始化动画（ResourceManager + AnimationManager）
        -> 启动游戏循环（Game.run，含系统托盘后台运行）
"""

from config import settings
from core.game import Game


def main():
    # 打包(onefile)首次运行时，把可写数据（配置/存档/内置皮肤）播种到 exe 旁目录；
    # 开发态为空操作。必须在创建 Game 之前，Game.__init__ 会读取这些配置。
    settings.ensure_user_data()
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
