from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from screens.base import VersionedScreen


RU = {
    "Food": "Еда",
    "Transport": "Транспорт",
    "Subscriptions": "Подписки",
    "Shopping": "Покупки",
    "Health": "Здоровье",
    "Home": "Дом",
    "Entertainment": "Развлечения",
    "Other": "Другое",
    "Salary": "Зарплата",
    "Freelance": "Фриланс",
    "Gift": "Подарок",
    "Investments": "Инвестиции",
}


class DashboardScreen(VersionedScreen):
    def refresh_content(self):
        app = self.app()
        summary = app.db.get_monthly_summary()
        self.ids.balance_label.text = app.format_currency(app.db.get_total_balance())
        self.ids.income_label.text = app.format_currency(summary["income"])
        self.ids.expense_label.text = app.format_currency(summary["expenses"])
        self.ids.updated_label.text = f"Операций в этом месяце: {summary['count']}"
        self._load_recent_transactions()

    def _load_recent_transactions(self):
        app = self.app()
        box = self.ids.recent_box
        box.clear_widgets()
        rows = app.db.get_recent_transactions(limit=6)
        if not rows:
            box.add_widget(self._empty_card("Пока нет операций", "Добавьте первую запись"))
            return
        for row in rows:
            amount = float(row["amount"] or 0)
            trans_type = row["type"]
            box.add_widget(
                self._transaction_card(
                    RU.get(row["category_name"] or "", row["category_name"] or "Без категории"),
                    f"{app.db.format_display_date(row['date_created'])} • {row['note'] or 'Без описания'}",
                    f"{'+' if trans_type == 'income' else '−'}{app.format_currency(amount)}",
                    app.ui("success") if trans_type == "income" else app.ui("expense"),
                )
            )

    def _empty_card(self, title, subtitle):
        app = self.app()
        card = MDCard(style="filled", md_bg_color=app.ui("card"), radius=[18, 18, 18, 18], padding=dp(14), size_hint_y=None, height=dp(80))
        line = MDBoxLayout(orientation="vertical", spacing=dp(2))
        line.add_widget(MDLabel(text=title, theme_text_color="Custom", text_color=app.ui("text"), bold=True))
        line.add_widget(MDLabel(text=subtitle, theme_text_color="Custom", text_color=app.ui("text_soft")))
        card.add_widget(line)
        return card

    def _transaction_card(self, title, subtitle, amount, amount_color):
        app = self.app()
        card = MDCard(style="filled", md_bg_color=app.ui("card"), radius=[18, 18, 18, 18], padding=dp(14), size_hint_y=None, height=dp(80))
        line = MDBoxLayout(spacing=dp(10))
        left = MDBoxLayout(orientation="vertical", spacing=dp(2))
        left.add_widget(MDLabel(text=title, theme_text_color="Custom", text_color=app.ui("text"), bold=True, shorten=True, max_lines=1))
        left.add_widget(MDLabel(text=subtitle, theme_text_color="Custom", text_color=app.ui("text_soft"), shorten=True, max_lines=1))
        line.add_widget(left)
        line.add_widget(MDLabel(text=amount, halign="right", theme_text_color="Custom", text_color=amount_color, size_hint_x=0.38))
        card.add_widget(line)
        return card

    def open_add(self, trans_type: str):
        screen = self.manager.get_screen("add_transaction")
        screen.prepare_new(trans_type)
        self.manager.current = "add_transaction"
