FROM --platform=linux/amd64 debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl wget gnupg lsb-release \
    xvfb \
    fonts-liberation fonts-dejavu-core \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 \
    libgbm1 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 \
    libpango-1.0-0 libpangocairo-1.0-0 \
    libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 \
    libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 \
    libxrender1 libxss1 libxtst6 xdg-utils \
    libvulkan1 libegl1 libgles2 \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install pnpm
RUN npm install -g pnpm

# Install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
       > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

ENV VK_ICD_FILENAMES=/opt/google/chrome/vk_swiftshader_icd.json
ENV DISPLAY=:99

WORKDIR /workspace

# Install Node deps
COPY app/package.json app/pnpm-workspace.yaml app/tsconfig.json ./app/
RUN cd app && pnpm install

# Install Python deps
COPY pyproject.toml uv.lock ./
RUN uv sync

# Install Playwright's Chromium
RUN uv run playwright install chromium --with-deps

# Copy source
COPY app/ ./app/
COPY agent/ ./agent/
COPY tasks/ ./tasks/
COPY ex/ ./ex/
COPY sdk.py curriculum.py seed_generator.py ./
RUN chmod +x ./agent/*.sh

VOLUME ["/workspace/tasks"]

ENTRYPOINT ["/workspace/agent/entrypoint.sh"]
