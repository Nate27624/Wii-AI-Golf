# P0 writer-input original fourteen-bank manifest qualification

## Why this separate draft exists

The independently executed source-selected writer-input analyzer in S002 #236 verifies bank lengths and SHA consistency across each local read, but its standalone CLI does not require each of the fourteen inputs to match the original numbered private archive manifest. A valid but different snapshot that was already changed before both hashes could be used silently.

This narrow source-gated wrapper does not replace #236 or #231. It checks the original local seven-pair manifest kind, seven numbered phases, exact ordered MEM1/MEM2 name and size, private copy_verified flags, false training/phase-mapping claims, and SHA256 against the fourteen original bank files. It then invokes #236's original source validator and writer-input comparator, and verifies all original manifest/bank digests again after sampling.

Strictly scoped: no new memory scan or evidence about ball XYZ, axes, frame clock, velocity, impact, power, score, CC endpoint prediction, or training.

## Run only after source-owner review

From an exact-SHA, reviewed worktree, pass the existing original directory inside the repository's ignored Data/captures to the script. This accepts only the private p0-new-cohort-*-PRIVATE archive shape.

    python -I scripts/audit_p0_seven_writer_manifest_guard_private.py --archive <private-archive-directory>

A failure exits 2 with a generic ABSTAIN message, never outputting the private path, RAM values, addresses, manifest hash, or original bank SHA. Success adds two guarded booleans: fourteen archived bank hashes match the original manifest before and after analysis, and the manifest itself remained unchanged. This does not cryptographically attest who originally created the mutable local manifest; the independent operator provenance remains necessary.

No Dolphin launch, shot, new capture, upload of RAM, merge into main, controller edits, or training/publish flags are authorized.

## Tests and owner review

    python -I tests/test_p0_seven_writer_manifest_guard_private.py

Fabricated tiny banks test matching, stable-but-modified preexisting bank, changed manifest SHA, wrong bank order, duplicate phase, false training claim, symlinked manifest, mutation during writer run, source failure, unsafe output claim, CLI failure and isolated imports. GitHub Actions runs synthetic-only on Windows and Ubuntu. Parent #236, S002 #231 and S000 #205 owners review before any local real archive execution or merge.