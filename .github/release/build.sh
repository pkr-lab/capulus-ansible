#!/usr/bin/env bash
set -euo pipefail

version="$1"
mkdir -p dist
git archive --format=tar.gz --prefix="capulus-ansible-v${version}/" -o "dist/capulus-ansible-v${version}.tar.gz" HEAD
