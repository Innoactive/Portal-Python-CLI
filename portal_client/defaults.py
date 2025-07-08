from os import getenv


def get_portal_backend_endpoint():
    return getenv("PORTAL_BACKEND_ENDPOINT", "https://api.innoactive.io")


def get_portal_session_management_endpoint():
    return getenv(
        "PORTAL_SESSION_MANAGEMENT_ENDPOINT", "https://session-management.innoactive.io"
    )
