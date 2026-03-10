from kivy.clock import Clock
from kivymd.uix.screen import MDScreen


class SplashScreen(MDScreen):
    _event = None

    def on_enter(self, *args):
        if self._event is not None:
            self._event.cancel()
        self._event = Clock.schedule_once(self.go_next, 0.45)
        return super().on_enter(*args)

    def on_leave(self, *args):
        if self._event is not None:
            self._event.cancel()
            self._event = None
        return super().on_leave(*args)

    def go_next(self, *_):
        if self.manager:
            self.manager.current = "dashboard"
