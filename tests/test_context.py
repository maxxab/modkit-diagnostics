import asyncio
import importlib

import pytest


def api():
    module = importlib.import_module("modkit_diagnostics")
    assert hasattr(module, "bind_context"), "scoped context API missing"
    return module


def test_snapshot_and_exception_restoration():
    m = api()
    source = {"nested": [1]}
    with m.bind_context(payload=source):
        source["nested"].append(2)
        assert m.get_context() == {"payload": {"nested": [1]}}
        m.get_context()["payload"]["nested"].append(3)
        with pytest.raises(RuntimeError):
            with m.bind_context(payload={"other": 4}):
                assert m.get_context() == {"payload": {"other": 4}}
                raise RuntimeError("exit")
        assert m.get_context() == {"payload": {"nested": [1]}}
    assert m.get_context() == {}


def test_async_tasks_inherit_but_do_not_share_mutable_context():
    m = api()

    async def worker(name):
        assert m.get_context() == {"parent": [1]}
        with m.bind_context(task=name):
            await asyncio.sleep(0)
            m.get_context()["parent"].append(name)
            assert m.get_context() == {"parent": [1], "task": name}
        assert m.get_context() == {"parent": [1]}

    async def run():
        with m.bind_context(parent=[1]):
            await asyncio.gather(worker("a"), worker("b"))
            assert m.get_context() == {"parent": [1]}

    asyncio.run(run())
    assert m.get_context() == {}
