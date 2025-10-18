"""Launch the Gradio frontend."""

from __future__ import annotations

from ssr_service.frontend import launch

if __name__ == "__main__":
    launch(server_port=7860)
