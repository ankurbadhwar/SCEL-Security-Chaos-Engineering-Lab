# Security Chaos Engineering Lab (SCEL)

Security Chaos Engineering Lab is a three-service Flask project for running controlled web attack simulations, deliberately disabling security controls, and observing how exploit behavior changes before and after chaos injection.

## Overview

SCEL was built to answer a simple question: what actually happens when application security controls stop working at runtime?

In many student security projects, the focus stays on finding vulnerabilities in isolation. That is useful, but it does not say much about resilience. Real systems fail in more interesting ways. A control that exists in code may be misconfigured, toggled off, bypassed, or only partially enforced. SCEL explores that gap by treating security controls as things that can degrade during operation and then measuring the effect on attack outcomes.

The project combines a vulnerable target web application, an attack engine, and a metrics dashboard. The target app exposes a small set of intentionally risky workflows such as login, profile access, file upload, command execution, and money transfer. The attack engine runs verified attack simulations against those workflows. Between phases, it toggles defenses on and off through a control API. The dashboard then shows how exploit success and time-to-exploit change across the two states.

From a practical standpoint, the project is useful as:

- a teaching lab for application security concepts
- a demonstration of security chaos engineering on a small, understandable system
- a way to compare “control enabled” versus “control disabled” behavior without setting up a large environment

## Key Features

- Brute force login simulation  
  The engine repeatedly attempts authentication using a fixed password list against the target login endpoint. This matters because it shows how rate limiting changes attack feasibility rather than just checking whether a login form exists.

- IDOR simulation  
  The project includes a profile access workflow where one user attempts to access another user’s data by changing the identifier. This matters because IDOR issues are easy to demonstrate in small apps and are a good fit for before/after control experiments.

- Command injection simulation  
  The target app exposes a ping form that becomes unsafe when input sanitization is disabled. This matters because it demonstrates how quickly a seemingly minor validation rule can turn a helper feature into an execution sink.

- Unrestricted file upload simulation  
  The upload route accepts files and applies a basic extension check when protections are enabled. This matters because upload handling is a common weak point in web apps and helps illustrate the difference between superficial filtering and actual hardening.

- CSRF transfer simulation  
  The app includes a transfer form protected by a CSRF token when the control is enabled. This matters because it gives the lab a state-changing business action that can be tested with and without request integrity checks.

- Runtime security control toggling  
  The target app exposes switchable controls for rate limiting, RBAC, input sanitization, CSRF protection, IDOR protection, and session protection. This matters because the project is not just scanning for flaws; it is explicitly experimenting with degraded defenses.

- Before-chaos and after-chaos orchestration  
  The attack engine can run all selected attacks with controls enabled, then repeat them with the controls disabled. This matters because the comparison is the core of the lab’s purpose.

- Metrics dashboard and persistence  
  Results are stored in SQLite and displayed through a separate dashboard service. This matters because the project keeps a history of experiments instead of treating each run as disposable console output.

- Engine API for remote triggering  
  The attack engine exposes HTTP endpoints for execution, status polling, control toggling, and result retrieval. This matters because it decouples orchestration from the UI and makes the project easier to test and extend.

## Project Structure

```text
SCEL-Security-Chaos-Engineering-Lab/
├── Attack_Engine/
│   ├── engine_api.py
│   ├── orchestrator.py
│   ├── run_demo.py
│   ├── brute_force_attack.py
│   ├── idor_attack.py
│   ├── command_injection_attack.py
│   ├── file_upload_attack.py
│   ├── csrf_attack.py
│   ├── db_logger.py
│   ├── dashboard_reporter.py
│   ├── config.py
│   └── attack_results.db
├── Metrics/
│   ├── app.py
│   ├── metrics_db.py
│   ├── scoring.py
│   ├── templates/
│   └── metrics.db
├── Target_webapp/
│   ├── app.py
│   ├── config.py
│   ├── models/
│   ├── routes/
│   ├── security/
│   ├── templates/
│   └── static/
├── tests/
│   └── test_integration.py
├── requirements.txt
├── start_scel.sh
├── scel_live.sh
└── README.md
```

### Component Notes

- `Target_webapp/`  
  The intentionally vulnerable Flask application used as the experiment target. It contains the login flow, profile access routes, upload page, command execution demo, CSRF transfer flow, and the runtime control toggle endpoints.

