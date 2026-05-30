from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

from .config import load_config_file, load_default_config
from .exporter import export_all, export_segments, export_volume, output_filenames
from .llm import auto_segment_chapter
from .models import Chapter, LLMConfig, SEGMENT_WARNING, Segment
from .parser import chapter_from_paste, parse_txt_file
from .segmentation import make_single_segments, merge_segments, renumber_segments, split_segment_at
from .validation import validate_segments


class SourcePreparerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Novel Studio - Source Preparer")
        self.geometry("1280x760")
        self.minsize(980, 620)

        self.chapters: list[Chapter] = []
        self.segments: list[Segment] = []
        self.config: LLMConfig = load_default_config()
        self.selected_chapter_index: int | None = None
        self.selected_segment_index: int | None = None
        self.volume_var = tk.StringVar(value="1")
        self.status_var = tk.StringVar(value=SEGMENT_WARNING)

        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self, padding=(10, 8))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(12, weight=1)

        ttk.Label(toolbar, text="Volume Number").grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(toolbar, textvariable=self.volume_var, width=8).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(toolbar, text="Open TXT", command=self.open_txt).grid(row=0, column=2, padx=3)
        ttk.Button(toolbar, text="Paste Mode", command=self.add_pasted_chapter).grid(row=0, column=3, padx=3)
        ttk.Button(toolbar, text="Load Config", command=self.load_config).grid(row=0, column=4, padx=3)
        ttk.Button(toolbar, text="Save Volume", command=self.save_volume).grid(row=0, column=5, padx=3)
        ttk.Button(toolbar, text="Save Segments", command=self.save_segments).grid(row=0, column=6, padx=3)

        content = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        content.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))

        left = ttk.Frame(content, padding=8)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        ttk.Label(left, text="Chapters").grid(row=0, column=0, sticky="w")
        self.chapter_list = tk.Listbox(left, exportselection=False)
        self.chapter_list.grid(row=1, column=0, sticky="nsew")
        self.chapter_list.bind("<<ListboxSelect>>", self.on_chapter_select)
        content.add(left, weight=1)

        center = ttk.Frame(content, padding=8)
        center.columnconfigure(0, weight=1)
        center.rowconfigure(1, weight=1)
        ttk.Label(center, text="Source Chapter Text").grid(row=0, column=0, sticky="w")
        self.source_text = ScrolledText(center, wrap=tk.WORD, undo=True)
        self.source_text.grid(row=1, column=0, sticky="nsew")
        content.add(center, weight=3)

        right = ttk.Frame(content, padding=8)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(3, weight=2)
        ttk.Label(right, text="Segments").grid(row=0, column=0, sticky="w")
        self.segment_list = tk.Listbox(right, exportselection=False, selectmode=tk.EXTENDED)
        self.segment_list.grid(row=1, column=0, sticky="nsew")
        self.segment_list.bind("<<ListboxSelect>>", self.on_segment_select)
        ttk.Label(right, text="Segment Editor").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.segment_text = ScrolledText(right, wrap=tk.WORD, undo=True, height=12)
        self.segment_text.grid(row=3, column=0, sticky="nsew")
        content.add(right, weight=2)

        bottom = ttk.Frame(self, padding=(10, 0, 10, 8))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(8, weight=1)
        ttk.Button(bottom, text="Auto Segment with Big LLM", command=self.auto_segment).grid(row=0, column=0, padx=3)
        ttk.Button(bottom, text="Split Here", command=self.split_here).grid(row=0, column=1, padx=3)
        ttk.Button(bottom, text="Merge Selected", command=self.merge_selected).grid(row=0, column=2, padx=3)
        ttk.Button(bottom, text="Validate", command=self.validate_current).grid(row=0, column=3, padx=3)
        ttk.Button(bottom, text="Export", command=self.export_all).grid(row=0, column=4, padx=3)
        ttk.Label(bottom, textvariable=self.status_var, wraplength=620).grid(row=0, column=8, sticky="e")

    def volume_number(self) -> int:
        return int(self.volume_var.get().strip())

    def selected_chapter(self) -> Chapter | None:
        if self.selected_chapter_index is None:
            return None
        if self.selected_chapter_index >= len(self.chapters):
            return None
        return self.chapters[self.selected_chapter_index]

    def save_current_source_editor(self) -> None:
        chapter = self.selected_chapter()
        if chapter is None:
            return
        self.chapters[self.selected_chapter_index] = Chapter(
            chapter=chapter.chapter,
            name=chapter.name,
            content=self.source_text.get("1.0", tk.END).strip(),
        )

    def save_current_segment_editor(self) -> None:
        if self.selected_segment_index is None or self.selected_segment_index >= len(self.segments):
            return
        segment = self.segments[self.selected_segment_index]
        self.segments[self.selected_segment_index] = Segment(
            chapter=segment.chapter,
            name=segment.name,
            segment=segment.segment,
            segment_ID=segment.segment_ID,
            content=self.segment_text.get("1.0", tk.END).strip(),
        )

    def refresh_chapters(self) -> None:
        self.chapter_list.delete(0, tk.END)
        for chapter in self.chapters:
            label = f"{chapter.chapter} - {chapter.name or 'Untitled'}"
            self.chapter_list.insert(tk.END, label)

    def refresh_segments(self) -> None:
        self.segment_list.delete(0, tk.END)
        for segment in self.segments:
            first_line = segment.content.strip().splitlines()[0] if segment.content.strip() else "Empty"
            self.segment_list.insert(tk.END, f"{segment.segment_ID} - {first_line[:64]}")

    def open_txt(self) -> None:
        path = filedialog.askopenfilename(
            title="Open source TXT",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.chapters = parse_txt_file(path)
            self.segments = make_single_segments(self.chapters, self.volume_number())
            self.selected_chapter_index = None
            self.selected_segment_index = None
            self.refresh_chapters()
            self.refresh_segments()
            self.status_var.set(f"Loaded {len(self.chapters)} chapters from {Path(path).name}.")
        except Exception as exc:
            messagebox.showerror("Open TXT failed", str(exc))

    def add_pasted_chapter(self) -> None:
        content = self.source_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Paste Mode", "Paste chapter content into the source text panel first.")
            return
        chapter_number = simpledialog.askstring("Paste Mode", "Chapter number", initialvalue=str(len(self.chapters) + 1))
        if not chapter_number:
            return
        name = simpledialog.askstring("Paste Mode", "Chapter name", initialvalue="")
        try:
            chapter = chapter_from_paste(chapter_number, name or "", content)
            self.chapters.append(chapter)
            self.segments = renumber_segments(self.segments + make_single_segments([chapter], self.volume_number()), self.volume_number())
            self.refresh_chapters()
            self.refresh_segments()
            self.status_var.set(f"Added pasted chapter {chapter.chapter}.")
        except Exception as exc:
            messagebox.showerror("Paste Mode failed", str(exc))

    def load_config(self) -> None:
        path = filedialog.askopenfilename(
            title="Load LLM config JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.config = load_config_file(path)
            self.status_var.set(f"Loaded config for model: {self.config.model or 'not set'}.")
        except Exception as exc:
            messagebox.showerror("Load Config failed", str(exc))

    def save_volume(self) -> None:
        self.save_current_source_editor()
        volume_name, _ = output_filenames(self.volume_number())
        path = filedialog.asksaveasfilename(
            title="Save volume JSON",
            initialfile=volume_name,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if path:
            try:
                export_volume(path, self.chapters)
                self.status_var.set(f"Saved {Path(path).name}.")
            except Exception as exc:
                messagebox.showerror("Save Volume failed", str(exc))

    def save_segments(self) -> None:
        self.save_current_source_editor()
        self.save_current_segment_editor()
        _, segment_name = output_filenames(self.volume_number())
        path = filedialog.asksaveasfilename(
            title="Save segment JSON",
            initialfile=segment_name,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if path:
            try:
                self.segments = renumber_segments(self.segments, self.volume_number())
                export_segments(path, self.chapters, self.segments, self.volume_number())
                self.refresh_segments()
                self.status_var.set(f"Saved {Path(path).name}.")
            except Exception as exc:
                messagebox.showerror("Save Segments failed", str(exc))

    def auto_segment(self) -> None:
        chapter = self.selected_chapter()
        if chapter is None:
            messagebox.showinfo("Auto Segment", "Select a chapter first.")
            return
        if not self.config.model:
            messagebox.showwarning("Auto Segment", "Load or enter a Big LLM config with a model first.")
            return
        self.save_current_source_editor()
        self.status_var.set("Auto segmenting with Big LLM...")

        def worker() -> None:
            try:
                new_segments = auto_segment_chapter(self.chapters[self.selected_chapter_index], self.volume_number(), self.config)
                self.after(0, lambda: self.replace_chapter_segments(chapter.chapter, new_segments))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Auto Segment failed", str(exc)))
                self.after(0, lambda: self.status_var.set("Auto segmentation failed."))

        threading.Thread(target=worker, daemon=True).start()

    def replace_chapter_segments(self, chapter_number: str, new_segments: list[Segment]) -> None:
        remaining = [segment for segment in self.segments if segment.chapter != chapter_number]
        insert_at = 0
        for index, segment in enumerate(self.segments):
            if segment.chapter == chapter_number:
                insert_at = index
                break
            insert_at = index + 1
        self.segments = renumber_segments(remaining[:insert_at] + new_segments + remaining[insert_at:], self.volume_number())
        self.refresh_segments()
        self.status_var.set(f"Auto segmented chapter {chapter_number}.")

    def split_here(self) -> None:
        if self.selected_segment_index is None:
            messagebox.showinfo("Split Here", "Select a segment first.")
            return
        self.save_current_segment_editor()
        try:
            offset = int(self.segment_text.count("1.0", tk.INSERT, "chars")[0])
            self.segments = split_segment_at(self.segments, self.selected_segment_index, offset, self.volume_number())
            self.refresh_segments()
            self.status_var.set(SEGMENT_WARNING)
        except Exception as exc:
            messagebox.showerror("Split Here failed", str(exc))

    def merge_selected(self) -> None:
        selected = list(self.segment_list.curselection())
        if not selected:
            messagebox.showinfo("Merge Selected", "Select adjacent segments first.")
            return
        self.save_current_segment_editor()
        try:
            self.segments = merge_segments(self.segments, selected, self.volume_number())
            self.selected_segment_index = None
            self.segment_text.delete("1.0", tk.END)
            self.refresh_segments()
            self.status_var.set(SEGMENT_WARNING)
        except Exception as exc:
            messagebox.showerror("Merge Selected failed", str(exc))

    def validate_current(self) -> None:
        self.save_current_source_editor()
        self.save_current_segment_editor()
        try:
            self.segments = renumber_segments(self.segments, self.volume_number())
        except Exception as exc:
            messagebox.showerror("Validate failed", str(exc))
            return
        self.refresh_segments()
        result = validate_segments(self.chapters, self.segments, self.volume_number())
        if result.ok:
            details = "\n".join(result.warnings) if result.warnings else "No issues found."
            messagebox.showinfo("Validation passed", details)
            self.status_var.set("Validation passed.")
        else:
            messagebox.showerror("Validation failed", "\n".join(result.errors + result.warnings))
            self.status_var.set("Validation failed.")

    def export_all(self) -> None:
        self.save_current_source_editor()
        self.save_current_segment_editor()
        directory = filedialog.askdirectory(title="Export source and segment files")
        if not directory:
            return
        try:
            self.segments = renumber_segments(self.segments, self.volume_number())
            volume_path, segment_path = export_all(directory, self.chapters, self.segments, self.volume_number())
            self.refresh_segments()
            self.status_var.set(f"Exported {volume_path.name} and {segment_path.name}.")
            messagebox.showinfo("Export complete", f"Saved:\n{volume_path}\n{segment_path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def on_chapter_select(self, _event: tk.Event) -> None:
        selection = self.chapter_list.curselection()
        if not selection:
            return
        self.save_current_source_editor()
        self.selected_chapter_index = selection[0]
        chapter = self.chapters[self.selected_chapter_index]
        self.source_text.delete("1.0", tk.END)
        self.source_text.insert("1.0", chapter.content)

    def on_segment_select(self, _event: tk.Event) -> None:
        selection = self.segment_list.curselection()
        if not selection:
            return
        self.save_current_segment_editor()
        self.selected_segment_index = selection[0]
        segment = self.segments[self.selected_segment_index]
        self.segment_text.delete("1.0", tk.END)
        self.segment_text.insert("1.0", segment.content)


def main() -> None:
    app = SourcePreparerApp()
    app.mainloop()
