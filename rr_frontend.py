from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional

from rr_backend import GanttEntry, Process, QueueSnapshot, calculate_metrics, simulate_round_robin


class RoundRobinApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Simulador Round Robin")
        self.root.geometry("1450x860")
        self.root.configure(bg="#f2efe8")

        self.process_rows: List[dict[str, object]] = []
        self.cpu_segment_count = 3
        self.gantt_scale = 28

        self.total_processes_var = tk.StringVar(value="4")
        self.quantum_var = tk.StringVar(value="50")
        self.context_var = tk.StringVar(value="5")
        self.cpu_segments_var = tk.StringVar(value="3")
        self.average_turnaround_var = tk.StringVar(value="0.00")
        self.average_waiting_var = tk.StringVar(value="0.00")

        self._build_layout()
        self.generate_process_inputs()

    def _build_layout(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10))

        header = tk.Frame(self.root, bg="#223b53", padx=18, pady=14)
        header.pack(fill="x")
        tk.Label(
            header,
            text="Simulador Round Robin",
            font=("Segoe UI Semibold", 22),
            fg="white",
            bg="#223b53",
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Tabla de entrada tipo pizarra: llegada y rafagas alternadas CPU / E-S / CPU.",
            font=("Segoe UI", 10),
            fg="#d8e4f3",
            bg="#223b53",
        ).pack(anchor="w", pady=(4, 0))

        body_container = tk.Frame(self.root, bg="#f2efe8")
        body_container.pack(fill="both", expand=True)
        body_container.grid_columnconfigure(0, weight=1)
        body_container.grid_rowconfigure(0, weight=1)

        self.body_canvas = tk.Canvas(body_container, bg="#f2efe8", highlightthickness=0)
        body_scrollbar = ttk.Scrollbar(body_container, orient="vertical", command=self.body_canvas.yview)
        self.body_canvas.configure(yscrollcommand=body_scrollbar.set)

        self.body_canvas.grid(row=0, column=0, sticky="nsew")
        body_scrollbar.grid(row=0, column=1, sticky="ns")

        body = tk.Frame(self.body_canvas, bg="#f2efe8", padx=16, pady=16)
        self.body_window = self.body_canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda _event: self.body_canvas.configure(scrollregion=self.body_canvas.bbox("all")))
        self.body_canvas.bind("<Configure>", lambda event: self.body_canvas.itemconfigure(self.body_window, width=event.width))
        self.body_canvas.bind_all("<MouseWheel>", self._on_body_mousewheel)

        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        self._build_input_panel(body)
        self._build_result_panel(body)

    def _build_input_panel(self, parent: tk.Frame) -> None:
        input_panel = tk.Frame(parent, bg="#fffaf3", bd=1, relief="solid", padx=14, pady=14)
        input_panel.grid(row=0, column=0, sticky="ew")
        input_panel.grid_columnconfigure(0, weight=1)

        config = tk.Frame(input_panel, bg="#fffaf3")
        config.grid(row=0, column=0, sticky="ew")

        self._labeled_entry(config, "Procesos", self.total_processes_var, 0, 0)
        self._labeled_entry(config, "Quantum (ms)", self.quantum_var, 0, 1)
        self._labeled_entry(config, "Intercambio (ms)", self.context_var, 0, 2)
        self._labeled_entry(config, "Columnas CPU", self.cpu_segments_var, 0, 3)

        actions = tk.Frame(input_panel, bg="#fffaf3")
        actions.grid(row=1, column=0, sticky="ew", pady=(12, 10))

        tk.Button(
            actions,
            text="Generar tabla",
            command=self.generate_process_inputs,
            bg="#ce6a2e",
            fg="white",
            font=("Segoe UI Semibold", 10),
            relief="flat",
            padx=12,
            pady=9,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            actions,
            text="Cargar ejemplo",
            command=self.load_example_table,
            bg="#9a7b4f",
            fg="white",
            font=("Segoe UI Semibold", 10),
            relief="flat",
            padx=12,
            pady=9,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            actions,
            text="Simular",
            command=self.run_simulation,
            bg="#2c7b49",
            fg="white",
            font=("Segoe UI Semibold", 10),
            relief="flat",
            padx=14,
            pady=9,
        ).pack(side="left")

        notes = tk.Label(
            input_panel,
            text="Usa 0 o deja vacio cuando no exista una rafaga. Las columnas CPU y E/S se interpretan en quantums (Q).",
            bg="#fffaf3",
            fg="#6e604f",
            font=("Segoe UI", 9),
        )
        notes.grid(row=2, column=0, sticky="w", pady=(0, 10))

        table_frame = tk.Frame(input_panel, bg="#fffaf3")
        table_frame.grid(row=3, column=0, sticky="ew")

        self.process_canvas = tk.Canvas(table_frame, bg="#fffaf3", highlightthickness=0, height=190)
        table_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.process_canvas.xview)
        table_scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.process_canvas.yview)
        self.process_canvas.configure(xscrollcommand=table_scroll_x.set, yscrollcommand=table_scroll_y.set)

        self.process_canvas.grid(row=0, column=0, sticky="nsew")
        table_scroll_y.grid(row=0, column=1, sticky="ns")
        table_scroll_x.grid(row=1, column=0, sticky="ew")
        table_frame.grid_columnconfigure(0, weight=1)

        self.process_table_frame = tk.Frame(self.process_canvas, bg="#fffaf3")
        self.process_canvas.create_window((0, 0), window=self.process_table_frame, anchor="nw")
        self.process_table_frame.bind(
            "<Configure>",
            lambda _event: self.process_canvas.configure(scrollregion=self.process_canvas.bbox("all")),
        )

    def _build_result_panel(self, parent: tk.Frame) -> None:
        result_panel = tk.Frame(parent, bg="#f2efe8")
        result_panel.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        result_panel.grid_columnconfigure(0, weight=1)
        result_panel.grid_rowconfigure(3, weight=1)

        gantt_frame = tk.Frame(result_panel, bg="#fffaf3", bd=1, relief="solid", padx=12, pady=12)
        gantt_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        tk.Label(gantt_frame, text="Diagrama de Gantt", font=("Segoe UI Semibold", 13), bg="#fffaf3").pack(anchor="w")

        gantt_area = tk.Frame(gantt_frame, bg="#fffaf3")
        gantt_area.pack(fill="both", expand=True, pady=(8, 0))
        self.gantt_canvas = tk.Canvas(
            gantt_area,
            bg="#fffdf8",
            highlightthickness=1,
            highlightbackground="#d6c8b4",
            height=150,
        )
        gantt_scroll_x = ttk.Scrollbar(gantt_area, orient="horizontal", command=self.gantt_canvas.xview)
        self.gantt_canvas.configure(xscrollcommand=gantt_scroll_x.set)
        self.gantt_canvas.grid(row=0, column=0, sticky="ew")
        gantt_scroll_x.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        gantt_area.grid_columnconfigure(0, weight=1)
        self._bind_gantt_scroll()

        stats = tk.Frame(result_panel, bg="#f2efe8")
        stats.grid(row=1, column=0, sticky="ew")
        stats.grid_columnconfigure(0, weight=1)
        stats.grid_columnconfigure(1, weight=1)

        self._summary_card(stats, "Promedio de retorno", self.average_turnaround_var, 0, "#274d7d")
        self._summary_card(stats, "Promedio de espera", self.average_waiting_var, 1, "#657421")

        process_results_frame = tk.Frame(result_panel, bg="#fffaf3", bd=1, relief="solid", padx=12, pady=12)
        process_results_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        tk.Label(
            process_results_frame,
            text="Resultados por proceso",
            font=("Segoe UI Semibold", 13),
            bg="#fffaf3",
        ).pack(anchor="w")

        self.process_result_text = tk.Text(
            process_results_frame,
            height=5,
            font=("Consolas", 10),
            bg="#fffdf8",
            relief="solid",
            bd=1,
            wrap="word",
        )
        self.process_result_text.pack(fill="x", pady=(8, 0))
        self.process_result_text.configure(state="disabled")

        bottom = tk.Frame(result_panel, bg="#f2efe8")
        bottom.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_rowconfigure(0, weight=1)

        ready_frame = tk.Frame(bottom, bg="#fffaf3", bd=1, relief="solid", padx=12, pady=12)
        ready_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(ready_frame, text="Cola de listos", font=("Segoe UI Semibold", 13), bg="#fffaf3").pack(anchor="w")
        ready_table_frame = tk.Frame(ready_frame, bg="#fffaf3")
        ready_table_frame.pack(fill="both", expand=True, pady=(8, 0))
        self.ready_tree = ttk.Treeview(ready_table_frame, columns=("time", "reason", "queue"), show="headings", height=14)
        for column, title, width in (
            ("time", "Tiempo", 80),
            ("reason", "Evento", 220),
            ("queue", "Cola", 280),
        ):
            self.ready_tree.heading(column, text=title)
            self.ready_tree.column(column, width=width, anchor="center")
        ready_scroll_y = ttk.Scrollbar(ready_table_frame, orient="vertical", command=self.ready_tree.yview)
        self.ready_tree.configure(yscrollcommand=ready_scroll_y.set)
        self.ready_tree.grid(row=0, column=0, sticky="nsew")
        ready_scroll_y.grid(row=0, column=1, sticky="ns")
        ready_table_frame.grid_columnconfigure(0, weight=1)
        ready_table_frame.grid_rowconfigure(0, weight=1)

        metrics_frame = tk.Frame(bottom, bg="#fffaf3", bd=1, relief="solid", padx=12, pady=12)
        metrics_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(metrics_frame, text="Metricas por proceso", font=("Segoe UI Semibold", 13), bg="#fffaf3").pack(
            anchor="w"
        )
        metrics_table_frame = tk.Frame(metrics_frame, bg="#fffaf3")
        metrics_table_frame.pack(fill="both", expand=True, pady=(8, 0))
        columns = ("pid", "arrival", "cpu", "io", "completion", "turnaround", "waiting")
        self.metrics_tree = ttk.Treeview(metrics_table_frame, columns=columns, show="headings", height=14)
        headings = {
            "pid": "Proceso",
            "arrival": "Llegada",
            "cpu": "CPU",
            "io": "E/S",
            "completion": "Finaliza",
            "turnaround": "T. vuelta",
            "waiting": "T. espera",
        }
        for column in columns:
            self.metrics_tree.heading(column, text=headings[column])
            self.metrics_tree.column(column, width=95, anchor="center")
        metrics_scroll_y = ttk.Scrollbar(metrics_table_frame, orient="vertical", command=self.metrics_tree.yview)
        self.metrics_tree.configure(yscrollcommand=metrics_scroll_y.set)
        self.metrics_tree.grid(row=0, column=0, sticky="nsew")
        metrics_scroll_y.grid(row=0, column=1, sticky="ns")
        metrics_table_frame.grid_columnconfigure(0, weight=1)
        metrics_table_frame.grid_rowconfigure(0, weight=1)

        self._bind_tree_scroll(self.ready_tree)
        self._bind_tree_scroll(self.metrics_tree)

    def _labeled_entry(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
        column: int,
    ) -> None:
        block = tk.Frame(parent, bg="#fffaf3")
        block.grid(row=row, column=column, sticky="ew", padx=(0, 12))
        tk.Label(block, text=label, bg="#fffaf3", font=("Segoe UI", 10)).pack(anchor="w")
        tk.Entry(block, textvariable=variable, width=12, font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))

    def _summary_card(
        self,
        parent: tk.Frame,
        title: str,
        variable: tk.StringVar,
        column: int,
        color: str,
    ) -> None:
        card = tk.Frame(parent, bg=color, padx=16, pady=14)
        card.grid(row=0, column=column, sticky="ew", padx=(0, 8) if column == 0 else (8, 0))
        tk.Label(card, text=title, font=("Segoe UI", 10), fg="#d7e6ff", bg=color).pack(anchor="w")
        tk.Label(card, textvariable=variable, font=("Segoe UI Semibold", 20), fg="white", bg=color).pack(anchor="w")

    def generate_process_inputs(self) -> None:
        total_processes = self._parse_int(self.total_processes_var.get(), "Procesos", minimum=1)
        cpu_segments = self._parse_int(self.cpu_segments_var.get(), "Columnas CPU", minimum=1)
        if total_processes is None or cpu_segments is None:
            return

        self.cpu_segment_count = cpu_segments

        for widget in self.process_table_frame.winfo_children():
            widget.destroy()
        self.process_rows.clear()

        headers = ["Proceso", "T. llegada"]
        for index in range(cpu_segments):
            headers.append(f"CPU {index + 1} (Q)")
            if index < cpu_segments - 1:
                headers.append(f"E/S {index + 1} (Q)")

        for column, title in enumerate(headers):
            bg = "#d9e6f2" if title.startswith(("Proceso", "T.")) else "#efe3cc"
            tk.Label(
                self.process_table_frame,
                text=title,
                bg=bg,
                fg="#20384f",
                font=("Segoe UI Semibold", 10),
                padx=10,
                pady=8,
                width=12,
            ).grid(row=0, column=column, sticky="nsew", padx=1, pady=1)

        for row_index in range(1, total_processes + 1):
            pid = f"P{row_index - 1}"
            pid_label = tk.Label(
                self.process_table_frame,
                text=pid,
                bg="#fffdf8",
                font=("Segoe UI", 10),
                padx=8,
                pady=8,
                width=12,
            )
            pid_label.grid(row=row_index, column=0, sticky="nsew", padx=1, pady=1)

            arrival = tk.Entry(self.process_table_frame, width=12, font=("Segoe UI", 10), justify="center")
            arrival.grid(row=row_index, column=1, sticky="ew", padx=1, pady=1)
            arrival.insert(0, str((row_index - 1) * 20))

            cpu_entries: List[tk.Entry] = []
            io_entries: List[tk.Entry] = []
            current_column = 2
            for segment_index in range(cpu_segments):
                cpu_entry = tk.Entry(self.process_table_frame, width=12, font=("Segoe UI", 10), justify="center")
                cpu_entry.grid(row=row_index, column=current_column, sticky="ew", padx=1, pady=1)
                cpu_entry.insert(0, "0")
                cpu_entries.append(cpu_entry)
                current_column += 1

                if segment_index < cpu_segments - 1:
                    io_entry = tk.Entry(self.process_table_frame, width=12, font=("Segoe UI", 10), justify="center")
                    io_entry.grid(row=row_index, column=current_column, sticky="ew", padx=1, pady=1)
                    io_entry.insert(0, "0")
                    io_entries.append(io_entry)
                    current_column += 1

            self.process_rows.append(
                {
                    "pid": pid,
                    "pid_label": pid_label,
                    "arrival": arrival,
                    "cpu_entries": cpu_entries,
                    "io_entries": io_entries,
                }
            )

        self.process_canvas.update_idletasks()
        self.process_canvas.configure(scrollregion=self.process_canvas.bbox("all"))

    def load_example_table(self) -> None:
        self.total_processes_var.set("4")
        self.cpu_segments_var.set("3")
        self.quantum_var.set("50")
        self.context_var.set("5")
        self.generate_process_inputs()

        example_rows = [
            {"pid": "P0", "arrival": 0, "cpu": [200, 0, 0], "io": [0, 0]},
            {"pid": "P1", "arrival": 40, "cpu": [100, 50, 0], "io": [100, 0]},
            {"pid": "P2", "arrival": 60, "cpu": [50, 100, 100], "io": [100, 100]},
            {"pid": "P3", "arrival": 120, "cpu": [100, 50, 0], "io": [50, 0]},
        ]

        for index, data in enumerate(example_rows):
            row = self.process_rows[index]
            row["pid"] = data["pid"]
            row["pid_label"].configure(text=data["pid"])
            row["arrival"].delete(0, "end")
            row["arrival"].insert(0, str(data["arrival"]))

            for entry, value in zip(row["cpu_entries"], data["cpu"]):
                entry.delete(0, "end")
                entry.insert(0, str(value))

            for entry, value in zip(row["io_entries"], data["io"]):
                entry.delete(0, "end")
                entry.insert(0, str(value))

    def run_simulation(self) -> None:
        quantum_size = self._parse_int(self.quantum_var.get(), "Quantum", minimum=1)
        context_switch_size = self._parse_int(self.context_var.get(), "Intercambio", minimum=0)
        if quantum_size is None or context_switch_size is None:
            return

        processes: List[Process] = []
        for row in self.process_rows:
            pid = str(row["pid"])
            arrival_time = self._parse_int(row["arrival"].get(), f"Llegada de {pid}", minimum=0)
            if arrival_time is None:
                return

            cpu_bursts: List[int] = []
            io_bursts: List[int] = []

            for entry in row["cpu_entries"]:
                value = self._parse_optional_int(entry.get(), f"CPU de {pid}")
                if value is None:
                    return
                cpu_bursts.append(value)

            for entry in row["io_entries"]:
                value = self._parse_optional_int(entry.get(), f"E/S de {pid}")
                if value is None:
                    return
                io_bursts.append(value)

            cpu_bursts = [value for value in cpu_bursts if value > 0]
            while io_bursts and io_bursts[-1] == 0:
                io_bursts.pop()

            if not cpu_bursts:
                messagebox.showerror("Dato no valido", f"{pid} debe tener al menos una rafaga de CPU mayor que 0.")
                return

            if len(io_bursts) > len(cpu_bursts) - 1:
                messagebox.showerror("Dato no valido", f"{pid} tiene mas E/S que espacios entre rafagas de CPU.")
                return

            for io_index, io_value in enumerate(io_bursts):
                if io_value == 0 and io_index < len(io_bursts) - 1:
                    messagebox.showerror(
                        "Dato no valido",
                        f"{pid} tiene una E/S intermedia en 0 antes de terminar las rafagas.",
                    )
                    return

            while len(io_bursts) < len(cpu_bursts) - 1:
                io_bursts.append(0)

            cpu_bursts_ms = [value * quantum_size for value in cpu_bursts]
            io_bursts_ms = [value * quantum_size for value in io_bursts]

            processes.append(
                Process(
                    pid=pid,
                    arrival_time=arrival_time,
                    cpu_bursts=cpu_bursts_ms,
                    io_bursts=io_bursts_ms,
                )
            )

        gantt, snapshots = simulate_round_robin(processes, quantum_size, context_switch_size)
        metrics = calculate_metrics(processes)

        self._populate_ready_queue(snapshots)
        self._populate_metrics(metrics)
        self._populate_process_results(metrics)
        self._draw_gantt(gantt)

        if metrics:
            average_turnaround = sum(int(item["turnaround"]) for item in metrics) / len(metrics)
            average_waiting = sum(int(item["waiting"]) for item in metrics) / len(metrics)
        else:
            average_turnaround = 0.0
            average_waiting = 0.0

        self.average_turnaround_var.set(f"{average_turnaround:.2f}")
        self.average_waiting_var.set(f"{average_waiting:.2f}")

    def _populate_ready_queue(self, snapshots: List[QueueSnapshot]) -> None:
        for item in self.ready_tree.get_children():
            self.ready_tree.delete(item)
        for snapshot in snapshots:
            queue = ", ".join(snapshot.queue) if snapshot.queue else "vacia"
            self.ready_tree.insert("", "end", values=(snapshot.time, snapshot.reason, queue))

    def _populate_metrics(self, metrics: List[dict[str, int | str]]) -> None:
        for item in self.metrics_tree.get_children():
            self.metrics_tree.delete(item)
        for metric in metrics:
            self.metrics_tree.insert(
                "",
                "end",
                values=(
                    metric["pid"],
                    metric["arrival"],
                    metric["cpu"],
                    metric["io"],
                    metric["completion"],
                    metric["turnaround"],
                    metric["waiting"],
                ),
            )

    def _populate_process_results(self, metrics: List[dict[str, int | str]]) -> None:
        self.process_result_text.configure(state="normal")
        self.process_result_text.delete("1.0", "end")

        if not metrics:
            self.process_result_text.insert("1.0", "Aun no hay resultados para mostrar.")
            self.process_result_text.configure(state="disabled")
            return

        lines = []
        for metric in metrics:
            lines.append(
                f"{metric['pid']}: tiempo de vuelta = {metric['turnaround']} ms | "
                f"tiempo de espera = {metric['waiting']} ms"
            )

        self.process_result_text.insert("1.0", "\n".join(lines))
        self.process_result_text.configure(state="disabled")

    def _draw_gantt(self, gantt: List[GanttEntry]) -> None:
        self.gantt_canvas.delete("all")
        if not gantt:
            self.gantt_canvas.create_text(
                20,
                40,
                text="No hay informacion para representar.",
                anchor="w",
                font=("Segoe UI", 11),
                fill="#6d5f4d",
            )
            return

        colors = {"CS": "#f1c776", "IDLE": "#d8d8d8"}
        quantum_size = max(1, int(self.quantum_var.get()))
        x = 24
        y = 58
        height = 58

        self.gantt_canvas.create_text(
            24,
            18,
            text="Quantum",
            anchor="w",
            font=("Segoe UI Semibold", 10),
            fill="#29445f",
        )
        self.gantt_canvas.create_text(x, y + height + 18, text=str(gantt[0].start), anchor="center", font=("Segoe UI", 9))

        for entry in gantt:
            width = max(int((entry.end - entry.start) / max(1, self.gantt_scale / 2)), 42)
            color = colors.get(entry.label, "#7ea8d1")
            self.gantt_canvas.create_rectangle(x, y, x + width, y + height, fill=color, outline="#40505f", width=1)
            self.gantt_canvas.create_text(
                x + width / 2,
                y + height / 2,
                text=entry.label,
                font=("Segoe UI Semibold", 10),
                fill="#1f1f1f",
            )
            if entry.label != "IDLE":
                quantum_text = self._format_quantum_count(entry.end - entry.start, quantum_size)
                self.gantt_canvas.create_text(
                    x + width / 2,
                    y - 16,
                    text=quantum_text,
                    font=("Segoe UI Semibold", 9),
                    fill="#29445f",
                )
            self.gantt_canvas.create_text(
                x + width,
                y + height + 18,
                text=str(entry.end),
                anchor="center",
                font=("Segoe UI", 9),
                fill="#2f2f2f",
            )
            x += width

        content_width = x + 30
        viewport_width = max(self.gantt_canvas.winfo_width(), 1)
        self.gantt_canvas.configure(scrollregion=(0, 0, max(content_width, viewport_width + 1), 160))
        self.gantt_canvas.xview_moveto(0.0)

    def _format_quantum_count(self, duration: int, quantum_size: int) -> str:
        if duration % quantum_size == 0:
            return f"{duration // quantum_size}Q"

        quantum_count = duration / quantum_size
        return f"{quantum_count:.2f}".rstrip("0").rstrip(".") + "Q"

    def _bind_gantt_scroll(self) -> None:
        self.gantt_canvas.bind("<Shift-MouseWheel>", self._on_gantt_shift_mousewheel)
        self.gantt_canvas.bind("<MouseWheel>", self._on_gantt_mousewheel)
        self.gantt_canvas.bind("<Button-4>", self._on_gantt_linux_scroll_left)
        self.gantt_canvas.bind("<Button-5>", self._on_gantt_linux_scroll_right)

    def _bind_tree_scroll(self, tree: ttk.Treeview) -> None:
        tree.bind("<MouseWheel>", lambda event, current_tree=tree: self._on_tree_mousewheel(event, current_tree))
        tree.bind("<Button-4>", lambda event, current_tree=tree: self._on_tree_linux_up(event, current_tree))
        tree.bind("<Button-5>", lambda event, current_tree=tree: self._on_tree_linux_down(event, current_tree))

    def _on_body_mousewheel(self, event: tk.Event) -> Optional[str]:
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if widget is not None and widget == self.gantt_canvas:
            return None
        step = -1 if event.delta > 0 else 1
        self.body_canvas.yview_scroll(step, "units")
        return "break"

    def _on_gantt_shift_mousewheel(self, event: tk.Event) -> str:
        step = -1 if event.delta > 0 else 1
        self.gantt_canvas.xview_scroll(step, "units")
        return "break"

    def _on_gantt_mousewheel(self, event: tk.Event) -> Optional[str]:
        if event.state & 0x0001:
            step = -1 if event.delta > 0 else 1
            self.gantt_canvas.xview_scroll(step, "units")
            return "break"
        return None

    def _on_gantt_linux_scroll_left(self, _event: tk.Event) -> str:
        self.gantt_canvas.xview_scroll(-1, "units")
        return "break"

    def _on_gantt_linux_scroll_right(self, _event: tk.Event) -> str:
        self.gantt_canvas.xview_scroll(1, "units")
        return "break"

    def _on_tree_mousewheel(self, event: tk.Event, tree: ttk.Treeview) -> str:
        step = -1 if event.delta > 0 else 1
        tree.yview_scroll(step, "units")
        return "break"

    def _on_tree_linux_up(self, _event: tk.Event, tree: ttk.Treeview) -> str:
        tree.yview_scroll(-1, "units")
        return "break"

    def _on_tree_linux_down(self, _event: tk.Event, tree: ttk.Treeview) -> str:
        tree.yview_scroll(1, "units")
        return "break"

    def _parse_int(self, value: str, label: str, minimum: int) -> Optional[int]:
        try:
            parsed = int(value)
        except ValueError:
            messagebox.showerror("Dato no valido", f"{label} debe ser un numero entero.")
            return None

        if parsed < minimum:
            messagebox.showerror("Dato no valido", f"{label} debe ser mayor o igual a {minimum}.")
            return None

        return parsed

    def _parse_optional_int(self, value: str, label: str) -> Optional[int]:
        raw = value.strip()
        if raw == "":
            return 0
        return self._parse_int(raw, label, minimum=0)


def main() -> None:
    root = tk.Tk()
    RoundRobinApp(root)
    root.mainloop()
