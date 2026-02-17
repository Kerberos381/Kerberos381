"""Subject list, detail, and form views."""

import tkinter as tk
from threading import Thread

import customtkinter as ctk

from app.models.subject import Subject
from app.services import persistence
from app.services.ares import fetch_subject, ARESError


class SubjectListView(ctk.CTkFrame):
    def __init__(self, parent, navigate_cb=None):
        super().__init__(parent, fg_color="transparent")
        self.navigate_cb = navigate_cb
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(header, text="Subjekty",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")

        ctk.CTkButton(header, text="+ Nový subjekt", width=140,
                      command=self._open_form).pack(side="right")

        # Search
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self.refresh())
        ctk.CTkEntry(self, textvariable=self._search_var,
                     placeholder_text="Hledat (název, IČO)...", width=300).pack(
            anchor="w", padx=20, pady=(0, 10))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        subjects = persistence.load_subjects()
        search = self._search_var.get().lower()
        if search:
            subjects = [s for s in subjects if
                        search in s.name.lower() or search in s.registration_no]

        subjects.sort(key=lambda s: s.name)

        if not subjects:
            ctk.CTkLabel(self.list_frame, text="Žádné subjekty. Přidejte klienta pomocí +.",
                         text_color="gray").pack(pady=40)
            return

        for subject in subjects:
            row = ctk.CTkFrame(self.list_frame, corner_radius=8, cursor="hand2")
            row.pack(fill="x", pady=2)
            row.bind("<Button-1>", lambda e, s=subject: self._open_detail(s))

            ctk.CTkLabel(row, text=subject.name,
                         font=ctk.CTkFont(size=12, weight="bold")).pack(
                side="left", padx=10, pady=8)

            ctk.CTkLabel(row, text=f"IČO: {subject.registration_no}",
                         font=ctk.CTkFont(size=10), text_color="gray").pack(
                side="left", padx=10, pady=8)

            if subject.is_vat_payer:
                ctk.CTkLabel(row, text="Plátce DPH",
                             font=ctk.CTkFont(size=10, weight="bold"),
                             text_color="#22C55E").pack(side="right", padx=10, pady=8)

    def _open_detail(self, subject: Subject):
        if self.navigate_cb:
            self.navigate_cb("subject_detail", subject)

    def _open_form(self):
        if self.navigate_cb:
            self.navigate_cb("subject_form", None)


class SubjectDetailView(ctk.CTkFrame):
    def __init__(self, parent, subject: Subject, navigate_cb=None):
        super().__init__(parent, fg_color="transparent")
        self.subject = subject
        self.navigate_cb = navigate_cb
        self._build_ui()

    def _build_ui(self):
        s = self.subject
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkButton(scroll, text="< Zpět", width=80, fg_color="gray",
                      command=lambda: self.navigate_cb("subjects", None) if self.navigate_cb else None
                      ).pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(scroll, text=s.name,
                     font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")

        # Info cards
        info = ctk.CTkFrame(scroll, corner_radius=8)
        info.pack(fill="x", pady=10)

        for label, val in [
            ("IČO:", s.registration_no),
            ("DIČ:", s.vat_no or "—"),
            ("Plátce DPH:", "Ano" if s.is_vat_payer else "Ne"),
            ("Ulice:", s.street),
            ("Město:", s.city),
            ("PSČ:", s.zip),
            ("Email:", s.email or "—"),
            ("Telefon:", s.phone or "—"),
            ("Číslo účtu:", s.bank_account or "—"),
        ]:
            row = ctk.CTkFrame(info, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=11, weight="bold"),
                         width=120).pack(side="left")
            ctk.CTkLabel(row, text=val, font=ctk.CTkFont(size=11)).pack(side="left")

        # ARES refresh
        actions = ctk.CTkFrame(scroll, fg_color="transparent")
        actions.pack(fill="x", pady=10)

        self.ares_status = ctk.CTkLabel(actions, text="", font=ctk.CTkFont(size=10))
        self.ares_status.pack(side="left", padx=10)

        ctk.CTkButton(actions, text="Obnovit z ARES", width=140,
                      command=self._refresh_ares).pack(side="left", padx=5)

        if s.last_ares_sync:
            self.ares_status.configure(text=f"Poslední sync: {s.last_ares_sync[:10]}",
                                       text_color="gray")

        # Invoices for this subject
        invoices = [i for i in persistence.load_invoices()
                    if i.subject_registration_no == s.registration_no]
        if invoices:
            ctk.CTkLabel(scroll, text=f"Faktury ({len(invoices)})",
                         font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(15, 5))
            for inv in sorted(invoices, key=lambda i: i.created_at, reverse=True)[:10]:
                row = ctk.CTkFrame(scroll, corner_radius=6)
                row.pack(fill="x", pady=1)
                ctk.CTkLabel(row, text=inv.invoice_number,
                             font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=10, pady=4)
                from app.models.enums import InvoiceState
                state = InvoiceState[inv.state]
                ctk.CTkLabel(row, text=state.label, text_color=state.color,
                             font=ctk.CTkFont(size=10)).pack(side="left", padx=5)

    def _refresh_ares(self):
        self.ares_status.configure(text="Načítám z ARES...", text_color="orange")

        def do_fetch():
            try:
                data = fetch_subject(self.subject.registration_no)
                self.subject.apply_ares_data(data)
                persistence.upsert_subject(self.subject)
                self.after(0, lambda: self.ares_status.configure(
                    text="Data aktualizována z ARES.", text_color="#22C55E"))
                # Rebuild the view
                self.after(100, lambda: self.navigate_cb("subject_detail", self.subject)
                           if self.navigate_cb else None)
            except ARESError as e:
                self.after(0, lambda: self.ares_status.configure(
                    text=str(e), text_color="#EF4444"))

        Thread(target=do_fetch, daemon=True).start()


