#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Core Analysis Module for Spotify Rediscovery Analyzer
"""

import json
import os
import sys
import math
import glob
from typing import List, Dict, Tuple, Optional, Union
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone


# Constants for analysis thresholds
MIN_MS = 0
SPIKE_Z = 2.0
SPIKE_MIN_PLAYS = 60
DROP_PEAK_SHARE = 0.40
DROP_RECENT_SILENCE_M = 24
DROP_PEAK_MIN_PLAYS = 20
GRIP_MIN_HOURS = 3.0
GRIP_DORMANT_YEARS = 2
ALBUM_DOMINANCE = 0.80
ALBUM_MIN_MONTH_PLAYS = 20
ALBUM_CONCENTRATION = 0.70
TOP_N = 100


def parse_ts(ts: Optional[str]) -> Optional[datetime]:
    """
    Parse a timestamp string into a timezone-aware datetime.

    Args:
        ts (str, optional): Timestamp string

    Returns:
        datetime or None: Parsed datetime in UTC, or None if parsing fails
    """
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        # Ensure timezone-aware (UTC) if input lacked tzinfo
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def is_podcast(row: Dict[str, str]) -> bool:
    """
    Check if a row represents a podcast entry.

    Args:
        row (dict): Streaming history row

    Returns:
        bool: True if the row is a podcast, False otherwise
    """
    return bool(row.get("episode_name") or row.get("episode_show_name"))


def safe_meta(row: Dict[str, str]) -> Tuple[str, str, str]:
    """
    Extract safe metadata from a streaming history row.

    Args:
        row (dict): Streaming history row

    Returns:
        tuple: (track, album, artist) with empty strings as fallbacks
    """
    track = row.get("master_metadata_track_name") or ""
    album = row.get("master_metadata_album_album_name") or ""
    artist = row.get("master_metadata_album_artist_name") or ""
    return track, album, artist


def month_key(dt: datetime) -> str:
    """
    Generate a consistent month key for a datetime.

    Args:
        dt (datetime): Input datetime

    Returns:
        str: Month key in 'YYYY-MM' format (UTC)
    """
    return dt.astimezone(timezone.utc).strftime("%Y-%m")


def expand_files(path: str) -> List[str]:
    """
    Expand a file path or directory to a list of JSON files.

    Args:
        path (str): Path to a directory or file pattern

    Returns:
        list: Sorted list of JSON file paths
    """
    if os.path.isdir(path):
        return sorted(glob.glob(os.path.join(path, "*.json")))
    else:
        return sorted(glob.glob(path))


def load_rows(files: List[str]) -> List[Dict[str, Union[str, int]]]:
    """
    Load streaming history rows from JSON files.

    Args:
        files (list): List of file paths to read

    Returns:
        list: Aggregated list of streaming history rows
    """
    rows = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    rows.extend(data)
        except Exception as e:
            sys.stderr.write(f"[WARN] failed to read {f}: {e}\n")
    return rows


def filter_music_rows(
    rows: List[Dict[str, Union[str, int]]],
    min_ms: int = MIN_MS,
    exclude_podcasts: bool = False
) -> List[Dict[str, Union[str, int, datetime]]]:
    """
    Filter and process music rows based on given criteria.

    Args:
        rows (list): Raw streaming history rows
        min_ms (int, optional): Minimum milliseconds played. Defaults to 0.
        exclude_podcasts (bool, optional): Whether to exclude podcast rows. Defaults to False.

    Returns:
        list: Processed and filtered music rows
    """
    music = []
    for r in rows:
        if exclude_podcasts and is_podcast(r):
            continue
        
        ms = int(r.get("ms_played") or 0)
        if ms < min_ms:
            continue
        
        track, album, artist = safe_meta(r)
        ts = parse_ts(r.get("ts"))
        
        if not ts:
            continue
        
        music.append({
            "ts": ts,
            "ms": ms,
            "track": track,
            "album": album,
            "artist": artist,
            "plays": 1  # Add a plays attribute for counting
        })
    
    return music


def compute_artist_stats(music: List[Dict[str, Union[str, int, datetime]]]):
    """
    Compute various artist-level statistics from music listening history.

    Args:
        music (list): Processed music rows

    Returns:
        dict: Comprehensive artist statistics
    """
    artist_month_counts = defaultdict(Counter)
    album_month_counts = defaultdict(Counter)
    artist_last_play = {}
    album_last_play = {}
    artist_first_play = {}
    artist_month_total_counts = defaultdict(Counter)
    artist_total_ms = defaultdict(int)

    for m in music:
        mk = month_key(m["ts"])
        a = m["artist"] or "<unknown>"
        al = m["album"] or "<unknown>"

        artist_month_counts[a][mk] += m.get("plays", 1)
        album_month_counts[(a, al)][mk] += m.get("plays", 1)
        artist_month_total_counts[a][mk] += m.get("plays", 1)
        artist_total_ms[a] += m["ms"]

        zero_dt = datetime.min.replace(tzinfo=timezone.utc)
        artist_last_play[a] = max(artist_last_play.get(a, zero_dt), m["ts"])
        album_last_play[(a, al)] = max(album_last_play.get((a, al), zero_dt), m["ts"])
        artist_first_play[a] = min(artist_first_play.get(a, datetime.max.replace(tzinfo=timezone.utc)), m["ts"])

    return {
        "artist_month_counts": artist_month_counts,
        "album_month_counts": album_month_counts,
        "artist_last_play": artist_last_play,
        "album_last_play": album_last_play,
        "artist_first_play": artist_first_play,
        "artist_month_total_counts": artist_month_total_counts,
        "artist_total_ms": artist_total_ms
    }


def zscore_series(counter: Counter, all_months: List[str]) -> Dict[str, Tuple[int, float]]:
    """
    Compute z-scores for a monthly counter series.

    Args:
        counter (Counter): Monthly play counts
        all_months (list): Sorted list of all months

    Returns:
        dict: Monthly z-scores with play counts
    """
    vals = [counter[m] for m in all_months]
    if not vals:
        return {}
    
    mu = sum(vals) / len(vals)
    var = sum((v - mu)**2 for v in vals) / len(vals) if len(vals) > 1 else 0.0
    sd = math.sqrt(var)
    
    return {m: (counter[m], 0.0 if sd == 0 else (counter[m] - mu) / sd) for m in all_months}


def analyze_spikes(
    artist_month_counts: Dict[str, Counter], 
    album_month_counts: Dict[Tuple[str, str], Counter]
):
    """
    Detect listening spikes for artists and albums.

    Args:
        artist_month_counts (dict): Monthly play counts per artist
        album_month_counts (dict): Monthly play counts per album

    Returns:
        tuple: (artist_spikes, album_spikes)
    """
    all_months = sorted({month for counts in artist_month_counts.values() for month in counts})

    spikes_artist = []
    for artist, monthly in artist_month_counts.items():
        for m, (v, z) in zscore_series(monthly, all_months).items():
            if v >= SPIKE_MIN_PLAYS and z >= SPIKE_Z:
                spikes_artist.append((m, artist, v, round(z, 2)))
    spikes_artist.sort(key=lambda x: (x[0], -x[2]))

    spikes_album = []
    for key, monthly in album_month_counts.items():
        for m, (v, z) in zscore_series(monthly, all_months).items():
            if v >= max(5, SPIKE_MIN_PLAYS // 2) and z >= SPIKE_Z:
                artist, album = key
                spikes_album.append((m, artist, album, v, round(z, 2)))
    spikes_album.sort(key=lambda x: (x[0], -x[3]))

    return spikes_artist, spikes_album


def months_since(dt: datetime) -> int:
    """
    Calculate months since a given datetime.

    Args:
        dt (datetime): Reference datetime

    Returns:
        int: Number of months since the reference datetime
    """
    now = datetime.now(timezone.utc)
    return (now.year - dt.year) * 12 + (now.month - dt.month)


def qualifies_dropoff(
    counter: Counter, 
    last_play_dt: Optional[datetime]
) -> Optional[Tuple[str, int, int]]:
    """
    Determine if an artist or album qualifies as a drop-off.

    Args:
        counter (Counter): Monthly play counts
        last_play_dt (datetime, optional): Last play datetime

    Returns:
        tuple or None: (peak_month, peak_plays, lifetime_plays) if qualifies
    """
    lifetime = sum(counter.values())
    if lifetime == 0:
        return None
    
    peak_m, peak_v = max(counter.items(), key=lambda kv: kv[1])
    
    if peak_v < DROP_PEAK_MIN_PLAYS:
        return None
    
    if peak_v < DROP_PEAK_SHARE * lifetime:
        return None
    
    if last_play_dt and months_since(last_play_dt) >= DROP_RECENT_SILENCE_M:
        return (peak_m, peak_v, lifetime)
    
    return None


def analyze_dropoffs(
    artist_month_counts: Dict[str, Counter], 
    album_month_counts: Dict[Tuple[str, str], Counter],
    artist_last_play: Dict[str, datetime],
    album_last_play: Dict[Tuple[str, str], datetime]
):
    """
    Analyze drop-offs for artists and albums.

    Args:
        artist_month_counts (dict): Monthly play counts per artist
        album_month_counts (dict): Monthly play counts per album
        artist_last_play (dict): Last play datetime per artist
        album_last_play (dict): Last play datetime per album

    Returns:
        tuple: (drop_artists, drop_albums)
    """
    drop_artists = []
    for artist, monthly in artist_month_counts.items():
        res = qualifies_dropoff(monthly, artist_last_play.get(artist))
        if res:
            peak_m, peak_v, lifetime = res
            share = peak_v / lifetime
            drop_artists.append((artist, peak_m, peak_v, lifetime, round(share, 2)))
    drop_artists.sort(key=lambda x: (x[1], -x[4]))

    drop_albums = []
    for key, monthly in album_month_counts.items():
        res = qualifies_dropoff(monthly, album_last_play.get(key))
        if res:
            peak_m, peak_v, lifetime = res
            a, al = key
            share = peak_v / lifetime
            drop_albums.append((a, al, peak_m, peak_v, lifetime, round(share, 2)))
    drop_albums.sort(key=lambda x: (x[2], -x[5]))

    return drop_artists, drop_albums


def analyze_dormant_artists(
    artist_total_ms: Dict[str, int], 
    artist_last_play: Dict[str, datetime]
):
    """
    Identify artists that were once heavily listened to but are now dormant.

    Args:
        artist_total_ms (dict): Total milliseconds listened per artist
        artist_last_play (dict): Last play datetime per artist

    Returns:
        list: Dormant artists with their stats
    """
    now = datetime.now(timezone.utc)
    grip_artists = []
    
    for a, ms_sum in artist_total_ms.items():
        last_dt = artist_last_play.get(a, datetime.min.replace(tzinfo=timezone.utc))
        dormant_years = (now - last_dt).days / 365.25 if last_dt else 100.0
        
        if (ms_sum/1000/60/60) >= GRIP_MIN_HOURS and dormant_years >= GRIP_DORMANT_YEARS:
            grip_artists.append((
                a, 
                round(ms_sum/1000/60/60, 2), 
                round(dormant_years, 1), 
                last_dt.date().isoformat()
            ))
    
    grip_artists.sort(key=lambda x: (-x[2], -x[1], x[0]))
    return grip_artists


def analyze_one_album_obsessions(
    music: List[Dict[str, Union[str, int, datetime]]],
    artist_month_total_counts: Dict[str, Counter],
    album_month_counts: Dict[Tuple[str, str], Counter]
):
    """
    Identify one-album obsessions.

    Args:
        music (list): Processed music rows
        artist_month_total_counts (dict): Monthly total plays per artist
        album_month_counts (dict): Monthly play counts per album

    Returns:
        list: One-album obsessions
    """
    album_datetimes = defaultdict(list)
    for m in music:
        a = m["artist"] or "<unknown>"
        al = m["album"] or "<unknown>"
        album_datetimes[(a, al)].append(m["ts"])

    one_album = []
    for a, month_counts in artist_month_total_counts.items():
        for mk, artist_month_total in month_counts.items():
            if artist_month_total < ALBUM_MIN_MONTH_PLAYS:
                continue
            
            dominant_album = None
            dominant_plays = 0
            
            for (aa, al), counts in album_month_counts.items():
                if aa != a:
                    continue
                
                p = counts.get(mk, 0)
                if p > dominant_plays:
                    dominant_plays = p
                    dominant_album = al
            
            if dominant_album and dominant_plays / artist_month_total >= ALBUM_DOMINANCE:
                times = sorted(album_datetimes[(a, dominant_album)])
                i = 0
                best = 0
                
                for j in range(len(times)):
                    while times[j] - times[i] > timedelta(days=60):
                        i += 1
                    best = max(best, j - i + 1)
                
                life = sum(album_month_counts[(a, dominant_album)].values())
                
                if life > 0 and best / life >= ALBUM_CONCENTRATION:
                    one_album.append((
                        mk, a, dominant_album, dominant_plays, 
                        artist_month_total, life, round(best/life, 2)
                    ))

    # Remove duplicates while preserving order
    seen = set()
    filtered = []
    for row in sorted(one_album, key=lambda x: x[0]):
        key = (row[1], row[2])
        if key in seen:
            continue
        seen.add(key)
        filtered.append(row)

    return filtered