# Data policy

Only small derived fixtures, manifests and checksums are committed.

Every recomputation records the public accession, source URI, input checksum, sample or cell filters, software versions, random seed, complete parameters and output checksum. Raw matrices, model weights and runtime caches stay in the external deployment work directory and are never committed.

The files under `data/derived/` are legacy UC/MCH regression fixtures. Their internal `schema_version` describes the snapshot format and does not make them part of the default V2.1 workflow.
