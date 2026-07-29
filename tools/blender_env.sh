#!/usr/bin/env bash
# Prefer GB10-capable Blender 5.2 over Ubuntu's 4.0.2 package.
export PATH="/opt/bin:/usr/local/bin:${PATH}"
export BLENDER="${BLENDER:-/opt/blender-5.2.0/blender-wrapper.sh}"
