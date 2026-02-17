"""Dashboard view — summary cards and recent invoices."""

import customtkinter as ctk
from decimal import Decimal

from app.models.enums import InvoiceState
from app.services import persistence
from app.services.overdue import check_overdue
from app.services.vat import czech_round


class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, navigate_cb=None):
        super().__init__(parent, fg_color="transparent")
        self.navigate_cb = navigate_cb
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Title
        title = ctk.CTkLabel(self, text="Přehled", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(anchor="w", padx=20, pady=(20, 10))

        # Cards row
        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.card_open = self._create_card(self.cards_frame, "Otevřené", "#3B82F6")
        self.card_overdue = self._create_card(self.cards_frame, "Po splatnosti", "#EF4444")
        self.card_sent = self._create_card(self.cards_frame, "Odeslané", "#F59E0B")
        self.card_total = self._create_card(self.cards_frame, "Celkem faktur", "#22C55E")

        for i in range(4):
            self.cards_frame.grid_columnconfigure(i, weight=1)

        # Recent invoices
        ctk.CTkLabel(
            self, text="Poslední faktury",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(10, 5))

        self.recent_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.recent_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def _create_card(self, parent, title: str, color: str) -> dict:
        col = len(parent.grid_slaves())
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")

        lbl_title = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=11),
                                 text_color="gray")
        lbl_title.pack(anchor="w", padx=12, pady=(10, 0))

        lbl_count = ctk.CTkLabel(frame, text="0", font=ctk.CTkFont(size=22, weight="bold"))
        lbl_count.pack(anchor="w", padx=12)

        lbl_amount = ctk.CTkLabel(frame, text="0 Kč",
                                  font=ctk.CTkFont(size=12, weight="bold"),
                                  text_color=color)
        lbl_amount.pack(anchor="w", padx=12, pady=(0, 10))

        return {"count": lbl_count, "amount": lbl_amount}

    def refresh(self):
        # Run overdue check
        check_overdue()

        invoices = persistence.load_invoices()

        states = {
            "OPEN": (self.card_open, []),
            "OVERDUE": (self.card_overdue, []),
            "SENT": (self.card_sent, []),
        }
        for inv in invoices:
            if inv.state in states:
                states[inv.state][1].append(inv)

        for state_name, (card, inv_list) in states.items():
            card["count"].configure(text=str(len(inv_list)))
            total = sum((i.total for i in inv_list), Decimal("0"))
            card["amount"].configure(text=self._fmt_currency(total))

        self.card_total["count"].configure(text=str(len(invoices)))
        total_all = sum((i.total for i in invoices), Decimal("0"))
        self.card_total["amount"].configure(text=self._fmt_currency(total_all))

        # Recent invoices list
        for widget in self.recent_frame.winfo_children():
            widget.destroy()

        recent = sorted(invoices, key=lambda i: i.created_at, reverse=True)[:15]
        for inv in recent:
            row = ctk.CTkFrame(self.recent_frame, corner_radius=8)
            row.pack(fill="x", pady=2)

            state_enum = InvoiceState[inv.state]
            badge = ctk.CTkLabel(
                row, text=state_enum.label,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=state_enum.color,
                width=80
            )
            badge.pack(side="left", padx=(10, 5), pady=6)

            ctk.CTkLabel(
                row, text=inv.invoice_number,
                font=ctk.CTkFont(size=12, weight="bold"), width=100
            ).pack(side="left", padx=5, pady=6)

            subject = persistence.get_subject(inv.subject_registration_no or "")
            name = subject.name if subject else "—"
            ctk.CTkLabel(row, text=name, font=ctk.CTkFont(size=11),
                         text_color="gray").pack(side="left", padx=5, pady=6, expand=True,
                                                  anchor="w")

            ctk.CTkLabel(
                row, text=self._fmt_currency(inv.total),
                font=ctk.CTkFont(size=12, weight="bold"), width=120
            ).pack(side="right", padx=10, pady=6)

    @staticmethod
    def _fmt_currency(value: Decimal) -> str:
        rounded = czech_round(value)
        s = f"{rounded:,.2f}".replace(",", " ").replace(".", ",")
        return f"{s} Kč"
