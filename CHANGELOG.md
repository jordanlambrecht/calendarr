# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.2] 2025-04-15

### Fixed
- Movie release lists were showing times and missing their 🎬 emoji. Movies should never display release times
- Slack was not correctly formatting markdown in the header/subheader

### Changed
- Some hard-coded messages were instead moved to the constants file

## [1.4.0] 2025-04-12

### Added
- Event deduplication feature to prevent duplicate entries when using multiple Sonarr/Radarr instances
- New configuration option `DEDUPLICATE_EVENTS` to control deduplication (defaults to true)
- pyproject.toml to make the snoots happy
- New `EventItem` class to provide a structured representation of events for display
- Discord Mentions now provide instructions on how a user can be notified
- Configuration option `DISCORD_HIDE_MENTION_INSTRUCTIONS` to hide the help text below Discord role mentions
- Fallback support for `MENTION_ROLE_ID` environment variable for backward compatibility.
- Markdown styling constants (`DISCORD_BOLD_START`, `SLACK_ITALIC_END`, etc.) to `constants.py` for easier maintenance.
- `TIMEZONE_NAME_MAP` in constants to provide user-friendly names for common timezones (e.g., "Central Time" for "America/Chicago").
- Configuration option `SHOW_TIMEZONE_IN_SUBHEADER` to display the configured timezone in the header message. (Addresses #6)
- Refactored formatting functions to use new markdown styling constants.


### Changed
- Refactored platform-specific formatting to properly separate content from presentation
- Enhanced `Event` model with comparison methods for reliable deduplication
- Updated `Day` class to store structured event data instead of pre-formatted strings
- Improved formatting of processed event summary log message.

### Fixed
- **Discord Embed Size Limit:** Implemented "smart batching" for Discord messages. Embeds are now grouped intelligently to stay under the 6000-character payload limit and 10-embed count limit, preventing failures on large weekly schedules while minimizing message spam. (Fixes [#3](https://github.com/jordanlambrecht/calendarr/issues/3))
- **Improved TV event formatting (Discord & Slack):** Correctly applies italics to descriptive episode details (like dates, guest names, or non-standard identifiers) while leaving standard `SxxExx` numbers unitalicized. This fixes inconsistent bolding/italics, especially for daily shows. (Fixes [#4](https://github.com/jordanlambrecht/calendarr/issues/4))
- Correctly generate `Day.name` when creating `Day` objects in `FormatterService`.
- **Deduplication: Issue with duplicate show entries appearing when using multiple Sonarr instances** (Fixes [#5](https://github.com/jordanlambrecht/calendarr/issues/5))
- Removed incorrect `end_time` validation from `Event.__post_init__`.
- Pass `source_type` correctly when creating `Event` objects instead of modifying raw iCal event data.
- Platform-specific formatting logic that was previously hardcoded
- Removed duplicate "Sending to..." log messages in `PlatformService`.
- Correctly pass stats dictionary keys when calling `platform.format_header`.

### Removed
- Removed unused `--debug` command-line argument. Debug mode is controlled via the `DEBUG` environment variable.
- Removed unused `build_content_summary_parts` and `join_content_parts` functions from `format_utils.py`.

## [1.3.0] 2025-04-07

### Added
- Ability to mention roles in Discord via `MENTION_ROLE_ID`

## [1.2.0] 2025-04-07

### Added
- Premiere count to the subheader
- Ability to switch between 12/24 hr format via `USE_24_HOUR` variable
- Ability to hide times via `DISPLAY_TIME` variable
- Ability to hide date range from the header via `SHOW_DATE_RANGE` variable
- Daily/Weekly mode toggle, set using `SCHEDULE_TYPE`
- `RUN_TIME` variable for setting time of day
- Improved logging. Now outputs to a log file. Featuring lots of Emojis because I'm basic like that 
- Debug mode
- Healthchecks
- Passed event handling along with a shiney new `PASSED_EVENT_HANDLING` env variable
- Better docstrings


### Refactored
- Broke large segments down into smaller functions to make it more "Pythonic"
- We now are using a small Flask app w/ exposed port to keep the container alive and using apscheduler instead of cron jobs for more reliability
- Dataclasses and Abstraction


### Fixed
- `START_WEEK_ON_MONDAY: false` was not being respected
- Issue with different timezones not displaying the correct times/dates




## [1.1.0] - 2025-04-04

### Added
- Multi-architecture Docker image support (amd64, arm64)
- Batch processing to handle Discord's embed limits
- Support for Slack messages
- slack-manifest.yml file

### Changed
- Optimized Docker image size using Python slim base image

### Fixed
- Properly handle various episode naming formats
- Error handling for API connection issues


## [1.0.0] - 2025-04-04

### Added
- Initial release of Calendarr
- Discord webhook integration for Sonarr and Radarr calendars
- Weekly TV and movie release schedule formatting
- Customizable header and date range options
- Special formatting for premieres and finales