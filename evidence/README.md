# Evidence contracts

OmniCAE's implemented semantic knowledge backend is the open-source
[R2R framework](https://github.com/SciPhi-AI/R2R). This package supplies the
backend-independent CAE contracts used to inventory and validate source
material before R2R ingestion. R2R remains an upstream project under its own
licence; OmniCAE does not claim its retrieval framework as project-owned code.

No retrieval service or SDK is required for this layer.

## Source manifests

Every source declares its stable identity, version, origin, licence,
redistribution status, and content hash. The ID remains unchanged when a local
source moves; the hash changes when its content changes.

The machine-readable contract is
[`schemas/source-manifest.schema.json`](schemas/source-manifest.schema.json).
Local paths are repository-relative. `content_hash` uses `sha256:` followed by
64 lowercase hexadecimal digits.

Hash a file or directory tree:

```bash
python3 -m evidence.manifest hash knowledge/calculix/CalculiX/ccx_2.23/doc/ccx
```

Validate one or more manifests against the repository and the files on disk:

```bash
python3 -m evidence.manifest validate --root . path/to/source.json
```

Remote `http` and `https` sources still require a declared hash, but validation
does not download them. Fetching and hash verification belong to the future
ingestion workflow.

Run the contract tests with:

```bash
python3 -m unittest discover -s evidence/tests -v
```

## Read-only MCP

The repository registers `evidence-library` for both supported coding-agent
hosts: `.mcp.json` is the Claude Code project configuration, while
`.codex/config.toml` is the Codex project configuration. It exposes exact
lookup, document navigation, authoritative source opening, and multi-need
retrieval.
The semantic route calls the local R2R service; it does not expose
R2R's answer-generating `rag` operation.

Set up and test it:

```bash
python3 -m venv .venv-mcp
.venv-mcp/bin/pip install -r requirements-mcp.txt
.venv-mcp/bin/python evidence/mcp_integration_test.py
claude mcp list
```
