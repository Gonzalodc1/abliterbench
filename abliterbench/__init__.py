"""AbliterBench evaluation framework.

Modules:
    config       - YAML config loader + dataclasses
    llm_client   - Ollama HTTP client wrapper
    tools        - Kali tool wrappers (Inspect AI tools)
    tasks        - Task definitions by track
    graders      - Scoring logic by track
    rag          - RAG indexer + retriever
    personas     - Synthetic persona generator (Track 1)
"""

__version__ = "0.1.0"
