#!/bin/bash

# Markdown to ReStructured Text
# 
# This tool will bootstrap a new set of ".rst" files for a given `two1` package with
# a `README.md` file in its root directory. Currently must be run from the root
# `two1` directory.
# 
# Usage:
#   ./docs/md_to_rst.sh two1/mkt/README.md
#

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check for pandoc
which pandoc &>/dev/null
if [ $? -ne 0 ]; then
    echo "error: please install 'pandoc' before running this tool." >&2
    exit 1
fi

set -e

# Check for command line arguments
MD_FILE=$1
if [ ! -e $MD_FILE ]; then
    echo "error: could not find file: "$MD_FILE >&2
    exit 1
fi

# Convert file to proper name
MODULE=$(echo $MD_FILE | sed s/.README.md// | tr / .)
RST_FILE=$DIR"/source/"$MODULE".rst"
SUBMOD_FILE=$DIR"/source/"$MODULE".submodules.rst"

echo "md_to_rst: starting"
pandoc --from=markdown --to=rst --output=$RST_FILE $MD_FILE
echo "md_to_rst: created "$MD_FILE

# Print primary *.rst file
cat <<EOF >>$RST_FILE


\`\`$MODULE\`\`: module contents
===================================
The \`\`$MODULE\`\` module is organized into the following submodules:

.. toctree::

    $MODULE.submodules
EOF

# Print ancillary *.submodules.rst file
SUBMOD=$MODULE".<YOUR_SUBMODULE_NAME>"
cat <<EOF >$SUBMOD_FILE
$SUBMOD
----------------------------------------

.. automodule:: $SUBMOD
    :members:
    :undoc-members:
    :special-members: __init__
    :show-inheritance:
EOF
echo "md_to_rst: added sphinx scaffolding"
echo "md_to_rst: done"

# Notify user of next steps
echo "be sure to edit your submodule files with the names of your submodules!"
echo "after that is done, its a good time to run 'cd docs/ && make html'"
