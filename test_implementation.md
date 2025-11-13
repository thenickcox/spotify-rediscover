# Test Implementation Plan for spotify_rediscover_cli.py

This document provides detailed implementation plans for each test file in our test suite.

## 1. conftest.py

This file will contain shared fixtures for all tests.

```python
import json
import os
import pytest
from unittest.mock import mock_open, patch
from datetime import datetime, timezone

# Mock data fixtures
@pytest.fixture
def valid_music_data():
    return [
        {
            "ts": "2023-01-15T14:30:45Z",
            "ms_played": 240000,
            "master_metadata_track_name": "Song Title 1",
            "master_metadata_album_album_name": "Album Name 1",
            "master_metadata_album_artist_name": "Artist Name 1"
        },
        {
            "ts": "2023-01-15T15:00:00Z",
            "ms_played": 180000,
            "master_metadata_track_name": "Song Title 2",
            "master_metadata_album_album_name": "Album Name 1",
            "master_metadata_album_artist_name": "Artist Name 1"
        },
        {
            "ts": "2023-02-20T10:15:30Z",
            "ms_played": 300000,
            "master_metadata_track_name": "Song Title 3",
            "master_metadata_album_album_name": "Album Name 2",
            "master_metadata_album_artist_name": "Artist Name 2"
        }
    ]

@pytest.fixture
def podcast_data():
    return [
        {
            "ts": "2023-03-10T08:45:00Z",
            "ms_played": 1800000,
            "episode_name": "Podcast Episode 1",
            "episode_show_name": "Podcast Show 1"
        },
        {
            "ts": "2023-03-15T14:20:00Z",
            "ms_played": 2400000,
            "episode_name": "Podcast Episode 2",
            "episode_show_name": "Podcast Show 1"
        }
    ]

@pytest.fixture
def mixed_data(valid_music_data, podcast_data):
    return valid_music_data + podcast_data

@pytest.fixture
def empty_data():
    return []

@pytest.fixture
def invalid_data():
    return "This is not valid JSON"

@pytest.fixture
def mock_file_system(valid_music_data, podcast_data, mixed_data, empty_data, monkeypatch):
    """Mock file system with predefined JSON files"""
    
    def mock_glob(pattern):
        if "*.json" in pattern:
            if os.path.join("test_dir", "*.json") in pattern:
                return [
                    os.path.join("test_dir", "file1.json"),
                    os.path.join("test_dir", "file2.json")
                ]
            elif "pattern*.json" in pattern:
                return [
                    "pattern1.json",
                    "pattern2.json"
                ]
            else:
                return ["file1.json"]
        return []
    
    def mock_isdir(path):
        return "test_dir" in path
    
    def mock_open_file(file_path, *args, **kwargs):
        if "file1.json" in file_path:
            return mock_open(read_data=json.dumps(valid_music_data))()
        elif "file2.json" in file_path:
            return mock_open(read_data=json.dumps(podcast_data))()
        elif "mixed.json" in file_path:
            return mock_open(read_data=json.dumps(mixed_data))()
        elif "empty.json" in file_path:
            return mock_open(read_data=json.dumps(empty_data))()
        elif "invalid.json" in file_path:
            return mock_open(read_data=invalid_data)()
        else:
            raise FileNotFoundError(f"Mock file not found: {file_path}")
    
    # Apply patches
    monkeypatch.setattr("glob.glob", mock_glob)
    monkeypatch.setattr("os.path.isdir", mock_isdir)
    
    # Return the mock_open_file function for patching open in tests
    return mock_open_file
```

## 2. test_argument_parsing.py

Tests for the `parse_args` function.

