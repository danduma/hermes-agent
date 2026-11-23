"""Local patch: ``xp:`` taps are acknowledged and handed to ``~/xpost/xpost.py tap`` in the background."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.telegram.adapter import TelegramAdapter


class _Query:
    def __init__(self, data):
        self.data = data
        self.message = SimpleNamespace(chat_id=111, chat=SimpleNamespace(type="private"), message_thread_id=None,
                                       message_id=5, text="draft")
        self.from_user = SimpleNamespace(id=111, first_name="tester")
        self.events = []

    async def answer(self, text=None, **kwargs):
        self.events.append(("answer", text))


def _adapter(authorized=True):
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="t", extra={}))
    adapter._bot = AsyncMock()
    adapter._is_callback_user_authorized = lambda *a, **k: authorized
    return adapter


@pytest.mark.asyncio
async def test_xpost_tap_is_answered_and_runs_xpost(monkeypatch):
    calls = []

    class _Proc:
        returncode = 0
        async def communicate(self): return b"", b""

    async def fake_exec(*args, **kwargs):
        calls.append(args)
        return _Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    query = _Query("xp:n:12:3:linkedin")
    await _adapter()._handle_callback_query(SimpleNamespace(callback_query=query), SimpleNamespace())
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert query.events == [("answer", "Posting to Linkedin…")]
    assert calls and calls[0][1].endswith("xpost.py") and calls[0][2:] == ("tap", "xp:n:12:3:linkedin", "111")


@pytest.mark.asyncio
async def test_unauthorized_xpost_tap_runs_nothing(monkeypatch):
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(side_effect=AssertionError("must not run")))
    query = _Query("xp:a:12:3")
    await _adapter(authorized=False)._handle_callback_query(SimpleNamespace(callback_query=query), SimpleNamespace())
    await asyncio.sleep(0)
    assert query.events and query.events[0][0] == "answer" and "Posting" not in (query.events[0][1] or "")
