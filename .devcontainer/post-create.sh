#!/usr/bin/env bash
set -e

# Ensure user binary paths are available immediately in this script
export PATH="$HOME/.local/bin:$HOME/.opencode/bin:$PATH"

# Install uv if missing
if ! command -v uv &> /dev/null; then
  echo "Installing Astral uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# Sync project dependencies
echo "Syncing dependencies with uv..."
uv sync

# Install OpenCode if missing
if ! command -v opencode &> /dev/null; then
  echo "Installing OpenCode..."
  curl -fsSL https://opencode.ai/install | bash
  export PATH="$HOME/.opencode/bin:$PATH"
fi

# Install global agent skills (tolerant to network/agent warnings)
echo "Installing global agent skills..."
npx -y skills add -g mattpocock/skills -y --all || echo "Warning: failed to install mattpocock/skills"
npx -y skills add -g huggingface/skills -y --all || echo "Warning: failed to install huggingface/skills"

echo "Codespace setup completed successfully!"
