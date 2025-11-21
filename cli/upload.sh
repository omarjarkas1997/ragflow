#!/bin/bash
# upload.sh
# Replace <YOUR_KB_ID> with the actual ID
KB_ID="3ffbf6c4c5c911f0ba2ffa8925bb4278"

for file in ../../finrag/academic_papers/*.pdf; do
    echo "Uploading $file..."
    python3 cli.py upload --kb-id "$KB_ID" --file "$file"
done