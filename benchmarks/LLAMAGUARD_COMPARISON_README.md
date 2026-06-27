# Llama Guard 3 (8B) vs AATIF — Head-to-Head Comparison

## What This Does

This script runs **Llama Guard 3 8B** on the **same 570 blind evaluation prompts** used to evaluate AATIF, producing a direct head-to-head comparison on identical data with identical ground-truth labels.

The blind evaluation dataset includes:
- **200** ToxiGen-style implicit toxicity prompts (English)
- **100** ToxiGen-style benign controls (English)
- **100** Arabic hate speech prompts
- **50** Arabic benign controls
- **120** Synthetic edge cases (social engineering, misinformation, copyright, manipulation, dialect benign, tricky benign)

For each prompt, the script:
1. Loads AATIF's existing classification from `blind_eval_results_2026-06-26.json`
2. Sends the prompt to Llama Guard 3 8B via Together AI
3. Records both systems' safe/unsafe decisions
4. Computes Accuracy, Precision, Recall, F1, and FPR for both systems on the same data

## Prerequisites

- Python 3.8+
- `requests` library (`pip install requests`)
- A Together AI API key (see below)

## Getting a Together AI API Key

1. Go to [https://api.together.xyz/signup](https://api.together.xyz/signup)
2. Create a free account (no credit card required)
3. Free tier includes **$5 credit** — more than enough for this experiment (~570 calls ≈ $0.05)
4. Copy your API key from the dashboard

## How to Run

```bash
# From the AATIF-academic directory:
cd ~/Desktop/AATIF-academic

# Full run (all 570 prompts, ~5-10 minutes)
TOGETHER_API_KEY=your_key_here python benchmarks/llamaguard_comparison.py

# Quick test (10 prompts, ~15 seconds)
TOGETHER_API_KEY=your_key_here python benchmarks/llamaguard_comparison.py --dry-run

# Custom output path
TOGETHER_API_KEY=your_key_here python benchmarks/llamaguard_comparison.py \
    --output benchmarks/my_results.json

# Resume a partial run (if interrupted)
TOGETHER_API_KEY=your_key_here python benchmarks/llamaguard_comparison.py \
    --resume benchmarks/llamaguard_comparison_results.json
```

## Expected Runtime

| Mode       | Prompts | Time       | Cost (approx)  |
|------------|---------|------------|----------------|
| `--dry-run`| 10      | ~15 sec    | < $0.01        |
| Full run   | 570     | 5–10 min   | ~$0.05         |

Runtime depends on Together AI's response latency. The script adds a 150ms delay between requests to respect rate limits and uses exponential backoff on 429/5xx errors.

## Output

The script produces:

1. **Console output** — a formatted comparison table showing both systems' metrics side by side
2. **JSON file** (`benchmarks/llamaguard_comparison_results.json`) containing:
   - Metadata (date, model, runtime)
   - Overall metrics for both systems
   - Per-category metrics for both systems
   - Individual results for all 570 prompts
   - Any API errors encountered

## Interpreting Results

The comparison table shows:

```
  Metric                     AATIF    LlamaGuard3      Delta
------------------------------------------------------------------
  Accuracy               0.XXXX         0.XXXX     +/-0.XXXX
  Precision              0.XXXX         0.XXXX     +/-0.XXXX
  Recall                 0.XXXX         0.XXXX     +/-0.XXXX
  F1 Score               0.XXXX         0.XXXX     +/-0.XXXX
  FPR                    0.XXXX         0.XXXX     +/-0.XXXX
```

- **Positive delta** = AATIF is better (except FPR, where lower is better)
- Both systems are evaluated against the same ground truth labels
- Per-category breakdown shows where each system excels or struggles

## Alternatives to Together AI

If Together AI doesn't work for you, here are other options:

### Option A: Replicate

```bash
pip install replicate
export REPLICATE_API_TOKEN=your_token

# Modify the script to use Replicate's API instead
# Model: meta/meta-llama-guard-3-8b
# See: https://replicate.com/meta/meta-llama-guard-3-8b
```

### Option B: Google Colab (free GPU)

1. Upload `blind_eval_results_2026-06-26.json` to Colab
2. Install: `!pip install transformers torch accelerate`
3. Load model locally:
   ```python
   from transformers import AutoTokenizer, AutoModelForCausalLM
   model_id = "meta-llama/Meta-Llama-Guard-3-8B"
   tokenizer = AutoTokenizer.from_pretrained(model_id)
   model = AutoModelForCausalLM.from_pretrained(
       model_id, torch_dtype="auto", device_map="auto"
   )
   ```
4. Run inference on each prompt (requires Llama access on HuggingFace)

### Option C: Ollama (local, if you have a GPU)

```bash
ollama pull llama-guard3:8b
# Then modify the script to call localhost:11434 instead of Together AI
```

## Methodology Notes

- **Llama Guard 3** is called with `temperature=0.0` for deterministic classification
- AATIF blocking decisions (`SAFE_STOP`, `SAFE_FREEZE`, `BLOCKED`) → classified as "unsafe"
- AATIF non-blocking decisions (`EXECUTE`, `CLARIFY`) → classified as "safe"
- Llama Guard 3 responses starting with "unsafe" → blocked; "safe" → passed
- API errors are logged but excluded from metric computation
- The script uses the same ground truth labels for both systems — no re-labeling
