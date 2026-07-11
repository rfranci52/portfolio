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
             "body": "In the real job these techniques aren't demos, they're infrastructure. The same GUI automation runs as unattended nightly pipelines that kick off on a schedule, chain a sequence of scripts, correct stray environment state that would corrupt input, kill and relaunch apps that hang, screenshot the exact moment anything fails, and deliver finished data to external partners over SFTP. A separate document pipeline assembles legal packages and runs each through compliance-grade redaction that removes sensitive text from the PDF instead of drawing a box over it, with a per-document audit log. This is the unglamorous plumbing a real operation runs on."},
        ],
        video_url="/demos/casedesk-automation.mp4",
        featured=True,
        sort_order=0,
    ),
    Project(
        slug="legacy-cms-integration",
        title="Direct-Database Integration for a Legacy CMS",
        tagline="Reverse-engineered a closed legacy system with no API, and made its data queryable in seconds.",
        summary=(
            "A firm in a heavily regulated industry ran on a legacy Delphi case-management "
            "system with no API and no supported integration path. The only way out was slow, "
            "fragile GUI automation. I connected directly to its embedded database engine "
            "through the vendor's own C client library, reverse-mapped ~127 business fields "
            "across a dozen tables, derived account balances to the penny from a 350 MB "
            "transaction ledger, and wrapped it in a natural-language report builder, turning "
            "a task that took minutes into seconds."
        ),
        tech=["Python", "ctypes", "embedded database (SQL)", "Claude API", "openpyxl", "tkinter"],
        highlights=[
            "Connected to a no-API legacy database through the vendor's 32-bit C engine via ctypes, driven from a 32-bit worker the 64-bit GUI shells out to",
            "Reverse-mapped ~127 fields across a dozen tables, validated per-column to the penny against ground-truth exports",
            "Derived balances from a 350 MB transaction ledger by parsing embedded records; no stored balance columns existed",
            "Natural-language report builder: plain English to real schema fields via an LLM bounded by a catalog so it can't invent a field",
            "Automated report delivery over email: an inbox watcher that detected a request, ran the report from the emailed input, and replied with the finished file in minutes, the loop that led to the self-serve natural-language builder",
            "Strict read-only discipline against a business-critical production database",
        ],
        sections=[
            {"heading": "The problem",
             "body": "The business ran on a legacy Delphi case-management system with no API, no supported export, and no database documentation. Getting data out meant driving the GUI with automation: slow, fragile, and it broke whenever the screen changed. I wanted to pull any fields for any list of accounts in seconds, safely, without touching the GUI."},
            {"heading": "The connection breakthrough",
             "body": "There was no ODBC driver (the database engine was end-of-life). Instead I reused the vendor's own C client engine that ships with the app, calling its C API directly from Python with ctypes. Because that engine is 32-bit, I drove it from a small 32-bit worker process that the 64-bit GUI launches as a subprocess and passes a job to (the same worker-launcher pattern good automation uses). All access was strictly read-only against production."},
            {"heading": "Reverse-mapping the schema",
             "body": "Nothing was documented, so I treated a real system export as ground truth: I ran my own field resolvers over the same accounts and measured a per-column match rate, building the map up incrementally until ~127 fields across a dozen tables matched exactly. The hardest part was money: balances weren't stored anywhere; they had to be derived by parsing a 350 MB transaction ledger, and I validated the derivation to the penny."},
            {"heading": "Reports on request, by email",
             "body": "Once I could pull any data safely, the bottleneck moved to delivery: people would email me asking for a report on a list of accounts. So I built an automation that watched a shared inbox and, whenever a request arrived with its account list attached, ran the report and emailed the finished file back, often within a couple of minutes. To whoever asked, it felt like magic: they sent an email and the report simply arrived. That request-to-report-to-reply loop is exactly what led to the natural-language layer below: the obvious next step was to take myself out of the loop entirely and let people describe the report they wanted in plain English."},
            {"heading": "The natural-language layer",
             "body": "Non-technical users don't know column names, so they type plain English ('client', 'balance', 'last payment'). A language model maps the request onto the real schema, but bounded by a catalog of fields that actually exist so it can never invent one, and a checklist UI shows the confident matches pre-checked and asks about anything unclear before running. It turned a specialist database task into something anyone could self-serve."},
            {"heading": "Try it live",
             "body": "The report builder above ran inside a confidential production system, so it can't be shown directly, so I rebuilt the idea in the open. This is a self-contained demo where you type a question in plain English about a small fictional business (a pizza shop) and watch it become SQL, run against a real database, and return live rows. It keeps the guardrails that actually mattered on the job: the model is given a described schema so it can't invent a field or table, every generated query is read-only, and when a request is ambiguous it asks a clarifying question instead of guessing. Different data, same engine: the natural-language-to-query layer, lifted out and made something you can type into yourself."},
        ],
        demo_url="https://demo.rakimfrancis.com",
        featured=True,
        sort_order=1,
    ),
    Project(
        slug="algorithmic-trading",
        title="Algorithmic Trading System",
        tagline="A self-built quant stack: live bots on Coinbase and Alpaca, an event-sourced core that audits itself, and an LLM that reviews every trade cycle.",
        summary=(
            "A personal end-to-end trading system, rebuilt around a hard lesson: "
            "spreadsheets make dishonest ledgers. Three live bots (two crypto mandates "
            "on Coinbase, one equities on Alpaca) run real money. The crypto side now "
            "sits on an event-sourced SQLite core: every trade, price tick, and system "
            "event is an append-only fact, and positions and P&L are derived views, so "
            "the books can be re-audited from raw history at any time. A crash-safe "
            "execution engine rests maker limit orders on the exchange, reconciles "
            "itself against real order history at every startup, and roughly halved "
            "the exchange's take per cycle. An LLM (Claude) reviews each completed "
            "cycle under a fixed monthly budget."
        ),
        tech=["Python", "SQLite", "Coinbase API", "Alpaca API", "Claude API",
              "CoinGecko API", "Google Sheets"],
        highlights=[
            "Two buy-trigger families: laddered buys below average cost, sized to the depth of the dip, plus pullback-from-high entries that restart cycles after each exit, with per-coin aggressiveness set by market-cap tier and time-based re-arms so a position can never strand",
            "Event-sourced core: trades, prices, and events are append-only facts; positions and P&L are derived views, so an accounting bug can be fixed retroactively and drift is caught by a standing audit query instead of luck",
            "The audit layer paid for itself on day one: it flagged a recorded loss that had never actually happened (a legacy double-count) and the books were corrected from raw trade history",
            "Execution engine rests maker limit orders on the exchange: exits keep working while the bot is offline, fills are booked atomically, startup reconciliation catches anything that filled in the gap, and the redesign cut the exchange's take from roughly 30% to 15% of gross per cycle",
            "Strategy-as-spec: the rules live in adjudicated specification documents, and the rebuild shipped behind 35 automated tests against a simulated exchange, with zero real orders placed in testing",
            "An LLM (Claude) reviews every completed cycle and writes a briefing at every startup, keeping a running memory of its own past analyses, under a hard monthly cost budget",
        ],
        sections=[
            {"heading": "End to end, and honest about it",
             "body": "This is a system I built for myself, start to finish, and it trades real money. Three bots with two mandates: one crypto bot harvests cycles (buy below its average cost, exit the whole position at a fixed take-profit), a second accumulates long-term positions and never sells, and an equities bot runs the same family of ideas on Alpaca (still on the older architecture, next in line for the rebuild). I'm deliberately leading with the engineering rather than any claim about returns: the interesting part isn't 'it makes money,' it's that it's built with the discipline of something that has to be trusted with real money."},
            {"heading": "An event-sourced core, because spreadsheets make dishonest ledgers",
             "body": "The first version kept its state in spreadsheets, and the spreadsheets lied. A month of forensics on the raw trade history turned up a recorded loss that never happened (a double-counted cost basis from a long-dead bug), coins sold that were never logged as bought, and reset logic that silently didn't exist. The fix wasn't better spreadsheets, it was a different shape of storage: an SQLite core where trades, price ticks, and system events are append-only facts, and positions, cycle P&L, and ledgers are views derived from them. Stored rollups keep bugs forever; derived views recompute the truth, so fixing an accounting bug retroactively fixes history. A standing drift-detection query now compares recorded results against the raw journal, and it caught its first real discrepancy the day it was turned on."},
            {"heading": "Execution built to be trusted",
             "body": "The rebuilt execution layer rests maker limit orders on the exchange instead of chasing prices with instant fills. Exits sit on the book around the clock, so a take-profit executes even if the bot is down. Entries are proximity-armed: a buy order is only posted when price comes within a narrow band of its trigger, so capital isn't locked in orders far from the action. Fill accounting is atomic (a fill books its trade, state change, and order close together or not at all), and on every startup the engine reconciles against the exchange's real order history and books anything that filled while it was offline. The redesign also cut the exchange's take from roughly 30% to roughly 15% of gross per cycle, a cost claim, not a returns claim."},
            {"heading": "The strategy is a document, not a habit",
             "body": "I build heavily with AI assistance, and the failure mode of that workflow is drift: an assistant quietly 'corrects' your strategy toward the textbook version of itself. The fix was to make the strategy a contract. Its intent lives in specification documents written in plain language; every divergence between what the code did and what I actually wanted got an explicit ruling, recorded with its reasoning; and the rebuilt bots shipped behind 35 automated tests, run against a simulated exchange, that assert the specs, including one test whose whole job is to fail loudly if anyone ever re-introduces the most persistent unwanted 'correction.' The AI writes code; the spec, and the judgment behind it, is mine."},
            {"heading": "An LLM that reviews its own trades",
             "body": "After every completed buy-and-sell cycle, and at every startup, the system hands its trade history to an LLM (Claude) and asks what worked, what stalled, and which rules to adjust, keeping a running memory of past observations so analyses build on each other. It all runs under a hard monthly cost budget, so a background analyst never turns into an expense. It is a small, honest example of putting an LLM to work inside a real system instead of bolting one on."},
            {"heading": "Realistic backtesting",
             "body": "Most hobby backtests look great because they quietly ignore costs. This one replays years of real market data and models both fees and taxes, so the output is a realistic estimate rather than a vanity number. The rebuilt system also records its own minute-level price history from live polling, building a first-party dataset so future backtests can replay against exactly what the live bots saw."},
        ],
        featured=True,
        sort_order=2,
    ),
    Project(
        slug="portfolio-site",
        title="This Portfolio Site",
        tagline="The site you're reading: a React + FastAPI + SQL app, not a static page.",
        summary=(
            "A deliberately full-stack portfolio: a React + TypeScript front end, a FastAPI "
            "+ SQL backend serving the projects and receiving contact messages. The site "
            "itself is the demonstration of the target stack."
        ),
        tech=["React", "TypeScript", "Vite", "FastAPI", "SQLModel", "SQLite"],
        highlights=[
            "Three-tier app (SPA + API + database) rather than a static page, so the site itself proves the stack",
            "Projects served from a real API; contact form persists to the database and emails on submit",
            "Typed end to end: TypeScript on the client, Pydantic/SQLModel on the server",
        ],
        sections=[
            {"heading": "Why a backend for a portfolio",
             "body": "A static site shows you can style a page. A working three-tier app shows you can design an API, model data, and wire a typed client to it, the actual job. The contact form needs somewhere to land, and the projects live in SQL, so the backend isn't decorative; it's the point."},
        ],
        featured=False,
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
