"""Invoice list, detail, and form views."""

import os
import subprocess
import tkinter as tk
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

import customtkinter as ctk

from app.models.enums import InvoiceState, InvoiceType, VATRate, SupplyCode
from app.models.invoice import Invoice, InvoiceLine
from app.services import persistence
from app.services.vat import czech_round
from app.services.pdf_renderer import render_invoice


class InvoiceListView(ctk.CTkFrame):
    def __init__(self, parent, navigate_cb=None):
        super().__init__(parent, fg_color="transparent")
        self.navigate_cb = navigate_cb
        self._filter_state = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(header, text="Faktury",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")

        ctk.CTkButton(header, text="+ Nová faktura", width=140,
                      command=self._open_new_form).pack(side="right")

        # Filter bar
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=(0, 10))

        self._filter_buttons = {}
        btn_all = ctk.CTkButton(filter_frame, text="Vše", width=70,
                                fg_color="#3B82F6",
                                command=lambda: self._set_filter(None))
        btn_all.pack(side="left", padx=2)
        self._filter_buttons[None] = btn_all

        for state in InvoiceState:
            btn = ctk.CTkButton(
                filter_frame, text=state.label, width=90,
                fg_color="gray",
                command=lambda s=state: self._set_filter(s)
            )
            btn.pack(side="left", padx=2)
            self._filter_buttons[state] = btn

        # Search
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self.refresh())
        ctk.CTkEntry(filter_frame, textvariable=self._search_var,
                     placeholder_text="Hledat...", width=200).pack(side="right", padx=5)

        # List
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def _set_filter(self, state):
        self._filter_state = state
        for s, btn in self._filter_buttons.items():
            btn.configure(fg_color="#3B82F6" if s == state else "gray")
        self.refresh()

    def refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        invoices = persistence.load_invoices()

        if self._filter_state:
            invoices = [i for i in invoices if i.state == self._filter_state.name]

        search = self._search_var.get().lower()
        if search:
            invoices = [i for i in invoices if
                        search in i.invoice_number.lower() or
                        search in (persistence.get_subject(
                            i.subject_registration_no or "")
                            or type("", (), {"name": ""})()).name.lower()]

        invoices.sort(key=lambda i: i.created_at, reverse=True)

        for inv in invoices:
            self._create_row(inv)

    def _create_row(self, inv: Invoice):
        row = ctk.CTkFrame(self.list_frame, corner_radius=8, cursor="hand2")
        row.pack(fill="x", pady=2)
        row.bind("<Button-1>", lambda e, i=inv: self._open_detail(i))

        state_enum = InvoiceState[inv.state]
        badge = ctk.CTkLabel(
            row, text=state_enum.label,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=state_enum.color, width=80
        )
        badge.pack(side="left", padx=(10, 5), pady=8)
        badge.bind("<Button-1>", lambda e, i=inv: self._open_detail(i))

        num = ctk.CTkLabel(row, text=inv.invoice_number,
                           font=ctk.CTkFont(size=12, weight="bold"), width=100)
        num.pack(side="left", padx=5, pady=8)
        num.bind("<Button-1>", lambda e, i=inv: self._open_detail(i))

        subject = persistence.get_subject(inv.subject_registration_no or "")
        name = subject.name if subject else "—"
        name_lbl = ctk.CTkLabel(row, text=name, font=ctk.CTkFont(size=11),
                                text_color="gray")
        name_lbl.pack(side="left", padx=5, pady=8, expand=True, anchor="w")
        name_lbl.bind("<Button-1>", lambda e, i=inv: self._open_detail(i))

        due_str = _fmt_date(inv.due_date)
        ctk.CTkLabel(row, text=due_str, font=ctk.CTkFont(size=10),
                     text_color="gray", width=80).pack(side="right", padx=5, pady=8)

        total_lbl = ctk.CTkLabel(
            row, text=_fmt_currency(inv.total),
            font=ctk.CTkFont(size=12, weight="bold"), width=120
        )
        total_lbl.pack(side="right", padx=10, pady=8)
        total_lbl.bind("<Button-1>", lambda e, i=inv: self._open_detail(i))

    def _open_detail(self, inv: Invoice):
        if self.navigate_cb:
            self.navigate_cb("invoice_detail", inv)

    def _open_new_form(self):
        if self.navigate_cb:
            self.navigate_cb("invoice_form", None)


