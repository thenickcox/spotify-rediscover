# Unit Tests for Spotify Rediscover CLI

This README provides instructions for running the unit tests for the `spotify_rediscover_cli.py` script.

## Overview

The test suite provides comprehensive coverage of the Spotify Rediscover CLI script, testing all major components:

- Argument parsing
- File handling
- Date/time handling
- Metadata extraction
- Data processing functions
- HTML report generation
- Main function execution

## Test Structure

The tests are organized in a single consolidated test file for simplicity:

```
Spotify Extended Streaming History/
├── spotify_rediscover_cli.py     # Original script
├── test_spotify_rediscover_cli.py # Single test file with all tests
└── mock_data/                    # Directory for mock JSON files (optional)
```

## Setup

1. Make sure you have pytest installed:

```bash
pip install pytest pytest-cov
```

2. Create the test file:

```bash
# Copy the test implementation from test_spotify_rediscover_cli_consolidated.md
# to a new file called test_spotify_rediscover_cli.py
```

## Running the Tests

To run all tests:

```bash
cd "Spotify Extended Streaming History"
python -m pytest test_spotify_rediscover_cli.py -v
```

To run tests with coverage reporting:

```bash
python -m pytest test_spotify_rediscover_cli.py --cov=spotify_rediscover_cli --cov-report=term
```

To run a specific test class:

```bash
python -m pytest test_spotify_rediscover_cli.py::TestArgumentParsing -v
```

To run a specific test:

```bash
python -m pytest test_spotify_rediscover_cli.py::TestArgumentParsing::test_parse_args_default -v
```

## Mock Data

The tests use pytest fixtures to create mock data in memory, so you don't need to create actual JSON files. However, if you want to test with real data, you can create the following files in a `mock_data` directory:

- `valid_data.json`: Contains valid music streaming entries
- `podcast_data.json`: Contains podcast streaming entries
- `mixed_data.json`: Contains both music and podcast entries
- `empty_data.json`: An empty JSON array
- `invalid_data.json`: A file with invalid JSON content

## Test Coverage

The test suite aims to cover:

1. **Happy Paths**: Normal operation with valid inputs
2. **Edge Cases**: Empty data, boundary conditions
3. **Error Handling**: Invalid inputs, missing files, malformed JSON

## Mocking Strategy

The tests use pytest's monkeypatch and unittest.mock to:

1. Mock file system operations (glob, os.path)
2. Mock file reading (open, json.load)
3. Mock command line arguments (sys.argv)
4. Mock datetime.now() for consistent time-based tests

This allows testing without actual files or system resources.

## Extending the Tests

To add new tests:

1. Add new test methods to the appropriate test class
2. For similar test cases, consider using pytest's parametrize decorator
3. For new functionality, create a new test class if needed

## Troubleshooting

If you encounter issues:

- Make sure pytest is installed
- Ensure you're running the tests from the correct directory
- Check that the import statement in the test file correctly imports the script
- Verify that any mocked constants match the actual constants in the script

## Notes on Test Design

1. **Independence**: Each test is independent and doesn't rely on the state from other tests
2. **Readability**: Tests are organized by functionality and have descriptive names
3. **Maintainability**: Common fixtures are reused across tests
4. **Completeness**: All major functions are tested, including edge cases