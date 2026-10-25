"""Automated network validation.

These tests connect to the running lab and assert that the network is
actually doing what the inventory says it should: interfaces up, VLANs
present, OSPF adjacencies formed, and end-to-end routing working.

    pytest -v

This is the "did my change break the network?" safety net — the same
idea as unit tests, but for a live network.
"""
import pytest
import yaml
from napalm import get_network_driver

HOSTS = yaml.safe_load(open("inventory/hosts.yaml"))
DEFAULTS = yaml.safe_load(open("inventory/defaults.yaml"))
CORES = [n for n, v in HOSTS.items() if v["data"]["role"] == "core"]


def connect(name):
    h = HOSTS[name]
    driver = get_network_driver("eos")
    dev = driver(
        hostname=h["hostname"],
        username=DEFAULTS["username"],
        password=DEFAULTS["password"],
        optional_args={"transport": "https"},
    )
    dev.open()
    return dev


@pytest.fixture(params=list(HOSTS), ids=list(HOSTS))
def device(request):
    dev = connect(request.param)
    yield request.param, dev
    dev.close()


@pytest.fixture(params=CORES, ids=CORES)
def core(request):
    dev = connect(request.param)
    yield request.param, dev
    dev.close()


def test_device_reachable(device):
    """Every device answers over its management API."""
    name, dev = device
    facts = dev.get_facts()
    assert facts["hostname"] == name


def test_configured_vlans_exist(device):
    """VLANs defined in inventory are actually on the device."""
    name, dev = device
    out = dev.cli(["show vlan"])["show vlan"]
    for vid in HOSTS[name]["data"]["vlans"]:
        assert str(vid) in out, f"VLAN {vid} missing on {name}"


def test_ospf_neighbors_full(core):
    """Both cores should have a FULL OSPF adjacency across the core link."""
    name, dev = core
    out = dev.cli(["show ip ospf neighbor"])["show ip ospf neighbor"]
    assert "FULL" in out, f"No FULL OSPF neighbor on {name}:\n{out}"


def test_core_to_core_routing(core):
    """Each core can reach the other core's loopback — proves OSPF is routing."""
    name, dev = core
    peer_loopback = "2.2.2.2" if name == "core1" else "1.1.1.1"
    my_loopback = "1.1.1.1" if name == "core1" else "2.2.2.2"
    out = dev.cli([f"ping {peer_loopback} source {my_loopback}"])
    result = list(out.values())[0]
    assert "received" in result and " 0 received" not in result, (
        f"{name} cannot reach {peer_loopback}:\n{result}"
    )
