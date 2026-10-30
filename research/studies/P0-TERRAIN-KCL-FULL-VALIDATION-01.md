# P0 KCL full-prism falsification — operator-only private archive

## Evidence basis

The operator ran the SHA/source-gated header probe on original numbered captures
1, 5, 7. Every capture showed a unique MEM2 file-style KCL candidate,
upper-bound prism slots 2,498, 7/7 sampled prisms reconstructable, hole 1, and
present course/model/minimap/PMP roots. These are repeated snapshots, not
independent proof of a native terrain surface or three distinct sessions.

## Follow-up tests

The new script scripts/p0_kcl_full_validation_private.py uses existing original
seven-pair manifest SHA and source-qualified hole/selected ball/pin gates. It
checks all bounded prism slots rather than seven samples:

- Point and normal index validity, referenced unit-length normals, finite
  nondegenerate reconstructed triangles, and first-invalid/interior/trailing
  invalid slot counts.
- Nearest tee/pin-to-triangle distances, expressed only in categorical
  thresholds relative to mesh bbox diagonal, assuming unproven untransformed
  shared source coordinates.
- Candidate header/point/normal/prism bytes equality across snapshots, via an
  in-process digest that is never printed.

This does not prove active course collision ownership, the correct world transform,
an octree, guest physics timing or exact prism count (section alignment padding
could be counted). Even close tee/pin proximity is correlation, not ownership proof.

## Windows PowerShell (run entire block)

    & {
      $repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
      $worktree = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Terrain-Full-P0'
      $branch = 'agent/terrain-full-prism-private-20261030'
      $archive = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\p0-new-cohort-20261028-063011392-955fd483-PRIVATE'
      git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
      if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
      if (!(Test-Path -LiteralPath $worktree)) {
        git -C $repo worktree add --detach $worktree "refs/remotes/origin/$branch"
        if ($LASTEXITCODE -ne 0) { throw 'Worktree failed' }
      }
      py -3 -I "$worktree\scripts\p0_kcl_full_validation_private.py" --archive "$archive" --captures 1 5 7
      if ($LASTEXITCODE -ne 0) { throw 'Source/archive/geometry gate abstained' }
    }

Dolphin not needed. All copyrighted native RAM remains in private ignored
archive. Input manifest SHA is verified before and after. No game modifications,
network transfer or training/publication approval.

## Ownership

Stacked follow-up branch depends on original draft terrain PR #403. New,
exclusive paths only: scripts/p0_kcl_full_validation_private.py,
tests/test_p0_kcl_full_validation_private.py,
research/studies/P0-TERRAIN-KCL-FULL-VALIDATION-01.md and dedicated CI workflow.
S000 manager should review before merge. Do not edit S001 input or S002 inspector.
