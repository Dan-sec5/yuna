#!/usr/bin/env bash
set -euo pipefail

AVATAR_DIR="$HOME/yuna/assets/avatars"
SOURCE="$AVATAR_DIR/Avatar.jpeg"

if [[ ! -f "$SOURCE" ]]; then
  echo "❌ No existe el avatar base: $SOURCE"
  exit 1
fi

states=(
  idle
  thinking
  working
  success
  error
  waiting
)

moods=(
  neutral
  happy
  focused
  serious
  amused
  concerned
  tired
  sleepy
)

times=(
  morning
  afternoon
  evening
  night
)

weathers=(
  unknown
  sunny
  partly_cloudy
  cloudy
  fog
  rain
  storm
  snow
)

created=0
skipped=0

copy_if_missing() {
  local target="$1"

  if [[ -f "$target" ]]; then
    ((skipped+=1))
  else
    cp "$SOURCE" "$target"
    ((created+=1))
  fi
}

echo "📁 Carpeta: $AVATAR_DIR"
echo "🖼️ Base   : $SOURCE"
echo

# ----------------------------------------------------------
# Fallbacks
# ----------------------------------------------------------
copy_if_missing "$AVATAR_DIR/avatar.jpeg"
copy_if_missing "$AVATAR_DIR/default.jpeg"

# ----------------------------------------------------------
# Individuales
# ----------------------------------------------------------
for s in "${states[@]}"; do
  copy_if_missing "$AVATAR_DIR/${s}.jpeg"
done

for m in "${moods[@]}"; do
  copy_if_missing "$AVATAR_DIR/${m}.jpeg"
done

for t in "${times[@]}"; do
  copy_if_missing "$AVATAR_DIR/${t}.jpeg"
done

for w in "${weathers[@]}"; do
  copy_if_missing "$AVATAR_DIR/${w}.jpeg"
done

# ----------------------------------------------------------
# state + mood
# ----------------------------------------------------------
for s in "${states[@]}"; do
  for m in "${moods[@]}"; do
    copy_if_missing "$AVATAR_DIR/${s}_${m}.jpeg"
  done
done

# ----------------------------------------------------------
# time + mood
# ----------------------------------------------------------
for t in "${times[@]}"; do
  for m in "${moods[@]}"; do
    copy_if_missing "$AVATAR_DIR/${t}_${m}.jpeg"
  done
done

# ----------------------------------------------------------
# weather + mood
# ----------------------------------------------------------
for w in "${weathers[@]}"; do
  for m in "${moods[@]}"; do
    copy_if_missing "$AVATAR_DIR/${w}_${m}.jpeg"
  done
done

# ----------------------------------------------------------
# time + weather
# ----------------------------------------------------------
for t in "${times[@]}"; do
  for w in "${weathers[@]}"; do
    copy_if_missing "$AVATAR_DIR/${t}_${w}.jpeg"
  done
done

echo
echo "✅ Avatares placeholder listos"
echo "   Creados : $created"
echo "   Omitidos: $skipped"

echo
echo "🔎 Total de archivos .jpeg en assets/avatars:"
find "$AVATAR_DIR" -maxdepth 1 -type f -name "*.jpeg" | wc -l
