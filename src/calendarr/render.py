# src/calendarr/render.py
"""Build platform payloads from a Report. One composition path, two envelopes."""

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from calendarr.config import Config, PastEventHandling
from calendarr.domain import EPISODE_PATTERN, DayReport, EventLine, Report

logger = logging.getLogger("render")

NO_NEW_RELEASES_MSG = "No new releases this week. Maybe this is a good time to take a walk?"
NO_CONTENT_TODAY_MSG = (
    "No releases scheduled for this day. Maybe you could call your mom and tell her you love her instead?"
)
MENTION_INSTRUCTIONS_MSG = "If you'd like to be notified when new content is available, join this role!"

DISCORD_FOOTER_FILE = "/app/custom_footers/discord_footer.md"
SLACK_FOOTER_FILE = "/app/custom_footers/slack_footer.md"

MAX_DISCORD_EMBEDS = 10
MAX_DISCORD_CONTENT = 2000
MAX_EMBED_DESCRIPTION = 4096
EMBED_BATCH_CHAR_BUDGET = 5500
MAX_SLACK_HEADER = 150

COLOR_ORDER = ["red", "orange", "yellow", "green", "blue", "indigo", "violet"]
DISCORD_COLORS = {
    "red": 15158332,
    "orange": 15844367,
    "yellow": 16776960,
    "green": 5763719,
    "blue": 3447003,
    "indigo": 10181046,
    "violet": 9846527,
}
SLACK_COLORS = {
    "red": "#E53935",
    "orange": "#FB8C00",
    "yellow": "#FFD600",
    "green": "#43A047",
    "blue": "#1E88E5",
    "indigo": "#5E35B1",
    "violet": "#8E24AA",
}

TIMEZONE_NAME_MAP = {
    "America/Los_Angeles": "Pacific Time",
    "America/Vancouver": "Pacific Time",
    "America/Denver": "Mountain Time",
    "America/Edmonton": "Mountain Time",
    "America/Chicago": "Central Time",
    "America/Toronto": "Eastern Time",
    "America/New_York": "Eastern Time",
    "Europe/London": "UK Time",
    "Europe/Berlin": "Central European Time",
    "Australia/Sydney": "Australian Eastern Time",
    "Asia/Tokyo": "Japan Standard Time",
    "Asia/Kolkata": "Indian Standard Time",
    "Asia/Hong_Kong": "Hong Kong Time",
    "UTC": "UTC",
}

WEEKDAYS_MONDAY_FIRST = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass(frozen=True)
class Style:
    bold: str
    italic: str
    strike: str
    premiere_marker: str


DISCORD_STYLE = Style(bold="**", italic="*", strike="~~", premiere_marker="🎉")
SLACK_STYLE = Style(bold="*", italic="_", strike="~", premiere_marker="🎉")


def pluralize(word: str, count: int) -> str:
    return word if count == 1 else word + "s"


def day_color(weekday: str, start_week_on_monday: bool, palette: dict) -> int | str:
    order = WEEKDAYS_MONDAY_FIRST if start_week_on_monday else (["Sunday"] + WEEKDAYS_MONDAY_FIRST[:-1])
    index = order.index(weekday) if weekday in order else 0
    return palette[COLOR_ORDER[index % len(COLOR_ORDER)]]


def compose_tv_line(line: EventLine, style: Style, past_handling: PastEventHandling) -> str:
    prefix = f"{line.time_str}: " if line.time_str else ""
    name = line.show_name or line.summary
    text = f"{style.bold}{name}{style.bold}"
    number, title = line.episode_number, line.episode_title
    if title:
        if number and EPISODE_PATTERN.match(number):
            text += f" - {number} - {style.italic}{title}{style.italic}"
        else:
            text += f" - {style.italic}{number} - {title}{style.italic}"
    elif number:
        if EPISODE_PATTERN.match(number):
            text += f" - {number}"
        else:
            text += f" - {style.italic}{number}{style.italic}"
    text = prefix + text
    if line.is_premiere:
        text += f"  {style.premiere_marker}"
    if line.is_past and past_handling is PastEventHandling.STRIKE:
        text = f"{style.strike}{text}{style.strike}"
    return text.strip()


def compose_movie_line(line: EventLine, style: Style, past_handling: PastEventHandling) -> str:
    name = line.show_name or line.summary
    text = f"🎬  {style.bold}{name}{style.bold}"
    if line.is_past and past_handling is PastEventHandling.STRIKE:
        text = f"{style.strike}{text}{style.strike}"
    return text.strip()


def day_body(day: DayReport, style: Style, past_handling: PastEventHandling) -> str:
    tv = [compose_tv_line(line, style, past_handling) for line in day.tv]
    movies = [compose_movie_line(line, style, past_handling) for line in day.movies]
    parts = []
    if tv:
        parts.append("\n".join(tv))
    if movies:
        parts.append(f"{style.bold}MOVIES{style.bold}\n" + "\n".join(movies))
    if not parts:
        return f"{style.italic}{NO_CONTENT_TODAY_MSG}{style.italic}"
    return "\n\n".join(parts)


def header_text(report: Report, config: Config) -> str:
    text = config.custom_header
    if config.show_date_range:
        if report.is_daily:
            text += f" ({report.start.strftime('%A, %b %d')})"
        else:
            last_day = report.end - timedelta(days=1)
            text += f" ({report.start.strftime('%b %d')} - {last_day.strftime('%b %d')})"
    return text


