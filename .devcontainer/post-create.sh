#!/usr/bin/env bash
set -e

# Sync project dependencies
uv sync

# Install OpenCode
curl -fsSL https://opencode.ai/install | bash

# Install global agent skills
npx -y skills add -g mattpocock/skills -y --all
npx -y skills add -g huggingface/skills -y --all
