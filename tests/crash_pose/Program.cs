using System.Buffers.Binary;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using RecompOne.Runtime;
using RecompOne.Runtime.Catalogs;
using RecompOne.Runtime.Events;
using RecompOne.Runtime.Memory;
using RecompOne.Runtime.Modding;

AppPaths.SetRoot(Path.Combine(Path.GetTempPath(), "cm64-crash-pose-" + Guid.NewGuid().ToString("N")));
var sources = Directory.GetFiles(Path.Combine(args[0], "integration/crash_pose"), "*.cs")
    .Select(p => (p, File.ReadAllText(p))).ToList();
var assembly = Assembly.Load(ModCompiler.Compile("cm64-crash-pose", sources) ?? throw new Exception("Compile failed"));
var type = assembly.GetType("CrashPoseMod")!;
IMod New() => (IMod)Activator.CreateInstance(type)!;
var mod = New();
var memory = new PSMemory();
using var receiver = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
receiver.Bind(new IPEndPoint(IPAddress.Loopback, 0)); receiver.Blocking = false;
const uint player = 0x80070000;
memory.WriteU32(Catalog.LevelIdAddr, 9);
memory.WriteU32(0x800566B4, player); memory.WriteU32(player, 1);
int[] fields = {-257, int.MinValue, 513, -1, 1024, int.MaxValue};
for (int i = 0; i < fields.Length; ++i) memory.WriteU32(player + 0x80u + (uint)i*4, unchecked((uint)fields[i]));
memory.WriteU32(player+0x2C, 2); memory.WriteU32(player+0x120, 8);
int checks = 0;
void Check(bool ok, string name) { if (!ok) throw new Exception("FAIL: " + name); ++checks; Console.WriteLine("PASS: " + name); }
void Set(string name, object value) => type.GetField(name, BindingFlags.Instance|BindingFlags.NonPublic)!.SetValue(mod, value);
T Get<T>(string name) => (T)type.GetField(name, BindingFlags.Instance|BindingFlags.NonPublic)!.GetValue(mod)!;
void Pad(int port = 0, ushort buttons = 0xffff) {
    var e = new PadReadEvent { Port=port, Buttons=buttons, Memory=memory };
    Event.Dispatch(e); Check(e.Buttons == buttons, "input remains byte-identical");
}
byte[]? Receive() {
    byte[] bytes = new byte[256];
    try { int n = receiver.Receive(bytes); return bytes[..n]; }
    catch(SocketException e) when(e.SocketErrorCode == SocketError.WouldBlock) { return null; }
}
uint U(byte[] p, int o) => BinaryPrimitives.ReadUInt32BigEndian(p.AsSpan(o));
byte[] Emit() { Set("nextSend", 0L); Pad(); return Receive() ?? throw new Exception("No fixture packet"); }
Environment.SetEnvironmentVariable("CM64_CRASH_POSE_ENABLE", null);
mod.OnLoad(); Pad(); Check(Receive() == null, "disabled by default"); mod.OnUnload();
Environment.SetEnvironmentVariable("CM64_CRASH_POSE_ENABLE", "1");
Environment.SetEnvironmentVariable("CM64_CRASH_POSE_PORT", ((IPEndPoint)receiver.LocalEndPoint!).Port.ToString());
Environment.SetEnvironmentVariable("CM64_CRASH_POSE_SESSION", new string('0', 32));
try { New().OnLoad(); throw new Exception("Zero session accepted"); }
catch(InvalidOperationException) { Check(true, "zero session rejected"); }
Environment.SetEnvironmentVariable("CM64_CRASH_POSE_SESSION", "00112233445566778899aabbccddeeff");
var error = new StringWriter(); var oldError = Console.Error; Console.SetError(error);
try {
    mod.OnLoad();
    var before = memory.Ram.ToArray();
    // IMemory reads decrement this counter and can inject VBlank; span observation must not.
    var accesses = typeof(PSMemory).GetField("_memYield", BindingFlags.Instance|BindingFlags.NonPublic)!;
    accesses.SetValue(memory, 12345);
    var first = Emit();
    Check(first.Length == 80 && first[4] == 1 && first[5] == 0 && first[6] == 0 && first[7] == 0,
        "CMW1 Crash UNKNOWN phase, exact length and flags");
    Check(Convert.ToHexString(first.AsSpan(8,16)) == "00112233445566778899AABBCCDDEEFF", "session preserved");
    Check(System.Text.Encoding.ASCII.GetString(first,24,4) == "M32D" && U(first,28)==9 && U(first,32)==1 && U(first,36)==0,
        "source level and observer epoch descriptor");
    Check(U(first,40)==1 && U(first,44)==1, "observer sequence and callback ordinal");
    Check(Enumerable.Range(0,6).All(i => unchecked((int)U(first,48+i*4)) == fields[i]) && U(first,72)==2 && U(first,76)==8,
        "signed xyz, genuine raw rotation and opaque state serialized");
    Check(before.AsSpan().SequenceEqual(memory.Ram) && (int)accesses.GetValue(memory)! == 12345,
        "entire RAM unchanged and no memory-access/VBlank side effects");
    Set("nextSend", Environment.TickCount64+1000); Pad(); Check(Receive()==null, "rate limiter drops immediate sample");
    Set("nextSend", 0L); Pad(1); Check(Receive()==null, "port one ignored");
    uint epoch = U(first,32);
    foreach(uint address in new uint[]{0x80056400,0x8005640C}) {
        memory.WriteU32(address,1); Set("nextSend",0L); Pad(); Check(Receive()==null, "native pause suppresses pose");
        memory.WriteU32(address,0); var resumed=Emit(); Check(U(resumed,32)>epoch, "pause invalidates observer epoch"); epoch=U(resumed,32);
    }
    Pad(buttons: 0xfff7); Check(Receive()==null, "Start request suppressed");
    var startResume=Emit(); Check(U(startResume,32)>epoch, "Start invalidates epoch"); epoch=U(startResume,32);
    memory.WriteU32(Catalog.LevelIdAddr,25); Set("nextSend",0L); Pad(); Check(Receive()==null, "catalog menu suppressed");
    memory.WriteU32(Catalog.LevelIdAddr,9); Check(U(Emit(),32)>epoch, "menu invalidates epoch");
    foreach(uint bad in new uint[]{0,0x80070001,0x801FFEE0,0x80270000,0xA0070000}) {
        memory.WriteU32(0x800566B4,bad); Set("nextSend",0L); Pad(); Check(Receive()==null,"invalid/mirrored/unaligned pointer rejected");
    }
    memory.WriteU32(0x800566B4,player);
    foreach(uint inactive in new uint[]{0,2}) {
        memory.WriteU32(player,inactive); Set("nextSend",0L); Pad(); Check(Receive()==null,"inactive native object rejected");
    }
    memory.WriteU32(player,1); epoch=U(Emit(),32);
    memory.WriteU32(player+0x20,0x80071000); Check(U(Emit(),32)>epoch,"observed lifecycle signature invalidates epoch");
    epoch=Get<uint>("epoch"); Set("lastCallback",Environment.TickCount64-251); Check(U(Emit(),32)>epoch,"callback gap invalidates epoch");
    Set("attempts",3000); Pad(); Check(Receive()==null && Get<Socket?>("socket")==null,"3000 attempts stops observer");
    mod.OnLoad(); Set("started",Environment.TickCount64-300000); Pad(); Check(Receive()==null && Get<Socket?>("socket")==null,"300 seconds stops observer");
    mod.OnLoad(); Set("tick",uint.MaxValue); Pad(); Check(Receive()==null && Get<Socket?>("socket")==null,"no callback counter wrap");
    mod.OnLoad(); mod.OnUnload(); Pad(); Check(Receive()==null,"unload removes observer");
} finally { mod.OnUnload(); Console.SetError(oldError); }
Check(!error.ToString().Contains("[Event]"), "event bus swallowed no observer errors");
Console.WriteLine($"{checks} Crash observer fixture assertions PASS; VERIFIED_SYNTHETIC only");
