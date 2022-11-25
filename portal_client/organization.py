import argparse

organization_parser = argparse.ArgumentParser(add_help=False)
organization_group = organization_parser.add_argument_group(
    "organization", "Options for Organization"
)

organization_group.add_argument(
    "--organization",
    type=int,
    help="Only return results from the given organization (id)",
)
