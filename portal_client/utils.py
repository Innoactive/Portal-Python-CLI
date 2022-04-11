from base64 import b64encode
import os


def get_authorization_header():
    if os.getenv("PORTAL_BACKEND_ACCESS_TOKEN"):
        return "Bearer %s" % os.getenv("PORTAL_BACKEND_ACCESS_TOKEN")

    if os.getenv("POTAL_BACKEND_USERNAME") and os.getenv("POTAL_BACKEND_PASSWORD"):
        return "Basic {}".format(
            b64encode(
                bytes(
                    "%s:%s"
                    % (
                        os.getenv("POTAL_BACKEND_USERNAME"),
                        os.getenv("POTAL_BACKEND_PASSWORD"),
                    ),
                    "utf-8",
                )
            ).decode("ascii")
        )

    raise Exception(
        "Missing authentication! Please specify either PORTAL_BACKEND_ACCESS_TOKEN or POTAL_BACKEND_USERNAME and POTAL_BACKEND_PASSWORD"
    )
