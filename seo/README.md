# Weekly SEO workflow (AspirantDaily)

A copy of the Teachings.ai `seo/` engine with the domain taken from `config.json`.
It fetches Search Console, GA4 and AdSense data (read-only), and Bing data once a Bing API key exists.
It then saves a dated snapshot, evaluates the experiments in `experiments.json`, and writes a report plus a prioritised plan.

| Path | In git? | What |
|---|---|---|
| `gapi.py`, `bing.py`, `weekly.py`, `analysis.py`, `config.json`, `requirements.txt`, `run_weekly.cmd` | yes | code and settings (no secrets) |
| `experiments.json` | yes | change log: change, commits, hypothesis, baseline (recorded automatically), evaluations |
| `data/`, `reports/`, `logs/` | **no** | raw snapshots and reports (they contain revenue; the repo is public) |
| `%APPDATA%\teachings-seo\` | **no** (outside the repo) | OAuth client file and token, shared with Teachings.ai |

`seo/` is in `.vercelignore`, so none of it is deployed. Nothing here writes to Google, Bing, the site or ads.

## Run (from the repo root, using the Teachings.ai virtualenv)

```
"%USERPROFILE%\Documents\GitHub\Teachings.ai\seo\.venv\Scripts\python.exe" seo\weekly.py --check
"%USERPROFILE%\Documents\GitHub\Teachings.ai\seo\.venv\Scripts\python.exe" seo\weekly.py
```

In Git Bash: `/c/Users/whynew/Documents/GitHub/Teachings.ai/seo/.venv/Scripts/python.exe seo/weekly.py`.

## Bing

Sign in to Bing Webmaster Tools, add and verify www.aspirantdaily.com, then generate an API key (Settings > API Access).
Save just the key in `%APPDATA%\teachings-seo\bing_api_key.txt`; don't paste it into chat.

## Logging a change

Add an entry to `experiments.json` when a change ships: `id`, `date`, `commits`, `pages_regex`, `change`, `hypothesis`, `metric`, `window_days`, `evaluate_after`, `confounders`.
The next run records the pre-change baseline itself. Change one major variable per page group where practical, and don't call a result before `evaluate_after`.
