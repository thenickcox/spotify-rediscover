# Unit Testing Plan for spotify_rediscover_cli.py

## Test Framework and Setup

We'll use **pytest** as our testing framework due to its simplicity, powerful fixtures, and parametrization capabilities. The test structure will follow these principles:

- Use fixtures for common test data and mocks
- Organize tests by function/component
- Use parametrized tests for similar test cases with different inputs
- Mock external dependencies (file system, JSON data)
- Test both happy paths and edge cases/error handling

## Test File Structure

```
Spotify Extended Streaming History/
├── spotify_rediscover_cli.py     # Original script
├── tests/
│   ├── __init__.py               # Make tests a package
│   ├── conftest.py               # Shared fixtures
│   ├── test_argument_parsing.py  # Tests for parse_args
│   ├── test_file_handling.py     # Tests for expand_files, load_rows
│   ├── test_datetime.py          # Tests for parse_ts, month_key
│   ├── test_metadata.py          # Tests for is_podcast, safe_meta
│   ├── test_processing.py        # Tests for data processing functions
│   ├── test_html.py              # Tests for HTML generation
│   ├── test_main.py              # Tests for main function
│   └── mock_data/                # Mock JSON files
│       ├── valid_data.json       # Valid Spotify history data
│       ├── empty_data.json       # Empty data
│       ├── invalid_data.json     # Malformed JSON
│       └── mixed_data.json       # Mix of music and podcasts
```

## Mock Data Structure

We'll create several mock JSON files to test different scenarios:

### 1. Valid Data (valid_data.json)

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

### 2. Podcast Data (podcast_data.json)

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

### 3. Mixed Data (mixed_data.json)

A combination of music and podcast entries.

### 4. Edge Cases

- Empty data
- Malformed JSON
- Missing fields
- Invalid timestamps
- Zero ms_played values

## Test Cases by Component

### 1. Argument Parsing (test_argument_parsing.py)

Test the `parse_args` function:

- Test default values
- Test providing each argument type
- Test invalid arguments
- Test help text generation

### 2. File Handling (test_file_handling.py)

Test the `expand_files` and `load_rows` functions:

- Test directory expansion
- Test glob pattern expansion
- Test loading valid JSON
- Test loading invalid JSON
- Test error handling for missing files
- Test loading multiple files

### 3. Date/Time Handling (test_datetime.py)

Test the `parse_ts` and `month_key` functions:

- Test parsing valid timestamps in different formats
- Test handling timezone information
- Test invalid timestamp formats
- Test month key generation
- Test consistency across timezone changes

### 4. Metadata Extraction (test_metadata.py)

Test the `is_podcast` and `safe_meta` functions:

- Test podcast detection with various input formats
- Test metadata extraction with complete data
- Test metadata extraction with missing fields
- Test handling of empty/None values

### 5. Data Processing (test_processing.py)

Test data processing functions like `zscore_series`, `qualifies_dropoff`, etc.:

- Test z-score calculation with various distributions
- Test drop-off detection with different patterns
- Test edge cases (empty data, single data point)
- Test threshold behavior

### 6. HTML Generation (test_html.py)

Test the `build_html` function:

- Test HTML structure generation
- Test escaping of special characters
- Test handling of empty data
- Test table generation

### 7. Main Function (test_main.py)

Test the `main` function with mocked dependencies:

- Test end-to-end flow with valid data
- Test filtering options
- Test error handling
- Test HTML report generation

## Mocking Strategy

We'll use pytest's monkeypatch and the unittest.mock library to mock:

1. File system operations
   - Mock `open`, `glob.glob`, and `os.path` functions
   - Return predefined mock data instead of reading actual files

2. JSON operations
   - Mock `json.load` to return our test data

3. Command line arguments
   - Use pytest's monkeypatch to mock sys.argv

4. Output capture
   - Use pytest's capsys fixture to capture stdout/stderr

## Example Test Implementation

Here's an example of how we'll implement a test for the `parse_ts` function:

```python
import pytest
from datetime import datetime, timezone
from spotify_rediscover_cli import parse_ts

@pytest.mark.parametrize("timestamp,expected", [
    ("2023-01-15T14:30:45Z", datetime(2023, 1, 15, 14, 30, 45, tzinfo=timezone.utc)),
    ("2023-01-15T14:30:45+00:00", datetime(2023, 1, 15, 14, 30, 45, tzinfo=timezone.utc)),
    ("2023-01-15T09:30:45-05:00", datetime(2023, 1, 15, 14, 30, 45, tzinfo=timezone.utc)),
    (None, None),
    ("invalid", None),
])
def test_parse_ts(timestamp, expected):
    result = parse_ts(timestamp)
    if expected is None:
        assert result is None
    else:
        assert result == expected
        assert result.tzinfo is not None  # Ensure timezone awareness
```

## Test Coverage Goals

We aim for high test coverage, focusing on:

1. Core functionality (data processing, analysis)
2. Edge cases and error handling
3. Integration between components

## Running the Tests

Tests will be run using pytest:

```bash
cd "Spotify Extended Streaming History"
python -m pytest tests/ -v
```

For coverage reporting:

```bash
python -m pytest tests/ --cov=. --cov-report=term