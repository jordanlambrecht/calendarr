#!/usr/bin/env python3

from constants import NO_NEW_RELEASES_MSG

def pluralize(word: str, count: int, plural: str = None) -> str:
    """Return singular or plural form based on count"""
    if plural is None:
        plural = word + "s"
    return word if count == 1 else plural

def apply_formatting(text, format_type, platform):
  """Apply platform-specific formatting"""
  if format_type == "strikethrough":
      return f"~~{text}~~" if platform == "discord" else f"~{text}~"
  elif format_type == "bold":
      return f"**{text}**" if platform == "discord" else f"*{text}*"
  return text

def process_movie_event(summary):
    """Format movie event for display"""
    return f"🎬  **{summary}**"

def count_premieres(days_data):
    """Count the number of season premieres in the data"""
    premiere_count = 0
    for day_content in days_data.values():
        for tv_item in day_content["tv"]:
            if "🎉" in tv_item:
                premiere_count += 1
    return premiere_count

def count_events_by_type(events):
    """Count TV episodes and movies in events"""
    tv_count = sum(1 for e in events if e.get("SOURCE_TYPE") == "tv")
    movie_count = sum(1 for e in events if e.get("SOURCE_TYPE") == "movie")
    
    return tv_count, movie_count


def build_content_summary_parts(tv_count, movie_count, premiere_count, platform="discord"):
    """
    Build the content summary parts with counts and emojis
    
    Args:
        tv_count: Number of TV episodes
        movie_count: Number of movie releases
        premiere_count: Number of premieres
        platform: 'discord' or 'slack' to control emoji spacing
        
    Returns:
        List of strings with formatted content parts
    """
    # Different platforms need different spacing after emojis
    emoji_spacing = "  " if platform == "slack" else " "
    
    parts = []
    # Add TV shows count if any
    if tv_count > 0:
        shows_text = pluralize("episode", tv_count)
        parts.append(f"📺{emoji_spacing}{tv_count} all-new {shows_text}")
    
    # Add movies if any
    if movie_count > 0:
        movies_text = pluralize("movie release", movie_count)
        parts.append(f"🎬{emoji_spacing}{movie_count} {movies_text}")
    
    # Add premieres if any
    if premiere_count > 0:
        premiere_text = pluralize("premiere", premiere_count)
        parts.append(f"🎉{emoji_spacing}{premiere_count} season {premiere_text}")
    
    return parts

def join_content_parts(parts, platform="discord"):
    """
    Join content parts with appropriate separators and formatting
    
    Args:
        parts: List of content summary parts
        platform: 'discord' or 'slack' for platform-specific formatting
        
    Returns:
        Formatted string with all parts joined
    """
    if not parts:
        return NO_NEW_RELEASES_MSG
    
    # Different bold syntax for different platforms
    bold_start = "*" if platform == "slack" else "**"
    bold_end = "*" if platform == "slack" else "**"
    
    if len(parts) == 1:
        return f"{bold_start}{parts[0]}{bold_end}"
    elif len(parts) == 2:
        return f"{bold_start}{parts[0]} and {parts[1]}{bold_end}"
    else:
        # Join all but last with commas, then add the last with "and"
        return f"{bold_start}{', '.join(parts[:-1])}, and {parts[-1]}{bold_end}"

def format_header_text(custom_header: str, start_date, end_date, show_date_range: bool) -> str:
    """
    Create a formatted header text with optional date range
    """
    header_text = f"# {custom_header}"
    
    if show_date_range:
        # Check if we're in daily mode (start and end date are the same day)
        if start_date.date() == end_date.date():
            # For daily mode, show just the day name and date
            header_text += f" ({start_date.strftime('%A, %b %d')})"
        else:
            # For weekly mode, show the range as before
            header_text += f" ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')})"
    
    return header_text


def format_subheader_text(tv_count: int, movie_count: int, premiere_count: int) -> str:
    """
    Format the subheader text showing counts of content
    """
    # Determine if there are any events at all
    if tv_count == 0 and movie_count == 0:
        # No events at all
        return "**No new releases. Maybe it's a good day to take a walk?**\n\n"
    
    # Handle pluralization
    shows_text = "episode" if tv_count == 1 else "episodes"
    movies_text = "movie release" if movie_count == 1 else "movie releases"
    
    # Simplify subheader construction
    subheader_parts = []

    # Add TV shows count
    if tv_count > 0:
        subheader_parts.append(f"📺 {tv_count} all-new {shows_text}")

    # Add movies if any
    if movie_count > 0:
        subheader_parts.append(f"🎬 {movie_count} {movies_text}")

    # Add premieres if any
    if premiere_count > 0:
        premiere_text = "premiere" if premiere_count == 1 else "premieres"
        subheader_parts.append(f"🎉 {premiere_count} season {premiere_text}")

    # Join with appropriate separators
    if len(subheader_parts) == 1:
        subheader = f"**{subheader_parts[0]}**"
    elif len(subheader_parts) == 2:
        subheader = f"**{subheader_parts[0]} and {subheader_parts[1]}**"
    else:
        # Join all but last with commas, then add the last with "and"
        subheader = f"**{', '.join(subheader_parts[:-1])}, and {subheader_parts[-1]}**"

    return subheader + "\n\n"  # Add line break