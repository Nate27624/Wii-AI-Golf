#!/usr/bin/env python3
"""Operator-controlled, read-only experimental live Wii Golf A-state discriminator.

NO controller writes, automatic swings, memory writes, or training. Samples the
source-gated selected player record. Manual hold/release labels are human intent,
not game input acceptance. 51 words are read sequentially, not atomically.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
import p0_live_directional_aim_series as source
import p0_live_no_contact_compare as base

CALIBRATION = (('R0', False), ('H0', True), ('R1', False), ('H1', True),
               ('R2', False), ('H2', True), ('R3', False))
FIT = ('R0', 'H0', 'R1', 'H1')
HELDOUT = ('R2', 'H2', 'R3')
PHASES = ('RELEASED', 'PRESSED')
WORDS = 51  # source-selected player record stride 0xCC

class Abstain(RuntimeError):
    pass

def _gate(ok, why):
    if not ok:
        raise Abstain(why)

def hex_record(rpc, addr):
    _gate(base.in_bank(addr, WORDS * 4, 'MEM2'), 'BAD_RECORD_RANGE')
    result = []
    for i in range(WORDS):
        word = rpc.call('memory.read_u32', [addr + 4*i])
        _gate(type(word) is int and 0 <= word <= 0xFFFFFFFF, 'INVALID_MEMORY_WORD')
        result.append(word)
    return tuple(result)

def capture(rpc, phase, index, expected, idle_ball, idle_aim):
    # Source-gated full owner/scene/root/field/ball before and after snapshot.
    event = source.packet(rpc, phase, index)
    identity = event['identity']
    _gate(expected is None or identity == expected, 'SOURCE_IDENTITY_CHANGED')
    words = event['words']
    _gate(idle_ball is None or words['selected_ball_plus_0x30'] == idle_ball,
          'BALL_MOVED_NO_CONTACT_PROTOCOL_STOP')
    _gate(idle_aim is None or words['aim_candidate_plus_0x3c'] == idle_aim,
          'AIM_MOVED_NO_CONTACT_PROTOCOL_STOP')
    record = hex_record(rpc, identity[6])
    _gate(source.end_epoch_matches(rpc, identity), 'POST_RECORD_EPOCH_CHANGED')
    return {'phase':phase, 'index':index, 'record':record,
            'identity':identity, 'ball':words['selected_ball_plus_0x30'],
            'aim':words['aim_candidate_plus_0x3c'],
            'start_ns':event['start_ns'], 'end_ns':time.monotonic_ns(),
            'frame_bracket_NOT_PHYSICS':event['frame_bracket']}

def modes(events):
    """Only return stable within-window words, no treating drift as a latch."""
    _gate(len(events) >= 2, 'INSUFFICIENT_WINDOW_SAMPLES')
    values = [e['record'] for e in events]
    return tuple(row[0] if len({a[i] for a in values}) == 1 else None
                 for i, row in enumerate(zip(*values)))

def choose_model(windows):
    """Fit on R0/H0/R1/H1, validate independently R2/H2/R3.

    Requiring 2 independent repeated phases per class means an A-associated
    position that remains latched across release cannot pass accidentally.
    """
    _gate(all(k in windows for k in FIT+HELDOUT), 'MISSING_CALIBRATION')
    fit = {key:modes(windows[key]) for key in FIT}
    distinct = []
    for offset in range(WORDS):
        rv0,rv1 = fit['R0'][offset],fit['R1'][offset]
        hv0,hv1 = fit['H0'][offset],fit['H1'][offset]
        if None not in (rv0,rv1,hv0,hv1) and rv0 == rv1 and hv0 == hv1 and rv0 != hv0:
            distinct.append((offset,rv0,hv0))
    validation = {p: {'expected': 'PRESSED' if p.startswith('H') else 'RELEASED',
                       'prediction': predict(windows[p],distinct)} for p in HELDOUT}
    # Prediction is valid only if all withheld labels match; UNKNOWN fails.
    passed = bool(distinct) and all(x['prediction'] == x['expected'] for x in validation.values())
    return (distinct if passed else []), {
        'candidate_offsets_hex': [f'+0x{k*4:02X}' for k,_,_ in distinct],
        'heldout':validation, 'heldout_pass':passed,
        'inference_enabled':passed,
        'reason': ('HELDOUT_PASS_CANDIDATE_ONLY' if passed else
                   'NO_STABLE_DISCRIMINATOR_OR_HELDOUT_FAILURE')
    }

def predict(events, model):
    if not model:
        return 'UNKNOWN'
    stable = modes(events)
    votes = []
    for offset, rv, hv in model:
        value = stable[offset]
        votes.append('RELEASED' if value == rv else 'PRESSED' if value == hv else 'UNKNOWN')
    if votes and len(set(votes)) == 1 and votes[0] != 'UNKNOWN':
        return votes[0]
    return 'UNKNOWN'

def private_root(path):
    path = path.resolve(strict=True)
    _gate(path.is_dir() and path != ROOT.resolve() and ROOT.resolve() not in path.parents,
          'PRIVATE_CAPTURE_FOLDER_UNSAFE')
    return path

def run(args, *, rpc_class=None, clock=time):
    if rpc_class is None:
        from wii_ai_golf.integration.rpc import FelkRPC
        rpc_class = FelkRPC
    folder = private_root(args.private_root) / (
        'p0-a-state-blind-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        + '-' + uuid.uuid4().hex[:8] + '-PRIVATE')
    folder.mkdir(mode=0o700)
    stream = folder / 'candidate-events-PRIVATE.jsonl'
    manifest = folder / 'manifest-PRIVATE.json'
    status = 'ABORTED'
    code = 'NOT_STARTED'
    windows = {}
    user_truth = {}
    predictions = {}
    expected = None
    idle_ball = None
    idle_aim = None
    packet_count = 0
    model = []
    fit_report = {'inference_enabled': False, 'reason': 'NOT_STARTED'}
    print('LIVE A-STATE CANDIDATE: manual controller only, NO SWING, NO AUTOMATIC INPUT.')
    print('Each window: keep Dolphin ready-to-hit, manually hold A only when instructed.')
    try:
        with stream.open('x',encoding='utf-8') as out:
            with rpc_class(port=args.port,timeout_s=15.0) as rpc:
                info = rpc.call('bridge.ping', [])
                _gate(isinstance(info,dict) and isinstance(info.get('bridge_version'),str),
                      'BRIDGE_PING_FAILED')
                answer = input('Confirm Hitting the Green ready-to-hit, NO swing. Type READY: ').strip()
                _gate(answer == 'READY', 'OPERATOR_CANCELLED')
                stages = [(key, hold) for key,hold in CALIBRATION]
                stages += [('B'+str(i), None) for i in range(args.blind_windows)]
                for phase,hold in stages:
                    if hold is None:
                        print('\nBLIND '+phase+': secretly choose A HELD or A RELEASED; do not swing.')
                        answer=input('Set intended state after countdown; type YES to arm: ').strip()
                    else:
                        print('\n'+phase+': '+('PRESS AND HOLD A' if hold else 'RELEASE A') + ' after HIGH beep; NO motion.')
                        answer=input('Type YES to arm; anything else cancels: ').strip()
                    _gate(answer == 'YES','OPERATOR_CANCELLED')
                    print('Focus Dolphin now. HIGH beep indicates sampling start; LOW beep means stop.',flush=True)
                    clock.sleep(args.focus_seconds)
                    try:
                        import winsound
                        winsound.Beep(1100, 300)
                    except (ImportError,RuntimeError,OSError):
                        print('HIGH BEEP',flush=True)
                    windows[phase] = []
                    for index in range(args.samples_per_window):
                        event = capture(rpc,phase,index,expected,idle_ball,idle_aim)
                        if expected is None:
                            expected = event['identity'];idle_ball=event['ball'];idle_aim=event['aim']
                        windows[phase].append(event)
                        private = {
                            'kind':'candidate_sample','phase':phase,'sample_index':index,
                            'start_monotonic_ns':event['start_ns'],
                            'end_monotonic_ns':event['end_ns'],
                            'source_identity_digest_private':sha256(str(event['identity']).encode()).hexdigest(),
                            'candidate_words_private_be_u32_hex':{
                                'selected_player_record_all_51': [f'{w:08x}' for w in event['record']]},
                            'bridge_frame_count_NOT_PHYSICS':event['frame_bracket'],
                            'training_approved':False}
                        out.write(json.dumps(private,separators=(',',':'))+'\n')
                        out.flush();packet_count += 1
                    try:
                        import winsound
                        winsound.Beep(500, 300)
                    except (ImportError,RuntimeError,OSError):
                        print('LOW BEEP',flush=True)
                    print('Captured',phase,'with',len(windows[phase]),'source-qualified packets.')
                    if phase == 'R3':
                        model,fit_report=choose_model(windows)
                        print('CALIBRATION',json.dumps(fit_report,sort_keys=True),flush=True)
                    if hold is None:
                        prediction=predict(windows[phase],model)
                        predictions[phase]=prediction
                        # prediction comes before human truth: no label leakage.
                        print('BLIND PREDICTION '+phase+': '+prediction,flush=True)
                        truth=input('Reveal actual A state during window [PRESSED/RELEASED/UNKNOWN]: ').strip().upper()
                        user_truth[phase]=truth if truth in ('PRESSED','RELEASED') else 'UNKNOWN'
                    else:
                        print('Calibration phase label is OPERATOR INTENT ONLY, not game A proof.')
        status='COMPLETE';code='CONTROL_STUDY_COMPLETED'
    except (Abstain,OSError,RuntimeError,ValueError,TimeoutError,EOFError,TypeError) as exc:
        code=str(exc) if isinstance(exc,Abstain) else type(exc).__name__
        print('ABSTAIN',code,flush=True)
    finally:
        if stream.exists():
            digest=sha256(stream.read_bytes()).hexdigest()
            # Manifest seals original stream. All raw memory stays on user's PC.
            manifest.write_text(json.dumps({
                'status':status,'reason_code':code,'protocol':'p0-a-state-blind-v1',
                'candidate_samples':packet_count,'stream_sha256':digest,
                'operator_intent_truth':user_truth,
                'predictions':predictions,'training_approved':False,
                'game_A_acceptance_verified':False,
                'guest_physics_step_verified':False,
            },indent=2)+'\n',encoding='utf-8')
    correct=sum(predictions[k]==truth for k,truth in user_truth.items() if truth in PHASES)
    scored=sum(truth in PHASES for truth in user_truth.values())
    summary={'status':status,'reason_code':code,'protocol':'p0-a-state-blind-v1',
             'sample_packets':packet_count,'calibration':fit_report,
             'blind_predictions':predictions,'blind_truth':user_truth,
             'blind_correct_including_UNKNOWN_as_wrong':correct,
             'blind_labeled_count':scored,
             'game_A_acceptance_verified':False,'guest_physics_step_verified':False,
             'training_approved':False}
    print(json.dumps(summary,indent=2,sort_keys=True))
    return 0 if status == 'COMPLETE' else 3

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=55355)
    parser.add_argument('--private-root',type=Path,required=True)
    parser.add_argument('--samples-per-window',type=int,default=3,choices=range(2,7))
    parser.add_argument('--blind-windows',type=int,default=4,choices=range(1,9))
    parser.add_argument('--focus-seconds',type=int,default=5,choices=range(3,9))
    args=parser.parse_args()
    raise SystemExit(run(args))

if __name__=='__main__':
    main()
