"""桌面虚拟宠物程序入口。

启动流程（由 Game.__init__ / Game.run 内部按顺序完成）：

    程序启动 -> 加载配置（desktop_config / behavior_config）
        -> 加载宠物数据（JSON 存档，缺失或损坏则使用默认值）
        -> 初始化桌面窗口（DesktopManager：无边框/透明/置顶/初始位置）
        -> 初始化动画（ResourceManager + AnimationManager）
        -> 启动游戏循环（Game.run，含系统托盘后台运行）
"""

from core.game import Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
