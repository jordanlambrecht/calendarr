#!/usr/bin/env python3
# src/utils/format_utils.py

# TODO: This file needs more debug logging eventually
from typing import Dict, List
from constants import NO_NEW_RELEASES_MSG, COLOR_PALETTE

from utils.date_utils import get_days_order


def pluralize(word: str, count: int, plural: str = None) -> str:
    """
    Return singular or plural form based on count
    
    Args:
        word: Singular form
        count: Count to determine plurality
        plural: Optional custom plural form
        
    Returns:
        Appropriate form based on count
    """
    if plural is None:
        plural = word + "s"
    return word if count == 1 else plural





def build_content_summary_parts(tv_count: int, movie_count: int, 
                               premiere_count: int, platform: str = "discord") -> List[str]:
    """
    Build the content summary parts with counts and emojis
    
    Args:
        tv_count: Number of TV episodes
        movie_count: Number of movie releases
        premiere_count: Number of premieres
        platform: Platform name for formatting
        
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


def join_content_parts(parts: List[str], platform: str = "discord") -> str:
    """
    Join content parts with appropriate separators and formatting
    
    Args:
        parts: List of content summary parts
        platform: Platform name for formatting
        
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


def format_header_text(custom_header: str, start_date, end_date, 
                      show_date_range: bool) -> str:
    """
    Create a formatted header text with optional date range
    
    Args:
        custom_header: Header text
        start_date: Start date
        end_date: End date
        show_date_range: Whether to show date range
        
    Returns:
        Formatted header text
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
    
    Args:
        tv_count: Number of TV episodes
        movie_count: Number of movie releases
        premiere_count: Number of premieres
        
    Returns:
        Formatted subheader text
    """
    # Determine if there are any events at all
    if tv_count == 0 and movie_count == 0:
        # No events at all
        return "**No new releases. Maybe it's a good day to take a walk?**\n\n"
    
    subheader_parts = []

    # Add TV shows count
    if tv_count > 0:
        shows_text = pluralize("episode", tv_count)
        subheader_parts.append(f"📺 {tv_count} all-new {shows_text}")

    # Add movies if any
    if movie_count > 0:
        movies_text = pluralize("movie release", movie_count)
        subheader_parts.append(f"🎬 {movie_count} {movies_text}")

    # Add premieres if any
    if premiere_count > 0:
        premiere_text = pluralize("premiere", premiere_count)
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


def get_day_colors(platform: str, start_week_on_monday: bool = True) -> Dict:
    """
    Get ROYGBIV color mapping for days of the week
    
    Args:
        platform: Platform name
        start_week_on_monday: Whether week starts on Monday
        
    Returns:
        Dictionary mapping day names to color codes
    """    

    days_order = get_days_order(start_week_on_monday)

    color_order = ["red", "orange", "yellow", "green", "blue", "indigo", "violet"]

    day_colors = {}
    for i, day in enumerate(days_order):
        color_name = color_order[i % len(color_order)]
        day_colors[day] = COLOR_PALETTE[platform.lower()][color_name]
    
    return day_colors

