from os import getenv


def get_portal_backend_endpoint():
    return getenv("PORTAL_BACKEND_ENDPOINT", "https://api.innoactive.io")
