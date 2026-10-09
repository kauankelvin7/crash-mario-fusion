"""Asset-free representation proof, not a commercial level or Launcher run."""
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest

from tools.volume_boundary import AuthoredLeaf, top_boundary
from tools.world_coordinates import FrameMap

ROOT=Path(__file__).resolve().parents[1]
C1_PIN="256fdcef59f15a190290cc19db3fa9a707843b69"
SM64_PIN="d7ca2c04364a6dd0dac58b47151e04e26887e6f0"


def leaf(y=16):
    return AuthoredLeaf((16,y,16),(64,16,64),"AUTHORED_C1_SINGLE_LEAF",3)


def boundary(value):
    return top_boundary(value,frame_map=FrameMap((0,0,0),(0,0,0),1,0),
        crash_level=9,calibrated_level=9,mario_frame="AUTHORED_REFERENCE_ONLY",
        material=dict(provenance="AUTHORED_SYNTHETIC",native_type=0,room=0),
        surface_capacity=4,node_capacity=256,surfaces_used=0,nodes_used=0)


class VolumeBoundaryTests(unittest.TestCase):
    def test_explicit_reference_units_and_two_upward_faces(self):
        result=boundary(leaf())
        self.assertEqual(result["source_raw_bounds"],((4096,4096,4096),(20480,8192,20480)))
        self.assertEqual(result["plan"]["surfaces_required"],2)
        self.assertTrue(all(s["unit_normal"]==(0,1,0) for s in result["plan"]["surfaces"]))
        self.assertFalse(result["full_volume_equivalence"])
        self.assertFalse(result["live_collision_inserted"])

    def test_unsupported_provenance_events_and_numeric_domain_fail(self):
        for value in (AuthoredLeaf((16,16,16),(64,16,64),"EXTRACTED_UNVERIFIED",3),
                      AuthoredLeaf((-1,0,0),(64,16,64),"AUTHORED_C1_SINGLE_LEAF",3),
                      AuthoredLeaf((0,0,0),(0,16,64),"AUTHORED_C1_SINGLE_LEAF",3),
                      AuthoredLeaf((0,0,0),(64,16,64),"AUTHORED_C1_SINGLE_LEAF",0x13),
                      AuthoredLeaf((2048,0,0),(64,16,64),"AUTHORED_C1_SINGLE_LEAF",3),
                      AuthoredLeaf((True,0,0),(64,16,64),"AUTHORED_C1_SINGLE_LEAF",3)):
            with self.assertRaises(ValueError): boundary(value)
        with self.assertRaisesRegex(ValueError,"compact"):
            top_boundary(AuthoredLeaf((3000,16,16),(64,16,64),"AUTHORED_C1_SINGLE_LEAF",3),
                frame_map=FrameMap((3000,0,0),(0,0,0),1,0),crash_level=9,
                calibrated_level=9,mario_frame="AUTHORED_REFERENCE_ONLY",
                material=dict(provenance="AUTHORED_SYNTHETIC",native_type=0,room=0),
                surface_capacity=2,node_capacity=256,surfaces_used=0,nodes_used=0)


class NativeBoxComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources={"c1":Path(os.environ.get("CM64_C1_ROOT","/workspace/.cache/crash-mario-m0/c1")),
                 "sm64":Path(os.environ.get("CM64_SM64EX_ROOT","/workspace/.cache/crash-mario-m0/sm64ex"))}
        if not shutil.which("gcc") or any(not p.is_dir() for p in sources.values()):
            if "CM64_C1_ROOT" in os.environ: raise AssertionError("Configured reference oracle dependencies missing")
            raise unittest.SkipTest("Set CM64_C1_ROOT and CM64_SM64EX_ROOT to public pinned sources")
        for name,pin in (("c1",C1_PIN),("sm64",SM64_PIN)):
            source=sources[name]
            if subprocess.check_output(["git","-C",str(source),"rev-parse","HEAD"],text=True).strip()!=pin:
                raise AssertionError("Wrong reference source pin")
            if subprocess.check_output(["git","-C",str(source),"status","--porcelain","--untracked-files=no"],text=True).strip():
                raise AssertionError("Reference source modified")
        cls.temp=tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.temp.cleanup)
        # Compile exact source slices rather than unrelated 32-bit engine code.
        # Pins checked above; no replacement query/math implementation is supplied.
        text=(sources["c1"]/"src/solid.c").read_text()
        selected=text[text.index("static void ZoneQueryOctreeR("):text.index("\nvoid PlotQueryWalls(")]
        selected+=text[text.index("void FindFloorY("):text.index("\nint FindCeilY(")]
        (Path(cls.temp.name)/"cm64_c1_queries.h").write_text('#include "solid.h"\n'+selected)
        common=["gcc","-g","-UNDEBUG","-ffunction-sections","-fdata-sections"]
        if platform.system()=="Linux":
            common += ["-fsanitize=address,undefined","-fno-sanitize-recover=all","-fno-pie","-no-pie"]
        cls.probes={}
        for name in ("c1","sm64"):
            source=sources[name]; exe=Path(cls.temp.name)/name
            if name=="c1":
                command=common+["-std=gnu11","-fplan9-extensions","-I"+str(source/"src"),
                    "-I"+cls.temp.name,str(ROOT/"tests/native_crash_box_probe.c")]
            else:
                command=common+["-std=c11","-DVERSION_US","-D_LANGUAGE_C","-DNON_MATCHING","-DAVOID_UB",
                    "-I"+str(source/"src"),"-I"+str(source/"include"),"-I"+str(source),
                    str(ROOT/"tests/native_mario_box_probe.c"),str(source/"src/engine/surface_collision.c")]
            command += ["-Wl,--gc-sections","-lm","-o",str(exe)]
            result=subprocess.run(command,capture_output=True,text=True,timeout=60)
            if result.returncode: raise AssertionError(result.stderr)
            cls.probes[name]=exe

    def compare(self,leaves,point):
        boxes=" ".join(str(v) for item in leaves for v in (*item.origin,*item.dimensions))+"\n"
        faces=[face for item in leaves for face in boundary(item)["plan"]["surfaces"]]
        triangles=" ".join(str(v) for face in faces for vertex in face["vertices"] for v in vertex)+"\n"
        outputs=[]
        for name,count,data in (("c1",len(leaves),boxes),("sm64",len(faces),triangles)):
            result=subprocess.run([str(self.probes[name]),str(count),*(str(v) for v in point)],
                                  input=data,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            value=float(result.stdout)
            outputs.append(value/256 if name=="c1" and value!=-1 else value)
        return tuple(outputs)

    def test_single_top_interior_diagonal_perimeter_and_outside(self):
        for point in ((32,64,32),(48,64,48),(16,64,16),(80,64,80),(80,64,32)):
            with self.subTest(point=point): self.assertEqual(self.compare([leaf()],point),(32,32))
        for point in ((15,64,32),(81,64,32),(32,64,81)):
            with self.subTest(point=point): self.assertEqual(self.compare([leaf()],point),(-1,-1))

    def test_overlap_is_measured_counterexample_not_equivalence(self):
        # Both unchanged algorithms run: Crash reference averages 32/48;
        # native Mario returns the highest eligible support at 48.
        self.assertEqual(self.compare([leaf(),leaf(32)],(32,64,32)),(40,48))

    def test_malformed_native_fixture_input_is_bounded(self):
        for name,count in (("c1",1),("sm64",2)):
            for data in ("9"*200+"\n","0 garbage\n","0 0"):
                result=subprocess.run([str(self.probes[name]),str(count),"32","64","32"],
                                      input=data,capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,2,result.stderr)


if __name__=="__main__": unittest.main()
