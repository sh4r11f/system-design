"""Matplotlib helpers for the three diagram types the course uses everywhere.

1. `system_diagram`  - box-and-arrow architecture diagrams (clients, services,
                       stores, queues, caches) on a simple x/y grid.
2. `message_timeline` - sequence diagrams: nodes as vertical lifelines, time
                       flowing downward, arrows for messages (optionally lost).
3. `hash_ring`       - a consistent-hashing ring with virtual nodes, ownership
                       arcs, and key placements.

Everything is plain matplotlib so diagrams are code (reproducible, tweakable)
rather than static images.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# Visual identity of each component kind used in architecture diagrams.
# (face color, edge color, line style)
KIND_STYLES: dict[str, tuple[str, str, str]] = {
    "client":   ("#eceff1", "#546e7a", "solid"),
    "service":  ("#e3f2fd", "#1565c0", "solid"),
    "store":    ("#e8f5e9", "#2e7d32", "solid"),
    "queue":    ("#fff3e0", "#ef6c00", "solid"),
    "cache":    ("#f3e5f5", "#6a1b9a", "solid"),
    "external": ("#fafafa", "#9e9e9e", "dashed"),
    "note":     ("#fffde7", "#f9a825", "solid"),
}

# Categorical palette for "one color per node" plots (rings, timelines).
PALETTE = plt.rcParams["axes.prop_cycle"].by_key().get(
    "color",
    ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
     "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"],
)


def use_style() -> None:
    """Apply the course's plot style. Call once at the top of a notebook."""
    plt.rcParams.update({
        "figure.figsize": (7.5, 4.2),
        "figure.dpi": 110,
        "font.size": 11,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
    })


# --------------------------------------------------------------------------- #
# 1. Architecture diagrams
# --------------------------------------------------------------------------- #
def system_diagram(
    nodes: list[dict],
    edges: list[dict],
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
    scale: float = 1.0,
):
    """Draw a box-and-arrow architecture diagram.

    Parameters
    ----------
    nodes:
        Dicts with keys: ``id``, ``x``, ``y`` (grid coordinates, 1 unit apart
        is comfortable), optional ``label`` (defaults to id, ``\\n`` allowed)
        and ``kind`` (one of KIND_STYLES, defaults to "service").
    edges:
        Dicts with keys: ``src``, ``dst`` (node ids), optional ``label``,
        ``style`` ("solid"/"dashed"), ``curve`` (arc3 rad, e.g. 0.2), and
        ``bidir`` (draw arrowheads on both ends).
    """
    if figsize is None:
        # Size the figure from the coordinate span so diagrams stay legible.
        xs = [n["x"] for n in nodes]
        ys = [n["y"] for n in nodes]
        figsize = (
            max(4.0, (max(xs) - min(xs) + 2.2) * 1.7 * scale),
            max(2.4, (max(ys) - min(ys) + 1.4) * 1.15 * scale),
        )
    fig, ax = plt.subplots(figsize=figsize)

    boxes: dict[str, FancyBboxPatch] = {}
    for n in nodes:
        label = n.get("label", n["id"])
        face, edge_color, ls = KIND_STYLES[n.get("kind", "service")]
        lines = label.split("\n")
        # Box width tracks the longest label line; height tracks line count.
        w = 0.135 * max(len(line) for line in lines) + 0.25
        h = 0.30 + 0.22 * len(lines)
        box = FancyBboxPatch(
            (n["x"] - w / 2, n["y"] - h / 2), w, h,
            boxstyle="round,pad=0.06,rounding_size=0.10",
            facecolor=face, edgecolor=edge_color, linestyle=ls, linewidth=1.4,
            zorder=2,
        )
        ax.add_patch(box)
        ax.text(n["x"], n["y"], label, ha="center", va="center",
                fontsize=10, zorder=3)
        boxes[n["id"]] = box

    positions = {n["id"]: (n["x"], n["y"]) for n in nodes}
    for e in edges:
        (x1, y1), (x2, y2) = positions[e["src"]], positions[e["dst"]]
        rad = e.get("curve", 0.0)
        arrow = FancyArrowPatch(
            (x1, y1), (x2, y2),
            # patchA/patchB make the arrow start/end at the box borders.
            patchA=boxes[e["src"]], patchB=boxes[e["dst"]],
            arrowstyle="<|-|>" if e.get("bidir") else "-|>",
            connectionstyle=f"arc3,rad={rad}",
            linestyle=e.get("style", "solid"),
            color="#455a64", linewidth=1.3, mutation_scale=13, zorder=1,
        )
        ax.add_patch(arrow)
        if e.get("label"):
            # Label sits at the edge midpoint, nudged perpendicular to the edge
            # so curved edges keep their label near the curve.
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            dx, dy = x2 - x1, y2 - y1
            norm = np.hypot(dx, dy) or 1.0
            off = rad * 0.55 + (0.10 if rad == 0 else 0)
            ax.text(mx - dy / norm * off, my + dx / norm * off, e["label"],
                    ha="center", va="center", fontsize=8.5, color="#37474f",
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.85,
                              pad=1.5),
                    zorder=3)

    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.margins(0.18)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=12, pad=10)
    fig.tight_layout()
    return fig, ax


