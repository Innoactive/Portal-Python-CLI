#!/usr/bin/env bash

if [ -z "$1" ]
  then
    >&2 echo "No argument supplied"
    exit 1
fi

echo "Updating Version to: $1"

sed -i "s/version=\".*\",/version=\"$1\",/" setup.py
