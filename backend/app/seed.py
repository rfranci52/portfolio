"""Seed the projects shown on the site. Idempotent: only runs if empty.

Case studies carry the story in their sections; that narrative is what
separates this from a CRUD-app portfolio. The work-derived studies are
generalized: no client, vendor, or product names, no confidential details.
After editing, run dump_projects.py to rebuild the frontend's projects.json.
"""

from sqlmodel import Session, select

from app.db import engine
from app.models import Project

PROJECTS = [
    Project(
        slug="gui-automation",
        title="GUI Automation for Legacy Systems, Demonstrated End to End",
        tagline=(
            "I automate desktop apps that have no API. To prove it without exposing "
            "confidential systems, I built a realistic one and automated it two ways, on video."
        ),
        summary=(
            "For years my most valuable skill, turning a manual click-through process into "
            "a hands-off tool, was also the hardest to show, because it lives inside closed "
            "systems I can't record. So I built CaseDesk: a complete desktop case-management "
            "app running on synthetic data, and automated it two ways. One bot drives it "
            "purely by sight, like a person. A separate engine watches a process once and "
            "drafts a reviewable automation from the recording. Both run on video, with "
            "nothing confidential in frame."
        ),
        tech=["Python", "pyautogui", "OpenCV (image matching)", "Claude Vision API",
              "PySide6 (Qt)", "SQLite", "openpyxl", "paramiko (SFTP)"],
        highlights=[
            "Built CaseDesk from scratch as a safe, shareable target: a real desktop CMS with a login gate, tabbed account views, search, and a document-export flow, all on synthetic data",
            "Approach one, image-recognition RPA: drives the app by sight, locating each control on screen, and waits for the interface to actually reach a state instead of sleeping and hoping",
            "Approach two, a record-and-learn engine: segments a screen recording into steps by frame-differencing, then a vision model drafts each step's action and the condition that means it's done",
            "The hard part, solved: knowing when a step has finished, including steps with no input at all (a page loading on its own), derived from pixels rather than guesswork",
            "In production these run as unattended nightly pipelines that recover on their own, deliver to partners over SFTP, and redact sensitive data by truly removing the text rather than covering it",
        ],
        sections=[
            {"heading": "Making an invisible skill visible",
             "body": "For years the most valuable thing I do, turning a manual click-through process into a hands-off tool, was also the least showable, because it lived inside closed systems I can't expose. This project fixes that. I built a realistic app to automate against, wrote automations that drive it start to finish, and recorded the whole thing. The result is something you can simply watch: proof of the skill, with nothing confidential in frame."},
            {"heading": "The app I built to automate against",
             "body": "CaseDesk is not a mockup. It's a working PySide6 desktop application over a SQLite database: a login gate, a searchable set of accounts with five tabs of detail each, bulk export and update tools that read and write real files, and a document flow that generates actual PDFs, all on entirely synthetic data (fake 900-series SSNs that were never issued). I gave it deliberate friction, the details that make automation hard: a flash-message popup that appears on only some accounts, a separate document-viewer window, click-based navigation. Building a believable line-of-business application, the very kind I spend my days integrating with, is a demonstration in itself."},
            {"heading": "Approach one: driving a GUI by sight",
             "body": "The app has no integration path, so the only way in is the way a person does it, through the screen. The automation locates each control by image recognition, clicks it, types, and reads the result: it signs in, searches an account, dismisses whatever pops up, opens a document, and works the export dialog, in a loop over a whole queue. What makes it robust is that it waits for the actual on-screen state before each step instead of sleeping and hoping, and it handles the popup that appears on some accounts and not others by checking for it and dismissing it only when it's really there. That conditional, state-aware handling is the line between a demo that works once and one that runs an entire queue unattended. It records itself into a clean side-by-side video: the app driven on one half, a narrated log on the other, every click marked."},
            {"heading": "Approach two: learning an automation by watching",
             "body": "The second approach flips the problem. Instead of writing the automation, I record myself doing the process once and let the engine draft it. It captures the screen and the input events on one clock, segments the recording into steps by diffing frames to find where the screen settles, and has a vision model read each before/after pair to name the action and, the genuinely hard part, the completion indicator: the visible evidence that a step has finished and the next can start. Because it has the recorded input as ground truth, the question narrows from guessing what happened to confirming it, and steps with no input, like a page loading on its own, are caught by the pixels alone. It writes a spec plus a review page where a human confirms the draft: the system drafts, the person confirms."},
            {"heading": "In production",
             "body": "In production these techniques aren't demos, they're infrastructure. The same GUI automation runs as unattended nightly pipelines that kick off on a schedule, chain a sequence of scripts, correct stray environment state that would corrupt input, kill and relaunch apps that hang, screenshot the exact moment anything fails, and deliver finished data to external partners over SFTP. A separate document pipeline assembles document packages and runs each through compliance-grade redaction that removes sensitive text from the PDF instead of drawing a box over it, with a per-document audit log. This is the unglamorous plumbing behind reliable automation."},
        ],
        video_url="/demos/casedesk-automation.mp4",
        featured=True,
        sort_order=0,
    ),
    Project(
        slug="legacy-cms-integration",
        title="Reporting and Integration for a Legacy System",
        tagline="Worked out how an older case system organizes its data, validated that against real exports, and made it queryable in seconds.",
        summary=(
            "A firm in a heavily regulated industry ran on an older case-management system "
            "(CMS) with limited integration options. Getting data out meant slow, fragile "
            "graphical user interface (GUI) automation. I worked out how its data was "
            "organized, validated that understanding against real exports, derived account "
            "balances to the penny from a large transaction ledger, and built "
            "reporting on top of it, including a natural-language report builder, turning a "
            "task that took minutes into seconds."
        ),
        tech=["Python", "Structured Query Language (SQL)", "Large language model (LLM)", "openpyxl", "tkinter"],
        highlights=[
            "Built a read-only reporting connection to an older case system with limited integration options, with the data access in a small worker process that the GUI launches and hands a job to",
            "Worked out how the system's data was organized and validated that understanding per column, to the penny, against ground-truth exports",
            "Derived balances from a large transaction ledger by parsing the records inside it; no stored balance columns existed",
            "Natural-language report builder: plain English to real schema fields via a large language model (LLM) bounded by a catalog so it can't invent a field",
            "Automated report delivery over email: an inbox watcher that detected a request, ran the report from the emailed input, and replied with the finished file in minutes, the loop that led to the self-serve natural-language builder",
            "The report builder is strictly read-only against a business-critical production database",
        ],
        sections=[
            {"heading": "The problem",
             "body": "The business ran on an older case-management system with limited integration options. Getting data out meant driving the GUI with automation: slow, fragile, and it broke whenever the screen changed. I wanted to pull any fields for any list of accounts in seconds, safely, without touching the GUI."},
            {"heading": "A read-only reporting connection",
             "body": "Standard ways of connecting to the system were limited, so I built a reporting connection of my own. The data access runs in a small worker process that the GUI launches as a subprocess and passes a job to (the same worker-launcher pattern good automation uses). The report builder built on this connection is strictly read-only against production."},
            {"heading": "Understanding the data",
             "body": "I worked out how the system organized its data by treating a real system export as ground truth: I ran my own field resolvers over the same accounts and measured a per-column match rate, building up my understanding incrementally until the business fields matched exactly. The hardest part was money: balances weren't stored anywhere; they had to be derived by parsing a large transaction ledger, and I validated the derivation to the penny."},
            {"heading": "Reports on request, by email",
             "body": "Once I could pull any data safely, the bottleneck moved to delivery: people would email me asking for a report on a list of accounts. So I built an automation that watched a shared inbox and, whenever a request arrived with its account list attached, ran the report and emailed the finished file back, often within a couple of minutes. To whoever asked, it felt like magic: they sent an email and the report simply arrived. I later extended it into a service that handled routine report requests sent by email, bounded by checks and by rules I defined for what it must refuse. That request-to-report-to-reply loop is exactly what led to the natural-language layer below: the obvious next step was to let people describe the report they wanted in plain English."},
            {"heading": "The natural-language layer",
             "body": "Non-technical users don't know column names, so they describe the fields they want in plain English. A language model maps the request onto the real schema, but bounded by a catalog of fields that actually exist so it can never invent one, and a checklist screen shows the confident matches pre-checked and asks about anything unclear before running. It turned a specialist database task into something anyone could self-serve."},
            {"heading": "Try it live",
             "body": "The report builder above ran inside a confidential production system, so it can't be shown directly, so I rebuilt the idea in the open. This is a self-contained demo where you type a question in plain English about a small fictional business (a pizza shop) and watch it become Structured Query Language (SQL), run against a real database, and return live rows. It keeps the guardrails that actually mattered in production: the model is given a described schema so it can't invent a field or table, every generated query is read-only, and when a request is ambiguous it asks a clarifying question instead of guessing. Different data, same engine: the natural-language-to-query layer, lifted out and made something you can type into yourself."},
        ],
        demo_url="https://demo.rakimfrancis.com",
        featured=True,
        sort_order=1,
    ),
    Project(
        slug="algorithmic-trading",
        title="Algorithmic Trading System",
        tagline="A self-built quant stack: live bots on Coinbase and Alpaca, an event-sourced core that audits itself, and a large language model (LLM) that reviews every trade cycle.",
        summary=(
            "A personal end-to-end trading system, rebuilt around a hard lesson: "
            "spreadsheets make dishonest ledgers. Three live bots (two crypto mandates on "
            "Coinbase, one equities on Alpaca) run real money. The crypto side now sits on "
            "an event-sourced SQLite core: every trade, price tick, and system event is an "
            "append-only fact, and positions and profit and loss (P&L) are derived views, "
            "so the books can be re-audited from raw history at any time. A crash-safe "
            "execution engine rests maker limit orders on the exchange, reconciles itself "
            "against real order history at every startup, and is designed to reduce "
            "exchange fees. An LLM (Claude) reviews each completed cycle under a fixed "
            "monthly budget."
        ),
        tech=["Python", "SQLite", "Coinbase API", "Alpaca API", "Claude API", "CoinGecko API", "Google Sheets"],
        highlights=[
            "Two buy-trigger families: laddered buys below average cost, sized to the depth of the dip, plus pullback-from-high entries that restart cycles after each exit, with per-coin aggressiveness set by market-cap tier and time-based re-arms so a position can never strand",
            "Event-sourced core: trades, prices, and events are append-only facts; positions and P&L are derived views, so an accounting bug can be fixed retroactively and drift is caught by a standing audit query instead of luck",
            "The audit layer paid for itself on day one: it flagged a recorded loss that had never actually happened (a legacy double-count) and the books were corrected from raw trade history",
            "Execution engine rests maker limit orders on the exchange: exits keep working while the bot is offline, fills are booked atomically, startup reconciliation catches anything that filled in the gap, and the design aims to reduce exchange fees by paying maker rates",
            "Strategy-as-spec: the rules live in adjudicated specification documents, and the rebuild shipped behind 35 automated tests against a simulated exchange, with zero real orders placed in testing",
            "An LLM (Claude) reviews every completed cycle and writes a briefing at every startup, under a hard monthly cost budget",
        ],
        sections=[
            {"heading": "End to end, and honest about it",
             "body": "This is a system I built for myself, start to finish, and it trades real money. Three bots with two mandates: one crypto bot harvests cycles (buy below its average cost, exit the whole position at a fixed take-profit), a second accumulates long-term positions and sells only small skims into strength, and an equities bot runs the same family of ideas on Alpaca. I'm deliberately leading with the engineering rather than any claim about returns: the interesting part isn't 'it makes money,' it's that it's built with the discipline of something that has to be trusted with real money."},
            {"heading": "An event-sourced core, because spreadsheets make dishonest ledgers",
             "body": "The first version kept its state in spreadsheets, and the spreadsheets lied. A month of forensics on the raw trade history turned up a recorded loss that never happened (a double-counted cost basis from a long-dead bug), coins sold that were never logged as bought, and reset logic that silently didn't exist. The fix wasn't better spreadsheets, it was a different shape of storage: an SQLite core where trades, price ticks, and system events are append-only facts, and positions, cycle P&L, and ledgers are views derived from them. Stored rollups keep bugs forever; derived views recompute the truth, so fixing an accounting bug retroactively fixes history. A standing drift-detection query now compares recorded results against the raw journal, and it caught its first real discrepancy the day it was turned on."},
            {"heading": "Execution built to be trusted",
             "body": "The rebuilt execution layer rests maker limit orders on the exchange instead of chasing prices with instant fills. Exits sit on the book around the clock, so a take-profit executes even if the bot is down. Entries started out proximity-armed, with a buy posted only when price came within a narrow band of its trigger. Price oscillating at the edge of that band caused repeated post-and-cancel churn, so since July 2026 a buy rests whenever it's affordable and is cancelled only for a cause. Fill accounting is atomic (a fill books its trade, state change, and order close together or not at all), and on every startup the engine reconciles against the exchange's real order history and books anything that filled while it was offline. The design also aims to reduce exchange fees by paying maker rates instead of taker rates, a cost goal, not a returns claim."},
            {"heading": "The strategy is a document, not a habit",
             "body": "I build heavily with AI assistance, and the failure mode of that workflow is drift: an assistant quietly 'corrects' your strategy toward the textbook version of itself. The fix was to make the strategy a contract. Its intent lives in specification documents written in plain language; every divergence between what the code did and what I actually wanted got an explicit ruling, recorded with its reasoning; and the rebuilt bots shipped behind 35 automated tests, run against a simulated exchange, that assert the specs, including one test whose whole job is to fail loudly if anyone ever re-introduces the most persistent unwanted 'correction.' The AI tools work from that contract; the spec, and the judgment behind it, is mine."},
            {"heading": "An LLM that reviews its own trades",
             "body": "After every completed buy-and-sell cycle, and at every startup, the system hands its trade history to an LLM (Claude) and asks what worked and what stalled. It may suggest a rule change after a cycle, but tiers, the take-profit target and buy sizing stay my decisions. It all runs under a hard monthly cost budget, so a background analyst never turns into an expense. It is a small, honest example of putting an LLM to work inside a real system instead of bolting one on."},
            {"heading": "Realistic backtesting",
             "body": "Most hobby backtests look great because they quietly ignore costs. This one replays years of real market data and models both fees and taxes, so the output is a realistic estimate rather than a vanity number. The rebuilt system also records its own price history from live polling, sampled every 10 minutes, building a first-party dataset so future backtests can replay against exactly what the live bots saw."},
        ],
        featured=True,
        sort_order=2,
    ),
    Project(
        slug="portfolio-site",
        title="This Portfolio Site",
        tagline="The site you're reading: React and TypeScript on Vercel, Python serverless functions, Neon Postgres, and a retrieval chatbot over my written case studies.",
        summary="The site you're reading. I built it as a React and TypeScript site on Vercel, with Python serverless functions and Neon Postgres behind it, and a retrieval chatbot that answers from my written case studies. Project data is baked into the deployed bundle. The FastAPI backend in the repository is used for local development only.",
        tech=["React", "TypeScript", "Vite", "Tailwind", "Vercel", "Python serverless functions", "Neon Postgres", "pgvector", "Claude API", "FastAPI (local development only)"],
        highlights=[
            "A React and TypeScript front end built with Vite and Tailwind and deployed on Vercel, with project data baked into the bundle",
            "Python serverless functions handle the contact form, the chatbot and visit tracking, each one a single self-contained file",
            "Neon Postgres is the database, with a separate least-privilege role for each task",
            "A retrieval chatbot searches my written case studies by meaning and by exact words, then Claude writes an answer from the passages it found and shows its sources",
            "A FastAPI backend lives in the repository and is used for local development only",
        ],
        sections=[
            {"heading": "What it actually runs on",
             "body": "It's a React and TypeScript site, built with Vite and Tailwind and hosted on Vercel. Project data is baked into the deployed bundle, so the project pages don't need a server. The parts that do need one run as Python serverless functions: the contact form, the chatbot, and visit tracking. Neon Postgres is the database, and the functions connect through least-privilege roles, each limited to one task. There's also a FastAPI backend in the repository, which I use for local development only."},
            {"heading": "A chatbot over my own case studies",
             "body": "The chat on the home page answers questions from case studies I wrote. For each question, code searches them two ways, by meaning and by exact words, merges the results, and hands the best passages to Claude, which writes the answer from those passages and shows where it came from. If my case studies don't cover something, it says that instead of guessing. The How this works page walks through the full path of a question."},
        ],
        featured=False,
        sort_order=4,
    ),
    Project(
        slug="fantasy-basketball-agent",
        title="An AI Agent That Runs a Fantasy Basketball Team",
        tagline="An artificial intelligence (AI) agent that manages my ESPN fantasy basketball team every day: Claude makes the judgment calls through tools, and code enforces every rule and owns every write.",
        summary="I built a system that manages my fantasy basketball team day to day without me. Claude makes the judgment calls through tool use: which free agent to add, which player to drop, and when, weighing injury news and minutes changes. Python does everything else, from ESPN reads and category math to lineups, and every write to ESPN passes guardrails the model has no way around. Three scheduled jobs have run it unattended on a Mac mini since October 17, 2026, under a hard monthly budget, with a code-only backup mode for when the model can't decide.",
        tech=["Python", "Claude (tool use)", "Anthropic Python library", "ESPN web endpoints", "launchd", "requests"],
        highlights=[
            "Claude works through six tools that read the week, list available players, check injuries and news, score a move, and submit it. Its only path to a write is the submit tool, and that tool checks every rule again first",
            "Key players are protected by two independent layers: the guardrails that judge each move, and a last check inside the one function every ESPN write goes through",
            "Each of the nine categories gets a win chance from a normal approximation, percentages come from projected makes and attempts, and lineups are solved with maximum bipartite matching",
            "A watcher checks often around games and wakes the model only on real triggers, with a daily cap",
            "A spend ledger paces the model's effort under a hard monthly budget, and a code-only backup mode takes over behind the same guardrails when the model can't decide",
            "As of November 9, 2026: first of 10 teams and 3-0 in matchups, after finishing 9th by hand last season. Three weeks is a small sample, and a better draft could explain some of it",
        ],
        sections=[
            {"heading": "Why it exists",
             "body": "Across four seasons in my league, the managers who kept rotating free agents through their rosters and set lineups every day finished at the top. I made 5 to 12 pickups a season and finished 6th, 5th, 8th and 9th. I knew what the job was and I wasn't doing it, because doing it means checking injuries, schedules and the waiver wire every single day. Most of that work is mechanical, so a script can do it. The part that isn't mechanical is the daily call: whose minutes are about to change, and whether he's worth one of the week's limited pickups. That split, mechanical work for code and the judgment call for a model, became the design."},
            {"heading": "Claude decides, code enforces",
             "body": "Claude gets the judgment call and nothing else. It works through six tools: read the week, list the available players, read the injury report, read a player's news, score a move, and submit a move. Every rule I care about is enforced in code, not left to the prompt: who can be dropped, the weekly pickup limit, a last pickup held back for injuries, whether a player is locked, and whether the move actually helps. The submit tool runs all of those again and refuses whatever they block, so a rule holds even if the model ignores it. The one thing I set as absolute was that none of my main players could ever be dropped, so they're protected twice: by the guardrails that judge each move, and by a separate last check inside the one function every ESPN write goes through, which refuses a protected drop no matter what code built the request."},
            {"heading": "The math behind each call",
             "body": "A head-to-head category week is nine small races, so each one gets a win chance. I project both teams' totals over the starter games they have left, compare the margin to its standard deviation, and read a win chance off a normal approximation. Expected category wins is the sum of the nine. Field goal and free throw percentages are never averaged: I project makes and attempts, then divide. Who can start on a given day is a maximum bipartite matching of players to the 10 starter seats, which handles position eligibility exactly and, with the best players seated first, decides who sits on crowded days. A move has to clear a test before it can happen. It must raise expected category wins or clearly lift a close category, it can't flip a projected win into a loss, it can't cost starter games unless the gain clearly outweighs them, and it's judged on top of any pending claims as if they land."},
            {"heading": "Running unattended",
             "body": "Three scheduled jobs run it on a Mac mini. The daily job runs overnight and waits for ESPN's waiver run, so the decision sees newly cleared players as soon as they're available. It settles the night's claims, lets Claude decide, and sets the day's lineup. Two lineup passes later in the day are code only. The watcher checks often while games are close or under way, and less often otherwise. Most of what it sees it handles in code. It wakes the model only on real triggers: one of my players newly ruled out, another team dropping someone whose best swap clears a bar, a free agent's ownership jumping, or a fresh injury that opens minutes for an available teammate. Those wakes are capped each day, with one always kept for my own players. Every move sends the reason to my phone."},
            {"heading": "Bounded cost",
             "body": "The model runs under a hard monthly budget. Every call is priced from its token usage and written to a spend ledger, and each day's decision gets a share of what's left. The code picks the highest effort level that share covers, using what decisions at each level have actually cost so far, so spending fast turns the effort down on its own."},
            {"heading": "Failing safely",
             "body": "Writes never retry on their own, because ESPN's endpoints have no idempotency key and a resend could make the same move twice. A write that gets no answer is recorded as unknown, counts against the limits until it's settled against ESPN's own records, and ends that run's moves. If the budget runs out, the Anthropic key is missing, or a model call fails before any move has been made, a code-only backup mode decides instead. It makes instant free-agent adds only, behind the same guardrails, with a bar that rises as the week's pickups run low. It can't read news, so it won't add anyone on the injury report. If a model call fails after a move has been made, the run just stops, and the next run starts from a fresh read. Since November 1, each daily run with pickups left also logs what backup mode would have done next to Claude's choice, so the gap can be measured instead of assumed."},
            {"heading": "What it got wrong, and what changed",
             "body": "On an early dry run, Claude reasoned that claiming a player early helps. Waivers in my league go by waiver order, so the tools now show our place in line, the instructions explain it, and a claim from anywhere but first gets a backup claim. A test run found that pending claims hold roster spots, so the code stopped calling a spot open while a claim was waiting on it. A review of the injury feature found that a minutes estimate of \"nan\" (not a number) slipped past every bound and made the move test pass. Minutes must now be a finite number, and the move test fails closed. Then a stale injury report woke the model for a player who had already played. Claude caught it from the news, but the day's spare wake was spent and later injuries couldn't get through, so now an injury wakes the model only if the fantasy game's own status also says out. The timing work got the heaviest scrutiny: a 56-agent adversarial review confirmed 44 findings and refuted 8, all fixed the same night, followed by later review rounds. One of those fixes cancels any pending claim whose drop I've since protected."},
            {"heading": "Results so far, as of November 9, 2026",
             "body": "After three completed matchups the team is first of 10 and 3-0, with a 17-9-1 record in category results (6-2-1, 5-4-0, 6-3-0). It has made 21 acquisitions, the most in the league, and the next highest is 16. Last season, managing by hand, I finished 9th with 7 adds. Since going live on October 17 it has logged 58 live ESPN transactions (20 free-agent adds, 10 waiver claims, 27 roster moves and 1 future-roster move), and its decision log holds 257 entries. I'm not claiming the agent earned that record. Three weeks is a small sample, and a better draft could explain some of it. What the numbers do show is the thing I set out to fix: the daily work is getting done."},
            {"heading": "How I built it",
             "body": "It's about 6,000 lines of Python, built with Claude Code, and I'm open about that. I set the rules and the design: what belongs to the model and what belongs to code, who can be dropped, what a move must clear, and when the watcher may wake the model. Claude Code did most of the implementation and ran the review passes. ESPN's fantasy endpoints are unofficial and undocumented, so I treated every untested call as unverified. There's no public code for this project, so this page is a write-up."},
        ],
        featured=True,
        sort_order=3,
    ),
]


def seed() -> None:
    with Session(engine) as session:
        if session.exec(select(Project)).first() is not None:
            return
        for project in PROJECTS:
            session.add(project)
        session.commit()
