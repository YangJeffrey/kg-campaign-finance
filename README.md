# Knowledge Graphs for Campaign Finance

Campaign finance data is most naturally modeled as a procedurally constructed relational graph, where donors, committees, and intermediary entities form typed vertices with financial interactions as attributed edges. This graph-native representation renders hidden relational regularities in FEC filings explicitly computable and makes dependencies, concentration effects, and multi-hop affiliations that remain opaque in flat schemas emerge as graph motifs and connectivity patterns. The system couples Neo4j's property graph model with a language-model-driven framework (Claude + LangChain) that translates analytical intent into executable Cypher queries, enabling compositional reasoning over political finance networks while preserving formal query semantics.

## Setup

### 1. Download FEC Data

Get "Contributions by Individuals" from the [FEC Bulk Data portal](https://www.fec.gov/data/browse-data/?tab=bulk-data).

### 2. Convert to CSV

```bash
python txt_to_csv.py
```

### 3. Load into Neo4j

Place `itcont.csv` in your database import folder, then:

```bash
python load_to_aura.py
```

The script creates:

- **Nodes**: `Donor` (name, city, state, zip_code, employer, occupation) and `Committee` (cmte_id)
- **Relationships**: `DONATED` with 14 transaction properties
- **Indexes**: Automatically created on Donor.name, Committee.cmte_id, and DONATED.tran_id

### 4. Configure Environment

Create `.env`:

```
NEO4J_URI=bolt://localhost:7000
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
ANTHROPIC_API_KEY=your_api_key
```

### 5. Start API

```bash
pip install -r requirements.txt
python api.py
```

## Usage

Query the API at `http://localhost:8000`:

```bash
curl 'http://localhost:8000/query?q=Who%20are%20the%20top%20donors'
```

### Endpoints

- `GET /` - Status
- `GET /health` - Connection check
- `GET /query?q=<question>` - Natural language query

## Troubleshooting Neo4j

Kill unresponsive Neo4j:

```bash
# Find process
ps aux | grep neo4j | grep -v grep

# Kill process
kill -9 <PID>

# Or kill all
pkill -f neo4j
```
