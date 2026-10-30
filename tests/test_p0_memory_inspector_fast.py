"""Synthetic-only parity, RPC count and fail-closed tests for inspector batch reads."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from wii_ai_golf.inspector.fast import packet as batch_packet

try:
    import p0_live_no_contact_compare as base
    import p0_live_directional_aim_series as canonical
except ImportError:
    base = canonical = None


class FixtureRPC:
    def __init__(self):
        self.words = {}
        self.calls = []
        self.frame=0
        self.mutate_source=False
        self.bad_range=False
        if base is None: return
        M=self.words
        mgr=0x80010000; scene=0x90010000; config=0x90020000
        field=0x90030000; pm=0x90040000; record=pm+4; ball=0x90050000
        nested=0x90060000; tee=0x90070000; pin=0x90080000
        tee_vec=0x90090000;pin_vec=0x900A0000
        M.update({base.SCENE_STATIC:mgr,base.SCENE_STATIC+4:0,mgr+0x18:5,
                  mgr+0xC:scene,scene+0x1C:5,scene+0x20:mgr,scene+0x54:2,
                  scene:0x803C7718,base.CONFIG_STATIC:config,base.FIELD_STATIC:field,
                  config+0x94:4,config+0x98:1,base.PLAYER_MANAGER_STATIC:pm,
                  pm:0x803C7DD0,pm+0x334:record,record+0x88:ball,
                  ball:0x803C7918,ball+0x4C:nested,field+0x50:tee,
                  field+0x44:pin,tee+0x4C:tee_vec,pin+0x4C:pin_vec,
                  record+0x3C:0x3f800000})
        for region in (ball+0x30,ball+0xCC,ball+0xF0,ball+0xFC,
                       nested,record+0x54,record+0x60,tee_vec,pin_vec,
                       record+0x30,record+0x90):
            for i in range(3):
                M[region+i*4]=0x3f000000+(i<<18)
        # All data is synthetic; no real game RAM, ROM or Dolphin.

    def call(self, method, args):
        self.calls.append((method,tuple(args)))
        if method=='frame.get_count':
            self.frame+=1;return self.frame
        if method=='memory.read_u32':
            addr=args[0]
            if self.mutate_source and addr==base.SCENE_STATIC: return 0x80020000
            return self.words.get(addr,0)
        if method=='memory.read_bytes':
            addr,size=args
            if self.bad_range and addr==0x90050000:return 'oops'
            if addr==0x80000000 and size==8:return b'RSPE01\x00\x01'.hex()
            assert addr%4==0 and size%4==0
            content = b''.join(int(self.words.get(a,0)).to_bytes(4,'big')
                            for a in range(addr,addr+size,4))
            if self.mutate_source and addr<=base.SCENE_STATIC<addr+size:
                idx=base.SCENE_STATIC-addr
                content=content[:idx]+(0x80020000).to_bytes(4,'big')+content[idx+4:]
            return content.hex()
        raise AssertionError('unexpected RPC '+method)


@unittest.skipIf(base is None, 'Full repository P0 readers are not mounted in isolated staging')
class FastPacketTests(unittest.TestCase):
    def test_exact_source_schema_and_words_match_canonical(self):
        a=FixtureRPC();b=FixtureRPC()
        previous=canonical.packet(a,'LIVE',0)
        current=batch_packet(b,'LIVE',0)
        self.assertEqual(current['identity'],previous['identity'])
        self.assertEqual(current['words'],previous['words'])
        self.assertEqual(current['frame_bracket'],previous['frame_bracket'])
        self.assertEqual(set(current),set(previous))
        self.assertGreater(len(a.calls),len(b.calls)*1.8)
        self.assertTrue(all(m in {'frame.get_count','memory.read_u32','memory.read_bytes'}
                            for m,_ in b.calls))

    def test_optimized_source_gate_and_live_a_record(self):
        x=FixtureRPC()
        data=batch_packet(x,'LIVE',0,include_a_state=True)
        self.assertEqual(len(data['a_record']),51)
        self.assertEqual(data['a_record'][0x3C//4], data['words']['aim_candidate_plus_0x3c'][0])
        self.assertLess(len(x.calls),35)

    def test_fails_on_source_mutation(self):
        x=FixtureRPC();x.mutate_source=True
        with self.assertRaises(ValueError):batch_packet(x,'LIVE',0)

    def test_fails_on_malformed_binary_read(self):
        x=FixtureRPC();x.bad_range=True
        with self.assertRaisesRegex(ValueError, 'bounded read'):
            batch_packet(x,'LIVE',0)

    def test_never_reads_outside_guest_banks(self):
        x=FixtureRPC();batch_packet(x,'LIVE',0)
        for meth,args in x.calls:
            if meth.startswith('memory.'):
                addr=args[0];size=args[1] if meth=='memory.read_bytes' else 4
                self.assertTrue(base.in_bank(addr,size))

if __name__=='__main__':unittest.main()
