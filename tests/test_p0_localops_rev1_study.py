"""Synthetic, offline positive/negative controls. No native archive needed."""
from __future__ import annotations
import importlib.util
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'audit_p0_localops_rev1_study.py'
SPEC = importlib.util.spec_from_file_location('p0rev1',SCRIPT)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def bl(pc, target):
    return (18 << 26) | ((target-pc) & 0x3fffffc) | 1


def stfs(fr, ra, off):
    return (52 << 26) | (fr << 21) | (ra << 16) | off


def dform(op, fr, ra, off):
    return (op << 26) | (fr << 21) | (ra << 16) | (off & 0xffff)


def psq(op, fr, ra, off, w=0, i=0):
    """Synthetic PowerPC DQ-form; W/I live above 12-bit signed displacement."""
    return ((op << 26) | (fr << 21) | (ra << 16) |
            (w << 15) | (i << 12) | (off & 0xfff))


def manifest():
    return {'kind':'p0-private-numbered-capture-inventory',
            'training_approved':False,
            'human_phase_file_mapping_verified':False,
            'capture_count':7,'capture_numbers':list(range(1,8)),
            'captures':[{'capture_number':n,'banks':[
                {'file':f'{n}.{i}.raw', 'bank':bank,'bytes':size,
                 'copy_verified':True,'sha256':'a'*64}
                for i,(bank,size) in enumerate((('MEM1',m.MEM1_SIZE),
                                                  ('MEM2',m.MEM2_SIZE)),1)]}
                for n in range(1,8)]}


def native():
    d={0x802A3D6C:bl(0x802A3D6C,0x8002F7E8),
       0x802A3D90:bl(0x802A3D90,0x8002F7E8),
       0x802A3DA8:bl(0x802A3DA8,0x8002F75C),
       0x802A3DE0:0x4e800020,
       0x802B2ECC:bl(0x802B2ECC,0x8002F898),
       0x802B2E54:bl(0x802B2E54,0x802A3CF4),
       0x802B2EE0:bl(0x802B2EE0,0x802A3CF4),
       0x802B2ED4:stfs(1,31,0x1b4),
       0x802B2EF4:stfs(1,31,0x1b0)}
    return d

