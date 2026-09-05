# LOINC Lab Mapper

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Reference Guidelines & Standards:** CAP / CLSI / ISO Standards

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## What It Does

LOINC Lab Mapper fuzzy maps local lab test names to LOINC codes using token overlap and Levenshtein similarity scoring. No external dependencies required for core mapping functionality.

Features:
- **Single Lookup**: Query individual lab test names and get top LOINC matches
- **Batch CSV Processing**: Process CSV files with lab test names in bulk
- **Fuzzy Matching**: Handles typos and variations via Levenshtein distance
- **REST API**: FastAPI-based web service with OpenAPI documentation
- **Audit Trail**: HMAC-SHA256 tamper-evident logging
- **PHI Guard**: Zero-PHI outbound interceptor for HIPAA compliance

---

## Installation

### Local Development
```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/loinc-lab-mapper.git
cd loinc-lab-mapper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Docker
```bash
docker build -t loinc-lab-mapper .
docker run -p 8000:8000 loinc-lab-mapper
```

---

## Usage

### Core LOINC Mapping

#### Single Lookup
```bash
# Look up a lab test by name
python loinc_mapper.py single creatinine

# With max results
python loinc_mapper.py single hemoglobin --max-results 3
```

#### Batch CSV Processing
```bash
# Process a CSV file with lab test names
python loinc_mapper.py batch --input sample.csv --output results.csv
```

The CSV should have a column named `query`, `test`, `lab`, or `name` (auto-detected). Output includes `top_hit` and `lookup_score` columns.

### Enterprise CLI

#### Audit Task Evaluation
```bash
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2
```

#### Batch Processing
```bash
python cli.py batch -i input.csv -o output.csv
```

#### Verify Audit Trail
```bash
python cli.py verify-audit
```

#### Launch REST API Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### REST API Endpoints

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/health` | GET | Health check |
| `/metrics` | GET | System metrics |
| `/api/audit` | POST | Submit task for evaluation |
| `/api/chat` | POST | Query supervisor chat |
| `/api/audit/logs` | GET | Get audit trail |

---

## Configuration

| Environment Variable | Description | Default |
|:---------------------|:------------|:--------|
| `AUDIT_SECRET_KEY` | HMAC-SHA256 key for audit trail | Development-only (set in production!) |
| `MODEL_PROVIDER` | LLM provider (`mock`, `ollama`, `claude`, `openai`) | `mock` |

---

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --cov=loinc_mapper --cov=agents

# Run specific test file
pytest tests/test_loinc_mapper_core.py -v
```

---

## Project Structure

```
loinc-lab-mapper/
├── loinc_mapper.py      # Core LOINC mapping engine
├── cli.py               # Enterprise CLI interface
├── enrichment.py        # Feature enrichment engines
├── simulator.py         # High-throughput simulation
├── agents/              # Enterprise agent framework
│   ├── base.py          # Security, PHI guard, audit trail
│   ├── models.py        # Pydantic data models
│   ├── supervisor.py    # Multi-agent orchestrator
│   ├── workers.py       # Specialized evaluation workers
│   ├── api.py           # FastAPI REST endpoints
│   ├── metrics.py       # Prometheus metrics
│   ├── learning.py      # Bayesian calibration engine
│   ├── llm_factory.py   # LLM provider factory
│   └── streamer.py      # WebSocket telemetry
├── tests/               # Test suite
├── web/                 # Operations console (HTML)
├── Dockerfile           # Container build
├── docker-compose.yml   # Container orchestration
└── pyproject.toml       # Python packaging
```

---

## Security

- **Zero-PHI Outbound Interceptor**: AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers
- **Tamper-Evident HMAC-SHA256 Audit Trail**: Chained, cryptographically signed logs
- **Input Validation**: All inputs validated and sanitized
- **No Hardcoded Secrets**: Production secrets via environment variables

---

## License

MIT License - see [LICENSE](LICENSE) for details.
