import argparse

pagination_parser = argparse.ArgumentParser(add_help=False)
pagination_group = pagination_parser.add_argument_group(
    "pagination", "Options for Pagination"
)
pagination_group.add_argument(
    "--page-size", type=int, help="How many results to return (per page)", default=10
)
pagination_group.add_argument(
    "--page",
    type=int,
    help="The page of results to fetch (based on --page-size)",
    default=1,
)
