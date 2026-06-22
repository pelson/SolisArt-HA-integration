from datetime import timedelta

DOMAIN = "solisart"

CONF_MODE = "mode"
CONF_LOCAL_URL = "local_url"
CONF_CLOUD_URL = "cloud_url"
CONF_USERNAME_LOCAL = "username_local"
CONF_PASSWORD_LOCAL = "password_local"
CONF_USERNAME_CLOUD = "username_cloud"
CONF_PASSWORD_CLOUD = "password_cloud"
CONF_INSTALL_ID = "install_id"
CONF_UPDATE_MODE = "update_mode"
CONF_UPDATE_INTERVAL_MIN = "update_interval_min"
CONF_EXPOSE_DIAGNOSTIC = "expose_diagnostic"

MODE_LOCAL = "local"
MODE_CLOUD = "cloud"
MODE_FALLBACK = "fallback"

UPDATE_MODE_MANUAL = "manual"
UPDATE_MODE_TIMER = "timer"

DEFAULT_CLOUD_URL = "https://my.solisart.fr"
DEFAULT_UPDATE_MODE = UPDATE_MODE_MANUAL
DEFAULT_TIMER_INTERVAL_MIN = 30
TIMER_INTERVAL_RANGE_MIN = (1, 360)

POST_WRITE_REFRESH_DELAY = timedelta(seconds=15)