# --------------------------------------------------------------------------- #
# 2. Message timelines (sequence diagrams)
# --------------------------------------------------------------------------- #
def message_timeline(
    actors: list[str],
    messages: list[dict],
    events: list[dict] | None = None,
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
):
    """Draw a sequence diagram: one vertical lifeline per actor, time downward.

    Parameters
    ----------
    actors:
        Ordered actor names; each gets a lifeline at x = its index.
    messages:
        Dicts with ``src``, ``dst`` (actor names), ``send``, ``recv`` (times),
        optional ``label``, ``color``, and ``lost`` (True draws the arrow
        fading out with an  x  at the point of loss).
    events:
        Optional dicts with ``t``, ``actor``, ``label``, optional ``color`` -
        drawn as a dot + annotation on the actor's lifeline (e.g. "crash!").
    """
    events = events or []
    xs = {a: i for i, a in enumerate(actors)}
    times = ([m["send"] for m in messages] + [m["recv"] for m in messages]
             + [e["t"] for e in events]) or [0.0]
    t_lo, t_hi = min(times), max(times)
    pad = max(1.0, (t_hi - t_lo) * 0.08)

    if figsize is None:
        figsize = (1.9 * len(actors) + 1.5, 0.28 * (t_hi - t_lo + 2 * pad) + 1.8)
        figsize = (figsize[0], min(figsize[1], 9.0))
    fig, ax = plt.subplots(figsize=figsize)

    # Lifelines + actor header boxes.
    for a, x in xs.items():
        ax.plot([x, x], [t_lo - pad, t_hi + pad], color="#b0bec5",
                linestyle="--", linewidth=1, zorder=1)
        ax.text(x, t_lo - pad, a, ha="center", va="bottom", fontsize=11,
                fontweight="bold",
                bbox=dict(facecolor="#eceff1", edgecolor="#546e7a", pad=3))

    for m in messages:
        x1, x2 = xs[m["src"]], xs[m["dst"]]
        color = m.get("color", "#1565c0")
        if m.get("lost"):
            # Draw the doomed message up to 55% of its path, then mark the loss.
            xe = x1 + (x2 - x1) * 0.55
            te = m["send"] + (m["recv"] - m["send"]) * 0.55
            ax.plot([x1, xe], [m["send"], te], color=color, linewidth=1.4,
                    linestyle=":", zorder=2)
            ax.scatter([xe], [te], marker="x", s=70, color="#c62828", zorder=3,
                       linewidths=2.2)
        else:
            ax.annotate(
                "", xy=(x2, m["recv"]), xytext=(x1, m["send"]),
                arrowprops=dict(arrowstyle="-|>", color=color, linewidth=1.4,
                                shrinkA=2, shrinkB=2),
            )
        if m.get("label"):
            mx, my = (x1 + xs[m["dst"]]) / 2, (m["send"] + m["recv"]) / 2
            ax.text(mx, my - (t_hi - t_lo + 1) * 0.015, m["label"],
                    ha="center", va="bottom", fontsize=8.5, color=color,
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.8,
                              pad=1.0))

    for e in events:
        x = xs[e["actor"]]
        color = e.get("color", "#c62828")
        ax.scatter([x], [e["t"]], s=45, color=color, zorder=4)
        ax.annotate(e["label"], xy=(x, e["t"]), xytext=(x + 0.08, e["t"]),
                    fontsize=8.5, color=color, va="center")

    ax.set_ylim(t_hi + pad, t_lo - pad * 2.2)  # inverted: time flows downward
    ax.set_xlim(-0.6, len(actors) - 0.4)
    ax.set_ylabel("time")
    ax.set_xticks([])
    ax.grid(False)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    if title:
        ax.set_title(title, fontsize=12, pad=18)
    fig.tight_layout()
    return fig, ax


