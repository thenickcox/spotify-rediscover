# Spotify Extended Streaming History Analyzer

## Project Overview
This project provides tools for analyzing Spotify streaming history data.

## Project Structure
```
spotify-streaming-history/
│
├── src/                  # Source code
│   ├── spotify_rediscover_cli.py
│   └── spotify_analyzer.sh
│
├── tests/                # Test files
│   ├── test_spotify_rediscover_cli.py
│   ├── test_implementation.md
│   ├── test_plan.md
│   └── test_spotify_rediscover_cli_consolidated.md
│
├── mock_data/            # Mock data for testing
│
├── .gitignore
└── README.md
```

## Prerequisites
- Python 3.x
- pytest (for running tests)

## Installation
1. Clone the repository
2. (Optional) Create and activate a virtual environment
3. Install dependencies:
   ```
   pip install pytest
   ```

## Running Tests
To run the tests, use pytest from the project root:

```bash
pytest tests/
```

### Test Details
- Detailed test plans and implementation notes can be found in the `tests/` directory:
  - `test_plan.md`: Overview of testing strategy
  - `test_implementation.md`: Specific implementation details
  - `test_spotify_rediscover_cli.py`: Main test script
  - `test_spotify_rediscover_cli_consolidated.md`: Consolidated test documentation

## Usage
### CLI Tools
- Spotify Rediscover CLI: 
  ```bash
  python src/spotify_rediscover_cli.py
  ```
- Spotify Analyzer:
  ```bash
  bash src/spotify_analyzer.sh
  ```

## Contributing
Please read the test plan and implementation documents in the `tests/` directory for more details on the project's testing approach.

## License
[Add your license information here]