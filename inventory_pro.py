
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import datetime, timedelta
from pathlib import Path

# =====================================================
# HIMA VAMSI INVENTORY PRO - VERSION 1.0
# Python + Tkinter + SQLite
# =====================================================

APP_NAME = "HIMA VAMSI INVENTORY PRO"
DB_FILE = Path(__file__).with_name("inventory_pro.db")

BG = "#101827"
PANEL = "#19263A"
CARD = "#22334C"
CYAN = "#19C5D8"
WHITE = "#F1F5F9"
MUTED = "#AAB8CA"
GREEN = "#22C55E"
RED = "#EF4444"


class Database:

    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                price REAL NOT NULL DEFAULT 0,
                quantity INTEGER NOT NULL DEFAULT 0,
                low_stock INTEGER NOT NULL DEFAULT 5
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)

        self.conn.commit()

    def close(self):
        self.conn.close()


class InventoryApp:

    def __init__(self, root):
        self.root = root
        self.db = Database()

# Automatically create demo business data
        self.seed_demo_data()
        self.export_demo_csvs()

        self.selected_product_id = None

        self.root.title(APP_NAME)
        self.root.geometry("1250x760")
        self.root.minsize(1050, 650)
        self.root.configure(bg=BG)

        self.setup_style()
        self.build_interface()
        self.refresh_all()

        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    # ---------------- STYLE ----------------

    def setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background=PANEL,
            foreground=WHITE,
            fieldbackground=PANEL,
            rowheight=34,
            borderwidth=0,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Treeview.Heading",
            background="#263B56",
            foreground=CYAN,
            font=("Segoe UI", 10, "bold"),
            padding=(10, 12),
            relief="flat"
        )
        style.map(
            "Treeview",
            background=[("selected", CYAN)],
            foreground=[("selected", BG)]
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#31506F")]
        )

        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(4, 8, 4, 0))
        style.configure(
            "TNotebook.Tab",
            background="#203149",
            foreground=WHITE,
            padding=(22, 13),
            font=("Segoe UI", 10, "bold"),
            borderwidth=0
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", CYAN), ("active", "#31506F")],
            foreground=[("selected", BG), ("active", WHITE)]
        )
        style.configure("Vertical.TScrollbar", background=PANEL, troughcolor=BG, bordercolor=BG, arrowcolor=CYAN)

    # ---------------- UI HELPERS ----------------

    def label(self, parent, text, size=10, color=WHITE, bold=False):
        return tk.Label(
            parent,
            text=text,
            bg=parent.cget("bg"),
            fg=color,
            font=("Segoe UI", size, "bold" if bold else "normal")
        )

    def entry(self, parent, width=22):
        field = tk.Entry(
            parent,
            width=width,
            bg=CARD,
            fg=WHITE,
            insertbackground=WHITE,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#304A68",
            highlightcolor=CYAN,
            font=("Segoe UI", 10),
            disabledbackground=PANEL
        )
        return field

    def button(self, parent, text, command, color=CYAN):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg=BG if color == CYAN else WHITE,
            activebackground=WHITE,
            activeforeground=BG,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=16,
            pady=10,
            highlightthickness=1,
            highlightbackground=color,
            highlightcolor=CYAN
        )
        hover = "#36D7E5" if color == CYAN else "#31506F"
        btn.bind("<Enter>", lambda _e: btn.configure(bg=hover))
        btn.bind("<Leave>", lambda _e: btn.configure(bg=color))
        return btn

    def make_tree(self, parent, columns, headings):
        shell = tk.Frame(parent, bg=PANEL, padx=1, pady=1)
        shell.pack(fill="both", expand=True, padx=16, pady=12)
        frame = tk.Frame(shell, bg=BG)
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col, heading in zip(columns, headings):
            tree.heading(col, text=heading)
            tree.column(col, width=145, minwidth=90, anchor="center", stretch=True)

        tree.tag_configure("odd", background="#192A40")
        tree.tag_configure("even", background="#213650")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        original_insert = tree.insert
        def striped_insert(parent, index, iid=None, **kwargs):
            if "tags" not in kwargs:
                row_number = len(tree.get_children(parent))
                kwargs["tags"] = ("even" if row_number % 2 == 0 else "odd",)
            return original_insert(parent, index, iid, **kwargs)
        tree.insert = striped_insert
        return tree

    def build_interface(self):
        header = tk.Frame(self.root, bg="#14243A", height=82, highlightthickness=1, highlightbackground="#29445F")
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="HIMA VAMSI",
            bg=PANEL,
            fg=CYAN,
            font=("Segoe UI", 21, "bold")
        ).pack(side="left", padx=25)

        tk.Label(
            header,
            text="INVENTORY PRO  |  VERSION 1.0",
            bg=PANEL,
            fg=WHITE,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=10)

        tk.Label(
            header,
            text="BUSINESS MANAGEMENT SYSTEM",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(side="right", padx=25)

        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self.dashboard_tab = tk.Frame(self.notebook, bg=BG)
        self.products_tab = tk.Frame(self.notebook, bg=BG)
        self.stock_tab = tk.Frame(self.notebook, bg=BG)
        self.sales_tab = tk.Frame(self.notebook, bg=BG)
        self.reports_tab = tk.Frame(self.notebook, bg=BG)

        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.products_tab, text="Products")
        self.notebook.add(self.stock_tab, text="Stock")
        self.notebook.add(self.sales_tab, text="Sales")
        self.notebook.add(self.reports_tab, text="Reports")

        self.build_dashboard()
        self.build_products()
        self.build_stock()
        self.build_sales()
        self.build_reports()

        footer = tk.Label(
            self.root,
            text="Hima Vamsi Inventory Pro  |  Powered by Python & SQLite",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9)
        )
        footer.pack(pady=5)

    def toggle_fullscreen(self, _event=None):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def exit_fullscreen(self, _event=None):
        self.root.attributes("-fullscreen", False)

    # ---------------- DASHBOARD ----------------

    def build_dashboard(self):
        titlebar = tk.Frame(self.dashboard_tab, bg=BG)
        titlebar.pack(fill="x", padx=22, pady=(20, 12))
        tk.Label(
            titlebar, text="Business Dashboard", bg=BG, fg=WHITE,
            font=("Segoe UI", 23, "bold")
        ).pack(side="left")
        tk.Label(
            titlebar, text="LIVE BUSINESS OVERVIEW", bg=BG, fg=MUTED,
            font=("Segoe UI", 9, "bold")
        ).pack(side="right", pady=8)

        cards = tk.Frame(self.dashboard_tab, bg=BG)
        cards.pack(fill="x", padx=12, pady=(0, 12))
        self.dashboard_values = {}
        card_info = [
            ("TOTAL PRODUCTS", "products", "▦"),
            ("TOTAL STOCK UNITS", "stock", "▤"),
            ("SALES TODAY", "sales", "₹"),
            ("INVENTORY VALUE", "value", "◆")
        ]

        for title, key, symbol in card_info:
            card = tk.Frame(cards, bg=CARD, padx=18, pady=16,
                            highlightthickness=1, highlightbackground="#304A68")
            card.pack(side="left", fill="both", expand=True, padx=7, pady=4)
            tk.Label(card, text=symbol, bg=CARD, fg=CYAN,
                     font=("Segoe UI Symbol", 19, "bold")).pack(anchor="w")
            tk.Label(card, text=title, bg=CARD, fg=MUTED,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(7, 0))
            value = tk.Label(card, text="0", bg=CARD, fg=WHITE,
                             font=("Segoe UI", 21, "bold"))
            value.pack(anchor="w", pady=(5, 0))
            self.dashboard_values[key] = value

        analytics = tk.Frame(self.dashboard_tab, bg=BG)
        analytics.pack(fill="both", expand=True, padx=18, pady=(4, 0))

        chart_panel = tk.Frame(analytics, bg=PANEL, highlightthickness=1,
                               highlightbackground="#304A68")
        chart_panel.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=5)
        tk.Label(chart_panel, text="SALES PERFORMANCE · LAST 7 DAYS",
                 bg=PANEL, fg=WHITE, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(12, 4))
        self.sales_chart = tk.Canvas(chart_panel, bg=PANEL, height=190,
                                     highlightthickness=0, bd=0)
        self.sales_chart.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.sales_chart.bind("<Configure>", lambda _e: self.draw_sales_chart())

        low_panel = tk.Frame(analytics, bg=PANEL, highlightthickness=1,
                             highlightbackground="#304A68")
        low_panel.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=5)
        tk.Label(low_panel, text="LOW STOCK ALERTS",
                 bg=PANEL, fg=WHITE, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(12, 0))
        self.low_stock_tree = self.make_tree(
            low_panel,
            ("sku", "name", "quantity", "limit"),
            ("SKU", "Product Name", "Available", "Minimum")
        )

    def refresh_dashboard(self):
        cur = self.db.conn.cursor()

        cur.execute("SELECT COUNT(*) FROM products")
        product_count = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(quantity), 0) FROM products")
        total_stock = cur.fetchone()[0]

        today = datetime.now().strftime("%Y-%m-%d")

        cur.execute(
            "SELECT COALESCE(SUM(total), 0) FROM sales WHERE date(created_at)=?",
            (today,)
        )
        sales_today = cur.fetchone()[0]

        cur.execute(
            "SELECT COALESCE(SUM(price * quantity), 0) FROM products"
        )
        stock_value = cur.fetchone()[0]

        self.dashboard_values["products"].config(
            text=str(product_count)
        )
        self.dashboard_values["stock"].config(
            text=str(total_stock)
        )
        self.dashboard_values["sales"].config(
            text=f"₹{sales_today:,.2f}"
        )
        self.dashboard_values["value"].config(
            text=f"₹{stock_value:,.2f}"
        )

        for item in self.low_stock_tree.get_children():
            self.low_stock_tree.delete(item)

        cur.execute("""
            SELECT sku, name, quantity, low_stock
            FROM products
            WHERE quantity <= low_stock
            ORDER BY quantity ASC
        """)

        for row in cur.fetchall():
            self.low_stock_tree.insert("", "end", values=row)

        self.draw_sales_chart()

    def draw_sales_chart(self):
        if not hasattr(self, "sales_chart"):
            return
        canvas = self.sales_chart
        canvas.delete("all")
        width = max(canvas.winfo_width(), 420)
        height = max(canvas.winfo_height(), 170)
        today = datetime.now().date()
        labels = [today - timedelta(days=6-i) for i in range(7)]
        values = []
        cur = self.db.conn.cursor()
        for day in labels:
            cur.execute(
                "SELECT COALESCE(SUM(total), 0) FROM sales WHERE date(created_at)=?",
                (day.strftime("%Y-%m-%d"),)
            )
            values.append(float(cur.fetchone()[0] or 0))

        left, right, top, bottom = 42, width - 18, 18, height - 32
        canvas.create_line(left, bottom, right, bottom, fill="#52677F", width=1)
        max_value = max(values) if max(values) > 0 else 1
        plot_height = bottom - top
        bar_gap = 12
        bar_width = max(18, (right-left - bar_gap*6) / 7)
        for i, (day, amount) in enumerate(zip(labels, values)):
            x0 = left + i * (bar_width + bar_gap)
            bar_height = (amount / max_value) * (plot_height - 24)
            y0 = bottom - bar_height
            canvas.create_rectangle(x0, y0, x0 + bar_width, bottom,
                                    fill=CYAN if i == 6 else "#347D9B", outline="")
            canvas.create_text(x0 + bar_width/2, max(top, y0-9),
                               text=f"{amount:,.0f}", fill=WHITE,
                               font=("Segoe UI", 8))
            canvas.create_text(x0 + bar_width/2, bottom+14,
                               text=day.strftime("%d %b"), fill=MUTED,
                               font=("Segoe UI", 8))

    # ---------------- PRODUCTS ----------------

    def build_products(self):
        tk.Label(
            self.products_tab,
            text="Product Management",
            bg=BG,
            fg=WHITE,
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w", padx=15, pady=12)

        form = tk.Frame(self.products_tab, bg=PANEL, padx=12, pady=12)
        form.pack(fill="x", padx=12)

        self.product_fields = {}

        fields = [
            ("SKU", "sku"),
            ("Product Name", "name"),
            ("Category", "category"),
            ("Unit Price", "price"),
            ("Opening Stock", "quantity"),
            ("Low Stock Limit", "low_stock")
        ]

        for index, (title, key) in enumerate(fields):
            tk.Label(
                form,
                text=title,
                bg=PANEL,
                fg=WHITE
            ).grid(row=index // 3 * 2, column=index % 3, sticky="w", padx=8, pady=4)

            entry = self.entry(form, 24)
            entry.grid(
                row=index // 3 * 2 + 1,
                column=index % 3,
                padx=8,
                pady=5,
                sticky="ew"
            )

            self.product_fields[key] = entry

        for col in range(3):
            form.grid_columnconfigure(col, weight=1)

        actions = tk.Frame(self.products_tab, bg=BG)
        actions.pack(fill="x", padx=15, pady=10)

        self.button(actions, "Add Product", self.add_product).pack(side="left", padx=4)
        self.button(actions, "Update Product", self.update_product).pack(side="left", padx=4)
        self.button(actions, "Delete Product", self.delete_product, RED).pack(side="left", padx=4)
        self.button(actions, "Clear Form", self.clear_product_form, CARD).pack(side="left", padx=4)

        search_frame = tk.Frame(self.products_tab, bg=BG)
        search_frame.pack(fill="x", padx=15)

        self.search_entry = self.entry(search_frame, 35)
        self.search_entry.pack(side="left", padx=5)

        self.button(
            search_frame,
            "Search",
            self.search_products
        ).pack(side="left", padx=5)

        self.button(
            search_frame,
            "Show All",
            self.refresh_products,
            CARD
        ).pack(side="left", padx=5)

        self.product_tree = self.make_tree(
            self.products_tab,
            ("id", "sku", "name", "category", "price", "quantity", "low_stock"),
            ("ID", "SKU", "Product", "Category", "Price", "Stock", "Low Stock Limit")
        )

        self.product_tree.bind(
            "<<TreeviewSelect>>",
            self.select_product
        )

    def get_product_values(self):
        values = {
            key: field.get().strip()
            for key, field in self.product_fields.items()
        }

        if not values["sku"] or not values["name"]:
            raise ValueError("SKU and Product Name are required.")

        try:
            values["price"] = float(values["price"])
            values["quantity"] = int(values["quantity"] or 0)
            values["low_stock"] = int(values["low_stock"] or 5)
        except ValueError:
            raise ValueError("Enter valid price and stock numbers.")

        if values["price"] < 0 or values["quantity"] < 0 or values["low_stock"] < 0:
            raise ValueError("Values cannot be negative.")

        return values

    def add_product(self):
        try:
            p = self.get_product_values()

            cur = self.db.conn.cursor()

            cur.execute("""
                INSERT INTO products
                (sku, name, category, price, quantity, low_stock)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                p["sku"],
                p["name"],
                p["category"],
                p["price"],
                p["quantity"],
                p["low_stock"]
            ))

            product_id = cur.lastrowid

            if p["quantity"] > 0:
                cur.execute("""
                    INSERT INTO stock_movements
                    (product_id, movement_type, quantity, note, created_at)
                    VALUES (?, 'IN', ?, ?, ?)
                """, (
                    product_id,
                    p["quantity"],
                    "Opening stock",
                    datetime.now().isoformat(timespec="seconds")
                ))

            self.db.conn.commit()

            messagebox.showinfo("Success", "Product added successfully.")
            self.clear_product_form()
            self.refresh_all()

        except sqlite3.IntegrityError:
            self.db.conn.rollback()
            messagebox.showerror("Duplicate SKU", "This SKU already exists.")
        except ValueError as error:
            messagebox.showerror("Invalid Input", str(error))

    def select_product(self, event=None):
        selected = self.product_tree.selection()

        if not selected:
            return

        values = self.product_tree.item(selected[0], "values")
        self.selected_product_id = int(values[0])

        mapping = {
            "sku": values[1],
            "name": values[2],
            "category": values[3],
            "price": values[4],
            "quantity": "",
            "low_stock": values[6]
        }

        for key, value in mapping.items():
            field = self.product_fields[key]
            field.delete(0, "end")
            field.insert(0, value)

        self.product_fields["quantity"].insert(0, values[5])

    def update_product(self):
        if self.selected_product_id is None:
            messagebox.showwarning("Select Product", "Select a product first.")
            return

        try:
            p = self.get_product_values()

            self.db.conn.execute("""
                UPDATE products
                SET sku=?, name=?, category=?, price=?, low_stock=?
                WHERE id=?
            """, (
                p["sku"],
                p["name"],
                p["category"],
                p["price"],
                p["low_stock"],
                self.selected_product_id
            ))

            self.db.conn.commit()

            messagebox.showinfo(
                "Updated",
                "Product details updated. Use Stock Management to change quantity."
            )

            self.clear_product_form()
            self.refresh_all()

        except sqlite3.IntegrityError:
            self.db.conn.rollback()
            messagebox.showerror("Duplicate SKU", "This SKU already exists.")
        except ValueError as error:
            messagebox.showerror("Invalid Input", str(error))

    def delete_product(self):
        if self.selected_product_id is None:
            messagebox.showwarning("Select Product", "Select a product first.")
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            "Delete this product? Products with sales history cannot be deleted."
        )

        if not confirm:
            return

        try:
            self.db.conn.execute(
                "DELETE FROM products WHERE id=?",
                (self.selected_product_id,)
            )
            self.db.conn.commit()

            messagebox.showinfo("Deleted", "Product deleted.")
            self.clear_product_form()
            self.refresh_all()

        except sqlite3.IntegrityError:
            self.db.conn.rollback()
            messagebox.showerror(
                "Cannot Delete",
                "This product has sales or stock history. Keep it for records."
            )

    def clear_product_form(self):
        self.selected_product_id = None

        for field in self.product_fields.values():
            field.delete(0, "end")

        self.product_fields["low_stock"].insert(0, "5")

    def refresh_products(self):
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)

        cur = self.db.conn.cursor()
        cur.execute("""
            SELECT id, sku, name, category, price, quantity, low_stock
            FROM products ORDER BY id DESC
        """)

        for row in cur.fetchall():
            self.product_tree.insert("", "end", values=row)

    def search_products(self):
        keyword = self.search_entry.get().strip()

        for item in self.product_tree.get_children():
            self.product_tree.delete(item)

        cur = self.db.conn.cursor()
        cur.execute("""
            SELECT id, sku, name, category, price, quantity, low_stock
            FROM products
            WHERE sku LIKE ? OR name LIKE ? OR category LIKE ?
            ORDER BY id DESC
        """, (
            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%"
        ))

        for row in cur.fetchall():
            self.product_tree.insert("", "end", values=row)

    # ---------------- STOCK MANAGEMENT ----------------

    def build_stock(self):
        tk.Label(
            self.stock_tab,
            text="Stock Management",
            bg=BG,
            fg=WHITE,
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w", padx=15, pady=15)

        form = tk.Frame(self.stock_tab, bg=PANEL, padx=20, pady=20)
        form.pack(fill="x", padx=15, pady=10)

        self.stock_product = ttk.Combobox(form, state="readonly", width=38)
        self.stock_product.grid(row=1, column=0, padx=8, pady=8)

        self.stock_type = ttk.Combobox(
            form,
            values=["IN", "OUT"],
            state="readonly",
            width=15
        )
        self.stock_type.set("IN")
        self.stock_type.grid(row=1, column=1, padx=8, pady=8)

        self.stock_quantity = self.entry(form, 15)
        self.stock_quantity.grid(row=1, column=2, padx=8, pady=8)

        self.stock_note = self.entry(form, 25)
        self.stock_note.grid(row=1, column=3, padx=8, pady=8)

        for col, title in enumerate(
            ["Product", "Movement", "Quantity", "Note"]
        ):
            self.label(form, title).grid(
                row=0,
                column=col,
                sticky="w",
                padx=8
            )

        self.button(
            form,
            "Save Stock Movement",
            self.adjust_stock
        ).grid(row=1, column=4, padx=10)

        self.stock_tree = self.make_tree(
            self.stock_tab,
            ("date", "sku", "product", "type", "quantity", "note"),
            ("Date", "SKU", "Product", "Type", "Quantity", "Note")
        )

    def refresh_product_choices(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT id, sku, name FROM products ORDER BY name")

        self.product_choices = {
            f"{row[1]} - {row[2]} (ID:{row[0]})": row[0]
            for row in cur.fetchall()
        }

        self.stock_product["values"] = list(self.product_choices.keys())
        self.sale_product["values"] = list(self.product_choices.keys())

    def adjust_stock(self):
        choice = self.stock_product.get()
        movement = self.stock_type.get()

        try:
            quantity = int(self.stock_quantity.get())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Quantity", "Enter a positive whole number.")
            return

        product_id = self.product_choices.get(choice)

        if product_id is None:
            messagebox.showwarning("Select Product", "Select a product.")
            return

        cur = self.db.conn.cursor()
        cur.execute(
            "SELECT quantity FROM products WHERE id=?",
            (product_id,)
        )
        current = cur.fetchone()[0]

        if movement == "OUT" and quantity > current:
            messagebox.showerror(
                "Insufficient Stock",
                f"Available stock: {current}"
            )
            return

        new_quantity = (
            current + quantity if movement == "IN"
            else current - quantity
        )

        try:
            cur.execute(
                "UPDATE products SET quantity=? WHERE id=?",
                (new_quantity, product_id)
            )

            cur.execute("""
                INSERT INTO stock_movements
                (product_id, movement_type, quantity, note, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                product_id,
                movement,
                quantity,
                self.stock_note.get().strip(),
                datetime.now().isoformat(timespec="seconds")
            ))

            self.db.conn.commit()

            messagebox.showinfo("Success", "Stock updated successfully.")

            self.stock_quantity.delete(0, "end")
            self.stock_note.delete(0, "end")

            self.refresh_all()

        except sqlite3.Error as error:
            self.db.conn.rollback()
            messagebox.showerror("Database Error", str(error))

    def refresh_stock(self):
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)

        cur = self.db.conn.cursor()
        cur.execute("""
            SELECT sm.created_at, p.sku, p.name,
                   sm.movement_type, sm.quantity, sm.note
            FROM stock_movements sm
            JOIN products p ON p.id = sm.product_id
            ORDER BY sm.id DESC
            LIMIT 200
        """)

        for row in cur.fetchall():
            self.stock_tree.insert("", "end", values=row)

    # ---------------- SALES ----------------

    def build_sales(self):
        tk.Label(
            self.sales_tab,
            text="Sales Management",
            bg=BG,
            fg=WHITE,
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w", padx=15, pady=15)

        form = tk.Frame(self.sales_tab, bg=PANEL, padx=20, pady=20)
        form.pack(fill="x", padx=15)

        self.sale_product = ttk.Combobox(form, state="readonly", width=38)
        self.sale_product.grid(row=1, column=0, padx=8, pady=8)

        self.sale_quantity = self.entry(form, 15)
        self.sale_quantity.grid(row=1, column=1, padx=8, pady=8)

        self.sale_price = self.entry(form, 15)
        self.sale_price.grid(row=1, column=2, padx=8, pady=8)

        for col, title in enumerate(
            ["Product", "Quantity", "Selling Price per Unit"]
        ):
            self.label(form, title).grid(
                row=0,
                column=col,
                sticky="w",
                padx=8
            )

        self.button(
            form,
            "Record Sale",
            self.record_sale
        ).grid(row=1, column=3, padx=12)

        self.sale_product.bind(
            "<<ComboboxSelected>>",
            self.load_sale_price
        )

        self.sales_tree = self.make_tree(
            self.sales_tab,
            ("date", "product", "quantity", "price", "total"),
            ("Date", "Product", "Quantity", "Unit Price", "Total")
        )

    def load_sale_price(self, event=None):
        product_id = self.product_choices.get(self.sale_product.get())

        if product_id is None:
            return

        cur = self.db.conn.cursor()
        cur.execute(
            "SELECT price FROM products WHERE id=?",
            (product_id,)
        )

        row = cur.fetchone()

        if row:
            self.sale_price.delete(0, "end")
            self.sale_price.insert(0, str(row[0]))

    def record_sale(self):
        product_id = self.product_choices.get(self.sale_product.get())

        if product_id is None:
            messagebox.showwarning("Select Product", "Select a product.")
            return

        try:
            quantity = int(self.sale_quantity.get())
            price = float(self.sale_price.get())

            if quantity <= 0 or price < 0:
                raise ValueError

        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Enter a positive quantity and a valid price."
            )
            return

        cur = self.db.conn.cursor()

        cur.execute(
            "SELECT name, quantity FROM products WHERE id=?",
            (product_id,)
        )
        product = cur.fetchone()

        if product is None:
            messagebox.showerror("Error", "Product not found.")
            return

        name, available = product

        if quantity > available:
            messagebox.showerror(
                "Insufficient Stock",
                f"{name}: Only {available} units available."
            )
            return

        total = quantity * price
        now = datetime.now().isoformat(timespec="seconds")

        try:
            cur.execute("""
                INSERT INTO sales
                (product_id, quantity, unit_price, total, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (product_id, quantity, price, total, now))

            cur.execute(
                "UPDATE products SET quantity=quantity-? WHERE id=?",
                (quantity, product_id)
            )

            cur.execute("""
                INSERT INTO stock_movements
                (product_id, movement_type, quantity, note, created_at)
                VALUES (?, 'OUT', ?, ?, ?)
            """, (
                product_id,
                quantity,
                "Sales transaction",
                now
            ))

            self.db.conn.commit()

            messagebox.showinfo(
                "Sale Recorded",
                f"Product: {name}\n"
                f"Quantity: {quantity}\n"
                f"Total: ₹{total:,.2f}"
            )

            self.sale_quantity.delete(0, "end")
            self.refresh_all()

        except sqlite3.Error as error:
            self.db.conn.rollback()
            messagebox.showerror("Database Error", str(error))

    def refresh_sales(self):
        for item in self.sales_tree.get_children():
            self.sales_tree.delete(item)

        cur = self.db.conn.cursor()
        cur.execute("""
            SELECT s.created_at, p.name, s.quantity,
                   s.unit_price, s.total
            FROM sales s
            JOIN products p ON p.id = s.product_id
            ORDER BY s.id DESC
            LIMIT 200
        """)

        for row in cur.fetchall():
            self.sales_tree.insert("", "end", values=row)

    # ---------------- REPORTS ----------------

    def build_reports(self):
        tk.Label(
            self.reports_tab,
            text="Sales Reports & Analytics",
            bg=BG,
            fg=WHITE,
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w", padx=15, pady=15)

        actions = tk.Frame(self.reports_tab, bg=BG)
        actions.pack(fill="x", padx=15)

        self.button(
            actions,
            "Refresh Report",
            self.refresh_reports
        ).pack(side="left", padx=5)

        self.button(
            actions,
            "Export CSV",
            self.export_sales_csv,
            GREEN
        ).pack(side="left", padx=5)

        self.report_summary = tk.Label(
            self.reports_tab,
            text="Sales summary will appear here.",
            bg=CARD,
            fg=CYAN,
            font=("Segoe UI", 13, "bold"),
            padx=15,
            pady=15
        )
        self.report_summary.pack(fill="x", padx=15, pady=15)

        self.report_tree = self.make_tree(
            self.reports_tab,
            ("date", "product", "quantity", "price", "total"),
            ("Date", "Product", "Quantity", "Unit Price", "Total")
        )

    def refresh_reports(self):
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)

        cur = self.db.conn.cursor()

        cur.execute("""
            SELECT s.created_at, p.name, s.quantity,
                   s.unit_price, s.total
            FROM sales s
            JOIN products p ON p.id = s.product_id
            ORDER BY s.id DESC
        """)

        rows = cur.fetchall()

        for row in rows:
            self.report_tree.insert("", "end", values=row)

        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        cur.execute(
            "SELECT COALESCE(SUM(total),0), COUNT(*) FROM sales WHERE date(created_at)=?",
            (today,)
        )
        daily_total, daily_count = cur.fetchone()

        cur.execute(
            "SELECT COALESCE(SUM(total),0) FROM sales WHERE substr(created_at,1,7)=?",
            (month,)
        )
        monthly_total = cur.fetchone()[0]

        self.report_summary.config(
            text=(
                f"Today's Revenue: ₹{daily_total:,.2f}    |    "
                f"Today's Transactions: {daily_count}    |    "
                f"This Month's Revenue: ₹{monthly_total:,.2f}"
            )
        )

    def export_sales_csv(self):
        cur = self.db.conn.cursor()
        cur.execute("""
            SELECT s.created_at, p.sku, p.name,
                   s.quantity, s.unit_price, s.total
            FROM sales s
            JOIN products p ON p.id = s.product_id
            ORDER BY s.id DESC
        """)

        rows = cur.fetchall()

        if not rows:
            messagebox.showinfo("No Data", "There are no sales records to export.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile="inventory_sales_report.csv"
        )

        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)

                writer.writerow([
                    "Date",
                    "SKU",
                    "Product",
                    "Quantity",
                    "Unit Price",
                    "Total"
                ])

                writer.writerows(rows)

            messagebox.showinfo(
                "Export Successful",
                f"Report saved successfully:\n{path}"
            )

        except OSError as error:
            messagebox.showerror("Export Error", str(error))

    # ---------------- REFRESH ----------------

    def refresh_all(self):
        self.refresh_products()
        self.refresh_dashboard()
        self.refresh_product_choices()
        self.refresh_stock()
        self.refresh_sales()
        self.refresh_reports()
    # ---------------- DEMO DATA GENERATOR ----------------

    def seed_demo_data(self):

        cur = self.db.conn.cursor()

        # Do not insert demo data again if products already exist
        cur.execute("SELECT COUNT(*) FROM products")
        if cur.fetchone()[0] > 0:
            return

        categories = {
            "Electronics": [
                "USB Cable", "Bluetooth Speaker", "Mouse",
                "Keyboard", "Headphones", "Power Bank",
                "USB Drive", "Webcam", "Charger", "LED Light"
            ],
            "Stationery": [
                "Notebook", "Blue Pen", "Black Pen",
                "Pencil", "Eraser", "Marker",
                "Stapler", "File Folder", "Scale", "Highlighter"
            ],
            "Groceries": [
                "Rice 1kg", "Wheat Flour", "Sugar 1kg",
                "Salt", "Cooking Oil", "Tea Powder",
                "Coffee Powder", "Dal 1kg", "Spices", "Biscuits"
            ],
            "Clothing": [
                "Cotton Shirt", "T-Shirt", "Jeans",
                "Formal Pants", "Socks", "Belt",
                "Cap", "Handkerchief", "Jacket", "Track Pants"
            ],
            "Home": [
                "Water Bottle", "Storage Box", "Bucket",
                "Mug", "Lunch Box", "Dustbin",
                "Cleaning Brush", "Towel", "Bedsheet", "Pillow"
            ],
            "Mobile Accessories": [
                "Phone Case", "Screen Guard", "OTG Cable",
                "Mobile Stand", "Earphones", "Car Charger",
                "Wireless Charger", "SIM Adapter", "Ring Holder", "Tripod"
            ],
            "Kitchen": [
                "Steel Plate", "Steel Glass", "Spoon",
                "Cooker", "Pan", "Knife",
                "Chopping Board", "Strainer", "Container", "Kettle"
            ],
            "Personal Care": [
                "Soap", "Shampoo", "Toothpaste",
                "Toothbrush", "Face Wash", "Comb",
                "Hair Oil", "Deodorant", "Lotion", "Tissue Pack"
            ],
            "Accessories": [
                "Watch", "Wallet", "Sunglasses",
                "Keychain", "Handbag", "Umbrella",
                "Travel Pouch", "Waterproof Bag", "Bracelet", "Diary"
            ],
            "Sports": [
                "Cricket Ball", "Football", "Tennis Ball",
                "Skipping Rope", "Yoga Mat", "Gym Gloves",
                "Badminton Racket", "Shuttlecock", "Sports Bottle", "Resistance Band"
            ]
        }

        product_ids = []

        # Create exactly 100 sample products
        index = 0

        for category, names in categories.items():

            for name in names:

                index += 1

                sku = f"HV{index:03d}"
                price = 50 + (index * 17) % 950
                quantity = 20 + (index * 7) % 60
                low_stock = 10

                cur.execute("""
                    INSERT INTO products
                    (sku, name, category, price, quantity, low_stock)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    sku,
                    name,
                    category,
                    price,
                    quantity,
                    low_stock
                ))

                product_id = cur.lastrowid
                product_ids.append(product_id)

                # Record opening stock
                cur.execute("""
                    INSERT INTO stock_movements
                    (product_id, movement_type, quantity, note, created_at)
                    VALUES (?, 'IN', ?, ?, ?)
                """, (
                    product_id,
                    quantity,
                    "Demo opening stock",
                    datetime.now().isoformat(timespec="seconds")
                ))

        # Add extra stock to 20 products
        for i in range(0, 100, 5):

            product_id = product_ids[i]
            extra_stock = 10 + (i % 10)

            cur.execute("""
                UPDATE products
                SET quantity = quantity + ?
                WHERE id = ?
            """, (extra_stock, product_id))

            cur.execute("""
                INSERT INTO stock_movements
                (product_id, movement_type, quantity, note, created_at)
                VALUES (?, 'IN', ?, ?, ?)
            """, (
                product_id,
                extra_stock,
                "Demo additional stock",
                datetime.now().isoformat(timespec="seconds")
            ))

        # Create 30 sample sales transactions
        for i in range(30):

            product_id = product_ids[i]
            quantity_sold = 1 + (i % 3)

            cur.execute("""
                SELECT name, price, quantity
                FROM products
                WHERE id = ?
            """, (product_id,))

            name, price, available = cur.fetchone()

            if available < quantity_sold:
                continue

            selling_price = round(price * 1.10, 2)
            total = round(selling_price * quantity_sold, 2)

            # Spread demo sales across recent days
            sale_date = datetime.now() - timedelta(days=i % 15)
            sale_time = sale_date.isoformat(timespec="seconds")

            cur.execute("""
                INSERT INTO sales
                (product_id, quantity, unit_price, total, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                product_id,
                quantity_sold,
                selling_price,
                total,
                sale_time
            ))

            cur.execute("""
                UPDATE products
                SET quantity = quantity - ?
                WHERE id = ?
            """, (quantity_sold, product_id))

            cur.execute("""
                INSERT INTO stock_movements
                (product_id, movement_type, quantity, note, created_at)
                VALUES (?, 'OUT', ?, ?, ?)
            """, (
                product_id,
                quantity_sold,
                "Demo sales transaction",
                sale_time
            ))

        self.db.conn.commit()

    # ---------------- AUTOMATIC CSV EXPORT ----------------

    def export_demo_csvs(self):

        reports_folder = Path(__file__).parent / "reports"
        reports_folder.mkdir(exist_ok=True)

        cur = self.db.conn.cursor()

        # Export Products
        cur.execute("""
            SELECT id, sku, name, category, price, quantity, low_stock
            FROM products
            ORDER BY id
        """)

        with open(
            reports_folder / "products_report.csv",
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "ID", "SKU", "Product", "Category",
                "Price", "Stock", "Low Stock Limit"
            ])

            writer.writerows(cur.fetchall())

        # Export Sales
        cur.execute("""
            SELECT s.id, s.created_at, p.sku, p.name,
                   s.quantity, s.unit_price, s.total
            FROM sales s
            JOIN products p ON p.id = s.product_id
            ORDER BY s.id
        """)

        with open(
            reports_folder / "sales_report.csv",
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "Sale ID", "Date", "SKU", "Product",
                "Quantity", "Unit Price", "Total"
            ])

            writer.writerows(cur.fetchall())

        # Export Stock Movements
        cur.execute("""
            SELECT sm.id, sm.created_at, p.sku, p.name,
                   sm.movement_type, sm.quantity, sm.note
            FROM stock_movements sm
            JOIN products p ON p.id = sm.product_id
            ORDER BY sm.id
        """)

        with open(
            reports_folder / "stock_report.csv",
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "Movement ID", "Date", "SKU", "Product",
                "Movement Type", "Quantity", "Note"
            ])

            writer.writerows(cur.fetchall())
    def close_app(self):
        self.db.close()
        self.root.destroy()
            

# ---------------- APPLICATION START ----------------

if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryApp(root)
    root.mainloop()




