"""Desktop graphical interface for PPC Optimizer.

A thin tkinter layer over the command-line entry point: the analysis runs
through main.run() in a background thread, so the window stays responsive
and every feature (configuration, logging, friendly errors) behaves
exactly as in the console.
"""

import io
import os
import queue
import subprocess
import sys
import threading
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from app.version import APP_NAME, __version__

_WINDOW_TITLE = f"{APP_NAME} v{__version__}"
_REPORT_FILE_TYPES = (
    ("Google Ads reports", "*.csv *.xlsx"),
    ("CSV files", "*.csv"),
    ("Excel files", "*.xlsx"),
)
_POLL_INTERVAL_MS = 100


def execute_analysis(source_paths: list[Path], output_path: Path) -> tuple[int, str]:
    """Run the full analysis and return the exit code and combined output.

    This is the only bridge between the interface and the application; it
    reuses main.run() unchanged, capturing everything it prints.
    """
    from main import run

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
        exit_code = run(source_paths, output_path=output_path)

    combined_output = (stdout_buffer.getvalue() + stderr_buffer.getvalue()).strip()
    return exit_code, combined_output


def open_in_system(path: Path) -> None:
    """Open a file or folder with the operating system's default handler."""
    if os.name == "nt":
        os.startfile(path)  # noqa: S606 — intentional, opens the user's report
        return

    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.run([opener, str(path)], check=False)


class PpcOptimizerGui:
    """Main application window."""

    def __init__(self, root) -> None:
        """Build the window layout."""
        import tkinter as tk
        from tkinter import ttk

        self._tk = tk
        self._root = root
        self._result_queue: queue.Queue[tuple[int, str]] = queue.Queue()
        self._source_paths: list[Path] = []
        self._output_path = Path("report.xlsx")

        root.title(_WINDOW_TITLE)
        root.minsize(640, 480)
        frame = ttk.Frame(root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)

        header = ttk.Label(frame, text="1. Choose Google Ads report files (one per campaign)")
        header.grid(row=0, column=0, columnspan=2, sticky="w")

        self._files_list = tk.Listbox(frame, height=6)
        self._files_list.grid(row=1, column=0, sticky="nsew", pady=(4, 8))
        buttons = ttk.Frame(frame)
        buttons.grid(row=1, column=1, sticky="ns", padx=(8, 0), pady=(4, 8))
        ttk.Button(buttons, text="Add files…", command=self._add_files).pack(fill=tk.X)
        ttk.Button(buttons, text="Clear", command=self._clear_files).pack(fill=tk.X, pady=(6, 0))

        output_row = ttk.Frame(frame)
        output_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        output_row.columnconfigure(1, weight=1)
        ttk.Label(output_row, text="2. Report file:").grid(row=0, column=0, padx=(0, 6))
        self._output_label = ttk.Label(output_row, text=str(self._output_path), relief="sunken")
        self._output_label.grid(row=0, column=1, sticky="ew")
        ttk.Button(output_row, text="Change…", command=self._choose_output).grid(
            row=0, column=2, padx=(6, 0)
        )

        self._generate_button = ttk.Button(
            frame,
            text="3. Generate report",
            command=self._start_analysis,
        )
        self._generate_button.grid(row=3, column=0, columnspan=2, sticky="ew", ipady=8)

        self._status_text = tk.Text(frame, height=8, state=tk.DISABLED, wrap="word")
        self._status_text.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(8, 8))

        actions = ttk.Frame(frame)
        actions.grid(row=6, column=0, columnspan=2, sticky="ew")
        self._open_report_button = ttk.Button(
            actions,
            text="Open report",
            command=self._open_report,
            state=tk.DISABLED,
        )
        self._open_report_button.pack(side=tk.LEFT)
        self._open_folder_button = ttk.Button(
            actions,
            text="Open folder",
            command=self._open_folder,
            state=tk.DISABLED,
        )
        self._open_folder_button.pack(side=tk.LEFT, padx=(6, 0))

        self._set_status("Add one or more report files and press Generate report.")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _add_files(self) -> None:
        """Ask for report files and add them to the list."""
        from tkinter import filedialog

        selected = filedialog.askopenfilenames(
            title="Choose Google Ads report files",
            filetypes=_REPORT_FILE_TYPES,
        )
        for raw_path in selected:
            path = Path(raw_path)
            if path not in self._source_paths:
                self._source_paths.append(path)
                self._files_list.insert(self._tk.END, path.name)

    def _clear_files(self) -> None:
        """Remove every chosen file."""
        self._source_paths.clear()
        self._files_list.delete(0, self._tk.END)

    def _choose_output(self) -> None:
        """Ask where to save the workbook."""
        from tkinter import filedialog

        selected = filedialog.asksaveasfilename(
            title="Save the report as",
            defaultextension=".xlsx",
            initialfile=self._output_path.name,
            filetypes=(("Excel workbook", "*.xlsx"),),
        )
        if selected:
            self._output_path = Path(selected)
            self._output_label.configure(text=str(self._output_path))

    def _start_analysis(self) -> None:
        """Run the analysis in a background thread."""
        from tkinter import messagebox

        if not self._source_paths:
            messagebox.showwarning(_WINDOW_TITLE, "Add at least one report file first.")
            return

        self._generate_button.configure(state=self._tk.DISABLED)
        self._open_report_button.configure(state=self._tk.DISABLED)
        self._open_folder_button.configure(state=self._tk.DISABLED)
        self._set_status("Analyzing… this may take a few seconds.")

        worker = threading.Thread(
            target=self._analysis_worker,
            args=(list(self._source_paths), self._output_path),
            daemon=True,
        )
        worker.start()
        self._root.after(_POLL_INTERVAL_MS, self._poll_result)

    def _analysis_worker(self, source_paths: list[Path], output_path: Path) -> None:
        """Background thread body: run the analysis, queue the result."""
        try:
            result = execute_analysis(source_paths, output_path)
        except Exception as error:  # noqa: BLE001 — surfaced to the user
            result = (3, f"Internal error: {type(error).__name__}: {error}")
        self._result_queue.put(result)

    def _poll_result(self) -> None:
        """Check whether the background analysis has finished."""
        try:
            exit_code, output = self._result_queue.get_nowait()
        except queue.Empty:
            self._root.after(_POLL_INTERVAL_MS, self._poll_result)
            return

        self._generate_button.configure(state=self._tk.NORMAL)
        if exit_code == 0:
            self._set_status(f"Done!\n\n{output}")
            self._open_report_button.configure(state=self._tk.NORMAL)
            self._open_folder_button.configure(state=self._tk.NORMAL)
        else:
            self._set_status(f"The analysis failed (exit code {exit_code}).\n\n{output}")

    def _open_report(self) -> None:
        """Open the generated workbook."""
        open_in_system(self._output_path)

    def _open_folder(self) -> None:
        """Open the folder containing the workbook."""
        open_in_system(self._output_path.resolve().parent)

    def _set_status(self, message: str) -> None:
        """Replace the status area content."""
        self._status_text.configure(state=self._tk.NORMAL)
        self._status_text.delete("1.0", self._tk.END)
        self._status_text.insert(self._tk.END, message)
        self._status_text.configure(state=self._tk.DISABLED)


def main() -> None:
    """Launch the graphical interface."""
    import tkinter as tk

    project_root = Path(__file__).resolve().parent.parent
    if (project_root / "config.yaml").is_file():
        os.chdir(project_root)

    root = tk.Tk()
    PpcOptimizerGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
