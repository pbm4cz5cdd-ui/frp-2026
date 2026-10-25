# ivypath.io: tasks for the week (Madi, s16)

**Idea:** help school students in Kazakhstan choose a university abroad and apply: a catalog with filters, "where do
my IELTS/TOEFL/SAT scores get me in", a page for each university, and an AI helper.
**Track:** Data and web (+ an AI agent).

**Today (Day 1):** one file `index.html` with 86 universities (12+ countries), IELTS for all, SAT for 14, one
official link each, a QS tab (a list typed into the code), guides, exam prices, an AI chat. Good start!
**The weak spot:** the facts have no source and no "checked on" date, and admission rules change every year. A
student must be able to trust every number. So this week: **trustworthy data first, then the agent.**

**Demo Day claim (measure it, then fill in):** "ivypath has N universities, every fact with its official source and
date; X of 20 random facts were right when we checked them by hand; the Prepare tab builds a personal plan for a
student in Y seconds."

## Tasks

1. **Day 2 - Data out of the page (Dataset 1).** Move the universities out of `index.html` into
   `data/universities.csv` (and `.parquet`). One row per university: name, country, official admissions page,
   IELTS, TOEFL, SAT, cost per year (with currency), deadline, admission rate for international students, QS rank,
   QS year, and for every fact: `source_url` + `checked` (date). Unknown = empty, never a guess. The page reads the file.
   Done when: the page shows the same 86 universities from the CSV, and the CSV has the source columns.
   Use: the agent (Python, pandas), materials/GITHUB.md (save every step).

2. **Day 2-3 - Check every official page (Dataset 1).** For each university, open its official admissions page
   (web fetch) and fill IELTS, TOEFL, SAT, deadline and cost from that page, with the link and the date.
   Done when: a table: how many of the 86 have each fact from an official page, and how many links are broken.
   Use: skill web-search (1 request per second).

3. **Day 3 - QS ranking with a source (Check 1).** QS has no free public API, and its data belongs to QS. So: for each
   of your universities, find its QS rank on topuniversities.com with web fetch and save rank + year + link. Then
   compare with the list typed into your page today (`QS_RAW`).
   Done when: "the typed list had E wrong ranks out of 50 checked", and the QS tab shows the year and the link.
   Use: skill web-search.

4. **Day 3-4 - New universities with the agent (Dataset 2).** Ask OpenCode to find new universities for a gap (for
   example: Kazakh students' favourites in Korea, Turkey, Hungary, Czechia), each with the official page and the facts
   from task 2.
   Done when: 30 new universities in the CSV, each fact with a source; you checked 5 of them by hand.
   Use: skill web-search.

5. **Day 4 - The "Prepare" tab: an agent (Agentic 1).** The student enters a profile: grade, IELTS/TOEFL/SAT,
   subject, countries, budget per year. The agent, using ONLY your CSV: (a) a shortlist: 3 reach, 3 match, 3 safe
   universities, with the reason; (b) a checklist for each: documents, tests, deadlines; (c) a month-by-month
   timeline until the first deadline; (d) a calendar file (.ics) with the deadlines. Every claim links to its source.
   Done when: for 3 different profiles the tab gives a full plan, and every deadline in it is in your CSV.
   Use: the class chat model (JSON answers), skill page-check.

6. **Day 5 - Test (measure the main promise).** (a) Facts: pick 20 random facts from the CSV, check each one on the
   official page yourself: X of 20 right. (b) Prepare: 5 real profiles (friends, classmates): a mentor checks each
   plan: are the shortlists sensible, are the deadlines right? (c) The score filter: 10 cases, is "you get in / you
   do not" right?
   Done when: `results.md` with the 3 numbers and the date.

7. **Day 6-7 - Show it, page, talk.** Fix the worst problem from Day 5. Share: `frp-publish projects/ivypath.io`
   gives a public link (materials/DEPLOY.md). Talk: problem -> data you can trust -> agent -> numbers -> limits.
   Done when: the public link works on a phone, and a 3-minute talk is ready.

## Why "Load failed" on your laptop

The AI chat calls the class model through your workspace (`/proxy/19040`). That path exists only inside your
workspace. On your laptop, on GitHub Pages or on the public link, the catalog works, but the chat cannot reach the
model. During FRP: show the chat from your workspace link. For the public page: hide the chat button, or show a
message "the AI helper works in the full version".

## After FRP: a real domain and user accounts

- **Domain + hosting:** GitHub Pages (free) + a domain you buy (about 10-40 $ a year; `.io` is the most expensive).
- **User accounts and saved lists:** a free database service with login (for example Supabase or Firebase).
- **The AI chat on the public site:** it needs a small server of your own with your own API key (never put a key in
  the page). Ask your mentor; it is a good next step after Demo Day, not this week.

## Risks

- **Official pages are hard to read** (PDFs, many pages). Backup: fewer universities with all facts checked is better
  than many without sources; mark the rest "not checked".
- **The agent invents facts.** Backup: give it only rows from your CSV, ask for JSON with the source of each fact,
  and show "no data" when the CSV has none.