def subheader_text(report: Report, style: Style) -> str:
    if report.total_events == 0:
        return f"{style.bold}{NO_NEW_RELEASES_MSG}{style.bold}"
    parts = []
    if report.tv_count:
        parts.append(f"{style.bold} 📺  {report.tv_count} all-new {pluralize('episode', report.tv_count)}{style.bold}")
    if report.movie_count:
        parts.append(
            f"{style.bold} 🎬  {report.movie_count} {pluralize('movie release', report.movie_count)}{style.bold}"
        )
    if report.premiere_count:
        parts.append(
            f"{style.bold} 🎉  {report.premiere_count} season {pluralize('premiere', report.premiere_count)}{style.bold}"
        )
    if len(parts) <= 2:
        return " and ".join(parts)
    return ", ".join(parts[:-1]) + ", and " + parts[-1]


def source_warning_text(report: Report, style: Style) -> str:
    if not report.source_errors:
        return ""
    names = ", ".join(err.source.display_name for err in report.source_errors)
    return f"{style.italic}⚠️ Could not reach {names}, listings may be incomplete{style.italic}"


def timezone_line(config: Config, style: Style) -> str:
    if not config.show_timezone_in_subheader:
        return ""
    name = TIMEZONE_NAME_MAP.get(config.timezone)
    if not name:
        try:
            name = datetime(datetime.now().year, 1, 1, tzinfo=config.tz).tzname()
        except Exception:
            name = None
    if not name:
        return ""
    return f"{style.italic}All times shown in {name}{style.italic}"


def read_footer(path: str) -> str:
    """Footer markdown with HTML comments stripped, empty when unavailable."""
    try:
        if not os.path.exists(path):
            logger.warning("Custom footer enabled but %s not found", path)
            return ""
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        return re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL).strip()
    except OSError as e:
        logger.error("Could not read footer %s (%s)", path, e)
        return ""


def _split_description(title: str, body: str) -> list[tuple[str, str]]:
    """Split an over-long embed body across continuation embeds at line breaks."""
    if len(body) <= MAX_EMBED_DESCRIPTION:
        return [(title, body)]
    chunks, current = [], ""
    for line in body.split("\n"):
        if len(line) > MAX_EMBED_DESCRIPTION:
            # A single oversize line gets hard sliced so no chunk can exceed the cap
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(line[i : i + MAX_EMBED_DESCRIPTION] for i in range(0, len(line), MAX_EMBED_DESCRIPTION))
            continue
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > MAX_EMBED_DESCRIPTION:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return [(title if i == 0 else f"{title} (cont.)", chunk) for i, chunk in enumerate(chunks)]


def discord_payloads(report: Report, config: Config, footer: str = "") -> list[dict]:
    """Ordered webhook payloads. Header first, then embed batches, then footer."""
    style = DISCORD_STYLE
    content = f"# {header_text(report, config)}\n\n{subheader_text(report, style)}"
    warning = source_warning_text(report, style)
    if warning:
        content += f"\n\n{warning}"
    tz_line = timezone_line(config, style)
    if tz_line:
        content += f"\n\n{tz_line}"
    if config.discord_mention_role_id:
        content += f"\n\n<@&{config.discord_mention_role_id}>"
        if not config.discord_hide_mention_instructions:
            content += f"\n{style.italic}{MENTION_INSTRUCTIONS_MSG}{style.italic}"
    payloads: list[dict] = [{"content": content[:MAX_DISCORD_CONTENT]}]

    embeds = []
    for day in report.days:
        color = day_color(day.weekday, config.start_week_on_monday, DISCORD_COLORS)
        body = day_body(day, style, config.passed_event_handling)
        for title, chunk in _split_description(day.title, body):
            embeds.append({"title": title, "description": chunk, "color": color})

    batch: list[dict] = []
    batch_chars = 0
    for embed in embeds:
        size = len(embed["title"]) + len(embed["description"])
        if batch and (len(batch) >= MAX_DISCORD_EMBEDS or batch_chars + size > EMBED_BATCH_CHAR_BUDGET):
            payloads.append({"embeds": batch})
            batch, batch_chars = [], 0
        batch.append(embed)
        batch_chars += size
    if batch:
        payloads.append({"embeds": batch})

    if footer:
        payloads.append({"content": footer[:MAX_DISCORD_CONTENT]})
    return payloads


def slack_payloads(report: Report, config: Config, footer: str = "") -> list[dict]:
    """Main message with header blocks plus day attachments, then optional footer."""
    style = SLACK_STYLE
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text(report, config)[:MAX_SLACK_HEADER]},
        }
    ]
    section_parts = [subheader_text(report, style)]
    warning = source_warning_text(report, style)
    if warning:
        section_parts.append(warning)
    tz_line = timezone_line(config, style)
    if tz_line:
        section_parts.append(tz_line)
    section_text = "\n\n".join(p for p in section_parts if p)
    if section_text:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": section_text}})

    attachments = []
    for day in report.days:
        attachments.append(
            {
                "color": day_color(day.weekday, config.start_week_on_monday, SLACK_COLORS),
                "title": day.title,
                "text": day_body(day, style, config.passed_event_handling),
                "mrkdwn_in": ["text"],
            }
        )

    payloads = [{"blocks": blocks, "attachments": attachments}]
    if footer:
        payloads.append({"blocks": [{"type": "context", "elements": [{"type": "mrkdwn", "text": footer}]}]})
    return payloads
