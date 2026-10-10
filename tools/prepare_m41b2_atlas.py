"""M4.1B2A controlled private-only patch for Crash-host owned guest texture.

It extends the previously pinned and verified M4.1B1 patch, refusing drift,
public-upstream edits, unknown existing guest resource source or retail files.
"""
import argparse
from pathlib import Path
from tools.prepare_m41b_host import verify_private as verify_m41b

GL_ANCHOR = "    static GL? _gl;\n"
GL_REPLACEMENT = GL_ANCHOR + "    internal static GL? CM64ActiveGL => _gl;\n"
SHUTDOWN_ANCHOR = "        _glBackend?.Dispose();\n"
SHUTDOWN_REPLACEMENT = "        OriginalMarioAtlas.Shutdown(_gl);\n" + SHUTDOWN_ANCHOR
MENU_ANCHOR = "        if (max.X <= min.X || max.Y <= min.Y) return;\n"
MENU_REPLACEMENT = (
    "        var activeGl = HostWindow.CM64ActiveGL;\n"
    "        if (activeGl != null)\n"
    "        {\n"
    "            try { OriginalMarioAtlas.RenderTick(activeGl); }\n"
    "            catch (Exception e)\n"
    "            {\n"
    "                OriginalMarioAtlas.ReleaseAtlas();\n"
    "                Console.Error.WriteLine(\"[cm64-atlas] upload disabled: \" + e.GetType().Name);\n"
    "            }\n"
    "        }\n"
    + MENU_ANCHOR
)
ATLAS_PATH = "RecompOne.Runtime/Host/Window/OriginalMarioAtlas.cs"

def action(source: Path, target: Path, atlas: Path, verify_only: bool):
    verify_m41b(source, target) if not verify_only else None
    host = target / "RecompOne.Runtime/Host/Window/HostWindow.cs"
    menu = target / "RecompOne.Runtime/Host/Window/MenuRegistry.cs"
    original_host = (source/"RecompOne.Runtime/Host/Window/HostWindow.cs").read_text(
        encoding="utf-8-sig").replace("\r\n","\n")
    orig_menu = menu.read_text(encoding="utf-8-sig").replace("\r\n","\n")
    replacement_source = atlas.read_text(encoding="utf-8")
    if not replacement_source.strip().endswith("}"):
        raise ValueError("Atlas resource owner source incomplete")
    if original_host.count(GL_ANCHOR)!=1 or original_host.count(SHUTDOWN_ANCHOR)!=1:
        raise ValueError("Unknown pinned Crash host lifecycle anchors")
    expected_host = original_host.replace(GL_ANCHOR, GL_REPLACEMENT).replace(
        SHUTDOWN_ANCHOR, SHUTDOWN_REPLACEMENT)
    if verify_only:
        if host.read_text(encoding="utf-8-sig").replace("\r\n","\n")!=expected_host:
            raise ValueError("Private Crash GL host drift")
        if orig_menu.count(MENU_REPLACEMENT)!=1:
            raise ValueError("Private Crash overlay dispatcher drift")
        if (target/ATLAS_PATH).read_text(encoding="utf-8")!=replacement_source:
            raise ValueError("Private original Mario atlas resource drift")
        print("M41B2_PRIVATE_SOURCE_VERIFIED")
        return
    if host.read_text(encoding="utf-8-sig").replace("\r\n","\n")!=original_host:
        raise ValueError("Original public runtime HostWindow was edited")
    if orig_menu.count(MENU_ANCHOR)!=1 or "OriginalMarioAtlas.RenderTick" in orig_menu:
        raise ValueError("Output overlay dispatch anchor changed")
    target_atlas=target/ATLAS_PATH
    if target_atlas.exists():
        raise ValueError("Existing private generated atlas source; refuse overwrite")
    host.write_text(expected_host,encoding="utf-8",newline="")
    menu.write_text(orig_menu.replace(MENU_ANCHOR,MENU_REPLACEMENT),
                    encoding="utf-8",newline="")
    target_atlas.write_text(replacement_source,encoding="utf-8",newline="")
    print("M41B2_PRIVATE_HOST_PATCHED atlas_owner=true")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--private-clone",type=Path,required=True)
    p.add_argument("--atlas",type=Path,default=Path("integration/embedded_mario/OriginalMarioAtlasHost.cs"))
    p.add_argument("--verify-only",action="store_true")
    a=p.parse_args()
    action(a.source,a.private_clone,a.atlas,a.verify_only)

if __name__=="__main__":main()
