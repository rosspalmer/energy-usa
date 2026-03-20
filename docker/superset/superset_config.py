import os

# Superset metadata database (charts, dashboards, users, datasource configs)
SQLALCHEMY_DATABASE_URI = os.environ["SUPERSET_DATABASE_URL"]

# Must be a long random string — generate with:
#   python -c "import secrets; print(secrets.token_hex(42))"
SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

# Feature flags
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
}

# Production: enable if Superset sits behind a reverse proxy (nginx, Caddy)
ENABLE_PROXY_FIX = os.environ.get("SUPERSET_PROXY_FIX", "false").lower() == "true"

# Tighten session cookie security for internet-facing deployments
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = os.environ.get("SUPERSET_COOKIE_SECURE", "false").lower() == "true"

# Disable anonymous access to charts/dashboards
PUBLIC_ROLE_LIKE = None
