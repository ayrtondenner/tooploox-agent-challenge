# pipecat-quickstart

This directory hosts two independent Python entry points that share one `uv` project:

1. **`bot.py`** — a Pipecat voice agent built with a cascade pipeline (STT → LLM → TTS). This is the original quickstart scaffold and is left unchanged.
2. **`quiz/`** — the **Markdown Quiz Agent** that is the actual Tooploox code-challenge deliverable. See the top-level [README.md](../README.md) for the full write-up, the scoring interpretation, and a note on how the build was driven (Claude Code + GSD + Superpowers).

Quick commands (from `server/`):

```bash
uv sync                          # install deps for both apps
uv run pytest                    # run quiz tests (60)
uv run python -m quiz.app        # launch the quiz Gradio UI at http://127.0.0.1:7860
uv run bot.py                    # launch the voice bot (unchanged)
```

---

## Voice bot configuration (unchanged from the scaffold)

- **Bot Type**: Web
- **Transport(s)**: SmallWebRTC, Daily (WebRTC)
- **Pipeline**: Cascade
  - **STT**: Deepgram
  - **LLM**: OpenAI Responses
  - **TTS**: Cartesia

## Setup

### Server

1. **Navigate to server directory**:

   ```bash
   cd server
   ```

2. **Install dependencies**:

   ```bash
   uv sync
   ```

3. **Configure environment variables**:

   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

4. **Run the bot**:

   - SmallWebRTC: `uv run bot.py`
   - Daily: `uv run bot.py --transport daily`

## Project Structure

```
pipecat-quickstart/
├── server/              # Python bot server
│   ├── bot.py           # Main bot implementation
│   ├── pyproject.toml   # Python dependencies
│   ├── .env.example     # Environment variables template
│   ├── .env             # Your API keys (git-ignored)
│   ├── Dockerfile       # Container image for Pipecat Cloud
│   └── pcc-deploy.toml  # Pipecat Cloud deployment config
├── .gitignore           # Git ignore patterns
└── README.md            # This file
```

## Deploying to Pipecat Cloud

This project is configured for deployment to Pipecat Cloud. You can learn how to deploy to Pipecat Cloud in the [Pipecat Quickstart Guide](https://docs.pipecat.ai/getting-started/quickstart#step-2-deploy-to-production).

Refer to the [Pipecat Cloud Documentation](https://docs.pipecat.ai/deployment/pipecat-cloud/introduction) to learn more about configuring, deploying, and managing your agents in Pipecat Cloud.

## Learn More

- [Pipecat Documentation](https://docs.pipecat.ai/)
- [Pipecat GitHub](https://github.com/pipecat-ai/pipecat)
- [Pipecat Examples](https://github.com/pipecat-ai/pipecat-examples)
- [Discord Community](https://discord.gg/pipecat)