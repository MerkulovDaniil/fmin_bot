#!/bin/bash

# Get the full path to the input MD file
INPUT_FILE="$1"

# Get the directory containing the input MD file
INPUT_DIR=$(dirname "$INPUT_FILE")

# Get the base name of the input file without extension
BASENAME=$(basename "$INPUT_FILE" .md)

# Convert MD to PDF using Pandoc with xelatex engine
pandoc "$INPUT_FILE" --pdf-engine=xelatex --template=xelatex_template.tex -s -o "$INPUT_DIR/$BASENAME.pdf"

# Settings
MARGIN=10 # Set margin size (you can adjust as per your requirement)
TARGET_RATIO=20

# Function to calculate aspect ratio of an image
get_aspect_ratio() {
  local image="$1"
  local width=$(identify -format "%w" "$image")
  local height=$(identify -format "%h" "$image")
  local ratio=$(bc <<< "scale=2; $width / $height")
  echo "$ratio"
}

# Convert each PDF page to a separate PNG file
mkdir -p "$INPUT_DIR/pages"
convert -density 300 "$INPUT_DIR/$BASENAME.pdf" -quality 90 -colorspace RGB "$INPUT_DIR/pages/${BASENAME}_%04d.png"

# Process each page
for page in "$INPUT_DIR/pages/${BASENAME}"_*.png; do
  # Trim and add margin
  convert "$page" -trim +repage -bordercolor white -border ${MARGIN}x${MARGIN} "$page"

  # Check and adjust aspect ratio
  while true; do
    current_ratio=$(get_aspect_ratio "$page")
    if (( $(bc <<< "$current_ratio > $TARGET_RATIO") )); then
      convert "$page" -bordercolor white -border 0x$MARGIN "$page"
    else
      break
    fi
  done
done

# Concatenate all pages into a single image file
convert "$INPUT_DIR/pages/${BASENAME}"_*.png -append "$INPUT_DIR/$BASENAME.png"

# Optional: Cleanup
rm -r "$INPUT_DIR/pages"
rm "$INPUT_DIR/$BASENAME.pdf"