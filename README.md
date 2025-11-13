# Metalized Background Detection API

A FastAPI-based service that detects metalized backgrounds in product images.

## Features

- Simple REST API endpoint for image processing
- Supports common image formats (JPEG, PNG, etc.)
- Fast and efficient processing
- Health check endpoint
- Confidence scoring for detections

## Prerequisites

- Python 3.8+
- pip

## Installation

1. Navigate to the app directory:
   ```bash
   cd app
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Server

```bash
uvicorn main:app --reload
```

The server will start at `http://127.0.0.1:8000`

## API Documentation

- Interactive API docs: `http://127.0.0.1:8000/docs`
- Alternative API docs: `http://127.0.0.1:8000/redoc`

## API Endpoints

### Detect Metalized Background

- **URL**: `/detect-metalized`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Body**: `file` (image file)

**Example Request**:
```bash
curl -X 'POST' \
  'http://localhost:8000/detect-metalized' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@path/to/your/image.jpg;type=image/jpeg'
```

**Example Response**:
```json
{
  "filename": "image.jpg",
  "is_metalized": true,
  "confidence": 75.5,
  "processing_time_seconds": 0.42,
  "details": {
    "brightness": 156.78,
    "contrast": 42.15
  }
}
```

### Health Check

- **URL**: `/health`
- **Method**: `GET`

**Example Response**:
```json
{
  "status": "healthy",
  "timestamp": "2023-11-13T09:48:00.123456",
  "service": "Metalized Background Detector"
}
```

## Development

1. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Run the development server with auto-reload:
   ```bash
   uvicorn main:app --reload
   ```

## Production Deployment

For production, use a production-grade ASGI server like `uvicorn` with multiple workers:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Or use `gunicorn` with `uvicorn` workers:

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

## Environment Variables

The following environment variables can be configured:

- `UPLOAD_DIR`: Directory to store temporary uploads (default: `uploads`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

## License

MIT
