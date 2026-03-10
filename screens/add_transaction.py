from datetime import datetime

from screens.base import VersionedScreen


class AddTransactionScreen(VersionedScreen):
    editing_transaction_id = 0
    current_type = "expense"

    def on_kv_post(self, *args):
        self.ids.type_spinner.bind(text=lambda *_: self._sync_categories())
        return super().on_kv_post(*args)

    def prepare_new(self, trans_type: str = "expense"):
        self.editing_transaction_id = 0
        self.current_type = trans_type
        self._fill_form(None)
        self.queue_refresh(force=True)

    def set_edit_transaction(self, trans_id: int):
        self.editing_transaction_id = int(trans_id)
        self.queue_refresh(force=True)

    def refresh_content(self):
        if self.editing_transaction_id:
            self._load_edit_data()
        else:
            self._load_reference_data()
            self._set_default_type(self.current_type)

    def _load_reference_data(self):
        app = self.app()
        account_rows = app.db.get_accounts()
        self._account_values = [row["name"] for row in account_rows]
        self._account_map = {row["name"]: int(row["id"]) for row in account_rows}
        self.ids.account_spinner.values = self._account_values
        if self._account_values and self.ids.account_spinner.text not in self._account_values:
            self.ids.account_spinner.text = self._account_values[0]
        self._sync_categories()
        self.ids.form_error.text = ""

    def _set_default_type(self, trans_type: str):
        self.ids.type_spinner.text = "Доход" if trans_type == "income" else "Расход"

    def _sync_categories(self):
        app = self.app()
        trans_type = "income" if self.ids.type_spinner.text == "Доход" else "expense"
        rows = app.db.get_categories(trans_type)
        self._category_values = [row["name"] for row in rows]
        self._category_map = {row["name"]: int(row["id"]) for row in rows}
        self.ids.category_spinner.values = self._category_values
        if self._category_values and self.ids.category_spinner.text not in self._category_values:
            self.ids.category_spinner.text = self._category_values[0]

    def _load_edit_data(self):
        app = self.app()
        self._load_reference_data()
        row = app.db.get_transaction(self.editing_transaction_id)
        if row is None:
            self.prepare_new("expense")
            return
        self.current_type = row["type"]
        self._fill_form(row)

    def _fill_form(self, row):
        self._load_reference_data()
        if row is None:
            self.ids.title_label.text = "Новая операция"
            self.ids.save_btn.text = "Сохранить"
            self.ids.type_spinner.text = "Доход" if self.current_type == "income" else "Расход"
            self._sync_categories()
            self.ids.amount_input.text = ""
            self.ids.note_input.text = ""
            self.ids.date_input.text = datetime.now().strftime("%d-%m-%Y")
            return
        self.ids.title_label.text = "Редактировать операцию"
        self.ids.save_btn.text = "Сохранить изменения"
        self.ids.type_spinner.text = "Доход" if row["type"] == "income" else "Расход"
        self._sync_categories()
        if row["category_name"] in self._category_values:
            self.ids.category_spinner.text = row["category_name"]
        if row["account_name"] in self._account_values:
            self.ids.account_spinner.text = row["account_name"]
        self.ids.amount_input.text = f"{float(row['amount']):.2f}".rstrip("0").rstrip(".")
        self.ids.note_input.text = row["note"] or ""
        self.ids.date_input.text = self.app().db.format_display_date(row["date_created"])
        self.ids.form_error.text = ""

    def save_transaction(self):
        trans_type = "income" if self.ids.type_spinner.text == "Доход" else "expense"
        amount_text = self.ids.amount_input.text.strip().replace(",", ".")
        note = self.ids.note_input.text.strip()
        category_name = self.ids.category_spinner.text
        account_name = self.ids.account_spinner.text
        date_text = self.ids.date_input.text.strip()

        if not amount_text:
            self.ids.form_error.text = "Введите сумму"
            return
        try:
            amount = float(amount_text)
        except ValueError:
            self.ids.form_error.text = "Сумма указана неверно"
            return
        if amount <= 0:
            self.ids.form_error.text = "Сумма должна быть больше нуля"
            return
        if category_name not in self._category_map:
            self.ids.form_error.text = "Выберите категорию"
            return
        if account_name not in self._account_map:
            self.ids.form_error.text = "Выберите счёт"
            return

        app = self.app()
        category_id = self._category_map[category_name]
        account_id = self._account_map[account_name]
        if self.editing_transaction_id:
            app.db.update_transaction(
                self.editing_transaction_id,
                trans_type,
                amount,
                category_id,
                account_id,
                note,
                date_text,
            )
        else:
            app.db.create_transaction(trans_type, amount, category_id, account_id, note, date_text)
        self.ids.form_error.text = ""
        self.editing_transaction_id = 0
        app.notify_data_changed()
        self.manager.current = "transactions"

    def go_back(self):
        self.manager.current = "transactions"
