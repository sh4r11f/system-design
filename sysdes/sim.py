"""A tiny deterministic discrete-event simulator with an unreliable network.

Why simulate instead of spinning up real servers? Because the interesting
distributed systems phenomena (stale reads, split brain, false failure
detection...) depend on *timing*, and a simulator gives us:

- a virtual clock, so "30 seconds of cluster time" runs in milliseconds,
- full determinism (seeded randomness), so every notebook run shows the same
  anomaly and inline assertions can check for it,
- easy fault injection: latency, message loss, and network partitions.

The model is the standard discrete-event one:

- `Sim` keeps a priority queue of (time, callback) events and a virtual clock.
  Running the sim repeatedly pops the earliest event, advances the clock to its
  timestamp, and invokes the callback (which may schedule further events).
- `Network` routes messages between named `Node`s, applying a random latency,
  optional random loss, and optional partitions to every send.
- `Node` is a base class: subclasses implement `handle(src, msg)` to define a
  protocol (e.g. a replica, a Raft peer). Messages are plain dicts by
  convention, with a "type" key.
"""

from __future__ import annotations

import heapq
import math
from typing import Any, Callable

import numpy as np


class Event:
    """Handle for a scheduled callback; lets protocols cancel timers.

    Example: a node schedules a timeout event, and cancels it when the awaited
    reply arrives first. Cancelled events stay in the queue but are skipped.
    """

    __slots__ = ("time", "seq", "fn", "args", "cancelled")

    def __init__(self, time: float, seq: int, fn: Callable, args: tuple):
        self.time = time
        self.seq = seq  # tie-breaker so simultaneous events fire in schedule order
        self.fn = fn
        self.args = args
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    # heapq compares events; order by (time, seq) for deterministic execution.
    def __lt__(self, other: "Event") -> bool:
        return (self.time, self.seq) < (other.time, other.seq)


class Sim:
    """Virtual clock + event queue. The heart of every simulation."""

    def __init__(self) -> None:
        self.now: float = 0.0
        self._queue: list[Event] = []
        self._seq = 0  # monotonically increasing tie-breaker

    def at(self, time: float, fn: Callable, *args: Any) -> Event:
        """Schedule `fn(*args)` at absolute virtual time `time`."""
        if time < self.now:
            raise ValueError(f"cannot schedule in the past: {time} < now={self.now}")
        event = Event(time, self._seq, fn, args)
        self._seq += 1
        heapq.heappush(self._queue, event)
        return event

    def after(self, delay: float, fn: Callable, *args: Any) -> Event:
        """Schedule `fn(*args)` `delay` time units from now."""
        if delay < 0:
            raise ValueError(f"negative delay: {delay}")
        return self.at(self.now + delay, fn, *args)

    def run(self, until: float = math.inf, max_events: int = 1_000_000) -> None:
        """Process events in timestamp order until the queue is empty,
        the clock passes `until`, or `max_events` fire (runaway-loop guard).
        """
        fired = 0
        while self._queue:
            if self._queue[0].time > until:
                break
            event = heapq.heappop(self._queue)
            if event.cancelled:
                continue
            self.now = event.time
            event.fn(*event.args)
            fired += 1
            if fired >= max_events:
                raise RuntimeError(
                    f"sim exceeded {max_events} events - likely an infinite loop"
                )
        # If we stopped because of `until`, advance the clock to that point so
        # consecutive run(until=...) calls behave like continuous time.
        if until != math.inf:
            self.now = max(self.now, until)