- `Target_webapp/routes/`  
  Route handlers for the target app. The important files are `auth.py`, `profile.py`, `csrf.py`, `upload.py`, `system.py`, and `toggle.py`.

- `Target_webapp/security/`  
  Small security helpers such as rate limiting, RBAC checks, sanitization, and session-token enforcement.

- `Attack_Engine/`  
  The automation layer that runs attacks against the target app, stores results, toggles controls, and optionally forwards metrics to the dashboard.

- `Attack_Engine/orchestrator.py`  
  The core phase runner. It applies the “before chaos” and “after chaos” control states and executes the registered attacks.

- `Attack_Engine/engine_api.py`  
  A separate Flask service that exposes REST endpoints for starting runs, polling progress, changing control states, and fetching results.

- `Metrics/`  
  The dashboard service. It stores experiment data in SQLite, proxies selected engine actions, and renders the browser-based results view.

- `tests/test_integration.py`  
  API-level and end-to-end tests that assume all three services are already running locally.

- `start_scel.sh` and `scel_live.sh`  
  Linux-oriented tmux launchers. One starts the whole demo including an attack run; the other starts the services and waits for dashboard/API-triggered execution.

## Technology Stack

| Category | Technology | Why it was used |
| --- | --- | --- |
| Language | Python | Fast to iterate on for a multi-service academic prototype and easy to read during demos and viva evaluation. |
| Web framework | Flask | Lightweight enough for small services and route-level security experiments without unnecessary framework overhead. |
| Database | SQLite | Simple local persistence for attack runs and dashboard metrics without requiring separate infrastructure. |
| HTTP client | Requests | Used by the attack engine and dashboard to call the target app and engine API. |
| Testing | Pytest | Straightforward for service integration tests and HTTP assertions. |
| Frontend | Jinja2 templates with HTML/CSS/JS | Enough for a local dashboard and attack demo UI without introducing a separate frontend build system. |
| Deployment/runtime | Local processes on ports 5000, 5001, and 5002 | The project is designed as a local lab rather than a production deployment. |
| Session storage | Flask signed cookie session | Sufficient for the target app’s authentication and control-state demonstrations. |

## Installation

### Prerequisites

- Python 3.10 or newer
- `pip`
- Git
- Optional: `tmux` if you want to use the provided launcher scripts on Linux

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/SCEL-Security-Chaos-Engineering-Lab.git
cd SCEL-Security-Chaos-Engineering-Lab
```

If you are using this from a local archive instead of GitHub, just extract it and open the project root.

### 2. Create a virtual environment

On Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Current dependencies in the repo are:

- `Flask==3.0.0`
- `requests==2.31.0`
- `pytest==8.1.1`

### 4. Create the current import-path compatibility link

Assumption: this repository is being run in its current form. Right now `Target_webapp/app.py` imports `app.routes...`, so the target app expects a root-level `app` alias pointing at `Target_webapp`.

On Linux/macOS:

```bash
ln -sfn Target_webapp app
```

On Windows PowerShell:

```powershell
New-Item -ItemType Junction -Path app -Target Target_webapp
```

This is a known startup workaround, not a recommended long-term packaging approach.

### 5. Review local configuration

Most defaults are already set for local use:

- target app: `http://127.0.0.1:5000`
- metrics dashboard: `http://127.0.0.1:5001`
- engine API: `http://127.0.0.1:5002`

The main configuration file for the engine is:

- [Attack_Engine/config.py](C:/Users/Ankur/Downloads/SCEL-Security-Chaos-Engineering-Lab/Attack_Engine/config.py)

The target app control defaults live in:

- [Target_webapp/config.py](C:/Users/Ankur/Downloads/SCEL-Security-Chaos-Engineering-Lab/Target_webapp/config.py)

If you change ports or hostnames, update the engine and dashboard config accordingly.

## Usage

### Run the services manually

Terminal 1: target webapp

```bash
python -m app.app
```

Expected result:

- Flask app starts on `http://127.0.0.1:5000`
- login page becomes available at `/`

Terminal 2: metrics dashboard

```bash
cd Metrics
python app.py
```

Expected result:

- dashboard starts on `http://127.0.0.1:5001`
- browser UI shows the experiment tables and controls

Terminal 3: engine API

```bash
cd Attack_Engine
python engine_api.py
```

