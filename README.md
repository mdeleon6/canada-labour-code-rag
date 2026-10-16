# Can Claude answer questions about the Canada Labour Code with citations?

**Answer:** Get plain-language answers to questions about federal labour standards, with the exact section of the Canada Labour Code cited for each answer. In testing, Claude cited the right section for 83% of test questions and flagged both off-topic test questions as not covered.

**Live app:** _(add after deploying)_

## The question
Ask a question about federal labour standards (Canada Labour Code, Part III). The system finds the most relevant sections of the law and Claude answers using only those sections, citing the section numbers so you can check the source.


## What I found
- **Claude never failed when it had the right section:** it cited the right section for
  every question where search found it. Every miss came from search.
- **Search is the weak link:** everyday words like "laid off" don't match the law's
  "terminates the employment", so the right section isn't always found.
- **Honest refusals:** both off-topic questions were marked "not covered" instead of guessed.
- **5 sections per question, not 9:** 9 answered 1–2 more questions, but in the answers
  I reviewed, both rule breaks (including using information from outside the law) came
  with the larger context. For a legal-information tool, staying grounded matters most.

## How sure is this?
**How well (tested on 20 questions: 18 answerable, 2 off-topic)**
- The right section was cited for 83% of answerable questions.
- Both off-topic questions were marked as not covered, and the user was told.
- Every miss came from search not finding the right section. When Claude had it, it always cited it.

**Limits**
- Everyday words like "laid off" or "fired" can miss, because the law says "terminates" and "dismissed".
- Small test set (20 questions), so treat the numbers as a guide.
- Law current to December 29, 2025 (last amended December 12, 2025).

- One test question was relabelled after a manual review of Claude's answer showed it was answerable (documented in the notebook).

## Method
1. Keyword search (BM25) finds the most relevant sections of the law.
2. The top 5 sections are given to Claude.
3. Claude answers in plain language and cites the sections it used.
- 205 sections of Part III parsed from the official XML; one section = one chunk
- Test set: 20 hand-labelled questions in workers' everyday words
- Retrieval measured with hit@k; answers graded with a scorecard (right section cited, off-topic flagged), plus a manual review
- Claude Opus 5.5 with structured outputs (`covered`, `answer`, `cited_sections`); system prompt in `prompt.py`

## Run it
**View the app** (uses the saved results, no API key needed):
```
pip install -r requirements.txt
streamlit run app.py
```
**Live questions need your own ANTHROPIC_API_KEY (environment variable locally, or Streamlit Secrets when deployed) and an APP_PASSWORD.**

**Re-run the eval yourself** (makes paid API calls):
```
pip install anthropic pandas numpy rank-bm25
```
Set your own `ANTHROPIC_API_KEY` environment variable, download the raw data into
`data/raw/` (see the notebook), delete the `answers_k5.csv` and `answers_k9.csv` files, and run `analysis.ipynb`.
**No API key is included in this repository.**

## Data
 Canada Labour Code (R.S.C. 1985, c. L-2), Justice Laws Website; reproduced under the Reproduction of Federal Law Order; not an official version; current to December 29, 2025. This only covers federally regulated workplaces.

 This is for informational purposes, not legal advice.

 **Live questions: available with an access code on request**