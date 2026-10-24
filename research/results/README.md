# Experiment results and provenance

Proposals in research/queue.jsonl do **not** imply queued execution. Store small validated experiment summaries here as STUDYID_UTC_RUNID.json. Large frames, traces and checkpoints belong outside Git, with hashes and references included in summaries.

Every result must record study_id, run_id, source (synthetic/emulator/human), environment and policy revisions, train/eval IDs and seeds, shot attempt counts, units, baselines, outcome/failure statistics, artifact hashes and limitations. Never label synthetic metrics as Wii Sports performance.