```python
import pytest
import sys
from spotify_rediscover_cli import parse_args

def test_parse_args_default():
    """Test parse_args with default values"""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "argv", ["spotify_rediscover_cli.py", "test_dir"])
        args = parse_args()
        assert args.path == "test_dir"
        assert args.min_ms == 0
        assert args.exclude_podcasts is False
        assert args.top == 10
        assert args.html is None

def test_parse_args_all_options():
    """Test parse_args with all options specified"""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "argv", [
            "spotify_rediscover_cli.py",
            "test_dir",
            "--min-ms", "30000",
            "--exclude-podcasts",
            "--top", "20",
            "--html", "report.html"
        ])
        args = parse_args()
        assert args.path == "test_dir"
        assert args.min_ms == 30000
        assert args.exclude_podcasts is True
        assert args.top == 20
        assert args.html == "report.html"

def test_parse_args_custom_argv():
    """Test parse_args with custom argv parameter"""
    custom_argv = [
        "spotify_rediscover_cli.py",
        "custom_dir",
        "--min-ms", "60000",
        "--top", "5"
    ]
    args = parse_args(custom_argv)
    assert args.path == "custom_dir"
    assert args.min_ms == 60000
    assert args.exclude_podcasts is False
    assert args.top == 5
    assert args.html is None
```

## 3. test_file_handling.py

Tests for the `expand_files` and `load_rows` functions.

```python
import pytest
import os
from unittest.mock import patch
from spotify_rediscover_cli import expand_files, load_rows

def test_expand_files_directory(mock_file_system):
    """Test expand_files with a directory path"""
    with patch("os.path.isdir", return_value=True):
        files = expand_files("test_dir")
        assert len(files) == 2
        assert os.path.join("test_dir", "file1.json") in files
        assert os.path.join("test_dir", "file2.json") in files

def test_expand_files_pattern(mock_file_system):
    """Test expand_files with a glob pattern"""
    with patch("os.path.isdir", return_value=False):
        files = expand_files("pattern*.json")
        assert len(files) == 2
        assert "pattern1.json" in files
        assert "pattern2.json" in files

def test_load_rows_valid_files(mock_file_system):
    """Test load_rows with valid JSON files"""
    with patch("builtins.open", mock_file_system):
        files = ["file1.json", "file2.json"]
        rows = load_rows(files)
        assert len(rows) == 5  # 3 music + 2 podcast entries

def test_load_rows_empty_file(mock_file_system):
    """Test load_rows with an empty JSON file"""
    with patch("builtins.open", mock_file_system):
        rows = load_rows(["empty.json"])
        assert len(rows) == 0

def test_load_rows_invalid_file(mock_file_system, capsys):
    """Test load_rows with an invalid JSON file"""
    with patch("builtins.open", mock_file_system):
        rows = load_rows(["invalid.json"])
        assert len(rows) == 0
        captured = capsys.readouterr()
        assert "failed to read" in captured.err

def test_load_rows_missing_file(mock_file_system, capsys):
    """Test load_rows with a missing file"""
    with patch("builtins.open", mock_file_system):
        rows = load_rows(["missing.json"])
        assert len(rows) == 0
        captured = capsys.readouterr()
        assert "failed to read" in captured.err
```

## 4. test_datetime.py

Tests for the `parse_ts` and `month_key` functions.

```python
import pytest
from datetime import datetime, timezone, timedelta
from spotify_rediscover_cli import parse_ts, month_key

@pytest.mark.parametrize("timestamp,expected", [
    ("2023-01-15T14:30:45Z", datetime(2023, 1, 15, 14, 30, 45, tzinfo=timezone.utc)),
    ("2023-01-15T14:30:45+00:00", datetime(2023, 1, 15, 14, 30, 45, tzinfo=timezone.utc)),
    ("2023-01-15T09:30:45-05:00", datetime(2023, 1, 15, 14, 30, 45, tzinfo=timezone.utc)),
    (None, None),
    ("invalid", None),
    ("2023-01-15T14:30:45", datetime(2023, 1, 15, 14, 30, 45, tzinfo=timezone.utc)),
])
def test_parse_ts(timestamp, expected):
    """Test parse_ts with various timestamp formats"""
    result = parse_ts(timestamp)
    if expected is None:
        assert result is None
    else:
        assert result == expected
        assert result.tzinfo is not None  # Ensure timezone awareness

def test_month_key():
    """Test month_key function"""
    # Test UTC timestamp
    dt_utc = datetime(2023, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
    assert month_key(dt_utc) == "2023-01"
    
    # Test non-UTC timestamp (should still return UTC-based month)
    offset = timezone(timedelta(hours=-5))  # EST
    dt_est = datetime(2023, 1, 15, 9, 30, 45, tzinfo=offset)
    assert month_key(dt_est) == "2023-01"
    
    # Test month boundary case
    dt_boundary = datetime(2023, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert month_key(dt_boundary) == "2023-02"
```

