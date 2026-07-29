#!/usr/bin/env bash
# Scoped pull of the Clyffy character canon from Google Drive.
#
# DELIBERATELY NARROW. This does NOT sync AngryVibes_LLC wholesale — it takes
# the CLYFFY character folder and the loose canon docs, nothing else.
# Remote is configured read-only (scope=drive.readonly) so this physically
# cannot write to or delete from Drive.

set -euo pipefail

RCLONE="${RCLONE:-/home/hades/.local/bin/rclone}"
REMOTE="${REMOTE:-clyffydrive}"
DEST="${DEST:-/home/hades/Projects/Clyffy_Avatar/canon}"

mkdir -p "$DEST"

echo "==> Shared Drives visible to this remote:"
"$RCLONE" backend drives "$REMOTE:" || true

echo
echo "==> Pulling CLYFFY character folder (art + video)"
"$RCLONE" copy \
  "$REMOTE:AngryVibes_LLC/CLYFFY_AND_MINIONS/CLYFFY" \
  "$DEST/CLYFFY" \
  --drive-acknowledge-abuse=false \
  --progress \
  --stats-one-line

echo
echo "==> Pulling the master registry"
"$RCLONE" copy \
  "$REMOTE:AngryVibes_LLC/CLYFFY_AND_MINIONS/_MASTER_REGISTRY.md" \
  "$DEST" --progress --stats-one-line

echo
echo "==> Exporting the Google Docs canon as markdown"
for doc in CLYFFY_EBB_AND_FLOW CLYFFY_SPEC WRITING_VOICE_PROFILE; do
  "$RCLONE" copy "$REMOTE:${doc}.md" "$DEST/docs" \
    --drive-export-formats md --progress --stats-one-line || \
    echo "   (skipped ${doc} — not at drive root, will locate separately)"
done

echo
echo "==> Result"
du -sh "$DEST"
find "$DEST" -type f | wc -l | xargs echo "files:"
