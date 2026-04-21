import os
import sys
import tkinter as tk
from tkinter import ttk
from app.database import SessionLocal
from app.models import Project, ProjectTask


if getattr(sys, "frozen", False):
    bundle_root = getattr(sys, "_MEIPASS", "")
    tcl_library = os.path.join(bundle_root, "tcl", "tcl8.6")
    tk_library = os.path.join(bundle_root, "tcl", "tk8.6")

    if os.path.isdir(tcl_library):
        os.environ["TCL_LIBRARY"] = tcl_library
    if os.path.isdir(tk_library):
        os.environ["TK_LIBRARY"] = tk_library


def ask_project_for_block(app_name: str):
    db = SessionLocal()
    projects = db.query(Project).filter(Project.is_active == True).all()
    db.close()

    result = {
        "project_id": None,
        "action": "later",
        "task_text": "",
        "comment_text": ""
    }

    root = tk.Tk()
    root.title("Zeitblock zuordnen")
    root.geometry("460x420")
    root.resizable(False, False)

    label = tk.Label(
        root,
        text=f"Keine sichere Zuordnung gefunden.\n\nApp: {app_name}\n\nProjekt und Aufgabe wählen:",
        justify="left",
        pady=10
    )
    label.pack()

    project_names = [p.name for p in projects]
    selected_project = tk.StringVar()

    combo = ttk.Combobox(
        root,
        textvariable=selected_project,
        values=project_names,
        state="readonly",
        width=40
    )
    combo.pack(pady=10)

    task_list_label = tk.Label(root, text="Vorhandene Aufgaben")
    task_list_label.pack()

    task_var = tk.StringVar()

    task_combo = ttk.Combobox(
        root,
        textvariable=task_var,
        values=[],
        state="readonly",
        width=40
    )
    task_combo.pack(pady=5)
    task_combo.set("")

    task_label = tk.Label(root, text="Oder neue Aufgabe / Ticket / Kommentar")
    task_label.pack()

    task_entry = tk.Entry(root, width=50)
    task_entry.pack(pady=5)

    comment_label = tk.Label(root, text="Kommentar / Details")
    comment_label.pack()

    comment_entry = tk.Entry(root, width=50)
    comment_entry.pack(pady=5)

    error_label = tk.Label(root, text="", fg="red")
    error_label.pack(pady=(0, 5))

    def load_tasks(event=None):
        chosen_name = selected_project.get()

        for p in projects:
            if p.name == chosen_name:
                db = SessionLocal()
                tasks = db.query(ProjectTask).filter(ProjectTask.project_id == p.id).all()
                db.close()

                task_names = [""] + [t.name for t in tasks]
                task_combo["values"] = task_names
                break

    def on_project_change(event=None):
        load_tasks()
        task_combo.set("")
        task_entry.delete(0, tk.END)
        error_label.config(text="")

    def on_task_combo_change(event=None):
        if task_var.get().strip():
            task_entry.delete(0, tk.END)
        error_label.config(text="")

    def on_task_entry_change(event=None):
        if task_entry.get().strip():
            task_combo.set("")
        error_label.config(text="")

    combo.bind("<<ComboboxSelected>>", on_project_change)
    task_combo.bind("<<ComboboxSelected>>", on_task_combo_change)
    task_entry.bind("<KeyRelease>", on_task_entry_change)
    comment_entry.bind("<KeyRelease>", lambda event: error_label.config(text=""))

    def assign():
        chosen_name = selected_project.get()
        selected_task = task_var.get().strip()
        new_task = task_entry.get().strip()
        comment_text = comment_entry.get().strip()

        if not chosen_name:
            error_label.config(text="Bitte ein Projekt auswählen.")
            return

        if selected_task and new_task:
            error_label.config(text="Bitte entweder vorhandene Aufgabe wählen oder neue Aufgabe eingeben.")
            return

        final_task = selected_task or new_task

        if not final_task and not comment_text:
            error_label.config(text="Bitte Aufgabe oder Kommentar eingeben oder auf Später klicken.")
            return

        for p in projects:
            if p.name == chosen_name:
                result["project_id"] = p.id
                result["action"] = "assign"
                result["task_text"] = final_task
                result["comment_text"] = comment_text
                break

        root.destroy()

    def later():
        result["action"] = "later"
        task_value = task_var.get().strip() or task_entry.get().strip()
        result["task_text"] = task_value
        result["comment_text"] = comment_entry.get().strip()
        root.destroy()

    
    button_frame = tk.Frame(root)
    button_frame.pack(pady=(12, 16))

    assign_button = tk.Button(button_frame, text="Speichern", command=assign, width=15)
    assign_button.grid(row=0, column=0, padx=5)

    later_button = tk.Button(button_frame, text="Später", command=later, width=15)
    later_button.grid(row=0, column=1, padx=5)

    root.mainloop()
    return result
