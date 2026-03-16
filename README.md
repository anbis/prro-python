# PRRO Python

Python middleware for Ukrainian fiscal register (ПРРО – Програмний Реєстратор Розрахункових Операцій) that bridges client applications with the State Tax Service (DFS) fiscal server.

## Overview

PRRO Python is an asynchronous service that:

- Receives fiscal commands from client applications via [NATS](https://nats.io/) messaging
- Signs documents using the [e-Life](https://sign.e-life.com.ua/) electronic signature service
- Forwards signed documents to the DFS fiscal HTTP API (`http://fs.tax.gov.ua:8609/fs`)
- Manages fiscal register state and shift totals
- Supports offline session management with CRC-based receipt numbering

## Architecture

The application uses a multi-process model with three components:

| Component | Description |
|-----------|-------------|
| **Balancer** | Main NATS subscriber; assigns unique channels to connecting clients |
| **Application** | Per-client request processor; handles signing and DFS communication |
| **StateQueue** | Fiscal register state cache; provides `NextLocalNum` and shift totals |

### Request Pipeline

```
Client → NATS → predispatch → command_handler (sign) → signed_handler (DFS) → postdispatch → Client
```

## Requirements

- Python 3.9+
- NATS server reachable at `nats://nats.anbis.pp.ua:5222`

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
# Production mode (starts all sub-processes)
python3 main.py

# Debug / single-application mode
python3 main.py -d
```

## Configuration

Configuration is managed in `application/config.py`.

| Setting | Default | Description |
|---------|---------|-------------|
| `protocol_version` | `v1` | NATS channel prefix |
| `nats_servers` | `nats://nats.anbis.pp.ua:5222` | NATS server list |
| `request_timeout` | `5` | Timeout in seconds for NATS requests |

## Supported Document Types

### JSON Commands (via `/cmd` endpoint)
`ServerState`, `Objects`, `TransactionsRegistrarState`, `Shifts`, `Documents`, `Check`, `CheckExt`, `ZRep`, `ZRepExt`, `LastShiftTotals`

### XML Documents (via `/doc` endpoint)
`OpenShiftCheck`, `CloseShiftCheck`, `ServiceDeposit`, `ServiceIssue`, `GoodsCheck`, `CheckReturn`, `StornoCheck`, `ZRepCheck`, `OfflineBegin`, `OfflineEnd`

## Docker

```bash
docker build -t prro-python .
docker run prro-python
```

## Testing

```bash
pip install pytest
pytest tests/
```

## Project Structure

```
├── main.py               # Entry point
├── balancer.py           # Process balancer & NATS subscriber
├── skeleton.py           # Base NATS async handler
├── state_queue.py        # Fiscal register state cache
├── requirements.txt      # Python dependencies
├── Dockerfile
└── application/
    ├── application.py    # Core request/response logic
    ├── config.py         # Configuration
    ├── connector.py      # DFS connector
    ├── esign.py          # e-Life electronic signature
    ├── exceptions.py     # Custom exceptions
    ├── interfaces/       # Abstract interfaces
    ├── logger.py         # Logging utility
    ├── offline.py        # Offline mode handler
    ├── repository.py     # Template registry
    ├── templates/        # Base template classes
    └── api/
        ├── common.py     # Enums and constants
        ├── json/         # JSON command templates
        └── xml/          # XML document templates
```
