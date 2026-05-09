from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional


@dataclass
class Process:
    pid: str
    arrival_time: int
    cpu_bursts: List[int]
    io_bursts: List[int]
    current_cpu_index: int = 0
    current_cpu_remaining: int = 0
    completion_time: Optional[int] = None
    first_start_time: Optional[int] = None

    def __post_init__(self) -> None:
        self.current_cpu_remaining = self.cpu_bursts[0]

    @property
    def total_cpu_time(self) -> int:
        return sum(self.cpu_bursts)

    @property
    def total_io_time(self) -> int:
        return sum(self.io_bursts)

    @property
    def finished(self) -> bool:
        return self.current_cpu_index >= len(self.cpu_bursts)


@dataclass
class GanttEntry:
    label: str
    start: int
    end: int


@dataclass
class QueueSnapshot:
    time: int
    reason: str
    queue: List[str] = field(default_factory=list)


def add_gantt_entry(gantt: List[GanttEntry], label: str, start: int, end: int) -> None:
    if start == end:
        return

    if gantt and gantt[-1].label == label and gantt[-1].end == start:
        gantt[-1].end = end
        return

    gantt.append(GanttEntry(label=label, start=start, end=end))


def queue_labels(queue: Deque[Process]) -> List[str]:
    return [process.pid for process in queue]


def enqueue_new_arrivals(
    processes: List[Process],
    next_arrival_index: int,
    current_time: int,
    ready_queue: Deque[Process],
) -> int:
    while next_arrival_index < len(processes) and processes[next_arrival_index].arrival_time <= current_time:
        ready_queue.append(processes[next_arrival_index])
        next_arrival_index += 1
    return next_arrival_index


def move_unblocked_processes(
    blocked: List[tuple[int, int, Process]],
    current_time: int,
    ready_queue: Deque[Process],
) -> None:
    unblocked = [item for item in blocked if item[0] <= current_time]
    blocked[:] = [item for item in blocked if item[0] > current_time]

    for _, _, process in sorted(unblocked, key=lambda item: (item[0], item[1])):
        ready_queue.append(process)


def next_event_time(
    processes: List[Process],
    next_arrival_index: int,
    blocked: List[tuple[int, int, Process]],
) -> Optional[int]:
    candidates: List[int] = []
    if next_arrival_index < len(processes):
        candidates.append(processes[next_arrival_index].arrival_time)
    if blocked:
        candidates.append(min(item[0] for item in blocked))
    return min(candidates) if candidates else None


def simulate_round_robin(
    processes: List[Process],
    quantum_size: int,
    context_switch_size: int,
) -> tuple[List[GanttEntry], List[QueueSnapshot]]:
    processes = sorted(processes, key=lambda item: (item.arrival_time, item.pid))
    ready_queue: Deque[Process] = deque()
    blocked: List[tuple[int, int, Process]] = []
    gantt: List[GanttEntry] = []
    snapshots: List[QueueSnapshot] = []

    time = 0
    next_arrival_index = 0
    completed_processes = 0
    block_sequence = 0

    next_arrival_index = enqueue_new_arrivals(processes, next_arrival_index, time, ready_queue)
    snapshots.append(QueueSnapshot(time=time, reason="Estado inicial", queue=queue_labels(ready_queue)))

    while completed_processes < len(processes):
        move_unblocked_processes(blocked, time, ready_queue)
        next_arrival_index = enqueue_new_arrivals(processes, next_arrival_index, time, ready_queue)

        if not ready_queue:
            event_time = next_event_time(processes, next_arrival_index, blocked)
            if event_time is None:
                break
            add_gantt_entry(gantt, "IDLE", time, event_time)
            time = event_time
            snapshots.append(QueueSnapshot(time=time, reason="CPU inactiva", queue=queue_labels(ready_queue)))
            continue

        current = ready_queue.popleft()
        if current.first_start_time is None:
            current.first_start_time = time
        snapshots.append(QueueSnapshot(time=time, reason=f"Se ejecuta {current.pid}", queue=queue_labels(ready_queue)))

        run_time = min(quantum_size, current.current_cpu_remaining)
        add_gantt_entry(gantt, current.pid, time, time + run_time)
        time += run_time
        current.current_cpu_remaining -= run_time
        should_requeue = False

        if current.current_cpu_remaining == 0:
            io_index = current.current_cpu_index
            current.current_cpu_index += 1

            if current.current_cpu_index >= len(current.cpu_bursts):
                current.completion_time = time
                completed_processes += 1
                reason = f"{current.pid} finaliza"
            else:
                io_duration = current.io_bursts[io_index]
                current.current_cpu_remaining = current.cpu_bursts[current.current_cpu_index]
                blocked.append((time + io_duration, block_sequence, current))
                block_sequence += 1
                reason = f"{current.pid} realiza E/S"
        else:
            reason = f"{current.pid} vuelve a listos"
            should_requeue = True

        move_unblocked_processes(blocked, time, ready_queue)
        next_arrival_index = enqueue_new_arrivals(processes, next_arrival_index, time, ready_queue)
        if should_requeue:
            ready_queue.append(current)
        snapshots.append(QueueSnapshot(time=time, reason=reason, queue=queue_labels(ready_queue)))

        if completed_processes < len(processes):
            pending_work = bool(ready_queue or blocked or next_arrival_index < len(processes))
            if context_switch_size > 0 and pending_work:
                add_gantt_entry(gantt, "CS", time, time + context_switch_size)
                time += context_switch_size
                move_unblocked_processes(blocked, time, ready_queue)
                next_arrival_index = enqueue_new_arrivals(processes, next_arrival_index, time, ready_queue)
                snapshots.append(
                    QueueSnapshot(time=time, reason="Fin de intercambio", queue=queue_labels(ready_queue))
                )

    return gantt, snapshots


def calculate_metrics(processes: List[Process]) -> List[dict[str, int | str]]:
    metrics: List[dict[str, int | str]] = []
    for process in processes:
        if process.completion_time is None:
            continue

        standard_turnaround = process.completion_time - process.arrival_time
        total_waiting = standard_turnaround - process.total_cpu_time - process.total_io_time
        response = 0 if process.first_start_time is None else process.first_start_time - process.arrival_time
        turnaround = standard_turnaround - process.total_io_time
        waiting = response
        metrics.append(
            {
                "pid": process.pid,
                "arrival": process.arrival_time,
                "cpu": process.total_cpu_time,
                "io": process.total_io_time,
                "completion": process.completion_time,
                "turnaround": turnaround,
                "waiting": waiting,
                "response": response,
                "standard_turnaround": standard_turnaround,
                "total_waiting": total_waiting,
            }
        )
    return metrics
