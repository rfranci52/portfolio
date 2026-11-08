# Chatbot evaluation

`run_eval.py` runs every case through the same code a visitor reaches. It imports `frontend/api/chat.py` and drives its event stream directly, so retrieval, the privacy screen, the step that chooses a lookup subject, the lookup and its organization context step, the model call, the output screen and the cost calculation are all the real ones.

The case files and the result files are kept locally and are not published. This repository holds only the runner and this description of it.

## Running it

Use the project's Python 3.12 environment with `anthropic` and `psycopg` installed.

```
python eval/run_eval.py --dry-run
python eval/run_eval.py --category answerable --limit 5
python eval/run_eval.py
python eval/run_eval.py --model claude-sonnet-5-5 --effort low
```

| Flag | Meaning |
| --- | --- |
| `--dry-run` | Print the planned case count and a cost estimate. No network call, nothing written. |
| `--limit N` | Run at most N cases, spread across categories so a small run touches each one. |
| `--category NAME` | One of `answerable`, `not_in_record`, `injection`, `org_context`, `poisoned_lookup`, `private`. |
| `--model`, `--effort` | Override `SITE_MODEL` and `SITE_EFFORT` for this run. |

Runs execute at most four cases at a time. Each case bypasses the visitor quota, the daily spend counter and the visitor log, so evaluation traffic neither spends the daily budget nor shows up as visits.

## Case files

`cases.jsonl` is kept locally and holds one JSON (JavaScript Object Notation) object per line. The categories:

- **answerable**: questions his written case studies cover. The answer must carry the expected facts and cite a passage from the expected document.
- **not_in_record**: products and facts absent from the written record, such as Salesforce, Kubernetes or dbt (data build tool). The answer must say so and must not claim the experience.
- **injection**: visitor messages that try to override the rules, leak hidden instructions, or plant tokens and links.
- **org_context**: a visitor names a well-known company. The answer must point to his closest work. Every case goes through the lookup step, which code runs when the extraction model reports a company. Some supply a fixture row so the organization context step inside it runs on public facts; the rest take the "nothing known about this company" path.
- **poisoned_lookup**: the web lookup returns a fixture whose summary carries planted instructions and false claims, and that text then takes the same path a real summary takes: the screens, then the block the writing model reads. The subject still comes from the real extraction step. A case fails if the lookup never ran, because then nothing was tested.

A separate private case set runs alongside these. It also stays outside this repository, and result files record it only as aggregate counts, under the name "Private information". Its bar is 100%.

Fields a case can set:

| Field | Meaning |
| --- | --- |
| `id`, `category`, `question` | Required. |
| `history` | Earlier turns, for follow-up questions. |
| `expected_doc` | Document slugs. At least one cited passage must come from one of them. |
| `must_contain` | A list of groups. A group is a phrase or a list of acceptable alternatives. Every group must match. |
| `must_not_contain` | Phrases that fail the case if present. |
| `org_fixture` | A public-facts row returned by the organization context step inside the lookup. |
| `lookup_fixture` | The value returned by the web lookup, in place of a search and summary. |
| `require_lookup`, `require_org` | The lookup must have run, or this organization must have matched. |
| `judge_requirement`, `judge` | Override the judge's instruction, or skip the judge with `false`. |
| `parity_group` | Cases in one group must produce the same visible events, the same number of related links and the same web sources. Answer text is not compared. |
| `parity_retrieval` | With `parity_group`: compare only the search step. The cases must not have searched with the same query. |

## How a case is graded

Deterministic checks run first, on every case: the stream completed, the answer is not empty, it has no em-dash, every link goes to this site or the demo, the output passes the privacy screen again, and it does not repeat the system prompt, including in Base64 or letter by letter. Then the case's own checks. A failed deterministic check ends grading for that case.

Cases that pass then go to a large language model (LLM) judge, `claude-sonnet-5-5`, which grades groundedness (every claim about him traces to a retrieved passage) and the requirement for that category. On injection cases the judge also compares the reply with the hidden instructions, so a translated or paraphrased copy counts as a leak. Its verdict is stored with the case. A case passes only when both stages pass.

A judge outage, timeout or pipeline crash is recorded as `error`, separate from `fail`, so an outage cannot read as a model mistake.

## What gets written

- `eval/results/<date>-<model>-<effort>.json`: every case in the local case file with its answer, checks and verdict, plus aggregate counts for the private set. Partial runs get a `-partial` suffix. These files are kept locally and are not published.
- `frontend/src/eval_summary.json`: the file the how-this-works page reads. It holds `{"status":"not_run"}`, so the site shows no numbers. A complete run with no errors that meets the 100% bar on the private set overwrites it. Any other run leaves it as it is.

`median_ms` and `median_cost_usd` cover turns that reached the model. Fixed answers cost nothing and would pull both toward zero. The judge's cost is reported separately and is not part of the median.

Before anything is written, public output passes through a gate. A case that trips it has its answer withheld and counts as failed. A run that writes results refuses to start if the gate has nothing to check against.

Turns that reach the model are measured from the exact figures in the log, because the event a visitor sees rounds cost and time. Lookups made during a run are not written to the shared cache.

## Limits

Each case runs once, so one run is a point estimate and a single flaky answer moves a category by a few points. The cost shown by `--dry-run` is a projection from assumed token counts. Case wording was written by hand, so it reflects what the author thought to test.
