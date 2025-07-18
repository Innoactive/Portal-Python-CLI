from base64 import b64encode
from os import getenv


def get_authorization_header():
    try:
        return get_bearer_authorization_header()
    except Exception:
        # Fallback to basic auth if bearer token is not set
        pass

    if getenv("PORTAL_BACKEND_USERNAME") and getenv("PORTAL_BACKEND_PASSWORD"):
        return "Basic {}".format(
            b64encode(
                bytes(
                    "%s:%s"
                    % (
                        getenv("PORTAL_BACKEND_USERNAME"),
                        getenv("PORTAL_BACKEND_PASSWORD"),
                    ),
                    "utf-8",
                )
            ).decode("ascii")
        )

    raise Exception(
        "Missing authentication! Please specify either PORTAL_BACKEND_ACCESS_TOKEN or PORTAL_BACKEND_USERNAME and PORTAL_BACKEND_PASSWORD"
    )


def get_bearer_authorization_header():
    if getenv("PORTAL_BACKEND_ACCESS_TOKEN"):
        return "Bearer %s" % getenv("PORTAL_BACKEND_ACCESS_TOKEN")

    raise Exception(
        "Missing authentication! Please specify either PORTAL_BACKEND_ACCESS_TOKEN or PORTAL_BACKEND_USERNAME and PORTAL_BACKEND_PASSWORD"
    )
