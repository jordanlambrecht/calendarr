# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- Dataclasses


### Fixed
- `START_WEEK_ON_MONDAY: false` was not being respected
- Issue with different timezones not displaying the correct times/dates

### Removed



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