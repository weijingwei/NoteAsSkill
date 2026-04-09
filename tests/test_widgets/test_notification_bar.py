"""NotificationBar 测试"""
import pytest


class TestNotificationBar:
    """NotificationBar 组件测试"""

    def test_import(self):
        from app.widgets.notification_bar import NotificationBar
        assert NotificationBar is not None

    def test_instantiation(self, qtbot):
        from app.widgets.notification_bar import NotificationBar
        bar = NotificationBar()
        qtbot.addWidget(bar)
        assert bar is not None
        assert not bar.isVisible()

    def test_show_info(self, qtbot):
        from app.widgets.notification_bar import NotificationBar
        bar = NotificationBar()
        qtbot.addWidget(bar)

        bar.show_info("Test info")
        assert bar.isVisible()
        assert bar.message_label.text() == "Test info"
        assert bar.icon_label.text() == "\u2139\ufe0f"

    def test_show_success(self, qtbot):
        from app.widgets.notification_bar import NotificationBar
        bar = NotificationBar()
        qtbot.addWidget(bar)

        bar.show_success("Success!")
        assert bar.isVisible()
        assert bar.message_label.text() == "Success!"
        assert bar.icon_label.text() == "\u2713"

    def test_show_error(self, qtbot):
        from app.widgets.notification_bar import NotificationBar
        bar = NotificationBar()
        qtbot.addWidget(bar)

        bar.show_error("Error occurred")
        assert bar.isVisible()
        assert bar.message_label.text() == "Error occurred"
        assert bar.icon_label.text() == "\u2717"

    def test_update_message(self, qtbot):
        from app.widgets.notification_bar import NotificationBar
        bar = NotificationBar()
        qtbot.addWidget(bar)

        bar.show_info("Initial")
        bar.update_message("Updated")
        assert bar.message_label.text() == "Updated"

    def test_auto_hide(self, qtbot):
        from app.widgets.notification_bar import NotificationBar
        bar = NotificationBar()
        qtbot.addWidget(bar)

        bar.show_info("Auto hide test", auto_hide=100)
        assert bar.isVisible()

        # 等待定时器触发
        qtbot.wait(150)
        assert not bar.isVisible()

    def test_show_progress(self, qtbot):
        from app.widgets.notification_bar import NotificationBar
        bar = NotificationBar()
        qtbot.addWidget(bar)

        bar.show_progress("Loading...")
        assert bar.isVisible()
        assert "Loading" in bar.message_label.text()
        assert bar.icon_label.text() == "\u25c6"

    def test_close_button_hides_bar(self, qtbot):
        from app.widgets.notification_bar import NotificationBar
        bar = NotificationBar()
        qtbot.addWidget(bar)

        bar.show_info("Test")
        assert bar.isVisible()

        bar.close_button.click()
        assert not bar.isVisible()

    def test_hide_stops_auto_hide_timer(self, qtbot):
        """手动隐藏应停止自动隐藏定时器"""
        from app.widgets.notification_bar import NotificationBar
        bar = NotificationBar()
        qtbot.addWidget(bar)

        bar.show_info("Test", auto_hide=5000)
        assert bar.isVisible()

        bar.hide()
        assert not bar.isVisible()

        # 即使过了自动隐藏时间，也不应再显示
        qtbot.wait(100)
        assert not bar.isVisible()

    def test_fixed_height(self, qtbot):
        from app.widgets.notification_bar import NotificationBar
        bar = NotificationBar()
        qtbot.addWidget(bar)

        assert bar.height() == 36
