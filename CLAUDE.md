# Project context
This is a user research AI Agent workspace. We use it for planning research, analysing qualitative data, and synthesising findings into reports.

# About me
I am a senior user researcher working in tech. My audience is non-technical stakeholders: products managers, senior responsible owners, and clients.

# Rules
- Always ask clarifying questions before starting a complex task
- Show your plan and steps before executing
- Keep reports and summaries concise - bullet points over paragraphs
- Save all output files to the output folder
- Save all planning documents in the planning folder
- Do not directly edit raw data in the data folder
- Cite sources when doing research
- When working with raw qualitative data avoid anonymise all outputs
- When coding and tagging qualitative data always ask before creating new tags
- After coding or tagging, always run the quality checks in workflows/coding-qa.md (verify every quote, then produce a spot-check sample). Coding is not finished until I have reviewed the spot check
- In synthesis, organise evidence into themes but do not write interpretations, implications or recommendations unless I ask; follow workflows/synthesis.md
- Shareable research reports follow workflows/report.md (a single self-contained HTML file in output/). Never write the summary or insights unless I ask, and label anything you draft as a draft

# Project structure
- workflows/ - Workflow instruction files (plain English recipes the agent follows)
- output/ - Finished deliverables (reports, drafts, analysis)
- planning/ - Planning documents (research plans, discussion guides, informed consent)
- data/ - Raw qualitative data (transcripts, notes)
- analysis/ - Analysis folder containing data that has been transformed (anonymised or coded/tagged)

# Tags
We use a hybrid approach to coding. Deductive coding is used to begin with but we are allowed to create new tags if we need to. Some predefined codes are below:
- behaviour - an observed behaviour that impacts the system
- belief - something they believe is true that impacts behaviour
- structure - something that supports an existing belief within the system
- workaround - when the system doesn't meet their expectations workarounds can identify gaps between design and operational reality
- decision - a decision they must make
- req-bus - a business requirement
- req-func - a functional requirement
- need - a human or systemic need (i need X to do Y)
- frustration - pain point, a frustration of some sort
- desirability - when value is created (if we had X we could do Y) or a desire is expressed (it would be good to...)
- capability - an ability to do something

Tags added from project work (approved):
- access-barrier - a practical obstacle that stops a willing person doing something (supply, appointment times, no GP, no private option, never being offered)
- eligibility - eligibility rules or cut-offs, and how people understand or interpret them
- trust-hcp - trust or distrust in health professionals or institutions as a basis for decisions
- information-source - where people look for information and how they judge whether it is credible
- collective-benefit - an action framed as protecting others or the wider community
