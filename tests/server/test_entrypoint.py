"""Server entrypoint tests."""

from __future__ import annotations

import sys
import types
import warnings

import doorae.server as server_module


def test_run_server_invokes_uvicorn_with_factory_mode(
    monkeypatch,
) -> None:
    calls: dict[str, object] = {}

    def fake_uvicorn_run(*args, **kwargs) -> None:
        calls["args"] = args
        calls["kwargs"] = kwargs

    monkeypatch.setitem(sys.modules, "uvicorn", types.SimpleNamespace(run=fake_uvicorn_run))

    server_module.run_server(host="127.0.0.1", port=9100)

    assert calls["args"] == ("doorae.server.app:create_app",)
    assert calls["kwargs"] == {
        "host": "127.0.0.1",
        "port": 9100,
        "factory": True,
        "reload": False,
    }


def test_legacy_main_warns_and_delegates_to_run_server(
    monkeypatch,
    capsys,
) -> None:
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        server_module,
        "get_server_settings",
        lambda: types.SimpleNamespace(host="127.0.0.1", port=9200),
    )
    monkeypatch.setattr(
        server_module,
        "run_server",
        lambda *, host, port: calls.update({"host": host, "port": port}),
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        server_module.main()

    captured = capsys.readouterr()
    assert calls == {"host": "127.0.0.1", "port": 9200}
    assert "doorae-server는 deprecated입니다." in captured.err
    assert any(
        warning.category is DeprecationWarning and "doorae serve" in str(warning.message)
        for warning in caught
    )
