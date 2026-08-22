# Standalone Target Test Application

A decoupled sample Python HTTP application used for testing and demonstrating AutoCure's automated remediation and log monitoring capabilities.

## Structure
- `app.py`: Compatibility exports and the uvicorn entry point.
- `api.py`: FastAPI application, routes, error handling, and webhook integration.
- `standalone_server.py`: Legacy `http.server` adapter and log ingestion endpoint.
- `domain.py`: Shared users, items, and calculation helpers.
- `logger.py`: Shared `ApplicationLogger` class and initialized application logger.
- `logging_config.py`: Backward-compatible logger import.
- `config.json`: Runtime URL configuration for error webhook delivery.
- `settings.py`: Shared filesystem settings.
- `test_app.py`: Pytest test suite verifying correct behavior.
- `trigger_error.py`: Utility script to trigger error endpoints.
- `requirements.txt`: Minimal dependencies for running the app and its tests.

## Running the Application Standalone

### 1. Run the HTTP Server
```bash
python app.py
```
The server will run on `http://127.0.0.1:8080` (or the port specified by `PORT` environment variable) and log to stdout and `app.log`.

### 2. Run the Unit Tests
```bash
pytest test_app.py
```

### 3. Simulate Errors
```bash
# Trigger ZeroDivisionError (/calculate?a=10&b=0)
python trigger_error.py calculate

# Trigger KeyError (/users?id=999)
python trigger_error.py users

# Trigger IndexError (/items?index=999)
python trigger_error.py items

# Trigger all errors
python trigger_error.py all
```

### 4. Validate the Project
```bash
pytest
python -m py_compile app.py
```

### 5. Run with Docker Compose
```bash
docker compose up -d --build
```
This builds the image from the included Dockerfile and starts the app on port 8080.

### 6. Open the API docs
The app exposes a FastAPI Swagger UI at:
```text
http://127.0.0.1:8080/docs
```
You can trigger validation errors from the interactive Swagger UI, including invalid division or missing records, without the implementation looking intentionally sabotaged.