Expected result:

- API starts on `http://127.0.0.1:5002`
- `GET /api/health` returns service status JSON

### Run the demo from the CLI

From `Attack_Engine/`:

```bash
python run_demo.py --clear-db
```

Useful options:

- `--phase before` runs only the secure baseline
- `--phase after` runs only the degraded state
- `--phase both` runs the full comparison
- `--no-dashboard` skips posting results to the dashboard
- `--clear-db` clears stored attack results before the run

Example:

```bash
cd Attack_Engine
python run_demo.py --phase both --no-dashboard --clear-db
```

Typical console behavior:

- the orchestrator enables all controls
- attacks run once in the baseline phase
- controls are disabled for chaos injection
- attacks run again in the degraded phase
- results are saved to SQLite and `results_summary.json`

### Trigger a run through the Engine API

```bash
curl -X POST http://127.0.0.1:5002/api/execute \
  -H "Content-Type: application/json" \
  -H "X-API-Key: scel-engine-key-2024" \
  -d '{"phase":"both","attacks":["brute_force","idor","csrf"]}'
```

Expected response:

```json
{
  "message": "Orchestration started",
  "run_id": "abcd1234",
  "phase": "both",
  "attacks": ["brute_force", "idor", "csrf"]
}
```

### Run integration tests

The integration suite assumes the target app, dashboard, and engine API are already running.

```bash
pytest tests/test_integration.py
```

## How It Works

SCEL is built around a simple loop: establish a secure baseline, degrade controls on purpose, run the same attacks again, and compare what changed.

### 1. Input

Inputs come from three places:

- the target app configuration, which defines whether controls are on or off
- the attack registry in the engine, which decides which attack modules run
- execution requests from the CLI, dashboard, or engine API

The current verified attacks are:

- brute force login
- IDOR
- command injection
- unrestricted file upload
- CSRF

### 2. Processing

#### Target webapp

The target application exposes intentionally testable routes:

- `/login` and `/login-ui` for authentication
- `/profile/<id>` and `/profile-ui/<id>` for IDOR-style access tests
- `/ping` for command injection testing
- `/upload` for file upload testing
- `/transfer-page` and `/transfer` for CSRF testing
- `/toggle`, `/toggle-ui`, and `/status` for runtime control changes

Security controls are implemented as lightweight guards:

- rate limiting for repeated login attempts
- RBAC checks on profile access
- input sanitization on login/ping/upload flows
- CSRF token validation on the transfer flow
- IDOR protection on profile access
- session-token enforcement on protected authenticated routes

#### Attack engine

The attack engine keeps a registry of attack functions and metadata. `AttackOrchestrator` runs them phase by phase:

1. turn all controls on
2. run selected attacks
3. record success, attempts, details, and time-to-exploit
4. turn all controls off
5. run the same attacks again
6. restore controls

Results are persisted through `db_logger.py` and can also be pushed to the metrics dashboard.

#### Metrics dashboard

The dashboard service receives experiment records, calculates display scores, stores them in SQLite, and renders them in the browser. It also proxies some engine operations so the UI can launch runs and poll status without requiring the user to call the engine API directly.

### 3. Output

Each attack produces a structured result with fields such as:

- attack name
- attack type
- success/failure
- time-to-exploit
- attempt count when relevant
- descriptive details
- phase context
- enabled control count
- resilience score

The final outputs appear in:

- the engine console
- `Attack_Engine/attack_results.db`
- `Attack_Engine/results_summary.json`
- `Metrics/metrics.db`
- the dashboard UI

## Results

The most important result from SCEL is not a single score; it is the difference in behavior between the baseline and the degraded state.

In the current implementation, the project successfully demonstrates:

- attack execution against a live target application
- runtime control toggling through an API
- repeated before/after experiments using the same attack set
- persistence of experiment data in SQLite
- dashboard visualization of stored results

Observed outcomes from the repo and audit work are consistent with the project’s intended design:

- brute force attempts are slowed or blocked when rate limiting is enabled
- cross-user profile access is blocked when IDOR and RBAC protections are active
- CSRF transfer attempts are blocked when token checks are active
- disabling controls reduces friction for the same attacks and increases exploit success

Two implementation caveats are still worth stating clearly:

- the file upload scenario exists and is demonstrable, but it is still partially unreliable
- the UI path for IDOR demonstration is not a perfect mirror of the engine’s backend attack path, even though the backend protection is now wired in

