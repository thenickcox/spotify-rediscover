# Spotify Rediscover CLI

## Project Setup

1. Clone the repository
2. Create a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the project in editable mode:
   ```
   pip install -e .
   ```

## Running Tests

To run the tests, use pytest:
```
python3 -m pytest tests
```

## Usage

Run the CLI tool with:
```
python3 -m src.spotify_rediscover_cli [options]
```

## Dependencies

- Python 3.8+
- pytest (for testing)