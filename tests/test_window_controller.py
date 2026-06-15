"""WindowController 坐标不变式（窗口中心 = 宠物屏幕坐标）的回归测试。

用 FakeDesktop / FakeSprite 替身，无需真实窗口即可验证坐标换算。
"""

from core.pet import Pet
from core.window_controller import WindowController

WINDOW_SIZE = (800, 600)
CENTER = (400, 300)


class FakeDesktop:
    """DesktopManager 的最小替身：在内存中模拟窗口与鼠标位置。"""

    def __init__(self, supported=True, position=(500, 300)):
        self.supported = supported
        self._position = position
        self.cursor = (0, 0)

    def get_position(self):
        return self._position

    def set_position(self, x, y):
        self._position = (x, y)

    def get_cursor_position(self):
        return self.cursor


class FakeSprite:
    def __init__(self):
        self.render_center = None


def _make(supported=True, position=(500, 300)):
    desktop = FakeDesktop(supported=supported, position=position)
    pet = Pet()
    sprite = FakeSprite()
    return WindowController(desktop, pet, sprite, WINDOW_SIZE), desktop, pet, sprite


def test_initialize_places_pet_at_window_center():
    wc, desktop, pet, sprite = _make(position=(500, 300))
    wc.initialize()
    assert sprite.render_center == CENTER
    assert pet.position == (500 + CENTER[0], 300 + CENTER[1])


def test_initialize_applies_saved_position():
    wc, desktop, pet, sprite = _make(position=(500, 300))
    wc.initialize([100, 80])
    assert desktop.get_position() == (100, 80)
    assert pet.position == (100 + CENTER[0], 80 + CENTER[1])


def test_window_drag_keeps_center_invariant():
    wc, desktop, pet, sprite = _make(position=(500, 300))
    wc.initialize()

    desktop.cursor = (1000, 1000)
    wc.begin_drag()
    assert wc.dragging_window

    # 鼠标移动 (+120, -40)，窗口与宠物应同步移动相同位移
    desktop.cursor = (1120, 960)
    wc.update_drag()
    assert desktop.get_position() == (620, 260)
    assert pet.position == (620 + CENTER[0], 260 + CENTER[1])

    wc.end_drag()
    assert not wc.dragging_window


def test_sync_to_pet_moves_window_under_pet():
    wc, desktop, pet, sprite = _make(position=(500, 300))
    wc.initialize()

    # 模拟自主移动：宠物屏幕坐标改变后，窗口应跟随到 pet - center
    pet.set_position(1000, 700)
    wc.sync_to_pet()
    assert desktop.get_position() == (1000 - CENTER[0], 700 - CENTER[1])
    assert wc.window_pos == (600, 400)


def test_set_geometry_recenters_and_switches_mode():
    wc, desktop, pet, sprite = _make(position=(500, 300))
    wc.initialize()
    wc.set_geometry((600, 400), (200, 100), follow=False)
    assert wc.center == (300, 200)
    assert wc.window_pos == (200, 100)
    assert wc.follow is False


def test_fixed_mode_sync_updates_render_center_not_window():
    # 围栏固定模式：窗口不动，宠物在固定窗口内按 (pet - window_pos) 渲染
    wc, desktop, pet, sprite = _make(position=(500, 300))
    wc.initialize()
    wc.set_geometry((600, 400), (200, 100), follow=False)

    pos_before = desktop.get_position()
    pet.set_position(450, 360)
    wc.sync_to_pet()
    assert desktop.get_position() == pos_before  # sync 不移动窗口（固定模式）
    assert sprite.render_center == (450 - 200, 360 - 100)  # (250, 260)


def test_fixed_mode_disables_window_drag():
    wc, desktop, pet, sprite = _make(position=(500, 300))
    wc.initialize()
    wc.set_geometry((600, 400), (200, 100), follow=False)
    wc.begin_drag()
    assert not wc.dragging_window  # 固定模式下不进行窗口拖拽


def test_follow_mode_restored_keeps_center_invariant():
    wc, desktop, pet, sprite = _make(position=(500, 300))
    wc.initialize()
    wc.set_geometry((600, 400), (200, 100), follow=False)
    # 恢复跟随模式后仍维持"窗口中心 = 宠物"
    wc.set_geometry(WINDOW_SIZE, (300, 200), follow=True)
    pet.set_position(1000, 700)
    wc.sync_to_pet()
    assert desktop.get_position() == (1000 - CENTER[0], 700 - CENTER[1])


def test_unsupported_platform_is_noop():
    wc, desktop, pet, sprite = _make(supported=False, position=(0, 0))
    wc.initialize([100, 80])
    # 不支持时不应移动窗口、不固定渲染中心
    assert sprite.render_center is None
    wc.begin_drag()
    assert not wc.dragging_window
    wc.update_drag()  # 不应抛异常
    pet.set_position(999, 999)
    wc.sync_to_pet()
    assert desktop.get_position() == (0, 0)
