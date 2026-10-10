"""Read-only audit of local Crash camera diagnostic stdout. No game assets.

A passing gate proves raw guest camera values varied while the source observer
reported one gameplay scene/epoch. It NEVER certifies postphysics, projection
equivalence, a depth buffer or Mario/Crash world calibration.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
import re

CAM = re.compile(
 r"^\[cm64-camera\] RAW_SAMPLE phase=PAD_UNKNOWN level=(\d+)"
 r" seq=(\d+) epoch=(\d+) projection=(\d+)"
 r" zone=0x([0-9A-F]{8}) path=0x([0-9A-F]{8})"
 r" progress=(\d+) tx=(-?\d+) ty=(-?\d+) tz=(-?\d+)"
 r" m=([-0-9,]+) changed=[01] safe_for_shared_depth=false$"
)

def parse(raw: str):
    observations=[]
    for line in raw.splitlines():
        if not line.startswith("[cm64-camera] RAW_SAMPLE"):
            continue
        m=CAM.fullmatch(line.strip())
        if m is None:
            raise ValueError("Malformed or misleading source camera sample")
        level, seq, epoch, projection=map(int,m.group(1,2,3,4))
        zone=int(m.group(5),16); path=int(m.group(6),16)
        progress,tx,ty,tz=map(int,m.group(7,8,9,10))
        mat=tuple(map(int,m.group(11).split(",")))
        if len(mat)!=9 or not any(mat) or any(not -32768<=v<=32767 for v in mat):
            raise ValueError("Invalid native s16 rendering matrix")
        if not 1<=projection<=4096 or not 0x80000000<=zone<0x80200000 or not 0x80000000<=path<0x80200000:
            raise ValueError("Invalid guest camera pointer/projection provenance")
        if seq<1 or epoch<1 or level>255 or any(not -(2**31)<=v<2**31 for v in (tx,ty,tz)):
            raise ValueError("Invalid raw camera state")
        observations.append({"level":level,"seq":seq,"epoch":epoch,"proj":projection,
          "zone":zone,"path":path,"progress":progress,"trans":(tx,ty,tz),"matrix":mat})
    return observations

def assess(rows,minimum=3):
    if not rows:return {"verified":False,"reason":"NO_VALID_GAMEPLAY_CAMERA_SAMPLE",
       "samples":0,"changed":0,"postphysics":False,"depth_complete":False,"camera_calibrated":False}
    if any(b["seq"]<=a["seq"] for a,b in zip(rows,rows[1:])):
        raise ValueError("Nonmonotonic observer sequence")
    groups=defaultdict(list)
    for row in rows:
        groups[(row["level"],row["epoch"],row["zone"],row["path"])].append(row)
    scores=[]
    for scope,records in groups.items():
        changed=sum((a["matrix"],a["trans"],a["progress"],a["proj"]) !=
                    (b["matrix"],b["trans"],b["progress"],b["proj"])
                    for a,b in zip(records,records[1:]))
        scores.append((scope,len(records),changed))
    candidates=[entry for entry in scores if entry[1]>=minimum and entry[2]>=2]
    selected=max(candidates or scores,key=lambda x:(x[2],x[1]))
    groupkey,best,changes=selected
    ok=bool(candidates)
    return {"verified":ok,"reason":"RAW_ORIGINAL_CAMERA_VARIATION_ONLY" if ok else "INSUFFICIENT_OR_STATIONARY_CAMERA",
      "samples":len(rows),"scope_samples":best,"changed":changes,
      "level":groupkey[0],"epoch":groupkey[1],
      "postphysics":False,"depth_complete":False,"camera_calibrated":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-log",type=Path,required=True)
    a=p.parse_args()
    if not a.private_log.is_file() or a.private_log.stat().st_size>4_000_000:
        p.exit(2,"Private stdout log absent or oversized\n")
    try:
        report=assess(parse(a.private_log.read_text(encoding="utf-8",errors="replace")))
    except (ValueError,OSError) as exc:
        p.exit(2,f"Camera sample rejection: {exc}\n")
    print("CAMERA_SOURCE_GATE", " ".join(f"{k}={v}" for k,v in report.items()))
    if not report["verified"]:
        p.exit(1,"Native camera provenance gate not yet verified\n")

if __name__=="__main__": main()
