from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivy.uix.button import Button
from screens.base import VersionedScreen


class AccountsScreen(VersionedScreen):
    editing_account_id = 0

    def refresh_content(self):
        app = self.app()
        rows = app.db.get_accounts_with_stats()
        self.ids.total_balance_label.text = app.format_currency(app.db.get_total_balance())
        box = self.ids.accounts_box
        box.clear_widgets()
        if not rows:
            box.add_widget(self._empty_card())
        else:
            for row in rows:
                box.add_widget(self._account_card(row))
        self._update_form_state()

    def _empty_card(self):
        app = self.app()
        card = MDCard(style="filled", md_bg_color=app.ui("card"), radius=[20,20,20,20], padding=dp(14), size_hint_y=None, height=dp(72))
        card.add_widget(MDLabel(text="Счета пока не добавлены", theme_text_color="Custom", text_color=app.ui("text_soft")))
        return card

    def _account_card(self, row):
        app = self.app()
        card = MDCard(style="filled", md_bg_color=app.ui("card"), radius=[20,20,20,20], padding=dp(14), size_hint_y=None, height=dp(142))
        root = MDBoxLayout(orientation="vertical", spacing=dp(6))
        header = MDBoxLayout(size_hint_y=None, height=dp(28))
        header.add_widget(MDLabel(text=row["name"], theme_text_color="Custom", text_color=app.ui("text"), bold=True, shorten=True, max_lines=1))
        header.add_widget(MDLabel(text=app.format_currency(row["balance"]), halign="right", theme_text_color="Custom", text_color=app.ui("text"), size_hint_x=0.45))
        root.add_widget(header)
        root.add_widget(MDLabel(text=f"Доход: {app.format_currency(row['income'])}", theme_text_color="Custom", text_color=app.ui("success"), size_hint_y=None, height=dp(18)))
        root.add_widget(MDLabel(text=f"Расход: {app.format_currency(row['expense'])}", theme_text_color="Custom", text_color=app.ui("expense"), size_hint_y=None, height=dp(18)))
        actions = MDBoxLayout(size_hint_y=None, height=dp(32), spacing=dp(8))
        edit_btn = Button(text="Изменить", size_hint_x=None, width=dp(120), background_normal="", background_color=app.ui("card_alt"), color=app.ui("text"))
        edit_btn.bind(on_release=lambda *_: self.start_edit(int(row["id"])))
        delete_btn = Button(text="Удалить", size_hint_x=None, width=dp(120), background_normal="", background_color=app.ui("card_alt"), color=app.ui("expense"))
        delete_btn.bind(on_release=lambda *_: self.delete_account(int(row["id"])))
        actions.add_widget(edit_btn)
        actions.add_widget(delete_btn)
        actions.add_widget(MDBoxLayout())
        root.add_widget(actions)
        card.add_widget(root)
        return card

    def start_edit(self, account_id: int):
        row = self.app().db.get_account(account_id)
        if row is None:
            return
        self.editing_account_id = account_id
        self.ids.account_name.text = row["name"] or ""
        self.ids.account_balance.text = str(row["balance"] or "")
        self.ids.account_error.text = ""
        self._update_form_state()

    def cancel_edit(self):
        self.editing_account_id = 0
        self.ids.account_name.text = ""
        self.ids.account_balance.text = ""
        self.ids.account_error.text = ""
        self._update_form_state()

    def _update_form_state(self):
        self.ids.form_title.text = "Изменить счёт" if self.editing_account_id else "Добавить счёт"
        self.ids.save_btn.text = "Сохранить изменения" if self.editing_account_id else "Добавить счёт"
        self.ids.cancel_btn.disabled = not bool(self.editing_account_id)
        self.ids.cancel_btn.opacity = 1 if self.editing_account_id else 0.35

    def save_account(self):
        app = self.app()
        name = self.ids.account_name.text.strip()
        balance_text = self.ids.account_balance.text.strip().replace(",", ".")
        if not name:
            self.ids.account_error.text = "Введите название счёта"
            return
        try:
            balance = float(balance_text) if balance_text else 0.0
        except ValueError:
            self.ids.account_error.text = "Неверный баланс"
            return
        if self.editing_account_id:
            app.db.update_account(self.editing_account_id, name, balance)
        else:
            app.db.create_account(name, "cash", balance)
        self.cancel_edit()
        self.queue_refresh(force=True)
        app.notify_data_changed(skip={self.name})

    def delete_account(self, account_id: int):
        if self.editing_account_id == account_id:
            self.cancel_edit()
        self.app().db.delete_account(account_id)
        self.queue_refresh(force=True)
        self.app().notify_data_changed(skip={self.name})
