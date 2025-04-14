#!/bin/sh
# entrypoint.sh

# Define source (in image) and destination (volume mount point)
DEFAULT_FOOTERS_DIR="/app/default_footers"
CUSTOM_FOOTERS_DIR="/app/custom_footers"

# Ensure the custom footers directory exists and is mounted
mkdir -p "$CUSTOM_FOOTERS_DIR"

echo "Checking for custom footer files in $CUSTOM_FOOTERS_DIR..."

# Check and copy discord_footer.md if it doesn't exist in the volume
if [ ! -f "$CUSTOM_FOOTERS_DIR/discord_footer.md" ]; then
  if [ -f "$DEFAULT_FOOTERS_DIR/discord_footer.md" ]; then
    echo "Copying default discord_footer.md to $CUSTOM_FOOTERS_DIR..."
    cp "$DEFAULT_FOOTERS_DIR/discord_footer.md" "$CUSTOM_FOOTERS_DIR/discord_footer.md"
  else
    echo "Warning: Default discord_footer.md not found in $DEFAULT_FOOTERS_DIR."
  fi
else
  echo "Found existing discord_footer.md in $CUSTOM_FOOTERS_DIR."
fi

# Check and copy slack_footer.md if it doesn't exist in the volume
if [ ! -f "$CUSTOM_FOOTERS_DIR/slack_footer.md" ]; then
  if [ -f "$DEFAULT_FOOTERS_DIR/slack_footer.md" ]; then
    echo "Copying default slack_footer.md to $CUSTOM_FOOTERS_DIR..."
    cp "$DEFAULT_FOOTERS_DIR/slack_footer.md" "$CUSTOM_FOOTERS_DIR/slack_footer.md"
  else
    echo "Warning: Default slack_footer.md not found in $DEFAULT_FOOTERS_DIR."
  fi
else
  echo "Found existing slack_footer.md in $CUSTOM_FOOTERS_DIR."
fi

echo "Starting application..."
exec "$@"
