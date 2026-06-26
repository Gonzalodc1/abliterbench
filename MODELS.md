# Models

All six models are served locally via [Ollama](https://ollama.com) (the paper used v0.24.0),
quantized **Q4_K_M** (GGUF). The matched pairs are:

| family | aligned tag | abliterated tag |
|---|---|---|
| Llama-3.1-8B | `llama3.1:8b-instruct-q4_K_M` | local modelfile over a Llama-3.1-8B abliterated build (`llama-3.1-8b-abliterated-tools`) |
| Qwen2.5-7B | `qwen2.5:7b-instruct-q4_K_M` | `huihui_ai/qwen2.5-abliterate:7b` |
| Granite-3.1-8B | `granite3.1-dense:8b-instruct-q4_K_M` | `huihui_ai/granite3.1-dense-abliterated:8b` |

The abliterated builds are community weights from the `huihui_ai` collection on the Ollama registry
/ Hugging Face. **We do not redistribute weights.**

## Pinning the exact digest

Ollama tags are mutable, so for exact reproducibility pin the image digest you actually ran:

```bash
ollama list                     # shows the short ID (digest) for each pulled tag
ollama show <tag> --modelfile   # shows the modelfile (template, parameters, base)
```

Record the `ID`/digest from `ollama list` alongside the tag. Each run CSV under `runs/` carries a
`model` column (e.g. `llama-aligned`, `qwen-abliterated`) that maps to the table above, so every
reported number is traceable to a specific matched-pair condition.

> Caveat (see paper, Limitations): the abliterated builds are repackaged community weights, not an
> abliteration we applied to the exact aligned checkpoint, so the two twins of a family may differ
> in more than the refusal direction (modelfile, tool-call template). See the tool-use diagnostics
> appendix in the paper.
