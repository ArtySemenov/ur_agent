# Workflow: shareable interactive research report

This workflow turns coded data, themes and the researcher's interpretation into **one self-contained HTML file**. It can be emailed, put on SharePoint or opened offline, and it works for any research topic.

The report gets more detailed as the reader scrolls:

| Level | Section | What the reader gets |
|---|---|---|
| 1 | At a glance | Title, key numbers, research questions, a 3–5 bullet summary |
| 2 | Insights | The "so what": each insight with implications, a supporting quote, how many people it rests on, and links to its themes |
| 3 | Themes | Every theme with its strength, its spread across groups, key quotes and counter-evidence; a theme × participant grid; one-off observations |
| 4 | Evidence explorer | Every coded excerpt, filterable by theme, code, topic, group and participant, with search; a chart of codes by participants |
| 5 | About the research | Method, quality and anonymisation, limitations, next steps, participant table, codebook |

**Who writes what:**
- **The researcher** writes the summary, insights, implications and limitations.
- **The AI** prepares the structure, fills in facts from the data, and builds the page.
- **The data** supplies every quote and every count. Nothing is typed in by hand.

## Before you start (gate)
- **Coding QA passed:** see workflows/coding-qa.md.
- **Synthesis done:** see workflows/synthesis.md. The researcher has marked theme Decisions (Keep / Merge / Drop) on the theme board.
- **For an early draft only,** the researcher can explicitly agree to include unreviewed candidate themes. The report then carries a "Candidate themes" banner.

## What the generator needs (works for any topic)
1. **Coded spreadsheet** (`analysis/<round>-coded-transcripts.xlsx`):
   - a **Coded excerpts** sheet with these columns: Excerpt ID, Participant, Topic, Transcript turn, Tags, Excerpt (…), Analyst note
   - a **Participants** sheet with a Participant column, plus optional **Group** and **Context…** columns
   - Group is the comparison you want readers to see (e.g. "New user" / "Expert"). Leave it out if there's no comparison. Up to 3 groups get their own colour; any further groups are shown in grey.
2. **Themes file and theme board** from the synthesis workflow. Only themes marked **Keep** are included, unless the run uses `--include-candidates`.
3. **Report brief** (`analysis/<round>-report-brief.md`): plain markdown, copied from `workflows/templates/report-brief.md`.
   - `# Title`, then `Subtitle:`, `Round:`, `Date:`, `Audience:`, `Contact:` lines.
   - Sections: `## Research questions`, `## Executive summary`, one `## Insight: <statement>` per insight, `## Method`, `## Quality and anonymisation`, `## Limitations`, `## Next steps`.
   - Each insight has a `Themes: T01, T03` line (required) and optionally a `Quotes: P02-15` line, which uses excerpt IDs, never quote text.
   - Any section can have a `Status: draft` or `Status: researcher` line. Draft sections are labelled "Draft · not reviewed by researcher" in the report, and a banner appears.
   - `Implications:` starts the "What this means" part of an insight.
   - Formatting: `- ` bullets, `**bold**`, `*italic*`; `[T01]` links to a theme.
   - `{{n_participants}}`, `{{n_excerpts}}`, `{{n_themes}}`, `{{n_tags}}` and `{{groups}}` are filled in from the data.
   - `[TO WRITE: …]` marks a placeholder. It's highlighted in the report and listed as a warning.

## Steps for the AI
1. **Copy the template** to `analysis/<round>-report-brief.md`.
2. **Pre-fill only facts:**
   - the method from the project files (interview type, dates, how groups were defined)
   - the quality and anonymisation section from the QA records
   - Use `{{tokens}}` for numbers.
3. **Leave the summary, insights, implications and limitations as placeholders.** Only draft them if the researcher explicitly asks. Then mark every drafted section `Status: draft`, and base each insight only on themes the researcher has kept, citing them with `Themes:`.
4. **Build:**
   `python -I workflows/tools/report.py analysis/<round>-report-brief.md analysis/<round>-coded-transcripts.xlsx analysis/<round>-themes.json output/<round>-report.html --board=analysis/<round>-theme-board.xlsx`
   - Add `--include-candidates` only when the researcher has agreed to a draft with unreviewed themes.
   - The build stops if an insight links to a theme that isn't included, cites an excerpt ID that doesn't exist, or has no themes.
   - It warns about typed counts ("7 of 12 parents") and leftover placeholders. Fix typed counts by rewording or using `{{tokens}}`.
5. **Check the page once:**
   - Open it in a browser or a headless render at desktop and phone width (about 390 px), in light and dark mode.
   - Check that every level renders, nothing is wider than the screen, and the chart is readable.
   - Fix what's broken; don't polish endlessly.
6. **Hand over:**
   - Give the file path.
   - List what's still a placeholder and what's still a draft.
   - Remind the researcher that the file contains every anonymised quote, so they should decide who receives it.

## Steps for the researcher
1. Write or rewrite the summary, insights, implications, limitations and next steps in the brief. Set each section's `Status: researcher` when it's yours.
2. Check the themes you've marked Keep on the theme board. Any "My interpretation" you wrote there appears on that theme in the report.
3. Ask the AI to rebuild. Share the HTML file when no Draft labels or placeholders remain.

## Rules
- **No typed quotes or counts.** Quotes come from excerpt IDs; counts come from the data or `{{tokens}}`.
- **The AI never removes a Draft label.** Only the researcher changes `Status: draft` to `Status: researcher`.
- **Interpretation belongs to the researcher** (see CLAUDE.md). AI-drafted insights are a starting point, always labelled as drafts.
- **Anonymised data only.** The report is built from the anonymised coded spreadsheet; raw transcripts are never read into it.
- **Self-contained.** No external fonts, scripts or images, so the report works offline and sends no data anywhere.
- **Save the report in output/; keep the brief in analysis/.**

## Files
| File | Purpose |
|---|---|
| `workflows/templates/report-brief.md` | Blank brief to copy for each round |
| `workflows/tools/report.py` | Validates the brief and data and builds the HTML |
| `workflows/tools/report_template.html` | The page design (layout, styles, charts, interactions) |
