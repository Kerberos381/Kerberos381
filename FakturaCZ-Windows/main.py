"""
FakturaCZ — Czech Invoicing Desktop Application
Entry point for the Windows .exe build.
"""

import customtkinter as ctk

from app.views.dashboard import DashboardView
from app.views.invoices import InvoiceListView, InvoiceDetailView, InvoiceFormView
from app.views.subjects import SubjectListView, SubjectDetailView, SubjectFormView
from app.views.tax import TaxReportView
from app.services.overdue import check_overdue
from app.services.recurring_scheduler import process_templates


class FakturaCZApp(ctk.CTk):
    """Main application window with sidebar navigation."""

    def __init__(self):
        super().__init__()

        self.title("FakturaCZ — Fakturační systém")
        self.geometry("1100x720")
        self.minsize(900, 600)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # Run startup tasks
        check_overdue()
        try:
            process_templates()
        except Exception:
            pass  # dateutil may not be installed; templates still work via manual trigger

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=180, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nswe")
        self.sidebar.grid_propagate(False)

        # App title in sidebar
        ctk.CTkLabel(
            self.sidebar, text="FakturaCZ",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(padx=15, pady=(20, 25))

        # Nav buttons
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        nav_items = [
            ("dashboard", "Přehled", "📊"),
            ("invoices", "Faktury", "📄"),
            ("subjects", "Subjekty", "👥"),
            ("tax", "Daně", "🏛"),
        ]
        for key, label, icon in nav_items:
            btn = ctk.CTkButton(
                self.sidebar, text=f"  {icon}  {label}",
                anchor="w", height=36, corner_radius=8,
                fg_color="transparent", text_color="gray",
                hover_color=("gray85", "gray25"),
                command=lambda k=key: self.navigate(k),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self._nav_buttons[key] = btn

        # Appearance toggle at bottom
        ctk.CTkLabel(self.sidebar, text="Vzhled:",
                     font=ctk.CTkFont(size=10)).pack(side="bottom", padx=15, pady=(0, 5))
        self._appearance_menu = ctk.CTkOptionMenu(
            self.sidebar, values=["System", "Light", "Dark"],
            command=lambda v: ctk.set_appearance_mode(v.lower()),
            width=140, height=28,
        )
        self._appearance_menu.pack(side="bottom", padx=15, pady=(0, 5))
        self._appearance_menu.set("System")

        # Content area
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nswe")

        self._current_view = None
        self.navigate("dashboard")

    def navigate(self, view_name: str, data=None):
        """Navigate to a view by name. Called by sidebar buttons and child views."""
        # Clear current view
        if self._current_view:
            self._current_view.destroy()

        # Update sidebar highlight
        for key, btn in self._nav_buttons.items():
            if key == view_name or (view_name.startswith(key.rstrip("s")) and key != view_name):
                btn.configure(fg_color=("gray75", "gray30"), text_color=("black", "white"))
            else:
                btn.configure(fg_color="transparent", text_color="gray")

        # Create the view
        if view_name == "dashboard":
            self._current_view = DashboardView(self.content, navigate_cb=self.navigate)
        elif view_name == "invoices":
            self._current_view = InvoiceListView(self.content, navigate_cb=self.navigate)
        elif view_name == "invoice_detail" and data:
            self._current_view = InvoiceDetailView(self.content, invoice=data, navigate_cb=self.navigate)
            self._highlight_nav("invoices")
        elif view_name == "invoice_form":
            self._current_view = InvoiceFormView(self.content, navigate_cb=self.navigate)
            self._highlight_nav("invoices")
        elif view_name == "subjects":
            self._current_view = SubjectListView(self.content, navigate_cb=self.navigate)
        elif view_name == "subject_detail" and data:
            self._current_view = SubjectDetailView(self.content, subject=data, navigate_cb=self.navigate)
            self._highlight_nav("subjects")
        elif view_name == "subject_form":
            self._current_view = SubjectFormView(self.content, navigate_cb=self.navigate)
            self._highlight_nav("subjects")
        elif view_name == "tax":
            self._current_view = TaxReportView(self.content, navigate_cb=self.navigate)
        else:
            self._current_view = DashboardView(self.content, navigate_cb=self.navigate)

        self._current_view.pack(fill="both", expand=True)

    def _highlight_nav(self, key: str):
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg_color=("gray75", "gray30"), text_color=("black", "white"))
            else:
                btn.configure(fg_color="transparent", text_color="gray")


def main():
    app = FakturaCZApp()
    app.mainloop()


if __name__ == "__main__":
    main()
