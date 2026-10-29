"""Offline source-anchored audit of Wii Sports golf RAM snapshots.

Prints relative word offsets/change counts, never raw RAM, pointers or game
values. A changed value is NOT proof of club pose, power or ball coordinates.
"""
from __future__ import annotations
import argparse,json,math,struct,sys
from pathlib import Path

MAX_BYTES=64*1024*1024
MAX_SAMPLES=2000
KNOWN={"golf_config","golf_field","sports_sequence",
       "minimap_ball_effect","minimap_player_effect","minimap_shot_line_effect"}

def known_role(region,offset):
    if region=="golf_config":
        if 0x04<=offset<0x94:return "player_hole_scores"
        return {0x94:"game_mode",0x98:"current_hole"}.get(offset,"undocumented")
    if region=="sports_sequence":
        if 0x14<=offset<0xA4:return "golf_scores"
        return {0x04:"sport",0x08:"sequence",0x0C:"training_game",
                0x10:"golf_final_hole",0xAC:"golf_mode"}.get(offset,"undocumented")
    if region=="golf_field":
        return {0x04:"player_shadow_ptr",0x10:"tree_shadow_timer",
                0x44:"current_pin_object_ptr",0x50:"current_start_object_ptr",
                0x54:"cup_object_ptr",0x80:"green_slope_opacity",
                0x88:"minimap_visible",0x94:"minimap_player_effect_ptr",
                0x98:"minimap_shot_line_effect_ptr",
                0x9C:"minimap_ball_effect_ptr"}.get(offset,"undocumented")
    if region.startswith("minimap_"):return "rendering_effect_undocumented"
    return "undocumented"

def _pointer(bits):
    return bits%4==0 and (0x80000000<=bits<0x81800000 or
                         0x90000000<=bits<0x94000000)

def _float(bits):
    val=struct.unpack(">f",struct.pack(">I",bits))[0]
    return math.isfinite(val) and 1e-5<=abs(val)<=360

def _regions(row):
    if row.get("game_id")=="RSPE01" and row.get("disc_revision")==1:
        result={}
        for name,entry in row.get("windows",{}).items():
            if name not in KNOWN:continue
            if not isinstance(entry,dict):raise ValueError("bad window")
            addr=entry.get("address")
            if not isinstance(addr,str) or not addr.startswith("0x"):
                raise ValueError("bad window address")
            int(addr,16)
            data=bytes.fromhex(entry["bytes_hex"])
            if not 4<=len(data)<=0x1C74 or len(data)%4:
                raise ValueError("unbounded memory window")
            result[name]=(addr,data)
        return result
    if "hex" in row and "pointer" in row and "phase" in row:
        data=bytes.fromhex(row["hex"])
        if len(data)!=128 or type(row["pointer"]) is not int:
            raise ValueError("not a minimap 128-byte capture")
        return {"minimap_ball_effect":(f'0x{row["pointer"]:08X}',data)}
    raise ValueError("not a supported Rev1 outcome or minimap snapshot")

def analyze(rows,top=80):
    if not 2<=len(rows)<=MAX_SAMPLES or not 1<=top<=500:
        raise ValueError("requires 2..2000 snapshots, top 1..500")
    changed={};prior=None;relocations=0;comparisons=0;phases={}
    for row in rows:
        if not isinstance(row,dict):raise ValueError("snapshot not object")
        phase=row.get("phase")
        if phase not in ("pre","post","settled","idle","aim_only","swing"):
            raise ValueError("unsupported phase")
        phases[phase]=phases.get(phase,0)+1
        windows=_regions(row)
        if prior is not None:
            pphase,pwindows=prior
            for name in windows.keys() & pwindows.keys():
                address,data=windows[name];old_address,old_data=pwindows[name]
                if address!=old_address or len(data)!=len(old_data):
                    relocations+=1;continue
                comparisons+=1
                for offset in range(0,len(data),4):
                    before=struct.unpack_from(">I",old_data,offset)[0]
                    after=struct.unpack_from(">I",data,offset)[0]
                    if before==after:continue
                    entry=changed.setdefault((name,offset),{
                        "within_phase":0,"across_phase":0,
                        "pointer_like_transitions":0,"plausible_float_transitions":0})
                    entry["within_phase" if phase==pphase else "across_phase"]+=1
                    entry["pointer_like_transitions"]+=int(_pointer(before) and _pointer(after))
                    entry["plausible_float_transitions"]+=int(_float(before) and _float(after))
        prior=phase,windows
    words=[{"window":name,"offset_hex":f"+0x{offset:X}",
            "known_role":known_role(name,offset),**stat}
           for (name,offset),stat in changed.items()]
    words.sort(key=lambda x:(-x["within_phase"],-x["across_phase"],
                             x["window"],int(x["offset_hex"][3:],16)))
    return {"schema_version":1,"kind":"offline_golf_memory_region_audit",
            "samples":len(rows),"phase_counts":phases,
            "same_instance_region_comparisons":comparisons,
            "relocation_skips":relocations,"changed_word_count":len(words),
            "top_changed_words":words[:top],
            "warnings":["Relative offsets and change counts only; raw memory stays private",
                        "Source labels documented; type patterns are only hints",
                        "No verified club pose, swing power, ball position or score"]}

def load(path):
    if not path.is_file() or not 0<path.stat().st_size<=MAX_BYTES:
        raise ValueError("missing or oversized raw capture")
    result=[]
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                result.append(json.loads(line))
                if len(result)>MAX_SAMPLES:raise ValueError("too many samples")
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--out",type=Path)
    p.add_argument("--top",type=int,default=80)
    a=p.parse_args(argv)
    try:
        if a.out and a.out.resolve()==a.input.resolve():
            raise ValueError("cannot overwrite raw input")
        result=analyze(load(a.input),a.top)
        output=json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n"
        if a.out:
            a.out.parent.mkdir(parents=True,exist_ok=True)
            with a.out.open("x",encoding="utf-8") as file:file.write(output)
        print(output,end="")
        return 0
    except (OSError,TypeError,ValueError,KeyError) as exc:
        print("Offline memory audit failed:",exc,file=sys.stderr)
        return 1

if __name__=="__main__":raise SystemExit(main())
