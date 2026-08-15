# Evidence contracts

This package owns the backend-independent contracts used to inventory and
validate source material before ingestion. R2R, RAGFlow, or another retrieval
backend receives only validated project records.

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
