# Local integration checklist

Record operating system, Python, Dolphin revision, game region/revision, Wii Remote emulation modality, rendering backend, speed setting, and game/input latency. Determine whether real or emulated Wii Remote motion can be reliably played back from code.

First characterize how the game responds to repeated controller traces. Vary one control dimension at a time and record recognized swings, accuracy and distance. Establish whether the reset method reproduces the same shot configuration and whether the displayed unit is feet, yards or meters.

Do not assume a specific Dolphin memory address or existing motion-control API works on this build. Save raw traces/footage locally; never commit the ROM or copyrighted assets.

A strong local NVIDIA GPU is available, but Dolphin control and shot throughput may be more limiting than model training speed.