## 5. test_metadata.py

Tests for the `is_podcast` and `safe_meta` functions.

```python
import pytest
from spotify_rediscover_cli import is_podcast, safe_meta

@pytest.mark.parametrize("row,expected", [
    ({"episode_name": "Episode 1", "episode_show_name": "Show 1"}, True),
    ({"episode_name": "Episode 1"}, True),
    ({"episode_show_name": "Show 1"}, True),
    ({"master_metadata_track_name": "Track"}, False),
    ({}, False),
    ({"episode_name": "", "episode_show_name": ""}, False),
    ({"episode_name": None, "episode_show_name": None}, False),
])
def test_is_podcast(row, expected):
    """Test is_podcast function with various inputs"""
    assert is_podcast(row) == expected

@pytest.mark.parametrize("row,expected", [
    (
        {
            "master_metadata_track_name": "Track Name",
            "master_metadata_album_album_name": "Album Name",
            "master_metadata_album_artist_name": "Artist Name"
        },
        ("Track Name", "Album Name", "Artist Name")
    ),
    (
        {
            "master_metadata_track_name": "",
            "master_metadata_album_album_name": "Album Name",
            "master_metadata_album_artist_name": "Artist Name"
        },
        ("", "Album Name", "Artist Name")
    ),
    (
        {
            "master_metadata_track_name": None,
            "master_metadata_album_album_name": None,
            "master_metadata_album_artist_name": None
        },
        ("", "", "")
    ),
    (
        {},
        ("", "", "")
    ),
])
def test_safe_meta(row, expected):
    """Test safe_meta function with various inputs"""
    assert safe_meta(row) == expected
```

## 6. test_processing.py

Tests for data processing functions like `zscore_series`, `qualifies_dropoff`, etc.

