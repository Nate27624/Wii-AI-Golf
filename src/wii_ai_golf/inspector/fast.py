"""Compact source-checked read-only Golf snapshot (no writes or input).

Big-endian blocks are read on the existing Felk bridge. All previous Rev1,
scene, vtable, selected owner, tee/pin, hole, and epoch guards are preserved,
with grouped (not cached) validation reads. Host sequential reads are NOT
an atomic guest physics frame. This is only an inspector display sampler.
"""
from __future__ import annotations
import time


def packet(rpc, phase: str, index: int, *, include_a_state: bool = False) -> dict:
    import p0_live_no_contact_compare as base

    def region(address: int, count: int, bank: str | None = None) -> tuple[int, ...]:
        if (type(address) is not int or type(count) is not int or count < 1
                or count > 1024 or not base.in_bank(address, 4 * count, bank)):
            raise ValueError('invalid source-scoped block')
        value = rpc.call('memory.read_bytes', [address, 4*count])
        if type(value) is not str or len(value) != count * 8:
            raise ValueError('malformed bounded read')
        try:
            data = bytes.fromhex(value)
        except ValueError as e:
            raise ValueError('invalid BE bytes') from e
        if len(data) != 4 * count:
            raise ValueError('short bounded read')
        return tuple(int.from_bytes(data[i:i+4], 'big') for i in range(0, len(data), 4))

    def get(xs: tuple[int, ...], offset: int) -> int:
        return xs[offset//4]

    def part(xs: tuple[int, ...], offset: int, count: int = 3) -> tuple[int,...]:
        return xs[offset//4:offset//4+count]

    def ptr(value: int, bank: str, length: int = 4) -> int:
        if not base.in_bank(value, length, bank):
            raise ValueError('invalid source actor pointer')
        return value

    def snapshot_globals() -> dict[int, int]:
        # All 4 known MEM1 roots live in this bounded 1020B region. No RAM
        # search and no reuse between start and end of a sample.
        start, end = base.SCENE_STATIC, base.PLAYER_MANAGER_STATIC + 4
        block = region(start, (end - start)//4, 'MEM1')
        return {addr: block[(addr-start)//4] for addr in (
            base.SCENE_STATIC, base.SCENE_STATIC+4,
            base.CONFIG_STATIC, base.FIELD_STATIC, base.PLAYER_MANAGER_STATIC)}

    def epoch_matches(identity: tuple[int,...]) -> bool:
        mgr, scene, config, field, pm, selected, record, ball, nested, tee, tee_vec, pin, pin_vec, hole = identity
        roots = snapshot_globals()
        if (roots[base.SCENE_STATIC] != mgr or roots[base.CONFIG_STATIC] != config
                or roots[base.FIELD_STATIC] != field or roots[base.PLAYER_MANAGER_STATIC] != pm):
            return False
        # Every item in directional source.end_epoch_matches is independently
        # re-read here, but adjacent checks are grouped into single RPCs.
        manager = region(mgr+0xC, 4, 'MEM1')
        config_check = region(config+0x94, 2, 'MEM2')
        field_check = region(field+0x44, 4, 'MEM2')
        if (manager[0] != scene or manager[3] != 5 or
                config_check != (4,hole) or
                field_check[0] != pin or field_check[3] != tee):
            return False
        return (region(pm+0x334,1,'MEM2')[0] == record and
                region(record+0x88,1,'MEM2')[0] == ball and
                region(ball+0x4C,1,'MEM2')[0] == nested and
                region(tee+0x4C,1,'MEM2')[0] == tee_vec and
                region(pin+0x4C,1,'MEM2')[0] == pin_vec)

    start_ns=time.monotonic_ns()
    before=rpc.call('frame.get_count',[])
    if type(before) is not int or before<0:
        raise ValueError('invalid frame bracket')
    header=rpc.call('memory.read_bytes',[0x80000000,8])
    if type(header) is not str or len(header)!=16:
        raise ValueError('invalid revision header')
    try:
        sig=bytes.fromhex(header)
    except ValueError as exc:
        raise ValueError('invalid revision header') from exc
    if sig[:6]!=b'RSPE01' or sig[7]!=1:
        raise ValueError('not Wii Sports USA Rev1')
    roots=snapshot_globals()
    mgr=ptr(roots[base.SCENE_STATIC],'MEM1',0x20)
    if roots[base.SCENE_STATIC+4]!=0:
        raise ValueError('invalid scene static')
    manager=region(mgr+0xC,4,'MEM1')
    if manager[3]!=5:
        raise ValueError('not Golf scene')
    scene=ptr(manager[0],'MEM2',0xA0)
    scene_head=region(scene,0x58//4,'MEM2')
    if (get(scene_head,0x1C)!=5 or get(scene_head,0x20)!=mgr
            or get(scene_head,0x54)!=2 or
            not 0x803C7718<=scene_head[0]<0x803C7798):
        raise ValueError('scene source/owner mismatch')
    config=ptr(roots[base.CONFIG_STATIC],'MEM2',0x9C)
    field=ptr(roots[base.FIELD_STATIC],'MEM2',0xA8)
    conf=region(config+0x94,2,'MEM2')
    if conf[0]!=4 or conf[1]>8:
        raise ValueError('not active Hitting-the-Green hole')
    hole=conf[1]
    pm=ptr(roots[base.PLAYER_MANAGER_STATIC],'MEM2',0x33C)
    manager_words=region(pm,0x338//4,'MEM2')
    if not 0x803C7DD0<=manager_words[0]<0x803C7DE0:
        raise ValueError('invalid player manager type')
    record=manager_words[0x334//4]
    selected=[i for i in range(4) if record==pm+4+i*base.STRIDE]
    if len(selected)!=1:
        raise ValueError('ambiguous selected player')
    record=ptr(record,'MEM2',base.STRIDE)
    r=region(record,base.STRIDE//4,'MEM2')
    ball=ptr(get(r,0x88),'MEM2',0x120)
    b=region(ball,0x108//4,'MEM2')
    if not 0x803C7918<=b[0]<0x803C7A50:
        raise ValueError('selected ball class mismatch')
    nested=ptr(get(b,0x4C),'MEM2',12)
    field_words=region(field+0x44,4,'MEM2')
    pin=ptr(field_words[0],'MEM2',0x50)
    tee=ptr(field_words[3],'MEM2',0x50)
    tee_vec=ptr(region(tee+0x4C,1,'MEM2')[0],'MEM2',12)
    pin_vec=ptr(region(pin+0x4C,1,'MEM2')[0],'MEM2',12)
    values={
      'selected_nested_plus_0x4c':region(nested,3,'MEM2'),
      'selected_ball_plus_0x30':part(b,0x30),
      'selected_ball_cache_plus_0xcc':part(b,0xCC),
      'selected_ball_cache_plus_0xf0':part(b,0xF0),
      'selected_ball_cache_plus_0xfc':part(b,0xFC),
      'record_initial_plus_0x54':part(r,0x54),
      'record_start_copy_plus_0x60':part(r,0x60),
      'tee_start_candidate':region(tee_vec,3,'MEM2'),
      'pin_candidate':region(pin_vec,3,'MEM2'),
      'aim_candidate_plus_0x3c':(get(r,0x3C),),
    }
    mid=rpc.call('frame.get_count',[])
    if type(mid) is not int or mid<before:
        raise ValueError('invalid frame bracket')
    identity=(mgr,scene,config,field,pm,selected[0],record,ball,nested,tee,tee_vec,pin,pin_vec,hole)
    extras={'selected_record_plus_0x30':part(r,0x30),
            'selected_record_plus_0x90':part(r,0x90)}
    # Detect non-stationarity during A reads BEFORE the final owner recheck.
    a_record=None
    if include_a_state:
        if (region(ball+0x30,3,'MEM2')==values['selected_ball_plus_0x30']
                and region(record+0x3C,1,'MEM2')==(get(r,0x3C),)):
            a_record=r
    if not epoch_matches(identity):
        raise ValueError('source identity changed across packet')
    end=rpc.call('frame.get_count',[])
    if type(end) is not int or end<mid:
        raise ValueError('invalid bridge ordering')
    payload={'phase':phase,'index':index,'start_ns':start_ns,'end_ns':time.monotonic_ns(),
             'frame_bracket':(before,end),'identity':identity,'words':{**values,**extras}}
    if include_a_state:
        payload['a_record']=a_record
    return payload
