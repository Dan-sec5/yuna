```bash
#!/bin/bash

# Define source and target directories
SOURCE="$HOME/Downloads"
TARGET="$HOME/Downloads/Imagenes"

# Create target directory if it doesn't exist
mkdir -p "$TARGET"

# List of common image extensions (case-insensitive)
IMAGE_EXTENSIONS=("jpg" "jpeg" "png" "gif" "webp" "heic" "heif")

# Move each image file to target directory
for ext in "${IMAGE_EXTENSIONS[@]}"; do
    for file in "$SOURCE"/*.${ext}; do
        [ -f "$file" ] && mv -v "$file" "$TARGET"
    done
done

# Show completion message
echo "¡Todas las imágenes han sido movidas a $TARGET!"
```