```python
import pytest
import math
from collections import Counter
from datetime import datetime, timezone, timedelta
from spotify_rediscover_cli import zscore_series, qualifies_dropoff, months_since

def test_zscore_series_normal_distribution():
    """Test zscore_series with a normal distribution"""
    months = ["2023-01", "2023-02", "2023-03", "2023-04", "2023-05"]
    counter = Counter({
        "2023-01": 10,
        "2023-02": 15,
        "2023-03": 20,  # peak
        "2023-04": 15,
        "2023-05": 10
    })
    
    result = zscore_series(counter)
    
    # Mean should be 14
    # Variance should be 14
    # Standard deviation should be 3.74
    
    assert len(result) == 5
    assert result["2023-01"][0] == 10
    assert result["2023-03"][0] == 20
    
    # Z-score for mean value should be close to 0
    assert abs(result["2023-02"][1]) < 0.5
    assert abs(result["2023-04"][1]) < 0.5
    
    # Z-score for peak should be positive
    assert result["2023-03"][1] > 1.0
    
    # Z-scores for low values should be negative
    assert result["2023-01"][1] < -0.5
    assert result["2023-05"][1] < -0.5

def test_zscore_series_spike():
    """Test zscore_series with a spike"""
    months = ["2023-01", "2023-02", "2023-03", "2023-04", "2023-05"]
    counter = Counter({
        "2023-01": 5,
        "2023-02": 8,
        "2023-03": 100,  # extreme spike
        "2023-04": 7,
        "2023-05": 6
    })
    
    result = zscore_series(counter)
    
    # Z-score for the spike should be very high
    assert result["2023-03"][1] > 2.0

def test_zscore_series_empty():
    """Test zscore_series with empty data"""
    counter = Counter()
    result = zscore_series(counter)
    assert result == {}

def test_zscore_series_single_value():
    """Test zscore_series with a single value"""
    counter = Counter({"2023-01": 10})
    result = zscore_series(counter)
    assert result["2023-01"][1] == 0.0  # Z-score should be 0 for a single value

def test_months_since():
    """Test months_since function"""
    # Mock the current date to a fixed value for testing
    with pytest.MonkeyPatch.context() as mp:
        # Set current date to 2023-05-15
        fixed_now = datetime(2023, 5, 15, tzinfo=timezone.utc)
        mp.setattr("datetime.datetime.now", lambda tz=None: fixed_now)
        
        # Test cases
        assert months_since(datetime(2023, 4, 15, tzinfo=timezone.utc)) == 1
        assert months_since(datetime(2023, 1, 1, tzinfo=timezone.utc)) == 4
        assert months_since(datetime(2022, 5, 15, tzinfo=timezone.utc)) == 12
        assert months_since(datetime(2022, 5, 16, tzinfo=timezone.utc)) == 11
        assert months_since(datetime(2023, 5, 15, tzinfo=timezone.utc)) == 0

def test_qualifies_dropoff():
    """Test qualifies_dropoff function"""
    # Mock constants for testing
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("spotify_rediscover_cli.DROP_PEAK_SHARE", 0.4)
        mp.setattr("spotify_rediscover_cli.DROP_RECENT_SILENCE_M", 6)
        mp.setattr("spotify_rediscover_cli.DROP_PEAK_MIN_PLAYS", 20)
        
        # Set current date to 2023-05-15
        fixed_now = datetime(2023, 5, 15, tzinfo=timezone.utc)
        mp.setattr("datetime.datetime.now", lambda tz=None: fixed_now)
        
        # Case 1: Qualifies for drop-off
        counter1 = Counter({"2022-01": 50, "2022-02": 10, "2022-03": 5})  # Peak is 50, total is 65
        last_play1 = datetime(2022, 3, 15, tzinfo=timezone.utc)  # 14 months ago
        result1 = qualifies_dropoff(counter1, last_play1)
        assert result1 is not None
        assert result1[0] == "2022-01"  # Peak month
        assert result1[1] == 50  # Peak value
        assert result1[2] == 65  # Lifetime plays
        
        # Case 2: Not enough plays in peak
        counter2 = Counter({"2022-01": 15, "2022-02": 10, "2022-03": 5})  # Peak is 15 (< 20)
        last_play2 = datetime(2022, 3, 15, tzinfo=timezone.utc)
        result2 = qualifies_dropoff(counter2, last_play2)
        assert result2 is None
        
        # Case 3: Peak not dominant enough
        counter3 = Counter({"2022-01": 30, "2022-02": 25, "2022-03": 25})  # Peak is 30/80 = 37.5% (< 40%)
        last_play3 = datetime(2022, 3, 15, tzinfo=timezone.utc)
        result3 = qualifies_dropoff(counter3, last_play3)
        assert result3 is None
        
        # Case 4: Not silent long enough
        counter4 = Counter({"2022-01": 50, "2022-02": 10, "2022-03": 5})
        last_play4 = datetime(2023, 1, 15, tzinfo=timezone.utc)  # 4 months ago (< 6)
        result4 = qualifies_dropoff(counter4, last_play4)
        assert result4 is None
```

## 7. test_html.py

Tests for the `build_html` function.

