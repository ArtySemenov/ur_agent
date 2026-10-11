# Workflow: quality-checking coded transcripts

Use this every time transcripts are coded or tagged. Coding isn't finished until the researcher has reviewed the spot check.

## Why
The agent can make two kinds of mistake:
- **Hallucination:** a quote that doesn't exist, is changed, or is put in the wrong mouth (interviewer instead of participant). A script catches these.
- **Judgement errors:** the wrong tag, a quote trimmed so its meaning changes, a note that overclaims, important content left uncoded, or a wrong summary fact. Only a human review catches these.

## Steps for the agent

1. **Run the verifier on the finished spreadsheet:**
   `python -I workflows/tools/verify.py analysis/<file>.xlsx`
   - It must report `PROBLEMS: 0`. Fix every flagged row before going on.
   - If new tags have been approved, add them: `--extra-tags=tag-a,tag-b`
2. **Create the spot-check sample:**
   `python -I workflows/tools/spotcheck.py analysis/<file>.xlsx`
   - This writes `<file>-spot-check.xlsx`, a fixed 30-row stratified sample: every tag used, every participant, and extra rows for multi-tag and "belief"-only rows.
   - Use a bigger sample (e.g. `60`) when there are more than about 500 excerpts, or when a tag is new.
3. **Hand over** both files and tell the researcher which tags you were least sure about.
   - Don't describe the coding as final.
   - Don't start synthesis until the QA results pass.
4. **After the review:**
   - Re-code every row for any tag that failed, not just the sampled rows.
   - Tighten that tag's definition in CLAUDE.md, with the researcher's agreement.
   - Re-run steps 1 and 2 with a new seed: `spotcheck.py <file> 30 2`

## Steps for the reviewer (about 45 minutes)

On the **Spot check** sheet, for each row:
1. **Quote found?** Ctrl+F a distinctive phrase in the .docx (data/ folder). Turn numbers count speaker turns; they are not page or line numbers.
2. **Your tags:** tag the quote yourself using the CLAUDE.md codebook. Do this **before** unhiding column L, which holds the agent's tags.
3. **Meaning kept?** Read the turns around it. Did any `[...]` trimming change what the person meant?
4. Unhide column L. **Tags agree?** Y = same tags, Partly = one tag missing or extra, N = different.
5. **Note accurate?** Does the analyst note claim more than the quote supports?

On the **Status check** sheet, confirm each participant's vaccination status and reason. These group the whole analysis.

**Coverage check:** read one whole section (e.g. "vaccination status & reasons") in 2 transcripts. Is anything important missing from the coded excerpts?

**Anonymisation:** filter the excerpts for names, places, employers and job titles.

## Pass marks (calculated on the QA results sheet)
| Check | Pass |
|---|---|
| Quotes found | 100% |
| Meaning kept | 100% |
| Tags fully agree | 80% or more |
| Notes accurate | 90% or more |
| Participant statuses correct | 100% |

If tag agreement fails, look for a pattern before re-coding. The disagreements usually share one tag (e.g. belief vs structure).

## Tools (workflows/tools/, standard library only)
- `transcripts.py`: reads the .docx files in data/ (read-only) and numbers the speaker turns.
- `verify.py`: checks quotes, speakers and tags; exits with an error if anything fails.
- `spotcheck.py`: builds the stratified sample and the QA results sheet.
- `xlsx.py`: reads and writes .xlsx files without extra packages.
