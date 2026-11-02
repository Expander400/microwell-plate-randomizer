"""Tkinter desktop interface. All widget updates run on the main thread."""

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import (COLUMNS, DEFAULT_LABELS, ROWS, SAMPLE_WELLS, default_water,
                   export_csv, parse_samples, randomize_plate)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Microwell Plate Randomizer")
        self.seed = tk.StringVar(value="20539")
        self.mode = tk.StringVar(value="water")
        self.water = default_water()
        self.excluded = set()
        self.result = None
        self.buttons = {}
        self.revision = 0
        self.busy = False
        self.completed = queue.Queue()
        self.status = tk.StringVar(value="Choose a well type, then click wells to edit the plate.")
        self.well_detail = tk.StringVar(value="Hover over a well to see its full label.")
        self.build()
        self.refresh()

    def build(self):
        # Scroll the whole layout so it remains usable on small screens / high DPI.
        self.minsize(600, 400)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        canvas = tk.Canvas(self, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(self, orient="horizontal", command=canvas.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        canvas.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
        body = ttk.Frame(canvas, padding=16)
        canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        ttk.Label(body, text="Microwell Plate Randomizer", font=("TkDefaultFont", 16, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(body, text="Replicates use different rows and are spread evenly across column groups 2–4, 5–7 and 8–11.").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 12))
        left = ttk.Frame(body)
        left.grid(row=2, column=0, sticky="nw", padx=(0, 16))
        ttk.Label(left, text="Seed (whole number)").pack(anchor="w")
        ttk.Entry(left, textvariable=self.seed, width=24).pack(fill="x", pady=(2, 10))
        ttk.Label(left, text="Sample, replicates (one per line)").pack(anchor="w")
        editor = ttk.Frame(left)
        editor.pack(fill="x", pady=(2, 4))
        self.labels = tk.Text(editor, width=24, height=15, undo=True, wrap="none")
        self.labels.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(editor, command=self.labels.yview)
        scrollbar.pack(side="right", fill="y")
        self.labels.configure(yscrollcommand=scrollbar.set)
        self.labels.insert("1.0", "\n".join(f"{label}, 3" for label in DEFAULT_LABELS))
        self.labels.edit_modified(False)
        self.labels.bind("<<Modified>>", self.labels_changed)
        ttk.Label(left, text="Example: LB-A, 3\n1–8 replicates; one per available row.").pack(anchor="w", pady=(0, 10))
        ttk.Label(left, text="Click wells to mark as:").pack(anchor="w")
        for text, value in [("Water", "water"), ("Do not randomize", "excluded"), ("Available", "available")]:
            ttk.Radiobutton(left, text=text, variable=self.mode, value=value).pack(anchor="w")
        ttk.Button(left, text="Reset well selection", command=self.reset).pack(fill="x", pady=(10, 0))
        plate = ttk.Frame(body)
        plate.grid(row=2, column=1, sticky="nw")
        for col in COLUMNS:
            ttk.Label(plate, text=str(col), anchor="center").grid(row=0, column=col, sticky="ew")
        for row_index, row in enumerate(ROWS, 1):
            ttk.Label(plate, text=row).grid(row=row_index, column=0, padx=(0, 5))
            for col in COLUMNS:
                well = (row, col)
                button = tk.Button(plate, width=9, height=2, font=("TkDefaultFont", 8),
                                   fg="#15202b", activeforeground="#15202b",
                                   command=lambda w=well: self.set_well(w))
                button.grid(row=row_index, column=col, padx=1, pady=1)
                button.bind("<Enter>", lambda _event, w=well: self.describe_well(w))
                button.bind("<FocusIn>", lambda _event, w=well: self.describe_well(w))
                self.buttons[well] = button
        ttk.Label(plate, textvariable=self.well_detail, wraplength=780).grid(row=9, column=0, columnspan=13, sticky="w", pady=(8, 4))
        ttk.Label(plate, text="Columns 1 and 12 are outside the sampling groups.\nExcluded wells stay empty; they do not preserve a previous sample.\nBlue = water · Gray = excluded/outside groups · Green = assigned sample", wraplength=780).grid(row=10, column=0, columnspan=13, sticky="w")
        actions = ttk.Frame(body)
        actions.grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 8))
        self.generate_button = ttk.Button(actions, text="Randomize plate", command=self.generate)
        self.generate_button.pack(side="left", padx=(0, 8))
        self.export_button = ttk.Button(actions, text="Export CSV", command=self.export, state="disabled")
        self.export_button.pack(side="left")
        ttk.Label(body, textvariable=self.status, wraplength=1000).grid(row=4, column=0, columnspan=2, sticky="w")
        self.seed.trace_add("write", lambda *_: self.invalidate())
        self.update_idletasks()
        width = min(body.winfo_reqwidth() + 24, self.winfo_screenwidth() - 80)
        height = min(body.winfo_reqheight() + 24, self.winfo_screenheight() - 100)
        self.geometry(f"{width}x{height}")

    def labels_changed(self, _event):
        if self.labels.edit_modified():
            self.labels.edit_modified(False)
            self.invalidate()

    def invalidate(self):
        self.revision += 1
        had_result = self.result is not None
        self.result = None
        self.export_button.configure(state="disabled")
        if had_result or self.busy:
            self.status.set("Settings changed. Randomize again before exporting.")
        self.refresh()

    def set_well(self, well):
        if self.mode.get() == "available" and well not in SAMPLE_WELLS:
            self.status.set("Columns 1 and 12 are outside the sampling groups. Use columns 2–11 for samples.")
            return
        self.water.discard(well)
        self.excluded.discard(well)
        if self.mode.get() == "water":
            self.water.add(well)
        elif self.mode.get() == "excluded":
            self.excluded.add(well)
        self.invalidate()
        self.describe_well(well)

    def reset(self):
        self.water = default_water()
        self.excluded.clear()
        self.invalidate()
        self.status.set("Restored the water perimeter and cleared excluded wells.")

    def well_display(self, well):
        if well in self.water:
            return "Water", "#cce8f6"
        if well in self.excluded:
            return "Excluded", "#e1e3e5"
        if well not in SAMPLE_WELLS:
            return "Outside groups", "#e1e3e5"
        if self.result is not None:
            value = self.result[well]
            return value, "#ffffff" if value == "Unused" else "#d8eedb"
        return "Available", "#ffffff"

    def describe_well(self, well):
        value, _ = self.well_display(well)
        self.well_detail.set(f"{well[0]}{well[1]}: {value}")

    def refresh(self):
        for well, button in self.buttons.items():
            text, color = self.well_display(well)
            shown = text if len(text) <= 12 else text[:11] + "…"
            button.configure(text=shown, bg=color, activebackground=color)

    def generate(self):
        if self.busy:
            return
        # Flush the Text modified flag before taking a settings snapshot.
        if self.labels.edit_modified():
            self.labels.edit_modified(False)
            self.invalidate()
        try:
            samples = parse_samples(self.labels.get("1.0", "end"))
            try:
                seed = int(self.seed.get().strip())
            except ValueError:
                raise ValueError("The seed must be a whole number, for example 20539.") from None
        except ValueError as exc:
            messagebox.showerror("Cannot randomize", str(exc), parent=self)
            return
        self.invalidate()
        revision = self.revision
        water, excluded = self.water.copy(), self.excluded.copy()
        self.busy = True
        self.generate_button.configure(state="disabled")
        self.status.set("Finding a plate layout…")

        def work():
            try:
                result = randomize_plate(seed, samples, water, excluded)
                error = None
            except Exception as exc:
                result, error = None, exc
            self.completed.put((revision, seed, samples, result, error))

        threading.Thread(target=work, daemon=True).start()
        self.after(50, self.finish_generation)

    def finish_generation(self):
        try:
            revision, seed, samples, result, error = self.completed.get_nowait()
        except queue.Empty:
            self.after(50, self.finish_generation)
            return
        self.busy = False
        self.generate_button.configure(state="normal")
        if revision != self.revision:
            self.status.set("Settings changed during generation. Randomize again to use the current settings.")
            return
        if error is not None:
            self.status.set("No plate generated. Adjust the settings and try again.")
            messagebox.showerror("Cannot randomize", str(error), parent=self)
            return
        self.result = result
        self.export_button.configure(state="normal")
        self.refresh()
        self.status.set(f"Generated {sum(samples.values())} wells for {len(samples)} samples with seed {seed}. Export to save the plate.")

    def export(self):
        if self.result is None:
            messagebox.showinfo("Generate a plate", "Randomize the plate before exporting.", parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, title="Export plate", initialfile=f"plate_seed_{self.seed.get().strip()}.csv",
                                          defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            export_csv(path, self.result)
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc), parent=self)
            return
        self.status.set(f"Saved plate to {path}")