```python
import pytest
import re
from spotify_rediscover_cli import build_html

def test_build_html_basic_structure():
    """Test basic HTML structure generation"""
    title = "Test Report"
    params = {"Files": "2", "Min ms": "0"}
    sections = []
    
    html = build_html(title, params, sections)
    
    # Check basic structure
    assert "<!doctype html>" in html.lower()
    assert "<html lang=\"en\">" in html
    assert "<title>Test Report</title>" in html
    assert "<h1>Test Report</h1>" in html
    
    # Check params
    assert "<span class=\"badge\">Files: 2</span>" in html
    assert "<span class=\"badge\">Min ms: 0</span>" in html
    
    # Check no sections message
    assert "No data matched this section" not in html  # No sections provided

def test_build_html_with_sections():
    """Test HTML generation with sections and tables"""
    title = "Test Report"
    params = {"Files": "2"}
    sections = [
        (
            "Section 1", 
            "Subtitle 1", 
            ["Header 1", "Header 2"], 
            [["Row 1 Col 1", "Row 1 Col 2"], ["Row 2 Col 1", "Row 2 Col 2"]]
        ),
        (
            "Section 2",
            "Subtitle 2",
            ["Header A", "Header B"],
            []  # Empty rows
        )
    ]
    
    html = build_html(title, params, sections)
    
    # Check sections
    assert "<h2>Section 1</h2>" in html
    assert "<p class=\"sub\">Subtitle 1</p>" in html
    assert "<th>Header 1</th>" in html
    assert "<td class=\"nowrap\">Row 1 Col 1</td>" in html
    
    # Check empty section
    assert "<h2>Section 2</h2>" in html
    assert "No data matched this section" in html

def test_build_html_escaping():
    """Test HTML escaping of special characters"""
    title = "Test & Report"
    params = {"Special": "<script>"}
    sections = [
        (
            "Section & Title", 
            "Subtitle < > \"", 
            ["Header &"], 
            [["Value & < >"]]
        )
    ]
    
    html = build_html(title, params, sections)
    
    # Check escaping
    assert "Test &amp; Report" in html
    assert "&lt;script&gt;" in html
    assert "Section &amp; Title" in html
    assert "Subtitle &lt; &gt; &quot;" in html
    assert "Header &amp;" in html
    assert "Value &amp; &lt; &gt;" in html

def test_build_html_css_js_inclusion():
    """Test CSS and JS inclusion in HTML"""
    html = build_html("Title", {}, [])
    
    # Check CSS inclusion
    assert "<style>" in html
    assert "body{" in html
    
    # Check JS inclusion
    assert "<script>" in html
    assert "document.querySelectorAll('table')" in html
```

## 8. test_main.py

Tests for the `main` function with mocked dependencies.

