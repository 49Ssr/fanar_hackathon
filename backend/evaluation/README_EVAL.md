# Qaarib Evaluation Harness

Run from repo root:

```bash
cd backend
python evaluation/run_eval.py
```

Required in `backend/.env`:

```env
FANAR_API_KEY=...
GEMINI_API_KEY=...
```

Useful controls:

```env
FANAR_EVAL_MODELS=Fanar,Fanar-C-1-8.7B,Fanar-C-2-27B
GEMINI_JUDGE_MODEL=gemini-3.5-flash
EVAL_TIME_LIMIT_MINUTES=60
```

Time-limit behaviour:

```txt
The runner checks the clock between cases.
Once a prompt/case starts, it finishes that prompt for all selected Fanar models and Gemini judging.
Then, if the time limit has expired, it stops before the next prompt.
```

Outputs:

```txt
backend/evaluation/outputs/latest_results.csv
backend/evaluation/outputs/latest_results.jsonl
```

This folder owns benchmarking. `backend/app.py` should not write CSV evaluation logs.
