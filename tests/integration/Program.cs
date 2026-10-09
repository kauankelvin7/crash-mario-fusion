using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Buffers.Binary;
using RecompOne.Runtime;
using RecompOne.Runtime.Catalogs;
using RecompOne.Runtime.Events;
using RecompOne.Runtime.Hardware;
using RecompOne.Runtime.Memory;
using RecompOne.Runtime.Modding;

if (args.Length != 2) throw new Exception("Usage: IntegrationChecks <repo> <compiled-native-sender>");
AppPaths.SetRoot(Path.Combine(Path.GetTempPath(), "cm64-check-" + Guid.NewGuid().ToString("N")));
string token = "00112233445566778899aabbccddeeff";
using var reservation = new UdpClient(new IPEndPoint(IPAddress.Loopback,0));
int port = ((IPEndPoint)reservation.Client.LocalEndPoint!).Port; reservation.Close();
Environment.SetEnvironmentVariable("CM64_SESSION",token);
Environment.SetEnvironmentVariable("CM64_PORT",port.ToString());
Environment.SetEnvironmentVariable("CM64_APPLY","1");
var sources = Directory.GetFiles(Path.Combine(args[0],"integration/crash"),"*.cs")
    .Select(path=>(path,File.ReadAllText(path))).ToList();
byte[] compiled = ModCompiler.Compile("cm64-coin-jump",sources) ?? throw new Exception("Native mod compiler rejected adapter");
var assembly = Assembly.Load(compiled);
var type = assembly.GetType("CoinJumpMod")!;
var mod = (IMod)Activator.CreateInstance(type)!;
int Applied() => (int)type.GetProperty("AppliedCount")!.GetValue(mod)!;
int Observed() => (int)type.GetProperty("ObservedCount")!.GetValue(mod)!;
var memory = new PSMemory();
memory.WriteU32(Catalog.LevelIdAddr,9); // Fixture RAM, not a running Crash.
ushort allowed = (ushort)(0xffff & ~Controller.R1);
ushort Pad(ushort buttons) { var e=new PadReadEvent { Port=0, Buttons=buttons, Memory=memory }; Event.Dispatch(e); return e.Buttons; }
void Check(bool condition,string name) { if(!condition)throw new Exception("FAIL: "+name); Console.WriteLine("PASS: "+name); }
using var sender = new UdpClient();
void Send(uint sequence, long age=0, bool foreign=false) {
    byte[] p=new byte[52]; "CMJ1"u8.CopyTo(p); Convert.FromHexString(token).CopyTo(p,4);
    if(foreign)p[4]^=1;
    BinaryPrimitives.WriteUInt32BigEndian(p.AsSpan(20),sequence);
    BinaryPrimitives.WriteInt64BigEndian(p.AsSpan(44),DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()-age);
    sender.Send(p,p.Length,new IPEndPoint(IPAddress.Loopback,port));
}
mod.OnLoad();
var errorSink = new StringWriter();
var originalError = Console.Error;
Console.SetError(errorSink);
try {
    // Real UDP/C interoperability into the runtime's actual Roslyn compiler and pad bus.
    var info=new ProcessStartInfo(args[1]) { RedirectStandardInput=true, UseShellExecute=false };
    using var native=Process.Start(info)!;
    native.StandardInput.Write('c'); native.StandardInput.Flush();
    ushort pad=allowed;
    for(int i=0;i<30 && Applied()==0;i++) { Thread.Sleep(3); pad=Pad(allowed); }
    Check(Applied()==1 && (pad & Controller.Cross)==0,"C sender → compiled Crash mod → active-low Cross");
    Send(1); Thread.Sleep(5); Pad(allowed);
    Check(Applied()==1,"duplicate does not retrigger");
    Thread.Sleep(220); Check((Pad(allowed)&Controller.Cross)!=0,"pulse releases to original input");
    Send(2,foreign:true); Thread.Sleep(5); Pad(allowed);
    Check(Observed()==1,"foreign session rejected");
    Send(2,age:5000); Thread.Sleep(5); Pad(allowed);
    Check(Applied()==1,"expired event rejected");
    Send(3); Thread.Sleep(5); Pad(0xffff);
    Check(Applied()==1 && Observed()==2,"unarmed input observes but does not inject");
    Send(4); memory.WriteU32(Catalog.LevelIdAddr,25); Thread.Sleep(5); Pad(allowed);
    Check(Applied()==1,"title/menu cannot inject");
    memory.WriteU32(Catalog.LevelIdAddr,9);
    Send(5); Thread.Sleep(5); Pad((ushort)(allowed&~Controller.Start));
    Check(Applied()==1,"Start/pause request prevents injection");
    Send(6); Thread.Sleep(5); Pad((ushort)(allowed&~Controller.Cross));
    Check(Applied()==1,"physical Cross hold cannot generate another jump edge");
    sender.Send(new byte[1500],1500,new IPEndPoint(IPAddress.Loopback,port));
    Send(7); Thread.Sleep(5); pad=Pad(allowed);
    Check(Applied()==2 && (pad&Controller.Cross)==0,"oversized packet does not interrupt the next eligible event");
    native.StandardInput.Close(); native.WaitForExit(); Check(native.ExitCode==0,"native sender exited successfully");
} finally { mod.OnUnload(); Console.SetError(originalError); }
Check(!errorSink.ToString().Contains("[Event]"),"native event bus swallowed no adapter exceptions");
Check(Pad(allowed)==allowed,"unload removes native pad handler");
Environment.SetEnvironmentVariable("CM64_SESSION",null);
Environment.SetEnvironmentVariable("CM64_PORT",null);
var passive = (IMod)Activator.CreateInstance(type)!;
passive.OnLoad(); Check(Pad(allowed)==allowed,"unpaired native launcher has no injected input"); passive.OnUnload();
Console.WriteLine("VERIFIED_SYNTHETIC: 14 checks; fixture RAM, no original gameplay or shared-world validation.");
