"""P0 public Rev1 OnUserDraw 2-word thunk: source-only seven-bank audit.

The public Golf header has RPGolScene::OnUserDraw at 0x8028DF78 and
OnExit at 0x8028DF80. This is a finite TWO-instruction hypothesis,
independent of #279's already-established OnCalculate thunk.

No Dolphin, framebuffer, game input, memory writes, arbitrary scans or
raw memory/code publication. Validating a draw callback source entry
does NOT identify rendered ball, draw submission or game physics frame.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

_HERE = str(Path(__file__).resolve().parent)
if _HERE in sys.path:
    sys.path.remove(_HERE)
sys.path.insert(0, _HERE)
import audit_p0_golf_oncalculate_dispatch_private as prior
import review_p0_golf_draw_main_13word_source as draw_main

DRAW_PC = 0x8028DF78
NEXT_NAMED_ENTRY = 0x8028DF80
PUBLIC_DRAW_ANNOTATION = "RPGolScene::OnUserDraw"
PUBLIC_HEADER_BLOB = "87ad1b8981dd601e9ca57296ca4f3000ece682b5"


def classify_draw_two_words(words):
    """Match exact PPC source structure; do not invent a virtual dispatch."""
    if type(words) not in (tuple, list) or len(words) != 2:
        raise ValueError("exactly two draw source instructions required")
    a, b = words
    if any(type(w) is not int or w < 0 or w > 0xFFFFFFFF for w in words):
        raise ValueError("unqualified PPC draw word")
    if NEXT_NAMED_ENTRY - DRAW_PC != 8:
        raise ValueError("public draw header annotation boundary changed")
    direct_scene_main = (a >> 26 == 32 and
                         (a >> 21) & 31 == 3 and
                         (a >> 16) & 31 == 3 and
                         (a & 0xFFFF) == prior.SCENE_MAIN_OFFSET)
    target = prior.decode_b_target(b, DRAW_PC+4)
    target_inside = (target is not None and
                     prior.MAIN_UNIT_LO <= target < prior.MAIN_UNIT_HI)
    status = ("SOURCE_TWO_WORD_DRAW_MAIN_TAILCALL_CANDIDATE"
              if direct_scene_main and target_inside
              else "NO_DRAW_MAIN_TAILCALL_SHAPE_CONFIRMED")
    return {
        "kind":"P0-SANITIZED-GOLF-ONUSERDRAW-TWO-WORD-STATIC",
        "public_header_onuserdraw_annotation":"RPGolScene::OnUserDraw",
        "header_draw_to_next_entry_exactly_two_PPC_words":True,
        "first_word_loads_scene_main_from_plus_0x9C_to_r3":direct_scene_main,
        "second_word_nonlink_direct_branch":target is not None,
        "branch_target_in_published_RPGolMain_text":target_inside,
        "qualified_target_public_PPC_code_PC":
            f"0x{target:08X}" if direct_scene_main and target_inside else None,
        "source_draw_main_tailcall_candidate":bool(direct_scene_main and target_inside),
        "status":status,
        "runtime_vtable_slot_verified":False,
        "game_draw_callback_executed_verified":False,
        "actual_ball_render_submission_verified":False,
        "visual_rendered_ball_correspondence_verified":False,
        "guest_game_physics_frame_clock_verified":False,
        "ball_world_xyz_velocity_impact_power_score_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }


def analyze(archive):
    archive=Path(archive)
    folders=prior.seven._check_archive(archive)
    draw_words=[]
    main_body_words=[]
    calculate_words=[]
    main_owner=[]
    for n in prior.PHASES:
        with ExitStack() as stack:
            banks=[]
            for i,size in enumerate(prior.seven.SIZE):
                path=prior.seven.src._file(folders[n], f"{n}.{i+1}.raw",size)
                fp=stack.enter_context(path.open("rb"))
                banks.append(stack.enter_context(mmap.mmap(
                    fp.fileno(),0,access=mmap.ACCESS_READ)))
            rd=prior.roster.TwoBankReader(*banks)
            original=prior.seven._get(rd)
            u=rd.u32
            sm=u(0x804BF4D8)
            if prior.roster._bank(sm,0x1C)!="MEM1":
                raise ValueError("unqualified original scene manager")
            scene=u(sm+0x0C)
            if (prior.roster._bank(scene,0xA0)!="MEM2" or
                    u(scene+0x1C)!=5 or u(scene+0x54)!=2):
                raise ValueError("unqualified Golf scene identity")
            owner=u(scene+prior.SCENE_MAIN_OFFSET)
            main_owner.append(prior.roster._bank(owner,4) if owner else "null")
            if original["hole"] not in range(9):
                raise ValueError("selected source hole invalid")
            calculate_words.append((u(prior.CALCULATE_PC),
                                    u(prior.CALCULATE_PC+4)))
            draw_words.append((u(DRAW_PC),u(DRAW_PC+4)))
            main_body_words.append(tuple(
                u(draw_main.ENTRY+j*4) for j in range(draw_main.WORD_COUNT)))
    if (any(x!=calculate_words[0] for x in calculate_words[1:]) or
            any(x!=draw_words[0] for x in draw_words[1:]) or
            any(x!=main_body_words[0] for x in main_body_words[1:])):
        raise ValueError("Rev1 source code was not stable in seven originals")
    existing=prior.classify_two_word_source(calculate_words[0])
    if (not existing["oncalculate_to_main_direct_thunk_supported"] or
            existing["candidate_target_public_code_pc"] !=
            "0x8028E158"):
        raise ValueError("original exact Calculate thunk target changed")
    if any(owner!="MEM2" for owner in main_owner):
        raise ValueError("scene RPGolMain member identity class changed")
    result=classify_draw_two_words(draw_words[0])
    # Only study the published 13-word source after its exact entry is
    # authenticated by the two-word native draw thunk.
    if (result.get("qualified_target_public_PPC_code_PC") !=
            f"0x{draw_main.ENTRY:08X}"):
        main_study = None  # negative source; never speculate a callee identity
    else:
        verified_words = main_body_words[0]
        main_study = draw_main.census(
            lambda pc:verified_words[(pc-draw_main.ENTRY)//4]
            if draw_main.ENTRY <= pc < draw_main.END and pc%4==0
            else (_ for _ in ()).throw(ValueError("out of exact draw range")))
    prior.seven._check_archive(archive)
    return {
        "kind":"P0-SANITIZED-REV1-GOLF-ONUSERDRAW-DISPATCH-AUDIT",
        "original_14_native_bank_SHA_pre_and_post_verified":True,
        "canonical_seven_source_selected_scene_mode_and_hole_qualified":True,
        "scene_main_member_MEM2_all_seven":True,
        "calculate_2_word_thunk_precondition_still_source_qualified":True,
        "source_draw_2_word_window_identical_seven_of_seven":True,
        "source_draw_target_13_word_window_identical_seven_of_seven":True,
        "source_draw_main_13_word_census":main_study,
        **{k:v for k,v in result.items() if k!="kind"},
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        result=analyze(args.archive)
    except (OSError,ValueError,KeyError,TypeError,OverflowError,
            AttributeError,IndexError):
        print(json.dumps({
            "kind":"P0-SANITIZED-REV1-GOLF-ONUSERDRAW-DISPATCH-AUDIT",
            "status":"ABSTAIN_SOURCE_OR_PRIVATE_ARCHIVE_GATE",
            "training_approved":False,"allowed_to_publish":False,
        },sort_keys=True))
        return 2
    print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
