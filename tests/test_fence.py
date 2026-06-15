"""电子围栏 FenceController 状态机与 popup_topleft 布局的回归测试。"""

from core.fence import FenceController, popup_topleft


def test_toggle_two_points_sets_fence():
    fc = FenceController()
    assert fc.toggle((100, 80)) == "first_corner"
    assert fc.fence is None
    assert fc.toggle((400, 300)) == "set"
    assert fc.fence == (100, 80, 400, 300)


def test_toggle_normalizes_corners():
    # 第二点在左上方时仍规范化为 (minx,miny,maxx,maxy)
    fc = FenceController()
    fc.toggle((400, 300))
    fc.toggle((100, 80))
    assert fc.fence == (100, 80, 400, 300)


def test_toggle_clears_existing_fence():
    fc = FenceController()
    fc.toggle((0, 0))
    fc.toggle((200, 200))
    assert fc.toggle((50, 50)) == "cleared"
    assert fc.fence is None


def test_pending_exposes_first_corner():
    fc = FenceController()
    assert fc.pending is None
    fc.toggle((120, 90))
    assert fc.pending == (120, 90)  # 取点中暴露第一个角供绘制预览
    fc.toggle((300, 250))
    assert fc.pending is None  # 第二点后清空待定


def test_clear_resets_fence_and_pending():
    fc = FenceController()
    fc.toggle((0, 0))
    fc.toggle((200, 200))
    assert fc.fence is not None
    fc.clear()
    assert fc.fence is None
    assert fc.pending is None
    # 清除后可重新取点
    assert fc.toggle((10, 10)) == "first_corner"


def test_contains_no_fence_is_always_true():
    fc = FenceController()
    assert fc.contains((9999, 9999))


def test_contains_inside_and_outside():
    fc = FenceController()
    fc.toggle((100, 100))
    fc.toggle((300, 300))
    assert fc.contains((200, 200))
    assert fc.contains((100, 100))  # 边界算内
    assert not fc.contains((50, 200))
    assert not fc.contains((200, 400))


def test_popup_topleft_none_without_fence():
    assert popup_topleft(None, (0, 0), (800, 600), (280, 400)) is None


def test_popup_topleft_prefers_left_corner_when_fits():
    # 围栏左上角转画布坐标后窗口向右展开能放下 -> 用左上角
    fence = (500, 400, 1100, 900)
    window_pos = (300, 200)
    # 左上角画布坐标 = (200, 200)，280 宽放得下 800 画布
    assert popup_topleft(fence, window_pos, (800, 600), (280, 400)) == (200, 200)


def test_popup_topleft_falls_back_to_right_corner():
    # 左上角放不下（会超出右边），改用右上角向左展开
    fence = (700, 100, 1000, 500)
    window_pos = (0, 0)
    # 左 anchor=700, 700+280=980>800 放不下；右 anchor=1000-280=720, 720+280=1000>800 也放不下
    # -> 夹取：max(0, min(700, 800-280)) = 520
    assert popup_topleft(fence, window_pos, (800, 600), (280, 400)) == (520, 100)


def test_popup_topleft_clamps_top_into_canvas():
    # 围栏上边在画布下方过深时，y 夹取到画布内（canvas_h - popup_h）
    fence = (100, 550, 400, 900)
    window_pos = (0, 0)
    x, y = popup_topleft(fence, window_pos, (800, 600), (280, 400))
    assert y == 600 - 400  # 200
