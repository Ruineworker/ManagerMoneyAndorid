from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen


class VersionedScreen(MDScreen):
    last_loaded_revision = -1
    _load_trigger = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_trigger = Clock.create_trigger(self._refresh_if_needed, 0)

    def app(self):
        return MDApp.get_running_app()

    def on_pre_enter(self, *args):
        self.queue_refresh(force=False)
        return super().on_pre_enter(*args)

    def queue_refresh(self, force: bool = False):
        if force:
            self.last_loaded_revision = -1
        self._load_trigger()

    def _refresh_if_needed(self, *_):
        app = self.app()
        if app is None or app.db is None:
            return
        if self.last_loaded_revision == app.db.revision and self.manager and self.manager.current == self.name:
            return
        self.refresh_content()
        self.last_loaded_revision = app.db.revision

    def refresh_content(self):
        raise NotImplementedError
