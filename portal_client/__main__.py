#!/usr/bin/env python

from portal_client import parser


def main():
    args = parser.parse_args()

    if hasattr(args, "func"):
        # run the command
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
