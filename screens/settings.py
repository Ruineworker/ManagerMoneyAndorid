import os
import shutil

from screens.base import VersionedScreen


class SettingsScreen(VersionedScreen):
    def refresh_content(self):
        app = self.app()
        self.ids.currency_spinner.text = app.db.get_currency()
        self.ids.theme_spinner.text = "Тёмная" if app.db.get_theme() == "dark" else "Светлая"
        self.ids.info_label.text = ""

    def set_currency(self, value: str):
        if value and value != "Выберите валюту" and value != self.app().db.get_currency():
            self.app().db.set_currency(value)
            self.app().notify_data_changed(skip={self.name})

    def set_theme(self, value: str):
        if value not in ("Светлая", "Тёмная"):
            return
        theme = "dark" if value == "Тёмная" else "light"
        app = self.app()
        if theme == app.db.get_theme():
            return
        app.db.set_theme(theme)
        app.apply_theme(theme)
        app.notify_data_changed(skip={self.name}, force=True)

    def backup_database(self):
        app = self.app()
        backup_path = "finwise_backup.db"
        shutil.copy2(app.db.db_name, backup_path)
        self.ids.info_label.text = f"Резервная копия создана: {backup_path}"

    def reset_demo(self):
        app = self.app()
        app.db.close()
        if os.path.exists(app.db.db_name):
            os.remove(app.db.db_name)
        from libs.database import Database
        from libs.models import init_db

        app.db = Database()
        init_db(app.db)
        app.db.populate_demo_data()
        app.apply_theme(app.db.get_theme())
        app.notify_data_changed(force=True)
        self.ids.info_label.text = "Демо-данные восстановлены"
