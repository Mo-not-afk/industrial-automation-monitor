# Industrial Automation Monitor

A local process-monitoring demonstration with a Modbus TCP client, included simulated PLC endpoint, register maps, alarms, and SQLite-backed event/trend API.

## Problem and objectives

Automation monitoring depends on bounded communications, correct register interpretation, and explicit alarm limits. This project provides a safe local simulator workflow for exploring those interfaces without connecting to plant equipment.

## Features

- Modbus TCP subset: read coils (FC01), discrete inputs (FC02), holding registers (FC03), input registers (FC04), write single coil (FC05), and write single register (FC06).
- A local threaded simulator bound to loopback, process register map, and deterministic changing temperature, pressure, motor speed, and tank level.
- Socket timeouts and malformed/exception response checks.
- Threshold alarm evaluation, SQLite event/sample history, FastAPI endpoints, and a live browser dashboard.
- pymodbus is declared as the maintained ecosystem dependency; the included minimal wire client is self-contained so the simulator/tests work without version-specific APIs.

## Architecture

```mermaid
flowchart LR
 Sim[Loopback Modbus simulator] <--> Client[Bounded TCP client]
 Client --> Decode[Register map + scaling]
 Decode --> Alarm[Threshold alarms]
 Alarm --> DB[(SQLite samples/events)]
 DB --> API[FastAPI /history /events]
```

Modbus TCP uses the MBAP transaction header followed by a function-code PDU. Register values are unsigned 16-bit words; scaling is applied at the application boundary. The process demo encodes temperature/tank values in tenths while pressure and RPM are integer units. The wire server exists for isolated tests and is not intended as a hardened industrial endpoint.

## Installation

Windows PowerShell: `py -3.11 -m venv .venv` then `\.venv\Scripts\python.exe -m pip install -e ".[test]"`.

Linux/macOS: `python3 -m venv .venv`, activate, and install `python -m pip install -e '.[test]'`.

## Usage

```powershell
plant-monitor --samples 10
uvicorn plant_monitor.api:app --reload
```

Open `http://127.0.0.1:8000/` for the live dashboard and `/docs` for the REST schema. `/process` advances and returns a simulator sample, `/history` gives chronological values, and `/events` lists threshold events. Example map: `examples/register_map.json`. Defaults bind only to `127.0.0.1` for the CLI simulator.

## Tests

Run `python scripts/run_tests.py` from an uninstalled checkout, or `python -m unittest discover -s tests -v` after installation. Four tests passed locally, including a Modbus simulator integration and CLI smoke test. Two optional FastAPI endpoint tests were skipped because FastAPI and SQLAlchemy were unavailable. No remote PLC or network is required.

## Limitations and safety

The project covers a useful subset, not the full Modbus specification. It has no authentication, TLS, multi-register floating point, vendor maps, retry policy, or production-grade server hardening. Protect real control networks and do not connect this demo to a real PLC without a separate safety and security review.

The tested process is synthetic and local. No real industrial PLC or production plant has been contacted.
