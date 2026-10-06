#!/usr/bin/env bash

if [ -z "$1" ]
  then
    >&2 echo "No argument supplied"
    exit 1
fi

echo "Updating Version to: $1"

sed -i "s/version = \".*\"$/version = \"$1\"/" pyproject.toml

# uv.lock records the project's own version as well; unless it matches pyproject.toml, `uv sync --locked` rejects
# the lockfile
sed -i "/^name = \"portal-client\"$/{n;s/^version = \".*\"$/version = \"$1\"/}" uv.lock
if ! grep -A1 '^name = "portal-client"$' uv.lock | grep -qx "version = \"$1\""; then
  >&2 echo "Could not update the portal-client version in uv.lock"
  exit 1
fi
