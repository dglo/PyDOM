#!/bin/sh

# make sure we're in the top-level PyDOM directory
#
if [ ! -d icecube -o ! -d icecube/domtest ]; then
  echo "$0: This script must be run from the top-level PyDOM directory" >&2
  exit 1
fi

# set up PYTHONPATH
#
CURDIR=`pwd`
if [ -z "$PYTHONPATH" ]; then
  PYTHONPATH="$CURDIR"
else
  PYTHONPATH="$CURDIR:$PYTHONPATH"
fi
export PYTHONPATH

# find and run all tests
#
for file in `find . -name '*Test.py' -print`; do
    echo -n "$file: "
    python ./$file
done
