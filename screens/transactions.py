from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
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


class TransactionsScreen(VersionedScreen):
    filter_type = "all"
    search_text = ""
    _search_trigger = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._search_trigger = Clock.create_trigger(self._apply_filters, 0.2)

    def on_kv_post(self, *args):
        self.ids.search_input.bind(text=self._on_search_text)
        return super().on_kv_post(*args)

    def _on_search_text(self, instance, value):
        self.search_text = value.strip()
        self._search_trigger()

    def set_filter(self, value: str):
        if self.filter_type == value:
            return
        self.filter_type = value
        self._apply_filters()

    def refresh_content(self):
        self._apply_filters()

    def _apply_filters(self, *_):
        app = self.app()
        self._update_filter_buttons()
        filters = {}
        if self.filter_type != "all":
            filters["type"] = self.filter_type
        if self.search_text:
            filters["search"] = self.search_text
        rows = app.db.get_transactions(limit=300, filters=filters)
        data = []
        for row in rows:
            trans_type = row["type"]
            amount = float(row["amount"] or 0)
            data.append(
                {
                    "trans_id": int(row["id"]),
                    "icon_text": row["category_icon"] or "tag",
                    "category_text": RU.get(row["category_name"] or "", row["category_name"] or "Без категории"),
                    "meta_text": f"{app.db.format_display_date(row['date_created'])} • {row['account_name'] or 'Счёт'}",
                    "note_text": row["note"] or "Без описания",
                    "amount_text": f"{'+' if trans_type == 'income' else '−'}{app.format_currency(amount)}",
                    "amount_color": app.ui("success") if trans_type == "income" else app.ui("expense"),
                }
            )
        if not data:
            data = [{
                "trans_id": 0,
                "icon_text": "magnify-close",
                "category_text": "Ничего не найдено",
                "meta_text": "Измените поиск или фильтр",
                "note_text": "",
                "amount_text": "",
                "amount_color": app.ui("text_soft"),
                "disabled_row": True,
            }]
        self.ids.transactions_rv.data = data
        self.ids.results_label.text = f"Найдено операций: {0 if data and data[0].get('disabled_row') else len(data)}"

    def _update_filter_buttons(self):
        app = self.app()
        for name, value in (("all_btn", "all"), ("income_btn", "income"), ("expense_btn", "expense")):
            btn = self.ids[name]
            active = self.filter_type == value
            btn.background_color = app.ui("primary") if active else app.ui("card_alt")
            btn.color = (0.08, 0.14, 0.16, 1) if active else app.ui("text")

    def open_new(self):
        screen = self.manager.get_screen("add_transaction")
        screen.prepare_new("expense")
        self.manager.current = "add_transaction"

    def edit_transaction(self, trans_id: int):
        if not trans_id:
            return
        screen = self.manager.get_screen("add_transaction")
        screen.set_edit_transaction(trans_id)
        self.manager.current = "add_transaction"

    def delete_transaction(self, trans_id: int):
        if not trans_id:
            return
        self.app().db.delete_transaction(trans_id)
        self.queue_refresh(force=True)
        self.app().notify_data_changed(skip={self.name})
