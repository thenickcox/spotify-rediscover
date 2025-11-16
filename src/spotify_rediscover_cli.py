#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Spotify Rediscovery Analyzer (CLI)

Adds `--html report.html` to write a beautiful, sortable HTML report
with all tables (spikes, drop-offs, dormant, one-album obsessions, top artists).
"""

import argparse
import os
import sys
import logging
from typing import Optional, List

from .spotify_analysis import (
    expand_files,
    load_rows,
    filter_music_rows,
    compute_artist_stats,
    analyze_spikes,
    analyze_dropoffs,
    analyze_dormant_artists,
    analyze_one_album_obsessions,
    TOP_N,
    parse_ts,
    month_key,
    is_podcast,
    safe_meta
)
from .html_report import generate_html_report as build_html
from .html_report import generate_html_report


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        verbose (bool, optional): Enable verbose logging. Defaults to False.

    Returns:
        logging.Logger: Configured logger
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler('spotify_rediscover.log', mode='w')
        ]
    )
    return logging.getLogger(__name__)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments for the Spotify Rediscovery Analyzer.

    Args:
        argv (list, optional): List of command-line arguments. Defaults to None.

    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    ap = argparse.ArgumentParser(description="Spotify Rediscovery Analyzer")
    ap.add_argument("path", help="Directory or glob for StreamingHistory*.json")
    ap.add_argument("--min-ms", type=int, default=0, help="Minimum ms_played to include (default 0)")
    ap.add_argument("--exclude-podcasts", action="store_true", help="Exclude podcast rows")
    ap.add_argument("--top", type=int, default=10, help="Top N for the all-time list (default 10)")
    ap.add_argument("--html", type=str, default=None, help="Write a full HTML report to this path")
    ap.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return ap.parse_args(argv)


def print_h(title: str) -> None:
    """
    Print a header with a title.

    Args:
        title (str): Header title
    """
    line = "=" * 80
    print("\n" + line)
    print(title)
    print(line)


def hours(ms: int) -> float:
    """
    Convert milliseconds to hours.

    Args:
        ms (int): Milliseconds

    Returns:
        float: Hours
    """
    return ms / 1000 / 60 / 60.0


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the Spotify Rediscovery Analyzer.

    Args:
        argv (list, optional): Command-line arguments. Defaults to None.

    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    try:
        # Parse arguments
        args = parse_args(argv)

        # Setup logging
        logger = setup_logging(args.verbose)
        logger.info("Starting Spotify Rediscovery Analyzer")

        # Expand and load files
        files = expand_files(args.path)
        if not files:
            print("No JSON files found.", file=sys.stderr)
            logger.error("No JSON files found.")
            sys.exit(2)

        # Load and filter rows
        rows = load_rows(files)
        music = filter_music_rows(rows, args.min_ms, args.exclude_podcasts)

        if not music:
            logger.warning("No qualifying music rows after filters.")
            return 0

        # Compute total statistics
        total_ms = sum(m["ms"] for m in music)
        artists_count = {artist: sum(m["plays"] for m in music if m["artist"] == artist)
                         for artist in set(m["artist"] for m in music if m["artist"])}
        artists_count = dict(sorted(artists_count.items(), key=lambda x: x[1], reverse=True))

        # Console output: Top artists
        print_h("Top artists (all time) — by plays")
        for i, (artist, plays) in enumerate(list(artists_count.items())[:args.top], start=1):
            print(f"{i:>2}. {artist}  ({plays} plays)")
        print("\n(Full results saved to HTML if --html was provided.)")

        # Compute detailed artist statistics
        stats = compute_artist_stats(music)

        # Analyze various aspects of listening history
        spikes_artist, spikes_album = analyze_spikes(
            stats["artist_month_counts"], 
            stats["album_month_counts"]
        )

        drop_artists, drop_albums = analyze_dropoffs(
            stats["artist_month_counts"], 
            stats["album_month_counts"],
            stats["artist_last_play"], 
            stats["album_last_play"]
        )

        grip_artists = analyze_dormant_artists(
            stats["artist_total_ms"], 
            stats["artist_last_play"]
        )

        one_album = analyze_one_album_obsessions(
            music, 
            stats["artist_month_total_counts"], 
            stats["album_month_counts"]
        )

        # Generate HTML report if requested
        if args.html:
            title = "Spotify Rediscovery Report"
            params = {
                "Files": str(len(files)),
                "Min ms": str(args.min_ms),
                "Exclude podcasts": str(args.exclude_podcasts),
                "Top artists shown in console": str(args.top),
            }
            
            sections = [
                # Top artists (all-time) — capped
                ("Top artists — all time (by plays, capped at {TOP_N})",
                 "Your lifetime listening, descending by play count.",
                 ["#", "Artist", "Plays"],
                 [(i+1, a, plays) for i, (a, plays) in enumerate(list(artists_count.items())[:TOP_N])]),

                # Spikes
                ("Highest‑intensity single‑month spikes — Artist",
                 "Detected via monthly play-count z-scores; unusually high, short-lived peaks.",
                 ["Month", "Artist", "Plays", "z"],
                 spikes_artist),

                ("Highest‑intensity single‑month spikes — Album",
                 "Detected via monthly play-count z-scores; unusually high, short-lived peaks.",
                 ["Month", "Artist", "Album", "Plays", "z"],
                 spikes_album),

                # Drop-offs
                ("Massive peak → total drop‑off — Artists",
                 f"Peak month ≥ {int(100 * 0.40)}% of lifetime plays, peak month ≥ 20 plays, and no plays in the last 24 months.",
                 ["Peak Month", "Artist", "Peak Plays", "Lifetime Plays", "Peak Share %"],
                 [(pm, a, pv, life, int(100 * pv / life)) for (a, pm, pv, life, share) in drop_artists]),

                ("Massive peak → total drop‑off — Albums",
                 f"Peak month ≥ {int(100 * 0.40)}% of lifetime plays, peak month ≥ 20 plays, and no plays in the last 24 months.",
                 ["Peak Month", "Artist", "Album", "Peak Plays", "Lifetime Plays", "Peak Share %"],
                 [(pm, a, al, pv, life, int(100 * pv / life)) for (a, al, pm, pv, life, share) in drop_albums]),

                # Dormant
                ("Had a grip on you, now dormant",
                 f"Artists with ≥3 hours lifetime and no plays in ≥2 years.",
                 ["Artist", "Hours (lifetime)", "Dormant ~years", "Last Played"],
                 grip_artists),

                # One-album obsessions
                ("One‑album obsessions",
                 f"In a month, one album was ≥{int(100 * 0.80)}% of that artist's plays AND ≥{int(100 * 0.70)}% of the album's lifetime plays fell within 60 days.",
                 ["Month", "Artist", "Album", "Month Plays (album)", "Month Plays (artist)", "Lifetime Plays (album)", "60‑day Concentration %"],
                 one_album)
            ]

            # Generate and write HTML report
            try:
                html_doc = generate_html_report(title, params, sections)
                with open(args.html, "w", encoding="utf-8") as fh:
                    fh.write(html_doc)
                logger.info(f"Wrote HTML report to: {os.path.abspath(args.html)}")
                print(f"\nWrote HTML report to: {os.path.abspath(args.html)}")
            except IOError as e:
                logger.error(f"Failed to write HTML report: {e}")
                return 1

        # Footer
        print_h("Summary")
        print(f"Files read: {len(files)}; music rows: {len(music)}; total hours: {hours(total_ms):.1f}")
        print("Done.")
        
        logger.info("Spotify Rediscovery Analyzer completed successfully")
        return 0

    except Exception as e:
        logger.exception("Unexpected error occurred")
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
