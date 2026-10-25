# ivypath.io: your plan for the week

**Who:** Madi (s16)

**Goal:** Help school students in Kazakhstan choose a university abroad and apply. Every number on the site has its official source, so students can trust it.

**On Demo Day (Sat 31 Oct) you say:** "ivypath has N universities, every fact with its official source and date. X of 20 random facts were right when we checked them by hand."

**Now:** Your site has 86 universities, a QS tab and an AI chat. Good start! The weak spot: the facts have no source and no date.

## How to start

1. Open your workspace: https://kitan-a.com/frp/s16/ and log in.
2. Find the terminal at the bottom of the window. OpenCode starts there by itself. No terminal? Press Ctrl + ` (the key under Esc) or click the menu ☰ > Terminal > New Terminal. Then type opencode and press Enter.
3. Copy the text of your task from this file. Paste it into OpenCode (Ctrl + V, or right-click > Paste) and press Enter. Answer its questions.
4. When the plan looks right, type /build and press Enter. Type /build again until the task is done.
5. Check the result yourself. Then type /save (a save point).

Stuck? Type /fix and write what you see, or paste the red error. Or ask a mentor.

## Tasks

### 1. Day 2: Data out of the page

- Move the universities from index.html into a table file.
- Every fact gets a source link and a date. Unknown = empty, never a guess.

Type this in OpenCode:

```
/plan In projects/ivypath.io: move the universities out of index.html into data/universities.csv and .parquet. One row per university: name, country, official admissions page, IELTS, TOEFL, SAT, cost per year with currency, deadline, international admission rate, QS rank, QS year, and source_url + checked date for every fact. The page must read the file.
```

**Done when:** The page shows the same 86 universities from the CSV.

### 2. Day 2-3: Check every official page

- For each university, open the official admissions page.
- Take IELTS, TOEFL, SAT, deadline and cost from that page, with the link and the date.

Type this in OpenCode:

```
/plan In projects/ivypath.io: for each university in data/universities.csv, open its official admissions page (max 1 request per second) and fill IELTS, TOEFL, SAT, deadline and cost from that page, with the link and today's date. Write a table: how many have each fact, and how many links are broken.
```

**Done when:** A table: how many of the 86 have each fact from an official page.

### 3. Day 3: QS rank with a source

- QS has no free API. Find each rank on topuniversities.com.
- Compare with the list in your page today.

Type this in OpenCode:

```
/plan In projects/ivypath.io: for each university, find its QS rank on topuniversities.com and save rank, year and link. Compare with the old QS list in index.html and tell me how many ranks were wrong.
```

**Done when:** "The old list had E wrong ranks out of 50", and the QS tab shows the year and the link.

### 4. Day 3-4: 30 new universities

- Ask OpenCode to find universities for a gap: for example Korea, Turkey, Hungary, Czechia.
- Check 5 of them yourself.

Type this in OpenCode:

```
/plan In projects/ivypath.io: find 30 new universities popular with Kazakh students in Korea, Turkey, Hungary and Czechia. For each: the official page and the facts from task 2, with source and date. Add them to data/universities.csv.
```

**Done when:** 30 new universities with sources; you checked 5 by hand.

### 5. Day 4: The Prepare tab: an AI helper

- The student enters grade, IELTS/TOEFL/SAT, subject, countries, budget.
- The agent makes a plan from your table only: 3 reach, 3 match, 3 safe universities, a checklist, a timeline and a calendar file.

Type this in OpenCode:

```
/plan In projects/ivypath.io: make the Prepare tab. The student enters grade, scores, subject, countries and budget. Using ONLY data/universities.csv, the class chat model returns JSON: 3 reach, 3 match, 3 safe universities with reasons, a checklist for each, a month-by-month timeline, and an .ics calendar file with the deadlines. Every claim links to its source.
```

**Done when:** 3 different profiles give a full plan, and every deadline is in your table.

### 6. Day 5: Test day

- Pick 20 random facts and check each on the official page.
- 5 real profiles (friends): a mentor checks each plan.
- 10 score cases: is "you get in / you do not" right?

Type this in OpenCode:

```
/plan In projects/ivypath.io: pick 20 random facts from data/universities.csv for me to check by hand, and write results.md with 3 numbers: facts right (X of 20), good plans (Y of 5), score filter right (Z of 10).
```

**Done when:** results.md has the 3 numbers and the date.

### 7. Day 6-7: Share and talk

- Fix the worst problem.
- Share: frp-publish gives a public link.
- A 3-minute talk.

Type this in OpenCode:

```
/plan Make projects/ivypath.io ready to share with frp-publish (see ~/work/materials/DEPLOY.md). Hide the AI chat button on the public page, or show "the AI helper works in the full version".
```

**Done when:** The public link works on a phone, and the talk is ready.

## Watch out

- "Load failed" on your laptop: the AI chat works only inside your workspace. On the public page, hide the chat.
- Your GitHub repository is public: never put a key or a password in it.
- Fewer universities with checked facts are better than many without sources.
