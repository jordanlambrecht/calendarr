# tests/test_render.py
"""Payload rendering for Discord and Slack."""

from datetime import date

from calendarr.config import EventType, PastEventHandling
from calendarr.domain import DayReport, EventLine, Report, SourceError
from calendarr.render import (
    DISCORD_STYLE,
    SLACK_STYLE,
    compose_movie_line,
    compose_tv_line,
    day_body,
    discord_payloads,
    header_text,
    slack_payloads,
    source_warning_text,
    subheader_text,
)
from conftest import aware, mk_config, tv_source


def tv_line(**kw) -> EventLine:
    base = dict(
        summary="Show - S01E05 - Title",
        source_type=EventType.TV,
        show_name="Show",
        episode_number="S01E05",
        episode_title="Title",
        time_str="20:00",
    )
    base.update(kw)
    return EventLine(**base)


def one_day_report(days=None, **kw) -> Report:
    if days is None:
        days = [DayReport(date=date(2026, 8, 24), tv=[tv_line()])]
    base = dict(
        days=days,
        start=aware(2026, 8, 24),
        end=aware(2026, 8, 31),
        tv_count=sum(len(d.tv) for d in days),
        movie_count=sum(len(d.movies) for d in days),
    )
    base.update(kw)
    return Report(**base)


class TestLineComposition:
    def test_discord_tv_line(self):
        line = compose_tv_line(tv_line(), DISCORD_STYLE, PastEventHandling.DISPLAY)
        assert line == "20:00: **Show** - S01E05 - *Title*"

    def test_slack_tv_line(self):
        line = compose_tv_line(tv_line(), SLACK_STYLE, PastEventHandling.DISPLAY)
        assert line == "20:00: *Show* - S01E05 - _Title_"

    def test_premiere_marker_parity(self):
        # Was register defect 13, Slack lost its premiere marker
        for style in (DISCORD_STYLE, SLACK_STYLE):
            plain = compose_tv_line(tv_line(), style, PastEventHandling.DISPLAY)
            premiere = compose_tv_line(tv_line(is_premiere=True), style, PastEventHandling.DISPLAY)
            assert premiere != plain
            assert "🎉" in premiere

    def test_strike_past(self):
        line = compose_tv_line(tv_line(is_past=True), DISCORD_STYLE, PastEventHandling.STRIKE)
        assert line.startswith("~~") and line.endswith("~~")

    def test_movie_line(self):
        line = EventLine(summary="Big Movie", source_type=EventType.MOVIE, show_name="Big Movie")
        assert compose_movie_line(line, DISCORD_STYLE, PastEventHandling.DISPLAY) == "🎬  **Big Movie**"

    def test_empty_day_placeholder(self):
        body = day_body(DayReport(date=date(2026, 8, 24)), DISCORD_STYLE, PastEventHandling.DISPLAY)
        assert "No releases scheduled" in body


class TestHeaders:
    def test_weekly_range_shows_inclusive_last_day(self):
        text = header_text(one_day_report(), mk_config(custom_header="Guide"))
        assert text == "Guide (Aug 24 - Aug 30)"

    def test_zero_events_message(self):
        report = one_day_report(days=[], tv_count=0, movie_count=0)
        assert "No new releases" in subheader_text(report, DISCORD_STYLE)

    def test_counts(self):
        report = one_day_report(tv_count=3, movie_count=1, premiere_count=1)
        text = subheader_text(report, DISCORD_STYLE)
        assert "3 all-new episodes" in text
        assert "1 movie release" in text
        assert "1 season premiere" in text

    def test_source_warning_hides_apikey(self):
        errors = [SourceError(source=tv_source("http://sonarr.local:8989/feed.ics?apikey=SECRET"), error="x")]
        report = one_day_report(source_errors=errors)
        warning = source_warning_text(report, DISCORD_STYLE)
        assert "sonarr.local:8989" in warning
        assert "SECRET" not in warning


class TestDiscordPayloads:
    def test_header_sent_exactly_once(self):
        # Was register defect 4, header duplicated across batches
        days = [DayReport(date=date(2026, 8, 24), tv=[tv_line()]) for _ in range(12)]
        payloads = discord_payloads(one_day_report(days=days), mk_config())
        content_payloads = [p for p in payloads if "content" in p]
        assert len(content_payloads) == 1

    def test_max_ten_embeds_per_payload(self):
        days = [DayReport(date=date(2026, 8, 24), tv=[tv_line()]) for _ in range(12)]
        payloads = discord_payloads(one_day_report(days=days), mk_config())
        for p in payloads:
            if "embeds" in p:
                assert len(p["embeds"]) <= 10

    def test_long_day_splits_into_continuation_embeds(self):
        lines = [tv_line(episode_title="X" * 200, summary=f"Show {i}") for i in range(30)]
        days = [DayReport(date=date(2026, 8, 24), tv=lines)]
        payloads = discord_payloads(one_day_report(days=days), mk_config())
        embeds = [e for p in payloads if "embeds" in p for e in p["embeds"]]
        assert len(embeds) > 1
        assert any("(cont.)" in e["title"] for e in embeds)
        assert all(len(e["description"]) <= 4096 for e in embeds)

    def test_single_oversize_line_hard_sliced(self):
        lines = [tv_line(episode_title="X" * 6000)]
        days = [DayReport(date=date(2026, 8, 24), tv=lines)]
        payloads = discord_payloads(one_day_report(days=days), mk_config())
        embeds = [e for p in payloads if "embeds" in p for e in p["embeds"]]
        assert all(len(e["description"]) <= 4096 for e in embeds)

    def test_mention_role_included(self):
        cfg = mk_config(discord_mention_role_id="1234")
        payloads = discord_payloads(one_day_report(), cfg)
        assert "<@&1234>" in payloads[0]["content"]

    def test_footer_is_separate_final_payload(self):
        payloads = discord_payloads(one_day_report(), mk_config(), footer="my footer")
        assert payloads[-1] == {"content": "my footer"}


class TestSlackPayloads:
    def test_main_payload_shape(self):
        payloads = slack_payloads(one_day_report(), mk_config())
        main = payloads[0]
        assert main["blocks"][0]["type"] == "header"
        assert main["attachments"][0]["title"] == "Monday, Aug 24"
        assert main["attachments"][0]["color"] == "#E53935"

    def test_footer_uses_context_block(self):
        # Was register defect 5, invalid block type broke Slack footers
        payloads = slack_payloads(one_day_report(), mk_config(), footer="hi")
        footer_block = payloads[-1]["blocks"][0]
        assert footer_block["type"] == "context"
        assert footer_block["elements"][0]["text"] == "hi"
