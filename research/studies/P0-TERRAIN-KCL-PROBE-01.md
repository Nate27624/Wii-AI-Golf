# P0 Terrain: source-gated original-bank KCL discovery (candidate only)

## Scope and ownership
New independent read-only paths only: `scripts/p0_kcl_private_probe.py`,
`tests/test_p0_kcl_private_probe.py`, this note and a dedicated CI workflow.
No changes to S001 shot/power collector, S002 inspector, S003 power study, S000
source readers or raw private banks. Requires S000 review before merge.

## Established observations
Operator confirmed the selected ball and A-button readout on their setup.
Tee/pin were previously source- and visually cross-checked; selected ball current
and +0xCC terminal cache observations are separate. None establishes terrain
triangles or guest physics cadence. Training remains disabled.

The source-derived Rev1 FieldManager root is 0x804BF868. Golf field+0x18 is
RPUtlMapData (PMP object placements), +0x70 the course object, +0x74 minimap.
RPGolMapObjBase+0x04 leads to an RPGrpModelG3D source model. These roots are
checked only as categorical pointer presence, never asserted KCL addresses.

Sources:
- https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolFieldManager.h
- https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolMapObjBase.h
- https://github.com/kiwi515/Resort2OG (Wii Sports KCL / PMP distinction)
- https://www.mkwiiki.org/wiki/KCL (general Nintendo Wii file-style KCL header/prisms)

## Operator command, once this PR is merged
From an existing `Wii-AI-Golf` checkout with its configured original private
capture archive:

```powershell
git pull --ff-only
py -3 -I scripts/p0_kcl_private_probe.py --archive 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\p0-new-cohort-20261028-063011392-955fd483' --capture 5
```

This is read-only and can run with Dolphin closed. `--capture 5` examines one
original numbered pair, not all seven. The existing original native 14-bank
manifest/size/SHA and Rev1/scene5/selected-owner/tee/pin gates run before scan;
all original SHA hashes are checked again afterward. The scanner maps (does not
copy) the selected pair, searches MEM1/MEM2 for aligned *file-style* KCL
headers, cross-checks section offsets/endianness, finite unit normals,
index-bounded candidate prisms and the triangle cross/dot reconstruction on
several spatially distributed sample prisms. No source RAM words, guest
pointers, file paths or reconstructed vertices are printed.

## Falsification and next work
- `CANDIDATES_ONLY`: *possible* file-style KCL sections. Verify the highest
  candidate by private native offset, parse whole prism/octree bounds, compare
  reconstructed raw components against tee/pin on two independent snapshots,
  then export a bounded private mesh. Do NOT yet render it as authoritative.
- `NO_FILE_STYLE_KCL_HEADER_DETECTED`: only falsifies THIS restrictive
  aligned, ordered, <=32MiB file-style layout. It does NOT imply absence of
  terrain: resident data might be relocated, compressed, unordered, in another
  asset representation or never retained in raw bank.
- `ABSTAIN_SOURCE_OR_ARCHIVE_GATE`: do not interpret candidate absence as a
  terrain result; first correct the original archive integrity/scene gates.

The probe does not extract a mesh file, alter game state, launch Dolphin, change
speed/clock, promote any physics/world units, or approve training. No real
private banks are shipped to CI. Local synthetic focus: 7/7 pass; exact branch
Windows+Ubuntu full-suite CI and ownership review are required before merge.