class Network:
    """Message router with configurable latency, loss, and partitions.

    Latency is sampled uniformly from `latency=(lo, hi)` per message, so
    messages can arrive OUT OF ORDER - exactly like a real network, and the
    source of many of the anomalies studied in Part 1.
    """

    def __init__(
        self,
        sim: Sim,
        latency: tuple[float, float] = (1.0, 10.0),
        loss: float = 0.0,
        seed: int = 0,
    ) -> None:
        self.sim = sim
        self.latency = latency
        self.loss = loss
        self.rng = np.random.default_rng(seed)
        self.nodes: dict[str, Node] = {}
        # Fault state: either a full partition (list of node-name groups) or
        # individual cut links (unordered name pairs).
        self._groups: list[set[str]] | None = None
        self._cut_links: set[frozenset[str]] = set()
        # Counters, handy for asserting "messages were actually dropped".
        self.sent = 0
        self.delivered = 0
        self.dropped = 0

    def add(self, node: "Node") -> None:
        if node.name in self.nodes:
            raise ValueError(f"duplicate node name: {node.name}")
        self.nodes[node.name] = node
        node.net = self
        node.sim = self.sim

    # ---------------------------------------------------------------- faults
    def partition(self, *groups: list[str] | set[str]) -> None:
        """Split the network: messages only flow within a group.

        Every registered node must appear in exactly one group - forgetting a
        node in a partition scenario is a silent-bug magnet, so we fail loudly.
        """
        named = [set(g) for g in groups]
        all_named = set().union(*named) if named else set()
        if all_named != set(self.nodes):
            missing = set(self.nodes) - all_named
            extra = all_named - set(self.nodes)
            raise ValueError(f"partition must cover all nodes (missing={missing}, unknown={extra})")
        self._groups = named

    def heal(self) -> None:
        """Remove the partition and any cut links."""
        self._groups = None
        self._cut_links.clear()

    def cut(self, a: str, b: str) -> None:
        """Sever the single link between two nodes (both directions)."""
        self._cut_links.add(frozenset((a, b)))

    def restore(self, a: str, b: str) -> None:
        self._cut_links.discard(frozenset((a, b)))

    def _reachable(self, src: str, dst: str) -> bool:
        if frozenset((src, dst)) in self._cut_links:
            return False
        if self._groups is not None:
            return any(src in g and dst in g for g in self._groups)
        return True

    # -------------------------------------------------------------- delivery
    def send(self, src: str, dst: str, msg: dict) -> None:
        """Send `msg` from `src` to `dst`, subject to loss/partition/latency."""
        if dst not in self.nodes:
            raise KeyError(f"unknown destination node: {dst}")
        self.sent += 1
        if not self._reachable(src, dst) or self.rng.random() < self.loss:
            self.dropped += 1
            return  # the message silently vanishes - just like on a real network
        delay = self.rng.uniform(*self.latency)

        def deliver() -> None:
            # Re-check reachability at delivery time: a partition that started
            # while the message was in flight also swallows it.
            if not self._reachable(src, dst):
                self.dropped += 1
                return
            self.delivered += 1
            self.nodes[dst].receive(src, msg)

        self.sim.after(delay, deliver)


class Node:
    """Base class for protocol participants. Subclass and implement `handle`."""

    def __init__(self, name: str):
        self.name = name
        self.net: Network | None = None  # set by Network.add
        self.sim: Sim | None = None

    def send(self, dst: str, msg: dict) -> None:
        if self.net is None:
            raise RuntimeError(f"node {self.name} is not attached to a network")
        self.net.send(self.name, dst, msg)

    def broadcast(self, msg: dict) -> None:
        """Send `msg` to every other node on the network."""
        assert self.net is not None, f"node {self.name} is not attached to a network"
        for other in self.net.nodes:
            if other != self.name:
                self.send(other, msg)

    def after(self, delay: float, fn: Callable, *args: Any) -> Event:
        """Schedule a local timer (e.g. a timeout)."""
        assert self.sim is not None, f"node {self.name} is not attached to a network"
        return self.sim.after(delay, fn, *args)

    def receive(self, src: str, msg: dict) -> None:
        # Central dispatch point: subclasses override `handle`. Keeping receive
        # separate lets notebooks wrap it (e.g. to trace every delivery).
        self.handle(src, msg)

    def handle(self, src: str, msg: dict) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement handle()")
