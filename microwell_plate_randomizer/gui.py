"""Tkinter desktop interface. All widget updates run on the main thread."""

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import (COLUMNS, DEFAULT_LABELS, ROWS, WELLS, default_water,
                   export_csv, parse_samples, randomize_plate, validate_custom_marks)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Microwell Plate Randomizer")
        self.seed = tk.StringVar(value="20539")
        self.mode = tk.StringVar(value="water")
        self.water = set()
        self.excluded = set()
        self.custom_marks = {}
        self.custom_text = tk.StringVar(value="Control")
        self.fill_unused = tk.BooleanVar(value=False)
        self.sample_wells = set()
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
        ttk.Label(body, text="Replicates use different rows and are spread evenly across column groups 1–4, 5–7 and 8–12.").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 12))
        left = ttk.Frame(body)
        left.grid(row=2, column=0, sticky="nw", padx=(0, 16))
        ttk.Label(left, text="Seed (whole number)").pack(anchor="w")
        ttk.Entry(left, textvariable=self.seed, width=24).pack(fill="x", pady=(2, 10))
        ttk.Label(left, text="Sample, replicates (one per line)").pack(anchor="w")
        editor = ttk.Frame(left)
        editor.pack(fill="x", pady=(2, 4))
        self.labels = tk.Text(editor, width=24, height=9, undo=True, wrap="none")
        self.labels.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(editor, command=self.labels.yview)
        scrollbar.pack(side="right", fill="y")
        self.labels.configure(yscrollcommand=scrollbar.set)
        self.labels.insert("1.0", "\n".join(f"{label}, 3" for label in DEFAULT_LABELS))
        self.labels.edit_modified(False)
        self.labels.bind("<<Modified>>", self.labels_changed)
        ttk.Label(left, text="Example: Sample A, 3\n1–8 replicates; one per available row.").pack(anchor="w", pady=(0, 10))
        ttk.Label(left, text="Click wells to mark as:").pack(anchor="w")
        for text, value in [("Water", "water"), ("Do not randomize (blank)", "excluded"), ("Available", "available"), ("Custom mark", "custom")]:
            ttk.Radiobutton(left, text=text, variable=self.mode, value=value).pack(anchor="w")
        ttk.Entry(left, textvariable=self.custom_text, width=24).pack(fill="x", pady=(2, 4))
        ttk.Label(left, text="Custom marks reserve wells from sampling.").pack(anchor="w")
        ttk.Checkbutton(left, text="Fill unused wells with water", variable=self.fill_unused).pack(anchor="w", pady=(10, 4))
        ttk.Button(left, text="Add water perimeter", command=self.add_water_perimeter).pack(fill="x", pady=(4, 0))
        ttk.Button(left, text="Reset all wells to available", command=self.reset).pack(fill="x", pady=(4, 0))
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
        ttk.Label(plate, text="Mark empty wells after randomization without moving samples.\nAssigned sample wells are protected; use Clear layout to edit them.\nBlue = water · Gray = excluded · Green = sample · Yellow = custom mark", wraplength=780).grid(row=10, column=0, columnspan=13, sticky="w")
        actions = ttk.Frame(body)
        actions.grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 8))
        self.generate_button = ttk.Button(actions, text="Randomize plate", command=self.generate)
        self.generate_button.pack(side="left", padx=(0, 8))
        self.export_button = ttk.Button(actions, text="Export CSV", command=self.export, state="disabled")
        self.export_button.pack(side="left")
        ttk.Button(actions, text="Clear layout", command=self.clear_layout).pack(side="left", padx=(8, 0))
        ttk.Label(body, textvariable=self.status, wraplength=1000).grid(row=4, column=0, columnspan=2, sticky="w")
        self.seed.trace_add("write", lambda *_: self.invalidate())
        self.fill_unused.trace_add("write", lambda *_: self.marks_changed())
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
        self.sample_wells.clear()
        self.export_button.configure(state="disabled")
        if had_result or self.busy:
            self.status.set("Settings changed. Randomize again before exporting.")
        self.refresh()

    def set_well(self, well):
        if self.labels.edit_modified():
            self.labels_changed(None)
        if well in self.sample_wells:
            self.status.set("This well contains an assigned sample. Use Clear layout before changing it.")
            return
        label = self.custom_text.get().strip()
        if self.mode.get() == "custom":
            try:
                samples = parse_samples(self.labels.get("1.0", "end"))
                validate_custom_marks({well: label}, samples)
            except ValueError as exc:
                messagebox.showerror("Cannot mark well", str(exc), parent=self)
                return
        self.water.discard(well)
        self.excluded.discard(well)
        self.custom_marks.pop(well, None)
        if self.mode.get() == "water":
            self.water.add(well)
        elif self.mode.get() == "excluded":
            self.excluded.add(well)
        elif self.mode.get() == "custom":
            self.custom_marks[well] = label
        self.marks_changed()
        self.describe_well(well)

    def marks_changed(self):
        """Update non-sample wells without discarding a completed layout."""
        self.revision += 1
        if self.result is not None:
            for well in WELLS:
                if well not in self.sample_wells:
                    self.result[well] = (
                        "Water" if well in self.water else self.custom_marks[well] if well in self.custom_marks
                        else "Unused" if well in self.excluded else "Water" if self.fill_unused.get() else "Unused"
                    )
            self.status.set("Well marks updated; sample positions are unchanged. Export to save the plate.")
        elif self.busy:
            self.status.set("Settings changed. Randomize again when the current search finishes.")
        else:
            self.status.set("Well selections updated. Randomize to place samples.")
        self.refresh()

    def add_water_perimeter(self):
        for well in default_water():
            if well not in self.sample_wells and well not in self.custom_marks and well not in self.excluded:
                self.water.add(well)
        self.marks_changed()
        self.status.set("Added perimeter water. Assigned samples, excluded wells and custom marks were kept.")

    def clear_layout(self):
        self.invalidate()
        self.status.set("Layout cleared. Edit any well, then randomize again.")

    def reset(self):
        self.water.clear()
        self.excluded.clear()
        self.custom_marks.clear()
        self.invalidate()
        self.fill_unused.set(False)
        self.status.set("All wells are available. Seed and sample labels were kept.")

    def well_display(self, well):
        if well in self.water:
            return "Water", "#cce8f6"
        if well in self.excluded:
            return "Excluded", "#e1e3e5"
        if well in self.custom_marks:
            return self.custom_marks[well], "#fff0b8"
        if self.result is not None:
            value = self.result[well]
            return value, "#ffffff" if value == "Unused" else "#cce8f6" if value == "Water" else "#d8eedb"
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
        custom_marks, fill_unused = self.custom_marks.copy(), self.fill_unused.get()
        self.busy = True
        self.generate_button.configure(state="disabled")
        self.status.set("Finding a plate layout…")

        def work():
            try:
                result = randomize_plate(seed, samples, water, excluded,
                                         custom_marks=custom_marks, fill_unused=fill_unused)
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
        self.sample_wells = {well for well, value in result.items() if value in samples}
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