# --------------------------------------------------------------------------- #
# 3. Consistent-hash rings
# --------------------------------------------------------------------------- #
def _theta(pos: float) -> float:
    """Ring position in [0,1) -> angle. 0 is at 12 o'clock, increasing clockwise."""
    return np.pi / 2 - 2 * np.pi * pos


def hash_ring(
    nodes: dict[str, list[float]],
    keys: dict[str, float] | None = None,
    title: str | None = None,
    figsize: tuple[float, float] = (5.6, 5.6),
):
    """Draw a consistent-hashing ring.

    Parameters
    ----------
    nodes:
        ``{node_name: [vnode positions in [0,1)]}``. Each node gets one color;
        the ring is painted with "ownership arcs": the arc *ending* at a vnode
        is owned by that vnode's node (keys walk clockwise to the next vnode).
    keys:
        Optional ``{key_label: position}`` markers placed just inside the ring.
    """
    keys = keys or {}
    fig, ax = plt.subplots(figsize=figsize)
    colors = {name: PALETTE[i % len(PALETTE)] for i, name in enumerate(nodes)}

    # Sorted list of (position, owner) pairs defines the ownership arcs.
    ring = sorted((p, name) for name, ps in nodes.items() for p in ps)
    if not ring:
        raise ValueError("hash_ring needs at least one virtual node")

    # Paint each arc (prev_pos -> pos] with the owner of the vnode at `pos`.
    for i, (pos, owner) in enumerate(ring):
        prev = ring[i - 1][0] if i > 0 else ring[-1][0] - 1.0  # wrap around
        span = np.linspace(prev, pos, max(8, int((pos - prev) * 240)))
        ax.plot(np.cos(_theta(span)), np.sin(_theta(span)),
                color=colors[owner], linewidth=7, solid_capstyle="butt",
                zorder=1)

    # Vnode markers on the ring.
    for name, ps in nodes.items():
        thetas = _theta(np.array(ps))
        ax.scatter(np.cos(thetas), np.sin(thetas), s=110, color=colors[name],
                   edgecolor="white", linewidth=1.4, zorder=3, label=name)

    # Key markers slightly inside the ring, with a tick showing their position.
    for label, pos in keys.items():
        th = _theta(pos)
        ax.scatter([0.86 * np.cos(th)], [0.86 * np.sin(th)], marker="^", s=55,
                   color="#37474f", zorder=3)
        ax.text(0.72 * np.cos(th), 0.72 * np.sin(th), label, ha="center",
                va="center", fontsize=8.5, color="#37474f")

    # "0.0" reference tick at 12 o'clock.
    ax.text(0, 1.13, "0.0", ha="center", va="center", fontsize=9,
            color="#78909c")
    ax.annotate("", xy=(np.cos(_theta(0.055)) * 1.12, np.sin(_theta(0.055)) * 1.12),
                xytext=(np.cos(_theta(0.02)) * 1.12, np.sin(_theta(0.02)) * 1.12),
                arrowprops=dict(arrowstyle="-|>", color="#78909c"))

    ax.set_aspect("equal")
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.35, 1.35)
    ax.axis("off")
    ax.legend(loc="center", fontsize=9)
    if title:
        ax.set_title(title, fontsize=12)
    fig.tight_layout()
    return fig, ax
