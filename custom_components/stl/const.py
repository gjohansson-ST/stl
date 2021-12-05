"""SVENSKA TRYGGHETSLÖSNINGAR INTEGRATION CONSTANTS FOR HOME ASSISTANT."""
DOMAIN = "stl"

API_URL = "https://visonic.stl.nu/rest_api/7.0"
URL_PANEL_LOGIN = API_URL + "/panel/login"
URL_LOGIN = API_URL + "/auth"
URL_STATUS = API_URL + "/status"
URL_ALARMS = API_URL + "/alarms"
URL_ALERTS = API_URL + "/alerts"
URL_TROUBLES = API_URL + "/troubles"
URL_PANEL_INFO = API_URL + "/panel_info"
URL_EVENTS = API_URL + "/events"
URL_WAKEUP_SMS = API_URL + "/wakeup_sms"
URL_ALL_DEVICES = API_URL + "/devices"
URL_SET_STATE = API_URL + "/set_state"
URL_LOCATIONS = API_URL + "/locations"
URL_PROCESS_STATUS = API_URL + "/process_status"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_APP_ID = "app_id"
CONF_PANEL = "panel_id"
CONF_CODE = "code"

MIN_SCAN_INTERVAL = 30

PLATFORMS = ["alarm_control_panel", "binary_sensor"]
