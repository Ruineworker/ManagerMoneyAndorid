from screens.base import VersionedScreen


class CategoriesScreen(VersionedScreen):
    category_type = "expense"

    def set_type(self, value: str):
        if self.category_type == value:
            return
        self.category_type = value
        self.queue_refresh(force=True)

    def refresh_content(self):
        app = self.app()
        rows = app.db.get_categories(self.category_type)
        self._update_buttons()
        self.ids.categories_rv.data = [
            {
                "icon_text": row["icon"],
                "title_text": row["name"],
                "subtitle_text": "Доход" if row["type"] == "income" else "Расход",
            }
            for row in rows
        ]

    def _update_buttons(self):
        app = self.app()
        for widget_id, value in (("expense_btn", "expense"), ("income_btn", "income")):
            btn = self.ids[widget_id]
            active = self.category_type == value
            btn.background_color = app.ui("primary") if active else app.ui("card_alt")
            btn.color = (0.08, 0.14, 0.16, 1) if active else app.ui("text")
