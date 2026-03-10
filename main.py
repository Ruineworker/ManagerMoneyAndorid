from kivy.core.window import Window
from kivy.lang import Builder
from kivy.utils import get_color_from_hex, platform
from kivymd.app import MDApp

from libs.database import Database
from libs.models import init_db
from screens.accounts import AccountsScreen
from screens.add_transaction import AddTransactionScreen
from screens.analytics import AnalyticsScreen
from screens.categories import CategoriesScreen
from screens.dashboard import DashboardScreen
from screens.settings import SettingsScreen
from screens.splash import SplashScreen
from screens.transactions import TransactionsScreen

if platform not in ("android", "ios"):
    Window.size = (414, 896)
    Window.left = 120
    Window.top = 60


class FinWiseApp(MDApp):
    LIGHT = {
        "bg": "#FCFEFE",
        "surface": "#FFFFFF",
        "surface_alt": "#F3FAF8",
        "hero": "#17383B",
        "card": "#FFFFFF",
        "card_alt": "#F2F8F7",
        "primary": "#1FB9AE",
        "primary_soft": "#D4F1EC",
        "secondary": "#79BFD0",
        "success": "#12B981",
        "expense": "#F26363",
        "text": "#17242A",
        "text_soft": "#66747C",
        "text_on_dark": "#F5FAFB",
        "border": "#E5EFEE",
        "nav": "#F8FBFB",
        "nav_active": "#D7F1ED",
        "input": "#FFFFFF",
    }
    DARK = {
        "bg": "#0B1217",
        "surface": "#131D24",
        "surface_alt": "#18252C",
        "hero": "#1A373B",
        "card": "#121B22",
        "card_alt": "#18252C",
        "primary": "#20C1B4",
        "primary_soft": "#B7E0DB",
        "secondary": "#8BC7CF",
        "success": "#13D1A8",
        "expense": "#FF7B74",
        "text": "#ECF3F4",
        "text_soft": "#A2B5BB",
        "text_on_dark": "#F6FAFB",
        "border": "#273740",
        "nav": "#142028",
        "nav_active": "#B7E1DC",
        "input": "#10191F",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "FinWise"
        self.db = None
        self._loaded_kv = False

    def build(self):
        self.theme_cls.material_style = "M3"
        self.theme_cls.primary_palette = "Teal"
        self.db = Database()
        init_db(self.db)
        self.apply_theme(self.db.get_theme())
        self._load_kv_files_once()
        return Builder.load_file("main.kv")

    def _load_kv_files_once(self):
        if self._loaded_kv:
            return
        for path in (
            "screens/splash.kv",
            "screens/dashboard.kv",
            "screens/transactions.kv",
            "screens/add_transaction.kv",
            "screens/categories.kv",
            "screens/accounts.kv",
            "screens/analytics.kv",
            "screens/settings.kv",
        ):
            Builder.load_file(path)
        self._loaded_kv = True

    def on_start(self):
        if self.db.is_first_run():
            self.db.populate_demo_data()
        self.root.current = "splash"

    def palette(self):
        return self.DARK if self.theme_cls.theme_style == "Dark" else self.LIGHT

    def ui(self, name):
        return get_color_from_hex(self.palette()[name])

    def apply_theme(self, theme_name: str):
        self.theme_cls.theme_style = "Dark" if str(theme_name).lower() == "dark" else "Light"
        Window.clearcolor = self.ui("bg")

    def notify_data_changed(self, skip=None, force: bool = False):
        skip = set(skip or set())
        if not self.root:
            return
        for screen in self.root.screens:
            if screen.name in skip:
                continue
            if hasattr(screen, "queue_refresh"):
                screen.queue_refresh(force=force)

    def format_currency(self, amount):
        currency = self.db.get_currency() if self.db else "₽"
        return f"{currency}{float(amount):,.2f}"


if __name__ == "__main__":
    FinWiseApp().run()
