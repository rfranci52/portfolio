"""Seed the projects shown on the site. Idempotent: only runs if empty.

Case studies carry the story in their sections — that narrative is what
separates this from a CRUD-app portfolio. The work-derived studies are
generalized: no client, vendor, or product names, no confidential details.
To re-seed after editing, delete backend/data/portfolio.db.
"""

from sqlmodel import Session, select

from app.db import engine
from app.models import Project

PROJECTS = [
    Project(
        slug="automation-engine",
        title="Script-to-Tool Automation Platform",
        tagline="Record a process once; get a reliable, guided automation.",
        summary=(
            "A platform that turns screen recordings of manual processes into "
            "reviewable automations. A frame-diff engine finds where each step "
            "settles; a vision model reads what happened; recorded input events "
            "supply the actions. The hard part it solves — knowing when a step "
            "has *finished* — is derived from pixels, not guesswork."
        ),
        tech=["Python", "FastAPI", "OpenCV", "Claude Vision API", "SQLModel", "pynput", "htmx"],
        highlights=[
            "Frame-differencing segments a recording into stable states vs. transitions, ignoring noise like blinking cursors and animated spinners",
            "Hybrid capture: input events give the action sequence as ground truth; pixel diffs give the step-completion indicators",
            "Vision model drafts each step; a human confirms — 'the system drafts, the user confirms'",
            "Cost-tuned: free local frame analysis decides which moments are worth a paid vision call; model is swappable per run",
        ],
        sections=[
            {"heading": "The problem, lived not imagined",
             "body": "An operations developer accumulates hundreds of automation scripts over years. They become reusable puzzle pieces — but only that person can run them. They become the human bottleneck for every automation they've ever built. The goal: wrap a process so a non-technical coworker can run it themselves, without the author present."},
            {"heading": "The insight — the video is the spec",
             "body": "The unsolved core of GUI automation is step-completion detection: knowing when a step has finished so the next can start. The usual hacks — fixed sleeps, image matching, polling — are slow or brittle. The insight here: a screen recording already contains the answer. What the screen looks like when a step finishes (a dialog vanishing, a row count changing, a status line updating) is visible in the frames. Diff the frames to find the stable-state transitions, and you've derived the wait conditions the user never had to write."},
            {"heading": "The hybrid design",
             "body": "Two channels, each doing what it's best at. A Start/Stop recorder captures the screen and the input stream (clicks, drags, keystrokes) on one clock. Input events are the action sequence — recorded ground truth, no inference. Frame diffs supply the completion indicators — the part that can't be recorded. A step with input is user-driven; a step with none (a page loading on its own) is system-driven and caught by the pixels alone. Proven on a real recording: a page-load step with zero input was still detected, because the screen settling is what marks it done."},
            {"heading": "Why the competition validates it",
             "body": "This sits in an active space — Microsoft's Power Automate, RPA vendors, and computer-use agents all work nearby. That's the point: a crowded market means real, funded demand, not an empty field. The differentiated piece — deriving wait conditions from pixels rather than narration or brittle selectors — is where the incumbents are weakest, and the target (small operators on legacy apps that never change) is where they're least focused."},
            {"heading": "Engineering decisions",
             "body": "Scripts run as isolated subprocesses with the run table as the queue — no broker needed for a single-machine tool. The vision stage uses structured outputs and a cheaper model by default, escalating only where confidence is low; the free local frame analysis is the cost filter that keeps paid calls proportional to real steps, not video length. Tested against a synthetic recording with known ground truth so the segmentation thresholds could be validated before ever touching real footage."},
        ],
        featured=True,
        sort_order=0,
    ),
    Project(
        slug="legacy-cms-integration",
        title="Direct-Database Integration for a Legacy CMS",
        tagline="Reverse-engineered a closed legacy system with no API — and made its data queryable in seconds.",
        summary=(
            "A firm in a heavily regulated industry ran on a legacy Delphi "
            "case-management system with no API and no supported integration "
            "path — the only way out was slow, fragile GUI automation. I "
            "connected directly to its embedded database engine through the "
            "vendor's own C client library, reverse-mapped ~127 business fields "
            "across a dozen tables, derived account balances to the penny from a "
            "350 MB transaction ledger, and wrapped it in a natural-language "
            "report builder — turning a task that took minutes into seconds."
        ),
        tech=["Python", "ctypes", "embedded database (SQL)", "Claude API", "openpyxl", "tkinter"],
        highlights=[
            "Connected to a no-API legacy database through the vendor's 32-bit C engine via ctypes — driven from a 32-bit worker the 64-bit GUI shells out to",
            "Reverse-mapped ~127 fields across a dozen tables, validated per-column to the penny against ground-truth exports",
            "Derived balances from a 350 MB transaction ledger by parsing embedded records — no stored balance columns existed",
            "Natural-language report builder: plain English → real schema fields via an LLM bounded by a catalog so it can't invent a field",
            "Strict read-only discipline against a business-critical production database",
        ],
        sections=[
            {"heading": "The problem",
             "body": "The business ran on a legacy Delphi case-management system with no API, no supported export, and no database documentation. Getting data out meant driving the GUI with automation — slow, fragile, and it broke whenever the screen changed. I wanted to pull any fields for any list of accounts in seconds, safely, without touching the GUI."},
            {"heading": "The connection breakthrough",
             "body": "There was no ODBC driver (the database engine was end-of-life). Instead I reused the vendor's own C client engine that ships with the app, calling its C API directly from Python with ctypes. Because that engine is 32-bit, I drove it from a small 32-bit worker process that the 64-bit GUI launches as a subprocess and passes a job to — the same worker-launcher pattern good automation uses. All access was strictly read-only against production."},
            {"heading": "Reverse-mapping the schema",
             "body": "Nothing was documented, so I treated a real system export as ground truth: I ran my own field resolvers over the same accounts and measured a per-column match rate, building the map up incrementally until ~127 fields across a dozen tables matched exactly. The hardest part was money — balances weren't stored anywhere; they had to be derived by parsing a 350 MB transaction ledger, and I validated the derivation to the penny."},
            {"heading": "The natural-language layer",
             "body": "Non-technical users don't know column names, so they type plain English ('client', 'balance', 'last payment'). A language model maps the request onto the real schema — but bounded by a catalog of fields that actually exist, so it can never invent one — and a checklist UI shows the confident matches pre-checked and asks about anything unclear before running. It turned a specialist database task into something anyone could self-serve."},
            {"heading": "Try it live",
             "body": "The report builder above ran inside a confidential production system, so it can't be shown directly — so I rebuilt the idea in the open. This is a self-contained demo where you type a question in plain English about a small fictional business (a pizza shop) and watch it become SQL, run against a real database, and return live rows. It keeps the guardrails that actually mattered on the job: the model is given a described schema so it can't invent a field or table, every generated query is read-only, and when a request is ambiguous it asks a clarifying question instead of guessing. Different data, same engine — the natural-language-to-query layer, lifted out and made something you can type into yourself."},
        ],
        demo_url="https://demo.rakimfrancis.com",
        featured=True,
        sort_order=1,
    ),
    Project(
        slug="gui-automation-showcase",
        title="Screen-Driven Document Automation — Recorded End to End",
        tagline="Signs in, works a queue of accounts, exports each document to PDF — driving the whole app by sight, no API. On video.",
        summary=(
            "The skill that changed my role, finally made watchable. An automation "
            "signs into a desktop app and, for each account in a spreadsheet, "
            "searches the record, clears an unpredictable popup, opens the right "
            "document, and exports it to a precisely-named PDF — driving the "
            "interface entirely by image recognition, with no API anywhere. It runs "
            "against CaseDesk, a mock CMS I built specifically for this, and records "
            "itself end to end."
        ),
        tech=["Python", "pyautogui", "OpenCV (image matching)", "openpyxl"],
        highlights=[
            "Drives a GUI with no API purely by sight — locating each button on screen by image recognition, then clicking and typing like a person",
            "Robust, not brittle: waits for the interface to actually reach a state instead of sleeping and hoping, and dismisses the popup only when it truly appears",
            "Spreadsheet-driven batch — loops a queue of accounts and documents, naming each export account_document_datetime",
            "Records itself hands-free into a clean side-by-side demo: the app driven on one half, a narrated log on the other, every click visualized",
            "Solved the real-world gotchas — window focus, macOS permissions, and Retina coordinate scaling",
        ],
        sections=[
            {"heading": "Making an invisible skill visible",
             "body": "For years the most valuable thing I do — turning a manual, click-through process into a hands-off tool — was also the least showable, because it lived inside closed systems I can't expose. This project fixes that. I built a realistic app to automate against (CaseDesk, listed separately), wrote the automation that drives it start to finish, and recorded the whole thing. The result is something you can simply watch: proof of the skill, with nothing confidential in frame."},
            {"heading": "Driving a GUI with no API",
             "body": "The app has no integration path, so the only way in is the way a person does it — through the screen. The automation locates each control by image recognition (matching a picture of the button against the live screen), clicks it, types, and reads the result. It signs in, opens the account search, finds a record, handles whatever pops up, opens a document, and works the export dialog: the exact motions a human makes, performed reliably in a loop over a whole queue."},
            {"heading": "The part that makes it robust",
             "body": "Naive automation sleeps for a fixed time and hopes the screen caught up — and breaks constantly. This one waits for the actual on-screen state before each step, so it tolerates the app being slow or fast. The hardest case is a popup that appears on some accounts and not others: the automation checks for it and dismisses it if present, and does nothing if it isn't — it can't assume either way. That conditional, state-aware handling is the line between a demo that works once and one that runs an entire queue unattended."},
            {"heading": "Built to be shown",
             "body": "It runs entirely hands-off and captures itself — starting a screen recording, bringing the app forward, and producing a side-by-side video: the application being driven on one half, a clean narrated log ('Account 101100 · Complaint → exported') scrolling on the other, with each click marked. Because the target is CaseDesk, an app I built for exactly this, the demonstration is fully clean-room — the skill on display, none of the confidential context."},
        ],
        video_url="/demos/casedesk-automation.mp4",
        featured=True,
        sort_order=2,
    ),
    Project(
        slug="casedesk-mock-cms",
        title="CaseDesk — A Mock Legacy CMS, Built to Automate Against",
        tagline="A full desktop case-management app I built from scratch, as a safe and realistic target for GUI automation.",
        summary=(
            "Most of my automation work drives systems I can never show — they're "
            "confidential and closed. So I built my own to demonstrate against: "
            "CaseDesk, a complete desktop case-management application — login, "
            "tabbed account views, search, a document-export flow — running on "
            "entirely synthetic data. It's a realistic, shareable stand-in for the "
            "kind of legacy system I integrate with, one I can automate in public "
            "without touching anyone's real data."
        ),
        tech=["Python", "PySide6 (Qt)", "SQLite", "openpyxl"],
        highlights=[
            "A real desktop app, not a mockup: a sign-in gate, a three-section workspace, account search, a five-tab account view, and functional bulk export/update tools",
            "Deliberately realistic friction — the details that make automation hard: a flash-message popup that appears on only some accounts, a separate document-viewer window, click-based navigation",
            "Entirely synthetic data (fake 900-series SSNs, which were never issued) — zero connection to any real person or system",
            "Functional end to end: the document flow exports real PDFs; the bulk tools read and write actual records",
        ],
        sections=[
            {"heading": "Why build a fake app on purpose",
             "body": "The GUI-automation skill that reshaped my career is the hardest thing to put in a portfolio, because everything I've automated sits behind closed, confidential systems I can't record or share. The fix was to build a stand-in of my own: a legacy-style case-management app, faithful to the shape of the real thing but populated entirely with synthetic data. Now the skill can be demonstrated in the open — the automation drives CaseDesk (listed separately), and no real data is anywhere near it."},
            {"heading": "The friction is the point",
             "body": "A too-clean app proves nothing, because real automation is hard precisely because of friction. So CaseDesk has it on purpose: a flash-message popup that appears when you open some accounts but not others (so a script can neither assume it's there nor that it isn't), a document that opens in its own window, and navigation that rewards clicking over tabbing. These are the exact unpredictable conditions a robust automation has to survive, recreated inside a system I own and can show."},
            {"heading": "A genuine build in its own right",
             "body": "CaseDesk isn't a hollow prop. It's a working PySide6 desktop application over a SQLite database: a login gate, a searchable set of accounts with five tabs of detail each, bulk export and update tools that read and write real files, and a document flow that generates actual PDFs. Building a believable line-of-business application — the very kind I spend my days integrating with — is a demonstration in itself."},
        ],
        featured=False,
        sort_order=3,
    ),
    Project(
        slug="nightly-automation",
        title="Unattended Nightly Operations Pipeline",
        tagline="A hands-off pipeline that runs the overnight data work while everyone's asleep.",
        summary=(
            "An automation that runs every night on a schedule and chains a "
            "sequence of scripts end to end: it pulls account data out of a "
            "legacy system with no API by reliably driving its interface, "
            "transforms it, and delivers it to external partners over SFTP. "
            "Engineered to run headless and recover on its own."
        ),
        tech=["Python", "RPA (pyautogui + image recognition)", "pywin32", "openpyxl", "paramiko (SFTP)", "psutil"],
        highlights=[
            "Orchestrates a chain of scripts from a single entry point, unattended, on a schedule",
            "Bridges a no-API legacy system via reliable GUI and image-recognition automation",
            "Defensive by design: corrects environment state that would corrupt input, kills and relaunches stuck apps, screenshots on failure, logs every step",
            "Delivers finished data to external partners over SFTP",
        ],
        sections=[
            {"heading": "Runs while I sleep",
             "body": "The whole pipeline kicks off on a schedule and runs to completion with no one at the keyboard — one entry point chains the sequence of steps, each handing off to the next. The goal was to take a nightly block of manual data work off a person entirely and have it just be done by morning."},
            {"heading": "Built to survive the real world",
             "body": "Unattended automation fails in boring, physical ways, so most of the engineering is resilience: it detects and corrects stray environment state (like a keyboard mode) that would silently corrupt automated input, terminates and relaunches applications that hang, captures a screenshot at the exact moment anything fails so a problem is diagnosable in seconds the next morning, and logs every step. If it breaks at 3 a.m., you know precisely where."},
            {"heading": "Bridging a system with no API",
             "body": "The source system had no integration path, so data comes out through GUI automation — including locating on-screen elements by image recognition when there's nothing else to target — then gets transformed and delivered to external partners over SFTP. It's the unglamorous plumbing that a real operation runs on."},
        ],
        featured=False,
        sort_order=4,
    ),
    Project(
        slug="document-redaction",
        title="Legal Document Pipeline + Compliance-Grade Redaction",
        tagline="Automated assembly and true-redaction of document packages across a dozen account types.",
        summary=(
            "Automates the collation of legal document packages and runs every "
            "one through a redaction step that *actually removes* sensitive data "
            "from the PDF — SSNs, account numbers — rather than drawing a box "
            "over it, with a per-document audit log and a dry-run preview. Turns "
            "a manual, error-prone assembly task into a repeatable pipeline."
        ),
        tech=["Python", "PyMuPDF", "regex", "openpyxl"],
        highlights=[
            "True text-removal redaction (not a visual overlay you can copy under), with a per-document audit log",
            "Dry-run mode + before/after rendering to verify redactions before committing",
            "Handles a dozen-plus document and account types with per-type collation rules",
            "Built as a reusable module that 15 other scripts import — composition over copy-paste",
        ],
        sections=[
            {"heading": "The task",
             "body": "Legal document packages have to be assembled to a partner's exact format — the right disclosures, notes, and statements pulled together per account, across more than a dozen account types. Done by hand it's slow and easy to get wrong. I turned it into a pipeline that assembles each package the same way every time."},
            {"heading": "True redaction, not black boxes",
             "body": "The part that matters most is the sensitive data. A black rectangle drawn over a PDF is not redaction — the text is still under it, copy-pasteable. This pipeline uses PyMuPDF to *remove the text itself* (SSNs, account numbers) from the document, writes a per-document audit log of what was removed, and has a dry-run mode that renders before/after so a human can verify before anything is committed. That's the difference between looking compliant and being compliant."},
            {"heading": "Reusable by design",
             "body": "The core is a single module that fifteen other scripts import, so a new document type or account prefix slots into the shared logic instead of spawning another copy-pasted one-off. That reuse is why one person could keep this maintainable across a dozen-plus variants."},
        ],
        featured=False,
        sort_order=5,
    ),
    Project(
        slug="algorithmic-trading",
        title="Algorithmic Crypto Trading System",
        tagline="A self-built quant stack: live tiered-exit bots, a fee- and tax-aware backtester, and ML price modeling.",
        summary=(
            "A personal end-to-end trading system. Live bots execute a tiered "
            "take-profit strategy through a broker API and reconcile their own "
            "records against the exchange's actual order history to catch drift. "
            "A separate backtester replays the strategy over five years and "
            "models trading fees and taxes for realistic — not vanity — returns. "
            "An RNN module explores ML-based price prediction."
        ),
        tech=["Python", "Coinbase API", "pandas", "gspread", "machine learning (RNN)"],
        highlights=[
            "Live bots run a tiered take-profit strategy via a broker API, logging every action to an audit trail",
            "Reconciliation tool checks the bot's records against the exchange's real order history — ground-truth discipline",
            "Backtesting engine replays five years of data and models taker fees and taxes (most hobby backtests ignore both)",
            "RNN-based experimentation with ML price modeling",
        ],
        sections=[
            {"heading": "End to end, and honest about it",
             "body": "This is a system I built for myself, start to finish. Live bots place and manage orders through a broker API on a tiered take-profit strategy, logging every action. I'm deliberately leading with the engineering rather than any claim about returns — the interesting part isn't 'it makes money,' it's that it's built with the discipline of something that has to be trusted with real money."},
            {"heading": "Records that check themselves",
             "body": "A trading bot's own logs can drift from what actually happened at the exchange. So a separate reconciliation tool pulls the exchange's real order history and compares it against the bot's records to surface any discrepancy. Trusting a system means being able to verify it against ground truth — the same instinct as validating a reverse-engineered database against a real export."},
            {"heading": "Realistic backtesting",
             "body": "Most hobby backtests look great because they quietly ignore costs. This one replays five years of market data and models both taker fees and taxes, so the output is a realistic estimate rather than a vanity number. A separate track experiments with an RNN for price modeling — the ML side of the same problem."},
        ],
        featured=False,
        sort_order=6,
    ),
    Project(
        slug="portfolio-site",
        title="This Portfolio Site",
        tagline="The site you're reading — a React + FastAPI + SQL app, not a static page.",
        summary=(
            "A deliberately full-stack portfolio: a React + TypeScript front end, "
            "a FastAPI + SQL backend serving the projects and receiving contact "
            "messages. The site itself is the demonstration of the target stack."
        ),
        tech=["React", "TypeScript", "Vite", "FastAPI", "SQLModel", "SQLite"],
        highlights=[
            "Three-tier app (SPA + API + database) rather than a static page, so the site itself proves the stack",
            "Projects served from a real API; contact form persists to the database and emails on submit",
            "Typed end to end — TypeScript on the client, Pydantic/SQLModel on the server",
        ],
        sections=[
            {"heading": "Why a backend for a portfolio",
             "body": "A static site shows you can style a page. A working three-tier app shows you can design an API, model data, and wire a typed client to it — the actual job. The contact form needs somewhere to land, and the projects live in SQL, so the backend isn't decorative; it's the point."},
        ],
        featured=False,
        sort_order=7,
    ),
]


def seed() -> None:
    with Session(engine) as session:
        if session.exec(select(Project)).first() is not None:
            return
        for project in PROJECTS:
            session.add(project)
        session.commit()
