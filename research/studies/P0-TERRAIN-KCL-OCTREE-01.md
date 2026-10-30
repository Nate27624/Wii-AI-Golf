# P0 KCL octree reference triage (offline / private)

## Operator evidence

The original SHA/source-gated numbered captures 1, 5, and 7 all independently
produce one MEM2 KCL-compatible candidate, 2,498/2,498 finite and nondegenerate
triangle reconstructions, identical candidate prism bytes and tee/pin proximity
within 2% of the candidate bbox diagonal. These are repeated snapshots of
potentially the same resident asset, not independent game assets or physics steps.

The earlier validator counts potential prism slots from the prism section length
and does NOT establish whether the game's collision-tree index ever references
them. The purpose of this follow-up is to distinguish *present prism table*
from *prisms reachable through KCL lookup*.

## Implementation

- Standalone read-only scripts/p0_kcl_octree_private.py uses the existing
  SHA-gated original 7-pair source reader to check Rev1 scene, mode, selected
  ball, tee and flag. It only reads MEM1/MEM2 from the private archive.
- Scans for the previously established unique MEM2 KCL file-style candidate.
- Interprets MKW-compatible KCL root masks and shifts, bounded root table,
  relative child block pointers, high-bit marked leaf pointers and u16
  one-based prism-ID lists with leading/terminal zero markers.
- Rejects invalid references, out-of-bank pointers, nonforward branches,
  excessive recursion, unbounded leaf lists and unreferenced-only trees.
- Reports counts and booleans only. No pointer offsets, raw indices, hashes,
  geometry, RAM, octree payloads or file paths appear in stdout.
- An unsupported layout returns OCTREE_LAYOUT_VARIANT_UNRESOLVED, not
  'not terrain'. KCL octree variants differ across Nintendo games.
- Even a successful octree structure remains candidate evidence only: active
  Wii Sports collision ownership, coordinate transforms, physics and training
  remain unverified.

KCL format reference: https://www.mkwiiki.org/wiki/KCL

## PowerShell (run the entire block together)

    & {
        $repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
        $worktree = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Terrain-Octree-P0'
        $branch = 'agent/terrain-octree-private-20261030'
        $archive = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\p0-new-cohort-20261028-063011392-955fd483-PRIVATE'
        if (!(Test-Path -LiteralPath $archive)) { throw 'Original archive missing' }
        git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
        if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
        if (!(Test-Path -LiteralPath $worktree)) {
            git -C $repo worktree add --detach $worktree "refs/remotes/origin/$branch"
            if ($LASTEXITCODE -ne 0) { throw 'Worktree creation failed' }
        }
        py -3 -I "$worktree\scripts\p0_kcl_octree_private.py" --archive "$archive" --captures 1 5 7
        if ($LASTEXITCODE -ne 0) { throw 'Octree format/source gate abstained' }
    }

Dolphin is not needed; all originals stay read-only and SHA-checked before and
after analysis. No private data uploaded.

## Ownership / dependencies

Separate four-file follow-up stacked on draft #406, which is stacked on #403.
Exclusive path names avoid S000/S001/S002/S003 and inspector collisions. This
must not merge before parent PRs, ownership review, and exact-head Win/Ubuntu
synthetic plus full regression green. training_approved=false.