```python
import pytest
import sys
import os
from unittest.mock import patch, mock_open
from io import StringIO
from spotify_rediscover_cli import main

def test_main_no_files(capsys):
    """Test main function with no files found"""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "argv", ["spotify_rediscover_cli.py", "empty_dir"])
        
        # Mock expand_files to return empty list
        with patch("spotify_rediscover_cli.expand_files", return_value=[]):
            with pytest.raises(SystemExit) as excinfo:
                main()
            
            assert excinfo.value.code == 2
            captured = capsys.readouterr()
            assert "No JSON files found" in captured.err

def test_main_no_music_rows(capsys, valid_music_data):
    """Test main function with no qualifying music rows"""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "argv", ["spotify_rediscover_cli.py", "test_dir", "--min-ms", "1000000"])
        
        # Mock expand_files and load_rows
        with patch("spotify_rediscover_cli.expand_files", return_value=["file1.json"]):
            with patch("spotify_rediscover_cli.load_rows", return_value=valid_music_data):
                with pytest.raises(SystemExit) as excinfo:
                    main()
                
                assert excinfo.value.code == 0
                captured = capsys.readouterr()
                assert "No qualifying music rows after filters" in captured.out

def test_main_basic_functionality(capsys, valid_music_data):
    """Test main function basic functionality"""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "argv", ["spotify_rediscover_cli.py", "test_dir"])
        
        # Mock functions
        with patch("spotify_rediscover_cli.expand_files", return_value=["file1.json"]):
            with patch("spotify_rediscover_cli.load_rows", return_value=valid_music_data):
                with patch("builtins.open", mock_open()):
                    main()
                    
                    captured = capsys.readouterr()
                    assert "Top artists (all time)" in captured.out
                    assert "Artist Name 1" in captured.out
                    assert "Artist Name 2" in captured.out
                    assert "Done." in captured.out

def test_main_with_html_report(capsys, valid_music_data):
    """Test main function with HTML report generation"""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "argv", ["spotify_rediscover_cli.py", "test_dir", "--html", "report.html"])
        
        # Mock functions
        with patch("spotify_rediscover_cli.expand_files", return_value=["file1.json"]):
            with patch("spotify_rediscover_cli.load_rows", return_value=valid_music_data):
                mock_file = mock_open()
                with patch("builtins.open", mock_file):
                    main()
                    
                    # Check that the HTML file was written
                    mock_file.assert_called_with("report.html", "w", encoding="utf-8")
                    
                    # Check console output
                    captured = capsys.readouterr()
                    assert "Wrote HTML report to:" in captured.out

def test_main_exclude_podcasts(capsys, mixed_data):
    """Test main function with podcast exclusion"""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "argv", ["spotify_rediscover_cli.py", "test_dir", "--exclude-podcasts"])
        
        # Mock functions
        with patch("spotify_rediscover_cli.expand_files", return_value=["mixed.json"]):
            with patch("spotify_rediscover_cli.load_rows", return_value=mixed_data):
                with patch("builtins.open", mock_open()):
                    main()
                    
                    captured = capsys.readouterr()
                    # Should only process music entries, not podcasts
                    assert "music rows: 3" in captured.out
```

## Mock JSON Data Examples

### 1. valid_data.json

```json
[
  {
    "ts": "2023-01-15T14:30:45Z",
    "ms_played": 240000,
    "master_metadata_track_name": "Song Title 1",
    "master_metadata_album_album_name": "Album Name 1",
    "master_metadata_album_artist_name": "Artist Name 1"
  },
  {
    "ts": "2023-01-15T15:00:00Z",
    "ms_played": 180000,
    "master_metadata_track_name": "Song Title 2",
    "master_metadata_album_album_name": "Album Name 1",
    "master_metadata_album_artist_name": "Artist Name 1"
  },
  {
    "ts": "2023-02-20T10:15:30Z",
    "ms_played": 300000,
    "master_metadata_track_name": "Song Title 3",
    "master_metadata_album_album_name": "Album Name 2",
    "master_metadata_album_artist_name": "Artist Name 2"
  }
]
```

### 2. podcast_data.json

```json
[
  {
    "ts": "2023-03-10T08:45:00Z",
    "ms_played": 1800000,
    "episode_name": "Podcast Episode 1",
    "episode_show_name": "Podcast Show 1"
  },
  {
    "ts": "2023-03-15T14:20:00Z",
    "ms_played": 2400000,
    "episode_name": "Podcast Episode 2",
    "episode_show_name": "Podcast Show 1"
  }
]
```

### 3. mixed_data.json

```json
[
  {
    "ts": "2023-01-15T14:30:45Z",
    "ms_played": 240000,
    "master_metadata_track_name": "Song Title 1",
    "master_metadata_album_album_name": "Album Name 1",
    "master_metadata_album_artist_name": "Artist Name 1"
  },
  {
    "ts": "2023-03-10T08:45:00Z",
    "ms_played": 1800000,
    "episode_name": "Podcast Episode 1",
    "episode_show_name": "Podcast Show 1"
  }
]
```

### 4. empty_data.json

```json
[]
```

### 5. invalid_data.json

```
This is not valid JSON data
```

## Running the Tests

To run the tests, you would use pytest:

```bash
cd "Spotify Extended Streaming History"
python -m pytest test_spotify_rediscover_cli.py -v
```

For coverage reporting:

```bash
python -m pytest test_spotify_rediscover_cli.py --cov=spotify_rediscover_cli --cov-report=term