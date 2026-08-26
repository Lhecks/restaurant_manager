"""
=====================================================
APPLICATION MULTI-PAGES - VERSION FONCTIONS (CORRIGÉE)
=====================================================
BUT : Application multi-pages avec navigation
PROBLÈME RÉSOLU : Les pages sont maintenant placées dans le conteneur
=====================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox

# =====================================================
# VARIABLES GLOBALES
# =====================================================

pages = {}

staff_list = [
    ("Alice Johnson", "Manager", "RH"),
    ("Bob Smith", "Développeur", "IT"),
    ("Carol White", "Designer", "Créatif"),
]

client_list = [
    ("Acme Corp", "john@acme.com", "555-0101"),
    ("Tech Solutions", "sarah@tech.com", "555-0202"),
    ("Creative Studio", "mike@creative.com", "555-0303"),
]

# =====================================================
# FONCTIONS DE NAVIGATION
# =====================================================


def show_page(page_name):
    """Affiche la page demandée."""
    page = pages.get(page_name)
    if page:
        page.tkraise()
        titles = {
            "menu": "🏠 Menu Principal",
            "staff": "👨‍💼 Gestion du Personnel",
            "client": "👤 Gestion des Clients",
            "staff_detail": "📋 Détails du Personnel",
            "client_detail": "📋 Détails du Client",
        }
        window.title(titles.get(page_name, "Application Multi-Pages"))


# =====================================================
# PAGE 1: MENU PRINCIPAL
# =====================================================


def create_menu_page():
    """Crée et place la page du menu principal."""
    page = tk.Frame(container, bg="#f0f0f0")

    # ✅ PLACER LA PAGE DANS LE CONTENEUR
    page.place(x=0, y=0, relwidth=1, relheight=1)
    pages["menu"] = page

    # En-tête
    header = tk.Label(
        page,
        text="🏠 MENU PRINCIPAL",
        font=("Arial", 28, "bold"),
        bg="#2C3E50",
        fg="white",
        pady=20,
    )
    header.pack(fill="x")

    tk.Label(
        page,
        text="Bienvenue dans l'application Multi-Pages",
        font=("Arial", 18),
        bg="#f0f0f0",
        fg="#2C3E50",
        pady=30,
    ).pack()

    tk.Label(
        page,
        text="Veuillez choisir une option ci-dessous :",
        font=("Arial", 14),
        bg="#f0f0f0",
        fg="#7f8c8d",
    ).pack()

    button_frame = tk.Frame(page, bg="#f0f0f0")
    button_frame.pack(pady=40)

    tk.Button(
        button_frame,
        text="👨‍💼 Gestion du Personnel",
        font=("Arial", 16, "bold"),
        command=lambda: show_page("staff"),
        bg="#3498db",
        fg="white",
        padx=40,
        pady=20,
        width=25,
        relief="raised",
        bd=3,
    ).pack(pady=10)

    tk.Button(
        button_frame,
        text="👤 Gestion des Clients",
        font=("Arial", 16, "bold"),
        command=lambda: show_page("client"),
        bg="#27ae60",
        fg="white",
        padx=40,
        pady=20,
        width=25,
        relief="raised",
        bd=3,
    ).pack(pady=10)

    tk.Button(
        button_frame,
        text="❌ Quitter",
        font=("Arial", 14),
        command=quitter_app,
        bg="#e74c3c",
        fg="white",
        padx=40,
        pady=10,
        width=25,
        relief="raised",
        bd=2,
    ).pack(pady=20)

    return page


# =====================================================
# PAGE 2: GESTION DU PERSONNEL
# =====================================================


def create_staff_page():
    """Crée et place la page de gestion du personnel."""
    page = tk.Frame(container, bg="#f0f0f0")

    # ✅ PLACER LA PAGE DANS LE CONTENEUR
    page.place(x=0, y=0, relwidth=1, relheight=1)
    pages["staff"] = page

    header_frame = tk.Frame(page, bg="#3498db")
    header_frame.pack(fill="x")

    tk.Label(
        header_frame,
        text="👨‍💼 GESTION DU PERSONNEL",
        font=("Arial", 22, "bold"),
        bg="#3498db",
        fg="white",
        pady=15,
    ).pack()

    content_frame = tk.Frame(page, bg="#f0f0f0")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # ---- GAUCHE: Ajouter ----
    left_frame = tk.LabelFrame(
        content_frame,
        text="➕ Ajouter un membre",
        font=("Arial", 14, "bold"),
        bg="#f0f0f0",
        padx=15,
        pady=15,
    )
    left_frame.pack(side="left", fill="both", expand=True, padx=10)

    tk.Label(left_frame, text="Nom :", font=("Arial", 12), bg="#f0f0f0").grid(
        row=0, column=0, sticky="e", pady=5, padx=5
    )
    staff_name_entry = tk.Entry(left_frame, font=("Arial", 12), width=25)
    staff_name_entry.grid(row=0, column=1, pady=5, padx=5)

    tk.Label(left_frame, text="Poste :", font=("Arial", 12), bg="#f0f0f0").grid(
        row=1, column=0, sticky="e", pady=5, padx=5
    )
    staff_position_entry = tk.Entry(left_frame, font=("Arial", 12), width=25)
    staff_position_entry.grid(row=1, column=1, pady=5, padx=5)

    tk.Label(left_frame, text="Département :", font=("Arial", 12), bg="#f0f0f0").grid(
        row=2, column=0, sticky="e", pady=5, padx=5
    )
    staff_dept_entry = tk.Entry(left_frame, font=("Arial", 12), width=25)
    staff_dept_entry.grid(row=2, column=1, pady=5, padx=5)

    def ajouter_staff():
        nom = staff_name_entry.get().strip()
        poste = staff_position_entry.get().strip()
        dept = staff_dept_entry.get().strip()

        if not nom or not poste or not dept:
            messagebox.showwarning("Erreur", "Veuillez remplir tous les champs !")
            return

        staff_list.append((nom, poste, dept))
        rafraichir_staff()

        staff_name_entry.delete(0, tk.END)
        staff_position_entry.delete(0, tk.END)
        staff_dept_entry.delete(0, tk.END)
        messagebox.showinfo("Succès", f"Membre '{nom}' ajouté !")

    tk.Button(
        left_frame,
        text="➕ Ajouter",
        font=("Arial", 12, "bold"),
        command=ajouter_staff,
        bg="#3498db",
        fg="white",
        padx=20,
        pady=5,
    ).grid(row=3, column=0, columnspan=2, pady=15)

    # ---- DROITE: Liste ----
    right_frame = tk.LabelFrame(
        content_frame,
        text="📋 Liste du personnel",
        font=("Arial", 14, "bold"),
        bg="#f0f0f0",
        padx=15,
        pady=15,
    )
    right_frame.pack(side="right", fill="both", expand=True, padx=10)

    staff_tree = ttk.Treeview(
        right_frame, columns=("Nom", "Poste", "Département"), show="headings", height=6
    )

    for col in ("Nom", "Poste", "Département"):
        staff_tree.heading(col, text=col)
        staff_tree.column(col, width=150)

    staff_tree.pack(fill="both", expand=True, pady=5)

    def rafraichir_staff():
        for item in staff_tree.get_children():
            staff_tree.delete(item)
        for staff in staff_list:
            staff_tree.insert("", tk.END, values=staff)

    rafraichir_staff()

    def ouvrir_details_staff(event):
        selected = staff_tree.selection()
        if selected:
            values = staff_tree.item(selected[0], "values")
            pages["staff_detail"].set_data(values)
            show_page("staff_detail")

    staff_tree.bind("<Double-1>", ouvrir_details_staff)

    # ---- Navigation ----
    nav_frame = tk.Frame(page, bg="#f0f0f0")
    nav_frame.pack(fill="x", pady=10)

    tk.Button(
        nav_frame,
        text="🔙 Retour au Menu",
        font=("Arial", 12),
        command=lambda: show_page("menu"),
        bg="#95a5a6",
        fg="white",
        padx=20,
        pady=8,
    ).pack(side="left", padx=20)

    return page


# =====================================================
# PAGE 3: GESTION DES CLIENTS
# =====================================================


def create_client_page():
    """Crée et place la page de gestion des clients."""
    page = tk.Frame(container, bg="#f0f0f0")

    # ✅ PLACER LA PAGE DANS LE CONTENEUR
    page.place(x=0, y=0, relwidth=1, relheight=1)
    pages["client"] = page

    header_frame = tk.Frame(page, bg="#27ae60")
    header_frame.pack(fill="x")

    tk.Label(
        header_frame,
        text="👤 GESTION DES CLIENTS",
        font=("Arial", 22, "bold"),
        bg="#27ae60",
        fg="white",
        pady=15,
    ).pack()

    content_frame = tk.Frame(page, bg="#f0f0f0")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # ---- GAUCHE: Ajouter ----
    left_frame = tk.LabelFrame(
        content_frame,
        text="➕ Ajouter un client",
        font=("Arial", 14, "bold"),
        bg="#f0f0f0",
        padx=15,
        pady=15,
    )
    left_frame.pack(side="left", fill="both", expand=True, padx=10)

    tk.Label(left_frame, text="Société :", font=("Arial", 12), bg="#f0f0f0").grid(
        row=0, column=0, sticky="e", pady=5, padx=5
    )
    client_name_entry = tk.Entry(left_frame, font=("Arial", 12), width=25)
    client_name_entry.grid(row=0, column=1, pady=5, padx=5)

    tk.Label(left_frame, text="Email :", font=("Arial", 12), bg="#f0f0f0").grid(
        row=1, column=0, sticky="e", pady=5, padx=5
    )
    client_email_entry = tk.Entry(left_frame, font=("Arial", 12), width=25)
    client_email_entry.grid(row=1, column=1, pady=5, padx=5)

    tk.Label(left_frame, text="Téléphone :", font=("Arial", 12), bg="#f0f0f0").grid(
        row=2, column=0, sticky="e", pady=5, padx=5
    )
    client_phone_entry = tk.Entry(left_frame, font=("Arial", 12), width=25)
    client_phone_entry.grid(row=2, column=1, pady=5, padx=5)

    def ajouter_client():
        nom = client_name_entry.get().strip()
        email = client_email_entry.get().strip()
        phone = client_phone_entry.get().strip()

        if not nom or not email or not phone:
            messagebox.showwarning("Erreur", "Veuillez remplir tous les champs !")
            return

        client_list.append((nom, email, phone))
        rafraichir_client()

        client_name_entry.delete(0, tk.END)
        client_email_entry.delete(0, tk.END)
        client_phone_entry.delete(0, tk.END)
        messagebox.showinfo("Succès", f"Client '{nom}' ajouté !")

    tk.Button(
        left_frame,
        text="➕ Ajouter",
        font=("Arial", 12, "bold"),
        command=ajouter_client,
        bg="#27ae60",
        fg="white",
        padx=20,
        pady=5,
    ).grid(row=3, column=0, columnspan=2, pady=15)

    # ---- DROITE: Liste ----
    right_frame = tk.LabelFrame(
        content_frame,
        text="📋 Liste des clients",
        font=("Arial", 14, "bold"),
        bg="#f0f0f0",
        padx=15,
        pady=15,
    )
    right_frame.pack(side="right", fill="both", expand=True, padx=10)

    client_tree = ttk.Treeview(
        right_frame,
        columns=("Société", "Email", "Téléphone"),
        show="headings",
        height=6,
    )

    for col in ("Société", "Email", "Téléphone"):
        client_tree.heading(col, text=col)
        client_tree.column(col, width=150)

    client_tree.pack(fill="both", expand=True, pady=5)

    def rafraichir_client():
        for item in client_tree.get_children():
            client_tree.delete(item)
        for client in client_list:
            client_tree.insert("", tk.END, values=client)

    rafraichir_client()

    def ouvrir_details_client(event):
        selected = client_tree.selection()
        if selected:
            values = client_tree.item(selected[0], "values")
            pages["client_detail"].set_data(values)
            show_page("client_detail")

    client_tree.bind("<Double-1>", ouvrir_details_client)

    # ---- Navigation ----
    nav_frame = tk.Frame(page, bg="#f0f0f0")
    nav_frame.pack(fill="x", pady=10)

    tk.Button(
        nav_frame,
        text="🔙 Retour au Menu",
        font=("Arial", 12),
        command=lambda: show_page("menu"),
        bg="#95a5a6",
        fg="white",
        padx=20,
        pady=8,
    ).pack(side="left", padx=20)

    return page


# =====================================================
# PAGE 4: DÉTAILS DU PERSONNEL
# =====================================================


def create_staff_detail_page():
    """Crée et place la page des détails du personnel."""
    page = tk.Frame(container, bg="#f0f0f0")

    # ✅ PLACER LA PAGE DANS LE CONTENEUR
    page.place(x=0, y=0, relwidth=1, relheight=1)
    pages["staff_detail"] = page

    page.data = ("Inconnu", "Inconnu", "Inconnu")

    def set_data(data):
        page.data = data
        for i, value in enumerate(data):
            if i < len(detail_labels):
                detail_labels[i].config(text=value)

    page.set_data = set_data

    tk.Label(
        page,
        text="📋 DÉTAILS DU PERSONNEL",
        font=("Arial", 22, "bold"),
        bg="#3498db",
        fg="white",
        pady=15,
    ).pack(fill="x")

    detail_frame = tk.Frame(page, bg="white", relief="ridge", bd=2)
    detail_frame.pack(padx=50, pady=50, fill="both", expand=True)

    detail_labels = []
    fields = ["Nom :", "Poste :", "Département :"]

    for i, field in enumerate(fields):
        tk.Label(detail_frame, text=field, font=("Arial", 14, "bold"), bg="white").grid(
            row=i, column=0, sticky="e", padx=20, pady=15
        )

        label = tk.Label(
            detail_frame, text="", font=("Arial", 14), bg="white", fg="#2C3E50"
        )
        label.grid(row=i, column=1, sticky="w", padx=20, pady=15)
        detail_labels.append(label)

    nav_frame = tk.Frame(page, bg="#f0f0f0")
    nav_frame.pack(fill="x", pady=20)

    tk.Button(
        nav_frame,
        text="🔙 Retour au Personnel",
        font=("Arial", 12),
        command=lambda: show_page("staff"),
        bg="#95a5a6",
        fg="white",
        padx=20,
        pady=8,
    ).pack(side="left", padx=20)

    tk.Button(
        nav_frame,
        text="🏠 Retour au Menu",
        font=("Arial", 12),
        command=lambda: show_page("menu"),
        bg="#2C3E50",
        fg="white",
        padx=20,
        pady=8,
    ).pack(side="left", padx=20)

    return page


# =====================================================
# PAGE 5: DÉTAILS DU CLIENT
# =====================================================


def create_client_detail_page():
    """Crée et place la page des détails du client."""
    page = tk.Frame(container, bg="#f0f0f0")

    # ✅ PLACER LA PAGE DANS LE CONTENEUR
    page.place(x=0, y=0, relwidth=1, relheight=1)
    pages["client_detail"] = page

    page.data = ("Inconnu", "Inconnu", "Inconnu")

    def set_data(data):
        page.data = data
        for i, value in enumerate(data):
            if i < len(detail_labels):
                detail_labels[i].config(text=value)

    page.set_data = set_data

    tk.Label(
        page,
        text="📋 DÉTAILS DU CLIENT",
        font=("Arial", 22, "bold"),
        bg="#27ae60",
        fg="white",
        pady=15,
    ).pack(fill="x")

    detail_frame = tk.Frame(page, bg="white", relief="ridge", bd=2)
    detail_frame.pack(padx=50, pady=50, fill="both", expand=True)

    detail_labels = []
    fields = ["Société :", "Email :", "Téléphone :"]

    for i, field in enumerate(fields):
        tk.Label(detail_frame, text=field, font=("Arial", 14, "bold"), bg="white").grid(
            row=i, column=0, sticky="e", padx=20, pady=15
        )

        label = tk.Label(
            detail_frame, text="", font=("Arial", 14), bg="white", fg="#2C3E50"
        )
        label.grid(row=i, column=1, sticky="w", padx=20, pady=15)
        detail_labels.append(label)

    nav_frame = tk.Frame(page, bg="#f0f0f0")
    nav_frame.pack(fill="x", pady=20)

    tk.Button(
        nav_frame,
        text="🔙 Retour aux Clients",
        font=("Arial", 12),
        command=lambda: show_page("client"),
        bg="#95a5a6",
        fg="white",
        padx=20,
        pady=8,
    ).pack(side="left", padx=20)

    tk.Button(
        nav_frame,
        text="🏠 Retour au Menu",
        font=("Arial", 12),
        command=lambda: show_page("menu"),
        bg="#2C3E50",
        fg="white",
        padx=20,
        pady=8,
    ).pack(side="left", padx=20)

    return page


# =====================================================
# QUITTER L'APPLICATION
# =====================================================


def quitter_app():
    if messagebox.askyesno("Quitter", "Voulez-vous vraiment quitter l'application ?"):
        window.destroy()


# =====================================================
# FENÊTRE PRINCIPALE
# =====================================================

window = tk.Tk()
window.title("🏠 Application Multi-Pages")
window.geometry("900x650")
window.minsize(800, 550)
window.configure(bg="#f0f0f0")

# =====================================================
# CONTENEUR POUR LES PAGES
# =====================================================

container = tk.Frame(window, bg="#f0f0f0")
container.pack(fill="both", expand=True)

# =====================================================
# CRÉER TOUTES LES PAGES
# =====================================================

create_menu_page()
create_staff_page()
create_client_page()
create_staff_detail_page()
create_client_detail_page()

# =====================================================
# AFFICHER LA PAGE DE DÉPART
# =====================================================

show_page("menu")

# =====================================================
# LANCER L'APPLICATION
# =====================================================

window.mainloop()
