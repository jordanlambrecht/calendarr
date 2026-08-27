# tests/test_render.py
"""Platform specific message formatting."""

import pytest

from config.settings import Config
from conftest import aware
from models.day import Day
from models.event_item import EventItem
from models.platform import DiscordPlatform, SlackPlatform
from services.webhook_service import WebhookService
from utils.format_utils import format_header_text, format_subheader_text, get_day_colors


def discord(config=None) -> DiscordPlatform:
    return DiscordPlatform("https://example.invalid/hook", WebhookService(30), [200, 204], config or Config())


def slack(config=None) -> SlackPlatform:
    return SlackPlatform("https://example.invalid/hook", WebhookService(30), [200, 201, 204], config or Config())


def tv_item(**kw) -> EventItem:
    base = dict(
        summary="Show - S01E05 - Title",
        source_type="tv",
        show_name="Show",
        episode_number="S01E05",
        episode_title="Title",
        time_str="20:00",
    )
    base.update(kw)
    return EventItem(**base)


class TestDiscordFormatting:
    def test_tv_event_line(self):
        line = discord().format_tv_event(tv_item(), "DISPLAY")
        assert line == "20:00: **Show** - S01E05 - *Title*"

    def test_premiere_marker(self):
        line = discord().format_tv_event(tv_item(is_premiere=True), "DISPLAY")
        assert "🎉" in line

    def test_strike_for_past(self):
        line = discord().format_tv_event(tv_item(is_past=True), "STRIKE")
        assert line.startswith("~~") and line.endswith("~~")

    def test_movie_line(self):
        item = EventItem(summary="Big Movie", source_type="movie", show_name="Big Movie")
        assert discord().format_movie_event(item, "DISPLAY") == "🎬  **Big Movie**"

    def test_day_embed_shape(self):
        day = Day(name="Monday, Aug 24", date=aware(2026, 8, 24).date(), tv_events=[tv_item()], movie_events=[])
        embed = discord().format_day(day)
        assert embed["title"] == "Monday, Aug 24"
        assert "**Show**" in embed["description"]
        assert embed["color"] == 15158332

    def test_header_contains_counts(self):
        payload = discord().format_header("New Releases", aware(2026, 8, 24), aware(2026, 8, 31), True, 3, 2, 1)
        content = payload["content"]
        assert content.startswith("# New Releases")
        assert "3 all-new episodes" in content
        assert "2 movie releases" in content


class TestSlackFormatting:
    def test_day_attachment_shape(self):
        day = Day(name="Monday, Aug 24", date=aware(2026, 8, 24).date(), tv_events=[tv_item()], movie_events=[])
        att = slack().format_day(day)
        assert att["title"] == "Monday, Aug 24"
        assert att["color"] == "#E53935"
        assert "*Show*" in att["text"]

    def test_header_blocks(self):
        payload = slack().format_header("New Releases", aware(2026, 8, 24), aware(2026, 8, 31), True, 3, 0, 0)
        assert payload["blocks"][0]["type"] == "header"

    @pytest.mark.xfail(reason="defect 13, Slack premiere marker was lost", strict=True)
    def test_premiere_marker_parity(self):
        plain = slack().format_tv_event(tv_item(), "DISPLAY")
        premiere = slack().format_tv_event(tv_item(is_premiere=True), "DISPLAY")
        assert premiere != plain


class TestHeaderHelpers:
    def test_weekly_range_text(self):
        text = format_header_text("Guide", aware(2026, 8, 24), aware(2026, 8, 31), True)
        assert text == "Guide (Aug 24 - Aug 31)"

    def test_zero_events_message(self):
        text = format_subheader_text(0, 0, 0, "discord")
        assert "No new releases" in text

    def test_day_colors_rotate_from_week_start(self):
        colors = get_day_colors("discord", start_week_on_monday=False)
        assert colors["Sunday"] == 15158332