class SubjectFormView(ctk.CTkFrame):
    """New subject form with ARES lookup."""

    def __init__(self, parent, navigate_cb=None):
        super().__init__(parent, fg_color="transparent")
        self.navigate_cb = navigate_cb
        self._build_ui()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkButton(scroll, text="< Zpět", width=80, fg_color="gray",
                      command=lambda: self.navigate_cb("subjects", None) if self.navigate_cb else None
                      ).pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(scroll, text="Nový subjekt",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w", pady=(0, 15))

        # IČO + ARES
        ico_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        ico_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(ico_frame, text="IČO:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")
        self.ico_var = tk.StringVar()
        ctk.CTkEntry(ico_frame, textvariable=self.ico_var, width=120).pack(side="left", padx=5)
        ctk.CTkButton(ico_frame, text="Načíst z ARES", width=130,
                      command=self._lookup_ares).pack(side="left", padx=5)

        self.ares_label = ctk.CTkLabel(ico_frame, text="", font=ctk.CTkFont(size=10))
        self.ares_label.pack(side="left", padx=10)

        # Fields
        self.name_var = tk.StringVar()
        self.street_var = tk.StringVar()
        self.city_var = tk.StringVar()
        self.zip_var = tk.StringVar()
        self.vat_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.account_var = tk.StringVar()

        fields = [
            ("Název:", self.name_var, 400),
            ("Ulice:", self.street_var, 400),
            ("Město:", self.city_var, 250),
            ("PSČ:", self.zip_var, 100),
            ("DIČ:", self.vat_var, 150),
            ("Email:", self.email_var, 250),
            ("Telefon:", self.phone_var, 180),
            ("Číslo účtu:", self.account_var, 250),
        ]

        for label, var, width in fields:
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=11, weight="bold"),
                         width=100).pack(side="left")
            ctk.CTkEntry(f, textvariable=var, width=width).pack(side="left", padx=5)

        # Submit
        ctk.CTkButton(scroll, text="Uložit subjekt", width=200, fg_color="#22C55E",
                      command=self._submit).pack(anchor="e", pady=20)

    def _lookup_ares(self):
        ico = self.ico_var.get().strip()
        if len(ico) != 8:
            self.ares_label.configure(text="IČO musí mít 8 číslic.", text_color="#EF4444")
            return

        self.ares_label.configure(text="Načítám...", text_color="orange")

        def do_fetch():
            try:
                data = fetch_subject(ico)
                self.after(0, lambda: self._apply_ares(data))
            except ARESError as e:
                self.after(0, lambda: self.ares_label.configure(
                    text=str(e), text_color="#EF4444"))

        Thread(target=do_fetch, daemon=True).start()

    def _apply_ares(self, data: dict):
        self.name_var.set(data.get("name", ""))
        self.street_var.set(data.get("street", ""))
        self.city_var.set(data.get("city", ""))
        self.zip_var.set(data.get("zip", ""))
        self.vat_var.set(data.get("vat_no", "") or "")
        self.ares_label.configure(text="Data načtena z ARES.", text_color="#22C55E")

    def _submit(self):
        ico = self.ico_var.get().strip()
        if not ico or not self.name_var.get().strip():
            self.ares_label.configure(text="IČO a název jsou povinné.", text_color="#EF4444")
            return

        subject = Subject(
            registration_no=ico,
            name=self.name_var.get().strip(),
            street=self.street_var.get().strip(),
            city=self.city_var.get().strip(),
            zip=self.zip_var.get().strip(),
            vat_no=self.vat_var.get().strip() or None,
            email=self.email_var.get().strip() or None,
            phone=self.phone_var.get().strip() or None,
            bank_account=self.account_var.get().strip() or None,
        )

        persistence.upsert_subject(subject)

        if self.navigate_cb:
            self.navigate_cb("subjects", None)