class StudyTests(unittest.TestCase):
    def test_manifest_valid(self):
        self.assertEqual(len(m._manifest_descriptor(manifest())),14)

    def test_manifest_rejects_false_claims(self):
        for change in ({'training_approved':True},
                       {'capture_count':8},
                       {'capture_numbers':[1,2,3,4,5,6,6]},
                       {'human_phase_file_mapping_verified':True}):
            with self.subTest(change=change):
                x=manifest();x.update(change)
                with self.assertRaises(m.Abstain):m._manifest_descriptor(x)

    def test_manifest_rejects_wrong_bank_and_hash(self):
        for key,bad in (('bank','bad'),('sha256','notasha'),('copy_verified',False)):
            x=manifest();x['captures'][0]['banks'][0][key]=bad
            with self.subTest(key=key),self.assertRaises(m.Abstain):
                m._manifest_descriptor(x)

    def test_branch_decode(self):
        for pc,dest in ((0x802A3D6C,0x8002F7E8),(0x802B2E54,0x802A3CF4)):
            self.assertEqual(m._branch(pc,bl(pc,dest)),dest)
        self.assertIsNone(m._branch(0x802B2ECC,0x4e800020))

    def test_source_gates_accept_expected(self):
        d=native()
        result=m._source_gates(lambda pc:d.get(pc,0))
        self.assertTrue(result['sin_fidx_call_gated'])
        self.assertEqual(len(result['nonlinear_helper_call_pcs']),2)

    def test_source_gates_fail_on_call_mutation(self):
        d=native();d[0x802A3D90]=bl(0x802A3D90,0x8002F75C)
        with self.assertRaisesRegex(m.Abstain,'qualification incomplete'):
            m._source_gates(lambda pc:d.get(pc,0))

    def test_source_gates_fail_on_store_mutation(self):
        d=native();d[0x802B2EF4]=stfs(1,31,0x1b8)
        with self.assertRaises(m.Abstain):
            m._source_gates(lambda pc:d.get(pc,0))

    def test_discovery_no_archive_sanitized(self):
        with tempfile.TemporaryDirectory() as root:
            checkout=pathlib.Path(root)/'checkout'
            checkout.mkdir()
            with self.assertRaises(m.Abstain) as cm:
                m._find_candidates(checkout)
            self.assertEqual(cm.exception.code,'NO_CANONICAL_ARCHIVE')

    def test_lexical_census_does_not_claim_receiver(self):
        lo,hi=m.SOURCE_WINDOWS[2]
        data=bytearray(hi-lo)
        ix=0x802B2ED4-lo
        data[ix:ix+4]=stfs(1,31,0x1b4).to_bytes(4,'big')
        rows=m._lexical_consumers({(lo,hi):bytes(data)})
        self.assertEqual(rows['+0x1B4']['lexical_dform_count'],1)
        self.assertFalse(rows['+0x1B4']['receiver_proven'])


    def test_source_gates_fail_on_helper_callsite_mutation(self):
        d=native()
        # Two total helper calls, but one moved to an unsupported source PC.
        d[0x802B2E54]=0
        d[0x802B2E50]=bl(0x802B2E50,0x802A3CF4)
        with self.assertRaises(m.Abstain):
            m._source_gates(lambda pc:d.get(pc,0))

    def test_source_gates_fail_on_wrong_store_base(self):
        d=native()
        d[0x802B2ED4]=stfs(1,30,0x1b4)
        with self.assertRaises(m.Abstain):
            m._source_gates(lambda pc:d.get(pc,0))

    def test_paired_single_dq_forms_and_quantization_bits(self):
        lo,hi=m.SOURCE_WINDOWS[2]
        data=bytearray(hi-lo)
        pc=lo+0x800
        for j,op in enumerate((56,57,60,61)):
            w=psq(op,2,31,0x1b0,w=j%2,i=j%8)
            data[pc-lo+j*4:pc-lo+j*4+4]=w.to_bytes(4,'big')
        rows=m._lexical_consumers({(lo,hi):bytes(data)})
        one=rows['+0x1B0']
        self.assertEqual(one['lexical_paired_single_dq_count'],4)
        self.assertEqual(one['lexical_dform_count'],0)
        self.assertTrue(one['indexed_pair_accesses_unresolved'])
        self.assertFalse(one['receiver_proven'])
        self.assertEqual({x.split(':')[1] for x in one['sample_paired_single_pc_operation']},
                         {'psq_l','psq_lu','psq_st','psq_stu'})

    def test_paired_single_negative_control_and_offset_separation(self):
        lo,hi=m.SOURCE_WINDOWS[2]
        data=bytearray(hi-lo)
        # Nearby offsets must not look like reads of +0x1B0.
        data[0:4]=psq(56,0,31,0x1b4).to_bytes(4,'big')
        data[4:8]=psq(60,0,31,0x1b8).to_bytes(4,'big')
        # Indexed or unrelated opcode has no DQ-form constant displacement.
        data[8:12]=((4<<26)|(31<<16)|0x1b0).to_bytes(4,'big')
        rows=m._lexical_consumers({(lo,hi):bytes(data)})
        self.assertEqual(rows['+0x1B0']['lexical_paired_single_dq_count'],0)
        self.assertEqual(rows['+0x1B4']['lexical_paired_single_dq_count'],1)
        self.assertEqual(rows['+0x1B8']['lexical_paired_single_dq_count'],1)


    def test_discovery_crowded_captures_with_only_one_exact_manifest(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            parent=pathlib.Path(root)
            checkout=parent/'viewer'
            checkout.mkdir()
            captures=parent/'Wii-AI-Golf-Data'/'captures'
            captures.mkdir(parents=True)
            for i in range(45):  # More than the old arbitrary 30-dir cap.
                (captures/f'historical-{i:03d}').mkdir()
            invalid=captures/'legacy-with-kind-but-no-7-pair'
            invalid.mkdir()
            (invalid/'manifest-PRIVATE.json').write_text(json.dumps({
                'kind':'p0-private-numbered-capture-inventory',
                'capture_count':2}),encoding='utf-8')
            good=captures/'original-seven'
            good.mkdir()
            (good/'manifest-PRIVATE.json').write_text(
                json.dumps(manifest()),encoding='utf-8')
            self.assertEqual(
                m._find_candidates(checkout), ((good,'direct-sibling'),))

    def test_discovery_rejects_two_canonical_manifests(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            parent=pathlib.Path(root)
            checkout=parent/'viewer'
            checkout.mkdir()
            captures=parent/'Wii-AI-Golf-Data'/'captures'
            captures.mkdir(parents=True)
            for name in ('first','second'):
                sub=captures/name
                sub.mkdir()
                (sub/'manifest-PRIVATE.json').write_text(
                    json.dumps(manifest()),encoding='utf-8')
            with self.assertRaises(m.Abstain) as ctx:
                m._find_candidates(checkout)
            self.assertEqual(ctx.exception.code,'AMBIGUOUS_ARCHIVE')

    def test_discovery_rejects_over_explicit_scan_bound(self):
        with tempfile.TemporaryDirectory() as root:
            parent=pathlib.Path(root)
            checkout=parent/'viewer'
            checkout.mkdir()
            captures=parent/'Wii-AI-Golf-Data'/'captures'
            captures.mkdir(parents=True)
            for i in range(m.MAX_CAPTURE_DIRS_PER_ROOT+1):
                (captures/f'historical-{i:04d}').mkdir()
            with self.assertRaises(m.Abstain) as ctx:
                m._find_candidates(checkout)
            self.assertEqual(ctx.exception.code,'TOO_MANY_ARCHIVES')

    def test_discovery_ignores_symlinked_capture_cohort(self):
        import json
        with tempfile.TemporaryDirectory() as root:
            parent=pathlib.Path(root)
            checkout=parent/'viewer'
            checkout.mkdir()
            captures=parent/'Wii-AI-Golf-Data'/'captures'
            captures.mkdir(parents=True)
            actual=parent/'external'
            actual.mkdir()
            (actual/'manifest-PRIVATE.json').write_text(
                json.dumps(manifest()),encoding='utf-8')
            try:
                (captures/'alias').symlink_to(actual,target_is_directory=True)
            except (OSError,NotImplementedError):
                self.skipTest('symlink creation not permitted on this OS')
            with self.assertRaises(m.Abstain) as ctx:
                m._find_candidates(checkout)
            self.assertEqual(ctx.exception.code,'NO_CANONICAL_ARCHIVE')


    def test_field_register_census_all_scalar_and_paired_update_forms(self):
        lo,hi=m.SOURCE_WINDOWS[2]
        data=bytearray(hi-lo)
        instructions=(
            dform(48,1,31,0x1b0), dform(49,2,30,0x1b4),
            dform(52,3,29,0x1b8), dform(53,4,28,0x1b0),
            psq(56,5,27,0x1b4,w=1,i=3),
            psq(57,6,26,0x1b8,w=1,i=5),
            psq(60,7,25,0x1b0,w=0,i=2),
            psq(61,8,24,0x1b4,w=0,i=7),
        )
        for j,w in enumerate(instructions):
            data[4*j:4*j+4]=w.to_bytes(4,'big')
        result=m._field_opcode_registers({(lo,hi):bytes(data)})
        rows=result['rows']
        self.assertEqual([r[2] for r in rows],
                         ['lfs','lfsu','stfs','stfsu','psq_l','psq_lu',
                          'psq_st','psq_stu'])
        self.assertEqual([r[3] for r in rows],list(range(31,23,-1)))
        self.assertEqual([r[4] for r in rows],list(range(1,9)))
        self.assertEqual(result['counts_by_field'],
                         {'1B0':3,'1B4':3,'1B8':2})
        self.assertFalse(result['receiver_alias_proven'])
        self.assertFalse(result['same_shot_selected_ball_consumer_proven'])

    def test_field_register_census_lexical_negative_controls(self):
        lo,hi=m.SOURCE_WINDOWS[2]
        data=bytearray(hi-lo)
        cases=(dform(32,1,31,0x1b0),     # unrelated lwz GPR
               dform(48,2,31,-0x1b0),    # signed negative, not +1B0
               dform(50,3,31,0x1b4),     # lfd not in studied f32 set
               (4<<26)|(2<<21)|(31<<16)|0x1b8)
        for j,w in enumerate(cases):
            data[4*j:4*j+4]=w.to_bytes(4,'big')
        result=m._field_opcode_registers({(lo,hi):bytes(data)})
        self.assertEqual(result['rows'],[])
        self.assertEqual(result['counts_by_field'],
                         {'1B0':0,'1B4':0,'1B8':0})

    def test_field_register_census_fails_closed_on_window_and_count(self):
        lo,hi=m.SOURCE_WINDOWS[2]
        with self.assertRaises(m.Abstain):
            m._field_opcode_registers({(lo,hi):b'\x00'*8})
        data=bytearray(hi-lo)
        w=dform(48,1,31,0x1b0).to_bytes(4,'big')
        for j in range(41):
            data[4*j:4*j+4]=w
        with self.assertRaises(m.Abstain) as cm:
            m._field_opcode_registers({(lo,hi):bytes(data)})
        self.assertEqual(cm.exception.code,'FIELD_LEXICAL_COUNT_CAP')

if __name__=='__main__':unittest.main()