from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from screens.base import VersionedScreen


class AnalyticsScreen(VersionedScreen):
    def refresh_content(self):
        app = self.app()
        snapshot = app.db.get_analytics_snapshot()
        summary = snapshot["summary"]
        self.ids.income_total.text = app.format_currency(summary["income"])
        self.ids.expense_total.text = app.format_currency(summary["expenses"])
        self.ids.net_total.text = app.format_currency(summary["income"] - summary["expenses"])

        self._fill_breakdown(self.ids.expense_box, snapshot["expense_breakdown"])
        self._fill_breakdown(self.ids.income_box, snapshot["income_breakdown"])
        self._fill_trend(self.ids.trend_box, snapshot["trend"])

    def _fill_breakdown(self, box, items):
        box.clear_widgets()
        if not items:
            box.add_widget(self._empty_card("Нет данных за текущий месяц"))
            return
        for item in items:
            box.add_widget(self._breakdown_card(item))

    def _fill_trend(self, box, items):
        box.clear_widgets()
        if not items:
            box.add_widget(self._empty_card("История ещё не накопилась"))
            return
        for item in items:
            box.add_widget(self._trend_card(item))

    def _empty_card(self, text):
        app = self.app()
        card = MDCard(style="filled", md_bg_color=app.ui("card"), radius=[18,18,18,18], padding=dp(14), size_hint_y=None, height=dp(60))
        card.add_widget(MDLabel(text=text, theme_text_color="Custom", text_color=app.ui("text_soft")))
        return card

    def _breakdown_card(self, item):
        app = self.app()
        percent = int(round(item["share"] * 100)) if item.get("share") else 0
        card = MDCard(style="filled", md_bg_color=app.ui("card"), radius=[18,18,18,18], padding=dp(14), size_hint_y=None, height=dp(72))
        line = MDBoxLayout(spacing=dp(10))
        left = MDBoxLayout(orientation="vertical", spacing=dp(2))
        left.add_widget(MDLabel(text=item["category_name"], theme_text_color="Custom", text_color=app.ui("text"), bold=True, shorten=True, max_lines=1))
        left.add_widget(MDLabel(text=f"{item['items_count']} операций • {percent}%", theme_text_color="Custom", text_color=app.ui("text_soft"), shorten=True, max_lines=1))
        line.add_widget(left)
        line.add_widget(MDLabel(text=app.format_currency(item["total"]), halign="right", theme_text_color="Custom", text_color=app.ui("text"), size_hint_x=0.38))
        card.add_widget(line)
        return card

    def _trend_card(self, item):
        app = self.app()
        card = MDCard(style="filled", md_bg_color=app.ui("card_alt"), radius=[18,18,18,18], padding=dp(14), size_hint_y=None, height=dp(72))
        box = MDBoxLayout(orientation="vertical", spacing=dp(2))
        box.add_widget(MDLabel(text=item["month"], theme_text_color="Custom", text_color=app.ui("text"), bold=True))
        box.add_widget(MDLabel(text=f"Доход: {app.format_currency(item['income'])}", theme_text_color="Custom", text_color=app.ui("success")))
        box.add_widget(MDLabel(text=f"Расход: {app.format_currency(item['expense'])}", theme_text_color="Custom", text_color=app.ui("expense")))
        card.add_widget(box)
        return card
