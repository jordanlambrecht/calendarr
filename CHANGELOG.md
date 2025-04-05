# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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