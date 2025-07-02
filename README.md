# Sacandaga Backend

## Development

Install [Python](https://www.python.org) (version [3.13.3](https://www.python.org/downloads/release/python-3133) confirmed working).

Install package dependencies and launch:

```bash
pip install -r requirements.txt
python -m server
```

## Production

Build and run in a Docker container:

```bash
docker build -t sacandaga-backend .
docker run -p 5001:5001 sacandaga-backend
```

Set the environment variable `APP_ENV` to `production` to enforce CORS whitelist policy and disable debug mode:

```
APP_ENV=production
```
