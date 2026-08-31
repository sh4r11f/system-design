"""Unit tests for sysdes.sim - the discrete-event simulator and lossy network."""

import pytest

from sysdes.sim import Network, Node, Sim


class Recorder(Node):
    """Test node that just logs (virtual time, src, msg) for every delivery."""

    def __init__(self, name):
        super().__init__(name)
        self.log = []

    def handle(self, src, msg):
        self.log.append((self.sim.now, src, msg))


def make_net(latency=(1.0, 1.0), loss=0.0, seed=0, names=("a", "b", "c")):
    sim = Sim()
    net = Network(sim, latency=latency, loss=loss, seed=seed)
    nodes = {n: Recorder(n) for n in names}
    for node in nodes.values():
        net.add(node)
    return sim, net, nodes


def test_events_fire_in_time_order():
    sim = Sim()
    fired = []
    sim.at(5.0, fired.append, "late")
    sim.at(1.0, fired.append, "early")
    sim.after(3.0, fired.append, "middle")
    sim.run()
    assert fired == ["early", "middle", "late"]
    assert sim.now == 5.0


def test_simultaneous_events_fire_in_schedule_order():
    sim = Sim()
    fired = []
    sim.at(1.0, fired.append, "first-scheduled")
    sim.at(1.0, fired.append, "second-scheduled")
    sim.run()
    assert fired == ["first-scheduled", "second-scheduled"]


def test_cancelled_event_does_not_fire():
    sim = Sim()
    fired = []
    handle = sim.at(1.0, fired.append, "timeout")
    sim.at(0.5, handle.cancel)  # reply arrives first, timer cancelled
    sim.run()
    assert fired == []


def test_scheduling_in_the_past_is_an_error():
    sim = Sim()
    sim.at(2.0, lambda: None)
    sim.run()
    with pytest.raises(ValueError):
        sim.at(1.0, lambda: None)


def test_runaway_loop_guard():
    sim = Sim()

    def forever():
        sim.after(1.0, forever)

    sim.after(1.0, forever)
    with pytest.raises(RuntimeError):
        sim.run(max_events=100)


def test_run_until_advances_clock_and_preserves_future_events():
    sim = Sim()
    fired = []
    sim.at(10.0, fired.append, "future")
    sim.run(until=5.0)
    assert sim.now == 5.0 and fired == []
    sim.run()
    assert fired == ["future"]


def test_network_delivers_with_latency():
    sim, net, nodes = make_net(latency=(2.0, 2.0))
    nodes["a"].send("b", {"type": "ping"})
    sim.run()
    assert nodes["b"].log == [(2.0, "a", {"type": "ping"})]
    assert (net.sent, net.delivered, net.dropped) == (1, 1, 0)


def test_total_loss_drops_everything():
    sim, net, nodes = make_net(loss=1.0)
    for _ in range(10):
        nodes["a"].send("b", {"type": "ping"})
    sim.run()
    assert nodes["b"].log == []
    assert net.dropped == 10


def test_partition_blocks_across_groups_only():
    sim, net, nodes = make_net()
    net.partition({"a", "b"}, {"c"})
    nodes["a"].send("b", {"type": "in-group"})
    nodes["a"].send("c", {"type": "cross-group"})
    sim.run()
    assert [m for _, _, m in nodes["b"].log] == [{"type": "in-group"}]
    assert nodes["c"].log == []


def test_partition_must_cover_all_nodes():
    _, net, _ = make_net()
    with pytest.raises(ValueError):
        net.partition({"a", "b"})  # forgot "c"


def test_heal_restores_traffic():
    sim, net, nodes = make_net()
    net.partition({"a"}, {"b", "c"})
    net.heal()
    nodes["a"].send("b", {"type": "ping"})
    sim.run()
    assert len(nodes["b"].log) == 1


def test_cut_and_restore_single_link():
    sim, net, nodes = make_net()
    net.cut("a", "b")
    nodes["a"].send("b", {"type": "blocked"})
    nodes["a"].send("c", {"type": "fine"})
    sim.run()
    assert nodes["b"].log == []
    assert len(nodes["c"].log) == 1
    net.restore("a", "b")
    nodes["a"].send("b", {"type": "works-now"})
    sim.run()
    assert len(nodes["b"].log) == 1


def test_partition_starting_mid_flight_swallows_message():
    sim, net, nodes = make_net(latency=(5.0, 5.0))
    nodes["a"].send("b", {"type": "in-flight"})
    # Partition begins at t=1, while the message (arriving t=5) is in flight.
    sim.at(1.0, net.partition, {"a"}, {"b", "c"})
    sim.run()
    assert nodes["b"].log == []
    assert net.dropped == 1


def test_broadcast_reaches_everyone_but_sender():
    sim, net, nodes = make_net()
    nodes["a"].broadcast({"type": "hello"})
    sim.run()
    assert len(nodes["b"].log) == 1 and len(nodes["c"].log) == 1
    assert nodes["a"].log == []


def test_same_seed_same_outcome():
    outcomes = []
    for _ in range(2):
        sim, net, nodes = make_net(latency=(1.0, 10.0), loss=0.3, seed=42)
        for _ in range(20):
            nodes["a"].send("b", {"type": "ping"})
        sim.run()
        outcomes.append([t for t, _, _ in nodes["b"].log])
    assert outcomes[0] == outcomes[1]


def test_unknown_destination_fails_loudly():
    _, _, nodes = make_net()
    with pytest.raises(KeyError):
        nodes["a"].send("nope", {"type": "ping"})


def test_unimplemented_handle_fails_loudly():
    sim = Sim()
    net = Network(sim)
    net.add(Node("bare"))
    net.add(Recorder("r"))
    net.nodes["r"].send("bare", {"type": "ping"})
    with pytest.raises(NotImplementedError):
        sim.run()
