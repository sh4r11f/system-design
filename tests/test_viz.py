"""Unit tests for sysdes.viz - run headless, assert figures actually contain
the artists we expect, and make sure rendering doesn't raise."""

import io

import matplotlib

matplotlib.use("Agg")  # headless backend for CI / test runs

import matplotlib.pyplot as plt
import pytest

from sysdes import viz


def render(fig):
    """Force a full draw to flush layout/text bugs, then free the figure."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    assert buf.getbuffer().nbytes > 0


def test_use_style_applies_rcparams():
    viz.use_style()
    assert plt.rcParams["axes.grid"] is True


def test_system_diagram_draws_boxes_and_arrows():
    fig, ax = viz.system_diagram(
        nodes=[
            {"id": "client", "x": 0, "y": 0, "kind": "client"},
            {"id": "api", "x": 2, "y": 0, "label": "API\nservice"},
            {"id": "db", "x": 4, "y": 0, "kind": "store"},
        ],
        edges=[
            {"src": "client", "dst": "api", "label": "HTTP"},
            {"src": "api", "dst": "db", "label": "SQL", "bidir": True},
        ],
        title="demo",
    )
    # 3 boxes + 2 arrows = 5 patches.
    assert len(ax.patches) == 5
    render(fig)


def test_system_diagram_unknown_kind_fails_loudly():
    with pytest.raises(KeyError):
        viz.system_diagram(
            nodes=[{"id": "x", "x": 0, "y": 0, "kind": "flying-saucer"}],
            edges=[],
        )


def test_message_timeline_draws_lifelines_events_and_lost_messages():
    fig, ax = viz.message_timeline(
        actors=["leader", "follower"],
        messages=[
            {"src": "leader", "dst": "follower", "send": 0, "recv": 3,
             "label": "replicate"},
            {"src": "leader", "dst": "follower", "send": 1, "recv": 4,
             "lost": True},
        ],
        events=[{"t": 5, "actor": "follower", "label": "timeout"}],
        title="demo",
    )
    # 2 lifelines + 1 dotted lost-message path.
    assert len(ax.lines) == 3
    # 1 lost-message x marker + 1 event dot.
    assert len(ax.collections) == 2
    # Time flows downward: y axis must be inverted.
    assert ax.get_ylim()[0] > ax.get_ylim()[1]
    render(fig)


def test_hash_ring_draws_arcs_nodes_and_keys():
    fig, ax = viz.hash_ring(
        nodes={"n1": [0.1, 0.6], "n2": [0.35, 0.85]},
        keys={"k": 0.5},
        title="demo",
    )
    # 4 vnodes -> 4 ownership arcs (lines); 2 node scatters + 1 key scatter.
    assert len(ax.lines) == 4
    assert len(ax.collections) == 3
    render(fig)


def test_hash_ring_empty_fails_loudly():
    with pytest.raises(ValueError):
        viz.hash_ring(nodes={})
