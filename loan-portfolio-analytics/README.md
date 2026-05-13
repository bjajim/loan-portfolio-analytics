# Loan Portfolio Analytics

A FastAPI service for credit union and small-bank loan portfolio analytics. Computes **CECL allowance** (vintage methodology), **ALM interest-rate shock** simulations, and portfolio KPIs over a loan book stored in PostgreSQL.

Built as a reference implementation of the kind of internal FinTech tooling I build for regulated financial institutions — production patterns at small scope.

## Why this exists

Small credit unions and community banks need CECL and ALM analytics, but commercial tools (e.g. Abrigo, FedFis) start at ~$30K/year and are over-built for institutions under $100M in assets. This service is the small-shop alternative: well-tested Python, clear methodology, easy to extend.

It's also the working example I point to for my Python and FinTech engineering work.

## Features

- **CECL Allowance Calculation** — Vintage methodology with configurable loss rates per loan segment. Computes lifetime expected credit losses across the portfolio.
- **ALM Stress Testing** — Net Economic Value and Earnings-at-Risk under ±100, ±200, ±300 bps parallel rate shocks.
- **Portfolio KPIs** — Delinquency rates, loan-to-share ratio, concentration analysis, charge-off trends.
- **REST API** — Async FastAPI with OpenAPI docs at `/docs`.
- **Production patterns** — Structured logging, typed everywhere, dependency injection, repository pattern, Alembic migrations, integration tests against a real Postgres in CI.

## Quick start

```bash
git clone https://github.com/[your-handle]/loan-portfolio-analytics.git
cd loan-portfolio-analytics
docker-compose up --build
# wait ~10s for postgres
docker-compose exec api alembic upgrade head
docker-compose exec api python -m scripts.seed   # seeds a realistic 500-loan portfolio
```

Then open http://localhost:8000/docs to explore the API.

### Try it

```bash
# Portfolio summary
curl http://localhost:8000/api/v1/portfolio/summary

# CECL allowance calculation
curl http://localhost:8000/api/v1/analytics/cecl

# ALM rate shock (+200 bps)
curl "http://localhost:8000/api/v1/analytics/alm?shock_bps=200"
```

## Architecture

```
app/
├── api/          # FastAPI routes (thin — just request/response)
├── core/         # Config, logging, dependencies
├── db/           # SQLAlchemy session + base
├── models/       # ORM models (Loan, Member, Payment, RateAssumption)
├── schemas/      # Pydantic request/response models
└── services/     # Business logic: CECL, ALM, KPIs
tests/            # pytest, including integration tests w/ real Postgres
alembic/          # Migrations
```

**Design principles I followed:**

- **Thin routes, fat services.** Routes handle HTTP; services hold the analytics logic. Easy to test, easy to reuse.
- **Async all the way down.** Async FastAPI + async SQLAlchemy 2.0. No sync sessions hiding in the stack.
- **Typed everywhere.** Full type hints, mypy-clean (`make typecheck`).
- **Repository pattern** for database access. Services depend on a repository interface, not on SQLAlchemy directly — makes unit testing the analytics straightforward.
- **Pydantic v2** for I/O. Single source of truth for API contracts.
- **Migrations from day one.** Schema lives in `alembic/versions/`, not in `Base.metadata.create_all()`.

## Methodology notes

### CECL (vintage)

I implemented the **vintage methodology** because it's the most defensible approach for small institutions without enough internal data for PD/LGD modeling. For each loan segment (e.g., used auto, new auto, unsecured), the service applies a configured lifetime loss rate against the amortized cost basis. Loss rates are stored in the `cecl_assumptions` table and versioned — every calculation references a specific assumption set, so historical runs are reproducible.

For institutions large enough to warrant PD/LGD or DCF methods, the service is structured so a new method can be added as another implementation behind the same `CECLMethod` interface in `services/cecl.py`.

### ALM rate shock

The ALM module runs parallel interest-rate shocks against a balance sheet of rate-sensitive assets and liabilities. For each shock scenario:

- Net Economic Value (NEV): present value of asset cash flows minus liability cash flows, discounted at shocked rates.
- Earnings at Risk (EaR): projected 12-month net interest income under shocked rates vs. base case.

Both are simplified versus what a regulator would expect for a Call Report filing (no convexity adjustment, no prepayment behavior modeling) — appropriate for an internal management tool, not a substitute for ALCO-grade software. The structure is in place to add those layers.

## Testing

```bash
make test        # full pytest suite
make typecheck   # mypy
make lint        # ruff
```

Tests include:

- Unit tests for CECL and ALM math against hand-computed expected values.
- Integration tests that spin up a Postgres container, run migrations, seed data, and exercise the API.
- A property-based test (Hypothesis) confirming CECL allowance is monotonic in loss rate.

## Production considerations not in this repo

This is a reference implementation, not a production deployment. For real use I'd add: authentication (likely OAuth via the credit union's IdP), audit logging on every analytics run, observability (OpenTelemetry traces, Prometheus metrics), database connection pooling tuned for the workload, and a separate read replica for analytics queries. Happy to discuss the production version of any of this.

## License

MIT — use it, fork it, ship it.

## Author

**Bolaji Ajimotokan** — Senior Python Engineer & FinTech SME
[LinkedIn](https://linkedin.com/in/bjajim) · bj10082270@gmail.com
