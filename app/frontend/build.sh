#!/bin/bash
echo "🎨 Building Tailwind CSS..."
./tailwindcss -i ./assets/css/input.css -o ./static/css/style.css --minify
echo "✅ CSS compiled! Size: $(du -h static/css/style.css | cut -f1)"
