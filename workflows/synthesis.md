# Workflow: synthesising coded data into themes

**The AI organises; the researcher interprets.**

The AI's job is to make synthesis easy: group the evidence, describe what participants said, and show how strong and how contested each pattern is. The researcher decides what the themes mean, why they matter and what follows from them. The AI never writes the "so what", implications or recommendations unless the researcher explicitly asks.

## Before you start (gate)
- **QA passed:** the coded spreadsheet has passed the checks in workflows/coding-qa.md (verify.py reports 0 problems, and the researcher has signed off the spot check).
- **Tags settled:** any new tags have been approved and applied.

## Steps for the AI

1. **Get an overview.** Run:
   `python -I workflows/tools/themes.py overview analysis/<coded>.xlsx`
   Then read the patterns:
   - which tags appear for how many people
   - how tags differ between groups. Groups come from the optional **Group** column on the coded spreadsheet's Participants sheet (e.g. "New user" / "Expert"). Without it, there's no split.
   - which topics are dominated by which tags
2. **Read every excerpt**, topic by topic, and then tag by tag for the cross-cutting tags. Don't theme from the counts alone.
3. **Draft candidate themes** in `analysis/<round>-themes.json`. For each theme:
   - **id:** T01, T02 and so on. Never reuse or renumber an ID once the researcher has seen the board.
   - **name:** a plain statement of the pattern, in participants' terms ("Parents who wanted the vaccine couldn't get it").
   - **description:** 1–3 sentences on what participants said and did. Use quantity words that match the counts: "most", "several", "some", "two parents".
   - **supporting:** the excerpt IDs that support the theme. An excerpt can support several themes.
   - **key_quotes:** 2–4 IDs from supporting, picked to show the range, not just the strongest.
   - **counter:** excerpt IDs that contradict or complicate the theme. Look for them actively.
   - **counter_summary:** one line describing the counter-evidence, or "None found."
   - **prompts:** 2–3 neutral questions to help the researcher think (see rules below).

   Patterns from only one participant go under **outliers**, not themes. Aim for about 12–20 themes. Too many fragments the picture; too few hides differences.
4. **Build the board.** Run:
   `python -I workflows/tools/themes.py board analysis/<coded>.xlsx analysis/<round>-themes.json analysis/<round>-theme-board.xlsx`
   - The script refuses to build if: an ID doesn't exist; a theme has fewer than 2 participants; key quotes aren't in supporting; counter-evidence is missing without "None found."; a prompt isn't a question; or interpretive wording is found (should, must, need to, recommend, implies, therefore…).
   - Fix the themes file and re-run. Never work around the check.
5. **Review the unassigned excerpts** on the board. If any share a pattern, or clearly belong to an existing theme, update the themes file and rebuild. It's fine to leave general background unassigned.
6. **Hand over:**
   - give the path to the board, the number of themes, outliers and unassigned excerpts, and which themes you were least sure about
   - don't summarise "key insights" or "what this means"; the board is the output

## Steps for the researcher (about 1–2 hours)
1. On **Themes**, read each theme with its key quotes and counter-evidence. Use **Theme evidence** (filter by Theme ID) to see everything behind it, and **Theme x participant** to see who it comes from.
2. Fill in **Decision**: Keep / Merge (with which theme) / Split (how) / Rename (to what) / Drop.
3. Check **Unassigned excerpts** and **Outliers** for anything important that's missing.
4. For the themes you keep, write **My interpretation (so what?)** and **Implications / who needs to know**. The prompts are there to think with; ignore them if they're not useful.
5. Ask the AI to apply your decisions.

## Applying the researcher's decisions (AI)
- Edit the themes file to merge, split, rename or drop, as instructed. Keep the surviving IDs; give new themes new IDs.
- Rebuild the board. The script carries over everything in the researcher's columns, matched by Theme ID.
- Never write in, change or summarise the researcher's columns. If merged themes both have researcher notes, say so; don't combine them yourself.

## Rules
- **The AI chooses evidence; scripts make the numbers and quotes.** Never type a quote or a count into the themes file or a summary. They come from the coded spreadsheet through themes.py.
- **Count people, not quotes.** Report "n of N participants" and the split between groups. No percentages with small samples.
- **Strength labels describe spread, not truth:** Strong = 6+ participants, Moderate = 3–5, Thin = 2.
- **Describe, don't explain.** Write what participants said and did. Explanations ("because the system…"), judgements ("fails parents"), implications and recommendations belong to the researcher.
- **Every theme gets counter-evidence**, or an explicit "None found." after looking.
- **Interviewer-led content:** if a participant only agreed with the interviewer's summary, it isn't evidence.
- **Prompts:**
  - They must be open, neutral questions that don't contain an answer.
  - Good: "Who is most affected by this, and who isn't?", "How does this differ between the two groups?", "What doesn't this data tell us?"
  - Avoid questions that assert a conclusion ("Why is the booking system failing parents?") or a solution ("Would evening clinics help?").
- **Anonymisation:** themes files hold only excerpt IDs and the AI's own descriptions. Never copy raw transcript text into them.

## Files
| File | Written by | Purpose |
|---|---|---|
| `analysis/<round>-themes.json` | AI | Theme definitions: names, descriptions, excerpt IDs, prompts |
| `analysis/<round>-theme-board.xlsx` | themes.py (researcher fills their columns) | The working board |
| `workflows/tools/themes.py` | – | Overview, validation, board build, carry-over of researcher columns |
