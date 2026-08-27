# tests/test_batching.py
"""Discord embed batching in PlatformService."""

import pytest

from config.settings import Config
from conftest import aware
from models.day import Day
from models.event_item import EventItem
from models.platform import DiscordPlatform
from services.platform_service import PlatformService


def build_days(count: int) -> list[Day]:
    days = []
    for i in range(count):
        item = EventItem(summary=f"Show {i} - S01E0{i % 9 + 1}", source_type="tv", show_name=f"Show {i}")
        days.append(Day(name="Monday, Aug 24", date=aware(2026, 8, 24).date(), tv_events=[item]))
    return days


def run_send(day_count: int, monkeypatch):
    sent = []

    def capture(self, payload):
        sent.append(payload)
        return True

    monkeypatch.setattr(DiscordPlatform, "send_message", capture)
    cfg = Config(discord_webhook_url="https://example.invalid/hook", use_discord=True, timezone="UTC")
    svc = PlatformService(cfg)
    summary = {"total_tv": day_count, "total_movies": 0, "total_premieres": 0}
    svc.send_to_platforms(build_days(day_count), summary, aware(2026, 8, 24), aware(2026, 8, 31))
    return sent


class TestDiscordBatching:
    def test_single_batch_message_shapes(self, monkeypatch):
        sent = run_send(3, monkeypatch)
        assert "content" in sent[0]
        embed_payloads = [p for p in sent if "embeds" in p]
        assert len(embed_payloads) == 1
        assert len(embed_payloads[0]["embeds"]) == 3

    def test_never_more_than_ten_embeds(self, monkeypatch):
        sent = run_send(12, monkeypatch)
        for p in sent:
            if "embeds" in p:
                assert len(p["embeds"]) <= 10

    @pytest.mark.xfail(reason="defect 4, header re-sent inside a later batch", strict=True)
    def test_header_sent_exactly_once(self, monkeypatch):
        sent = run_send(12, monkeypatch)
        header_payloads = [p for p in sent if "content" in p and p["content"]]
        assert len(header_payloads) == 1
