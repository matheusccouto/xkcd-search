FROM mcr.microsoft.com/devcontainers/javascript-node:4-24-trixie

SHELL ["/bin/bash", "-eu", "-o", "pipefail", "-c"]

USER vscode

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
 && curl -fsSL https://opencode.ai/v2/install | bash

RUN --mount=type=bind,source=skills-lock.json,target=/home/vscode/skills-lock.json \
    cd /home/vscode && npx -y skills@1.7.4 experimental_install
