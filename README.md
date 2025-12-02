# Multi-Region Dashboard

![Multi Region Dashboard](../multi_region_dashboard.png)

A FastAPI-based dashboard for monitoring and testing database connections across multiple regions (US-East, EU-West, Asia-Pacific) with LaunchDarkly feature flag integration.

## Features

- **Multi-Region Support**: Monitor connections to US-East, EU-West, and Asia-Pacific regions
- **Async PostgreSQL**: Uses `asyncpg` for efficient async database connections
- **LaunchDarkly Integration**: Feature flags for controlling region access and features
- **HTMX + Tailwind CSS**: Modern, responsive UI with dynamic updates
- **Health Monitoring**: Real-time health metrics for each region
- **Load Testing**: Built-in load testing capabilities per region
- **Demo Mode**: Works without LaunchDarkly SDK key for development

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI app with lifespan events
│   ├── config.py            # Region definitions
│   ├── database.py          # Async PostgreSQL with asyncpg
│   ├── feature_flags.py     # LaunchDarkly integration (demo mode included)
│   ├── routers/
│   │   ├── pages.py         # Full HTML page routes
│   │   └── api.py           # HTMX API endpoints (return HTML partials)
│   └── templates/
│       ├── base.html        # Tailwind CSS + HTMX setup
│       ├── index.html       # Main dashboard
│       └── partials/        # HTMX response fragments
├── static/                  # Static files directory
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md               # This file
```

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your LaunchDarkly SDK key (optional)
   ```

3. **Configure Database Connections**:
   Edit `app/config.py` to set your database connection details for each region.

4. **Run the Application**:
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Access the Dashboard**:
   Open your browser to `http://localhost:8000`

## Configuration

### Region Configuration

Edit `app/config.py` to configure your database connections:

```python
REGIONS = {
    "us-east": Region(
        name="US East",
        code="us-east",
        host="localhost",
        port=5432,
        database="us_east_db",
        user="postgres",
        password="postgres"
    ),
    # ... other regions
}
```

### Feature Flags

The application supports LaunchDarkly feature flags with demo mode fallback:

- **Demo Mode**: If `LAUNCHDARKLY_SDK_KEY` is not set, the app runs in demo mode with all features enabled
- **LaunchDarkly Mode**: Set `LAUNCHDARKLY_SDK_KEY` in `.env` to use real feature flags

#### Supported Feature Flags:

- `region-{region-code}-enabled`: Enable/disable specific regions
- `enable-load-testing`: Enable/disable load testing feature
- `enable-health-monitoring`: Enable/disable health monitoring feature

## API Endpoints

### Pages
- `GET /` - Main dashboard page
- `GET /dashboard` - Dashboard page

### HTMX API Endpoints
- `GET /api/test-connection/{region_code}` - Test database connection
- `GET /api/health/{region_code}` - Get health metrics
- `POST /api/load-test/{region_code}` - Run load test
- `GET /api/all-results` - Get connection status for all regions
- `GET /api/flag-panel` - Get feature flag status panel

## Technologies

- **FastAPI**: Modern Python web framework
- **asyncpg**: Async PostgreSQL driver
- **LaunchDarkly**: Feature flag management
- **HTMX**: Dynamic HTML updates without JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Jinja2**: Template engine

## Development

The application uses FastAPI's lifespan events to:
- Initialize database connection pools on startup
- Close connections gracefully on shutdown
- Initialize LaunchDarkly client (or fall back to demo mode)

## License

MIT