### Screenshots and demo artifacts

The repository includes report assets and presentation material, including:

- `SECURITY CHAOS ENGINEERING LAB (SCEL).pptx`
- `SCEL-mini project - doc.docx`

If you want to add dashboard screenshots to this README later, this section is the right place for them.

## Challenges Faced

This project has a few very typical student-built distributed-app problems, and they are worth documenting honestly.

### Control logic existed before enforcement was complete

One of the harder issues was that some controls were present in configuration, UI, and orchestration before they were fully enforced in the backend. `IDOR_PROTECTION` and `SESSION_PROTECTION` were visible as real controls, but until recently they did not actually gate the routes that mattered.

Why it happened:

- the project evolved feature-by-feature
- control toggles were added faster than the underlying route protections
- the dashboard and documentation got ahead of the implementation

How it was handled:

- the profile routes were updated so IDOR protection affects real backend access decisions
- a session guard was added so session protection now depends on an actual session token issued at login
- attack metadata was updated so the engine reports the controls it genuinely exercises

Lesson learned:

- in security tooling, a visible toggle is not the same thing as an implemented defense

### Packaging and startup are still rough

The target application currently depends on a root-level `app` alias pointing to `Target_webapp`. That works, but it is a workaround rather than a clean package layout.

Why it happened:

- the project was likely first run from one specific local environment
- startup scripts were written around that environment and then carried forward

How it is currently mitigated:

- the README documents the symlink/junction step explicitly
- the provided launcher scripts create the alias automatically on Linux

What still needs improvement:

- imports should be normalized so the app can start as `python -m Target_webapp.app` without special setup

### File upload was harder to make deterministic than expected

The unrestricted upload scenario looks simple on paper, but in practice it is one of the less stable parts of the project.

Why it happened:

- the route uses a very basic extension-based filter
- the upload directory handling is minimal
- the scenario depends on request shape and file handling being exactly right

How it was mitigated:

- the feature remains in the project because the route and attack flow are implemented
- audit documents classify it honestly as partially verified rather than pretending it is fully stable

What remains:

- better validation
- safer file handling
- more repeatable end-to-end testing

### Integration testing is useful but expensive to run

The tests are not isolated unit tests. They assume three live services are already running and reachable on fixed local ports.

Why it happened:

- the project architecture is service-oriented
- the most meaningful tests are interaction tests, not pure function tests

Tradeoff:

- this makes the tests more realistic
- it also makes them slower, more fragile, and less convenient for quick refactoring

How it was handled:

- the test suite focuses on health checks, API behavior, orchestration flow, and service boundaries rather than deep mocking

### There was a constant tradeoff between realism and simplicity

The project tries to simulate security failure without becoming a full enterprise security platform. That boundary showed up everywhere: authentication is intentionally simple, the dashboard uses SQLite, and the control model is coarse rather than policy-driven.

Why it happened:

- the project is meant to be teachable and demo-friendly
- the team had to fit a meaningful system into academic time and complexity limits

How that tradeoff was managed:

- keep the target app small
- keep the attack set focused
- make the before/after comparison the main learning outcome

## Future Improvements

There are several realistic next steps for this repo.

- Fix the target app package structure so startup does not rely on an `app` symlink or junction.
- Make the IDOR dashboard actions use the same exact path and semantics as the engine’s backend attack flow.
- Stabilize the file upload scenario and strengthen server-side validation around missing files and upload directories.
- Remove dead helpers and duplicate scoring logic from the attack engine.
- Replace the hardcoded API key and secret key with environment-based configuration.
- Add a proper `docs/` structure and archive stale audit files outside the repo root.
- Expand the attack set with clearly separated future work such as SQL injection or XSS, but only after the current flows are stable.
- Improve test automation so services can be started in a temporary test harness instead of assuming an already-running local stack.

## Contributors

- Ankur — Project author and maintainer
- Additional contributors — Assumption: add names and roles here if this repository was developed by a team

## Acknowledgements

- Flask, for keeping each service simple and readable
- Requests, for the internal HTTP communication between services
- Pytest, for the integration test harness
- OWASP guidance and common web security training material, which clearly influenced the choice of attack scenarios

The repository also contains project report and presentation artifacts that helped document the original academic submission.