class InvoiceDetailView(ctk.CTkFrame):
    """Detail view for a single invoice."""

    def __init__(self, parent, invoice: Invoice, navigate_cb=None):
        super().__init__(parent, fg_color="transparent")
        self.invoice = invoice
        self.navigate_cb = navigate_cb
        self._build_ui()

    def _build_ui(self):
        inv = self.invoice
        subject = persistence.get_subject(inv.subject_registration_no or "")
        lines = inv.get_lines()
        lines.sort(key=lambda l: l.sort_order)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Back button
        ctk.CTkButton(scroll, text="< Zpět", width=80, fg_color="gray",
                      command=lambda: self.navigate_cb("invoices", None) if self.navigate_cb else None
                      ).pack(anchor="w", pady=(0, 10))

        # Header
        type_label = InvoiceType[inv.type].label.upper()
        state_enum = InvoiceState[inv.state]

        header = ctk.CTkFrame(scroll, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text=f"{type_label} č. {inv.invoice_number}",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text=state_enum.label,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=state_enum.color).pack(side="right")

        if inv.is_locked:
            ctk.CTkLabel(scroll, text="🔒 Faktura je uzamčena pro účetní export",
                         font=ctk.CTkFont(size=11),
                         text_color="#D97706").pack(anchor="w", pady=5)

        # Dates
        dates_frame = ctk.CTkFrame(scroll, corner_radius=8)
        dates_frame.pack(fill="x", pady=10)
        for label, val in [
            ("Datum vystavení:", _fmt_date(inv.issued_date)),
            ("DUZP:", _fmt_date(inv.taxable_supply_date)),
            ("Splatnost:", _fmt_date(inv.due_date)),
        ]:
            row = ctk.CTkFrame(dates_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=11, weight="bold"),
                         width=160).pack(side="left")
            ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=11)).pack(side="left")

        # Subject
        if subject:
            sub_frame = ctk.CTkFrame(scroll, corner_radius=8)
            sub_frame.pack(fill="x", pady=10)
            ctk.CTkLabel(sub_frame, text="Odběratel:",
                         font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(8, 2))
            ctk.CTkLabel(sub_frame, text=subject.name,
                         font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12)
            ctk.CTkLabel(sub_frame, text=subject.formatted_address,
                         font=ctk.CTkFont(size=10)).pack(anchor="w", padx=12)
            ctk.CTkLabel(sub_frame, text=f"IČO: {subject.registration_no}",
                         font=ctk.CTkFont(size=10)).pack(anchor="w", padx=12)
            if subject.vat_no:
                ctk.CTkLabel(sub_frame, text=f"DIČ: {subject.vat_no}",
                             font=ctk.CTkFont(size=10)).pack(anchor="w", padx=12, pady=(0, 8))

        # Line items
        items_frame = ctk.CTkFrame(scroll, corner_radius=8)
        items_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(items_frame, text="Položky",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))

        # Table header
        th = ctk.CTkFrame(items_frame, fg_color="transparent")
        th.pack(fill="x", padx=12)
        for text, w in [("Popis", 200), ("Mn.", 50), ("Cena/ks", 80), ("DPH", 45), ("Celkem", 90)]:
            ctk.CTkLabel(th, text=text, font=ctk.CTkFont(size=9, weight="bold"),
                         width=w).pack(side="left")

        for line in lines:
            tr = ctk.CTkFrame(items_frame, fg_color="transparent")
            tr.pack(fill="x", padx=12, pady=1)
            ctk.CTkLabel(tr, text=line.item_description, font=ctk.CTkFont(size=9),
                         width=200, anchor="w").pack(side="left")
            ctk.CTkLabel(tr, text=f"{line.quantity} {line.unit}",
                         font=ctk.CTkFont(size=9), width=50).pack(side="left")
            ctk.CTkLabel(tr, text=_fmt_currency(line.unit_price),
                         font=ctk.CTkFont(size=9), width=80).pack(side="left")
            ctk.CTkLabel(tr, text=line.vat_rate_enum.label,
                         font=ctk.CTkFont(size=9), width=45).pack(side="left")
            ctk.CTkLabel(tr, text=_fmt_currency(line.line_total_with_vat),
                         font=ctk.CTkFont(size=9, weight="bold"), width=90).pack(side="left")

        # Totals
        total_frame = ctk.CTkFrame(scroll, corner_radius=8)
        total_frame.pack(fill="x", pady=10)
        row = ctk.CTkFrame(total_frame, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(row, text="Celkem k úhradě:",
                     font=ctk.CTkFont(size=14)).pack(side="left")
        ctk.CTkLabel(row, text=_fmt_currency(inv.total),
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="right")

        # Actions
        actions = ctk.CTkFrame(scroll, fg_color="transparent")
        actions.pack(fill="x", pady=10)

        if inv.can_transition(InvoiceState.SENT):
            ctk.CTkButton(actions, text="Odeslat", width=120,
                          command=lambda: self._transition(InvoiceState.SENT)).pack(side="left", padx=5)

        if inv.can_transition(InvoiceState.PAID):
            ctk.CTkButton(actions, text="Zaplaceno", width=120, fg_color="#22C55E",
                          command=lambda: self._transition(InvoiceState.PAID)).pack(side="left", padx=5)

        ctk.CTkButton(actions, text="Exportovat PDF", width=140, fg_color="#6366F1",
                      command=self._export_pdf).pack(side="right", padx=5)

        if not inv.is_locked and inv.state_enum == InvoiceState.OPEN:
            ctk.CTkButton(actions, text="Smazat", width=100, fg_color="#EF4444",
                          command=self._delete).pack(side="right", padx=5)

    def _transition(self, new_state: InvoiceState):
        self.invoice.transition(new_state)
        persistence.upsert_invoice(self.invoice)
        if self.navigate_cb:
            self.navigate_cb("invoice_detail", self.invoice)

    def _export_pdf(self):
        exports_dir = persistence.get_exports_dir()
        path = exports_dir / f"{self.invoice.invoice_number}.pdf"
        render_invoice(self.invoice, path)
        # Open the file
        if os.name == "nt":
            os.startfile(str(path))
        else:
            subprocess.run(["xdg-open", str(path)], check=False)

    def _delete(self):
        persistence.delete_invoice(self.invoice.invoice_number)
        if self.navigate_cb:
            self.navigate_cb("invoices", None)


class InvoiceFormView(ctk.CTkFrame):
    """New invoice creation form."""

    def __init__(self, parent, navigate_cb=None):
        super().__init__(parent, fg_color="transparent")
        self.navigate_cb = navigate_cb
        self._lines: list[dict] = [self._empty_line()]
        self._build_ui()

    @staticmethod
    def _empty_line() -> dict:
        return {"desc": "", "qty": "1", "price": "0", "vat": "STANDARD", "unit": "ks"}

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Back
        ctk.CTkButton(scroll, text="< Zpět", width=80, fg_color="gray",
                      command=lambda: self.navigate_cb("invoices", None) if self.navigate_cb else None
                      ).pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(scroll, text="Nová faktura",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w", pady=(0, 15))

        # Type
        ctk.CTkLabel(scroll, text="Typ faktury:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.type_var = tk.StringVar(value="STANDARD")
        ctk.CTkOptionMenu(scroll, values=[t.name for t in InvoiceType],
                          variable=self.type_var, width=200).pack(anchor="w", pady=(0, 10))

        # Subject
        ctk.CTkLabel(scroll, text="Odběratel:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        subjects = persistence.load_subjects()
        subject_names = ["— Vyberte —"] + [f"{s.name} ({s.registration_no})" for s in subjects]
        self._subjects = subjects
        self.subject_var = tk.StringVar(value=subject_names[0])
        ctk.CTkOptionMenu(scroll, values=subject_names,
                          variable=self.subject_var, width=400).pack(anchor="w", pady=(0, 10))

        # Dates
        today = date.today()
        due = today + timedelta(days=14)

        dates_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        dates_frame.pack(fill="x", pady=5)

        self.issued_var = tk.StringVar(value=today.isoformat())
        self.duzp_var = tk.StringVar(value=today.isoformat())
        self.due_var = tk.StringVar(value=due.isoformat())

        for label, var in [
            ("Datum vystavení:", self.issued_var),
            ("DUZP:", self.duzp_var),
            ("Splatnost:", self.due_var),
        ]:
            f = ctk.CTkFrame(dates_frame, fg_color="transparent")
            f.pack(side="left", padx=(0, 15))
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10)).pack(anchor="w")
            ctk.CTkEntry(f, textvariable=var, width=120).pack(anchor="w")

        # Payment
        pay_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        pay_frame.pack(fill="x", pady=10)

        f1 = ctk.CTkFrame(pay_frame, fg_color="transparent")
        f1.pack(side="left", padx=(0, 15))
        ctk.CTkLabel(f1, text="Variabilní symbol:", font=ctk.CTkFont(size=10)).pack(anchor="w")
        self.vs_var = tk.StringVar()
        ctk.CTkEntry(f1, textvariable=self.vs_var, width=140).pack(anchor="w")

        f2 = ctk.CTkFrame(pay_frame, fg_color="transparent")
        f2.pack(side="left", padx=(0, 15))
        ctk.CTkLabel(f2, text="Číslo účtu:", font=ctk.CTkFont(size=10)).pack(anchor="w")
        self.account_var = tk.StringVar()
        ctk.CTkEntry(f2, textvariable=self.account_var, width=200).pack(anchor="w")

        # Line items
        ctk.CTkLabel(scroll, text="Položky:",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(15, 5))

        self.lines_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.lines_frame.pack(fill="x")

        self._line_widgets: list[dict] = []
        self._rebuild_lines()

        ctk.CTkButton(scroll, text="+ Přidat položku", width=140, fg_color="gray",
                      command=self._add_line).pack(anchor="w", pady=5)

        # Note
        ctk.CTkLabel(scroll, text="Poznámka:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", pady=(10, 0))
        self.note_var = tk.StringVar()
        ctk.CTkEntry(scroll, textvariable=self.note_var, width=500).pack(anchor="w", pady=(0, 15))

        # Total display
        self.total_label = ctk.CTkLabel(scroll, text="Celkem: 0 Kč",
                                        font=ctk.CTkFont(size=18, weight="bold"))
        self.total_label.pack(anchor="e", pady=10)

        # Submit
        ctk.CTkButton(scroll, text="Vytvořit fakturu", width=200,
                      fg_color="#22C55E", command=self._submit).pack(anchor="e")

    def _rebuild_lines(self):
        for w in self.lines_frame.winfo_children():
            w.destroy()
        self._line_widgets.clear()

        # Header
        hdr = ctk.CTkFrame(self.lines_frame, fg_color="transparent")
        hdr.pack(fill="x")
        for text, w in [("Popis", 200), ("Množství", 60), ("Cena", 80), ("DPH", 80), ("Jedn.", 50)]:
            ctk.CTkLabel(hdr, text=text, font=ctk.CTkFont(size=9, weight="bold"),
                         width=w).pack(side="left", padx=2)

        for i, line_data in enumerate(self._lines):
            row = ctk.CTkFrame(self.lines_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)

            desc_var = tk.StringVar(value=line_data["desc"])
            qty_var = tk.StringVar(value=line_data["qty"])
            price_var = tk.StringVar(value=line_data["price"])
            vat_var = tk.StringVar(value=line_data["vat"])
            unit_var = tk.StringVar(value=line_data["unit"])

            for var in (desc_var, qty_var, price_var, vat_var, unit_var):
                var.trace_add("write", lambda *_: self._update_total())

            ctk.CTkEntry(row, textvariable=desc_var, width=200).pack(side="left", padx=2)
            ctk.CTkEntry(row, textvariable=qty_var, width=60).pack(side="left", padx=2)
            ctk.CTkEntry(row, textvariable=price_var, width=80).pack(side="left", padx=2)
            ctk.CTkOptionMenu(row, values=[r.name for r in VATRate],
                              variable=vat_var, width=80).pack(side="left", padx=2)
            ctk.CTkEntry(row, textvariable=unit_var, width=50).pack(side="left", padx=2)

            if len(self._lines) > 1:
                ctk.CTkButton(row, text="×", width=30, fg_color="#EF4444",
                              command=lambda idx=i: self._remove_line(idx)).pack(side="left", padx=2)

            self._line_widgets.append({
                "desc": desc_var, "qty": qty_var, "price": price_var,
                "vat": vat_var, "unit": unit_var
            })

    def _add_line(self):
        self._sync_lines()
        self._lines.append(self._empty_line())
        self._rebuild_lines()

    def _remove_line(self, idx):
        self._sync_lines()
        if len(self._lines) > 1:
            self._lines.pop(idx)
        self._rebuild_lines()

    def _sync_lines(self):
        for i, widgets in enumerate(self._line_widgets):
            if i < len(self._lines):
                self._lines[i] = {
                    "desc": widgets["desc"].get(),
                    "qty": widgets["qty"].get(),
                    "price": widgets["price"].get(),
                    "vat": widgets["vat"].get(),
                    "unit": widgets["unit"].get(),
                }

    def _update_total(self):
        total = Decimal("0")
        for widgets in self._line_widgets:
            try:
                qty = Decimal(widgets["qty"].get() or "0")
                price = Decimal(widgets["price"].get() or "0")
                rate = VATRate[widgets["vat"].get()]
                line_total = qty * price
                total += line_total + line_total * rate.multiplier
            except (InvalidOperation, KeyError):
                pass
        self.total_label.configure(text=f"Celkem: {_fmt_currency(czech_round(total))}")

    def _submit(self):
        self._sync_lines()

        number = persistence.next_invoice_number()
        subject_text = self.subject_var.get()
        subject_reg = None
        if subject_text != "— Vyberte —":
            for s in self._subjects:
                if f"{s.name} ({s.registration_no})" == subject_text:
                    subject_reg = s.registration_no
                    break

        inv = Invoice(
            invoice_number=number,
            type=self.type_var.get(),
            state="OPEN",
            issued_date=self.issued_var.get(),
            taxable_supply_date=self.duzp_var.get(),
            due_date=self.due_var.get(),
            variable_symbol=self.vs_var.get() or None,
            bank_account=self.account_var.get() or None,
            supply_code="DOMESTIC",
            subject_registration_no=subject_reg,
            note=self.note_var.get() or None,
        )

        line_dicts = []
        for i, ld in enumerate(self._lines):
            try:
                line = InvoiceLine(
                    item_description=ld["desc"],
                    quantity=Decimal(ld["qty"] or "1"),
                    unit_price=Decimal(ld["price"] or "0"),
                    vat_rate=ld["vat"],
                    unit=ld["unit"],
                    sort_order=i,
                )
                line_dicts.append(line.to_dict())
            except InvalidOperation:
                pass

        inv.lines = line_dicts
        persistence.upsert_invoice(inv)

        if self.navigate_cb:
            self.navigate_cb("invoices", None)


# -- Helpers --

def _fmt_currency(value: Decimal) -> str:
    rounded = czech_round(value)
    s = f"{rounded:,.2f}".replace(",", " ").replace(".", ",")
    return f"{s} Kč"

def _fmt_date(iso_date: str) -> str:
    d = date.fromisoformat(iso_date)
    return d.strftime("%d.%m.%Y")
