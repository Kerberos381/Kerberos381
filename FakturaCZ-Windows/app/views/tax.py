"""Tax reports view — DPH, KH generation and accounting exports."""

import os
import subprocess
import tkinter as tk
from datetime import date

import customtkinter as ctk

from app.models.enums import TaxPeriod
from app.services import persistence
from app.services.tax_report import fetch_taxable_invoices, generate_dph_xml, generate_kh_xml
from app.services.accounting_export import perform_sharp_export, generate_pohoda_xml


CZECH_MONTHS = [
    "Leden", "Únor", "Březen", "Duben", "Květen", "Červen",
    "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec",
]


class TaxReportView(ctk.CTkFrame):
    def __init__(self, parent, navigate_cb=None):
        super().__init__(parent, fg_color="transparent")
        self.navigate_cb = navigate_cb
        self._invoices = []
        self._dph_xml = None
        self._kh_xml = None
        self._build_ui()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text="Daňové přehledy",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=(0, 15))

        # Period selection
        period_frame = ctk.CTkFrame(scroll, corner_radius=8)
        period_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(period_frame, text="Období",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 5))

        row1 = ctk.CTkFrame(period_frame, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=5)

        ctk.CTkLabel(row1, text="Typ:", font=ctk.CTkFont(size=11)).pack(side="left")
        self.period_var = tk.StringVar(value="MONTHLY")
        ctk.CTkOptionMenu(row1, values=["MONTHLY", "QUARTERLY"],
                          variable=self.period_var, width=130).pack(side="left", padx=5)

        ctk.CTkLabel(row1, text="Rok:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(15, 0))
        self.year_var = tk.StringVar(value=str(date.today().year))
        ctk.CTkOptionMenu(row1, values=[str(y) for y in range(2020, 2031)],
                          variable=self.year_var, width=80).pack(side="left", padx=5)

        ctk.CTkLabel(row1, text="Měsíc:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(15, 0))
        self.month_var = tk.StringVar(value=str(date.today().month))
        ctk.CTkOptionMenu(row1, values=[str(m) for m in range(1, 13)],
                          variable=self.month_var, width=60).pack(side="left", padx=5)

        row2 = ctk.CTkFrame(period_frame, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(row2, text="DIČ poplatníka:", font=ctk.CTkFont(size=11)).pack(side="left")
        self.vat_no_var = tk.StringVar()
        ctk.CTkEntry(row2, textvariable=self.vat_no_var, width=180).pack(side="left", padx=5)

        # Generate button
        ctk.CTkButton(period_frame, text="Generovat přiznání", width=200,
                      command=self._generate).pack(padx=12, pady=10, anchor="w")

        self.status_label = ctk.CTkLabel(period_frame, text="", font=ctk.CTkFont(size=11))
        self.status_label.pack(anchor="w", padx=12, pady=(0, 10))

        # Export buttons
        export_frame = ctk.CTkFrame(scroll, corner_radius=8)
        export_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(export_frame, text="Exporty",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 5))

        btn_row = ctk.CTkFrame(export_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=5)

        self.btn_dph = ctk.CTkButton(btn_row, text="Export DPH XML", width=160,
                                     fg_color="#6366F1", state="disabled",
                                     command=lambda: self._save_xml(self._dph_xml, "dph"))
        self.btn_dph.pack(side="left", padx=5)

        self.btn_kh = ctk.CTkButton(btn_row, text="Export KH XML", width=160,
                                    fg_color="#6366F1", state="disabled",
                                    command=lambda: self._save_xml(self._kh_xml, "kh"))
        self.btn_kh.pack(side="left", padx=5)

        btn_row2 = ctk.CTkFrame(export_frame, fg_color="transparent")
        btn_row2.pack(fill="x", padx=12, pady=5)

        self.btn_sharp = ctk.CTkButton(
            btn_row2, text="Ostrý export (uzamkne faktury)", width=250,
            fg_color="#D97706", state="disabled",
            command=self._sharp_export
        )
        self.btn_sharp.pack(side="left", padx=5)

        self.btn_pohoda = ctk.CTkButton(
            btn_row2, text="Export pro Pohoda", width=160,
            fg_color="#6366F1", state="disabled",
            command=self._export_pohoda
        )
        self.btn_pohoda.pack(side="left", padx=5)

        self.export_status = ctk.CTkLabel(export_frame, text="", font=ctk.CTkFont(size=10))
        self.export_status.pack(anchor="w", padx=12, pady=(0, 10))

    def _generate(self):
        vat_no = self.vat_no_var.get().strip()
        if not vat_no:
            self.status_label.configure(text="Zadejte DIČ poplatníka.", text_color="#EF4444")
            return

        year = int(self.year_var.get())
        month = int(self.month_var.get())
        period = TaxPeriod[self.period_var.get()]

        self._invoices = fetch_taxable_invoices(year, month, period)
        count = len(self._invoices)
        self.status_label.configure(
            text=f"Nalezeno {count} faktur pro dané období.",
            text_color="#22C55E" if count > 0 else "gray"
        )

        if count > 0:
            self._dph_xml = generate_dph_xml(self._invoices, vat_no, year, month, period)
            self._kh_xml = generate_kh_xml(self._invoices, vat_no, year, month)
            self.btn_dph.configure(state="normal")
            self.btn_kh.configure(state="normal")
            self.btn_sharp.configure(state="normal")
            self.btn_pohoda.configure(state="normal")
        else:
            self._dph_xml = None
            self._kh_xml = None
            self.btn_dph.configure(state="disabled")
            self.btn_kh.configure(state="disabled")
            self.btn_sharp.configure(state="disabled")
            self.btn_pohoda.configure(state="disabled")

    def _save_xml(self, xml_content: str | None, prefix: str):
        if not xml_content:
            return
        exports_dir = persistence.get_exports_dir()
        year = self.year_var.get()
        month = self.month_var.get()
        filename = f"{prefix}_{year}_{month}.xml"
        path = exports_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml_content)
        self.export_status.configure(
            text=f"Uloženo: {path}", text_color="#22C55E")
        self._open_file(path)

    def _sharp_export(self):
        if not self._invoices:
            return
        year = int(self.year_var.get())
        month = int(self.month_var.get())
        record = perform_sharp_export(self._invoices, "ISDOC", year, month)
        self.export_status.configure(
            text=f"Uzamčeno {len(record.invoice_ids)} faktur. ISDOC export vytvořen.",
            text_color="#D97706"
        )

    def _export_pohoda(self):
        if not self._invoices:
            return
        xml = generate_pohoda_xml(self._invoices)
        exports_dir = persistence.get_exports_dir()
        year = self.year_var.get()
        month = self.month_var.get()
        path = exports_dir / f"pohoda_{year}_{month}.xml"
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        self.export_status.configure(text=f"Uloženo: {path}", text_color="#22C55E")
        self._open_file(path)

    @staticmethod
    def _open_file(path):
        if os.name == "nt":
            os.startfile(str(path))
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
