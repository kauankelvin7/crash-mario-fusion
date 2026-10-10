"""Finite passive localhost CMW1 collector, one receiver clock for both engines.

Never launches games, sends input, extrapolates poses or claims physical sync.
Native emitters are started separately by the local operator with explicit sessions.
"""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import socket
import time
import uuid

from integration.observation_alignment import Binding,ObservationAlignment,Reason,descriptor
from integration.world_snapshot import CRASH,MARIO,decode

MAX_ATTEMPTS=10000
MAX_CONFIG_BYTES=4096


def read_config(path):
    with Path(path).open('rb') as stream: data=stream.read(MAX_CONFIG_BYTES+1)
    if len(data)>MAX_CONFIG_BYTES: raise ValueError('Receiver config exceeds 4 KiB')
    document=json.loads(data.decode('utf-8-sig'))
    if type(document) is not dict or type(document.get('schema_version')) is not int or document['schema_version']!=1:
        raise ValueError('Receiver config requires schema_version=1')
    sources=document['sources']
    if type(sources) is not dict or set(sources)!={'crash','mario'}: raise ValueError('Bind both independent sources')
    bindings={e:Binding(bytes.fromhex(sources[name]['session']),bytes.fromhex(sources[name]['frame']))
              for e,name in ((CRASH,'crash'),(MARIO,'mario'))}
    return bindings,document['max_age_ns'],document['max_gap_ns']


class PairedObserver:
    """Fixed counters and two CMW1 slots; receipt freshness is not source freshness."""
    def __init__(self,bindings,*,clock_id,max_age_ns,max_gap_ns):
        self.alignment=ObservationAlignment(bindings,receiver_clock_id=clock_id,
            max_age_ns=max_age_ns,max_gap_ns=max_gap_ns)
        self.rejections={r.value:0 for r in Reason if r!=Reason.ACCEPTED}
        self.sources={e:dict(accepted=0,sequence_holes=0,last_sequence=0,
            last_arrival_ns=None,maximum_arrival_gap_ns=0) for e in (CRASH,MARIO)}
        self.attempts=0

    def accept(self,packet,now_ns,*,peer='127.0.0.1'):
        if self.attempts>=MAX_ATTEMPTS: raise ValueError('Finite receiver attempt budget exhausted')
        self.attempts+=1
        observed=None
        try:
            value=decode(packet)
            identity=descriptor(value.engine,value.frame)
            observed=dict(engine=value.engine,sequence=value.sequence,native_tick=value.native_tick,
                phase=value.phase,paused=value.paused,identity=asdict(identity),
                session=value.session.hex(),frame=value.frame.hex(),
                tick_kind='observer_pad_callback' if value.engine==CRASH else 'engine_local_update',
                native_frame_generation='UNKNOWN')
        except (ValueError,TypeError): value=None
        if peer!='127.0.0.1':
            accepted,reason=False,Reason.MALFORMED # no packet-selected remote endpoint
        else:
            admission=self.alignment.accept(packet,now_ns,receiver_clock_id=self.alignment.clock_id)
            accepted,reason=admission.accepted,admission.reason
        if reason!=Reason.ACCEPTED: self.rejections[reason.value]+=1
        holes=gap=None
        since_last_accepted=None
        if value is not None and value.session==self.alignment.bindings[value.engine].session:
            last=self.sources[value.engine]['last_arrival_ns']
            if last is not None and type(now_ns) is int and now_ns>=last:
                since_last_accepted=now_ns-last
        if accepted:
            stats=self.sources[value.engine]
            holes=value.sequence-stats['last_sequence']-1
            gap=None if stats['last_arrival_ns'] is None else now_ns-stats['last_arrival_ns']
            stats['accepted']+=1
            stats['sequence_holes']+=holes
            stats['last_sequence']=value.sequence
            stats['last_arrival_ns']=now_ns
            stats['maximum_arrival_gap_ns']=max(stats['maximum_arrival_gap_ns'],gap or 0)
        row=dict(kind='arrival',receiver_clock_id=self.alignment.clock_id,receiver_monotonic_ns=now_ns,
            accepted=accepted,reason=reason.value,observed=observed,sequence_holes=holes,
            receiver_arrival_gap_ns=gap,since_last_accepted_ns=since_last_accepted,source_delay='UNKNOWN',physical_status='BLOCKED',calibration_ready=False)
        # Raw pose stays private and is only exposed for an admitted packet.
        if accepted:
            pose=asdict(value)
            pose.update(session=value.session.hex(),frame=value.frame.hex(),
                tick_kind='observer_pad_callback' if value.engine==CRASH else 'engine_local_update',
                native_frame_generation='UNKNOWN')
            row['snapshot']=pose
        return row

    def status(self,now_ns):
        result=self.alignment.evaluate(now_ns,receiver_clock_id=self.alignment.clock_id)
        return dict(kind='status',receiver_clock_id=self.alignment.clock_id,receiver_monotonic_ns=now_ns,
            telemetry_comparable=result.telemetry_comparable,physical_status=result.physical_status,
            calibration_ready=result.calibration_ready,gate=result.gate,
            receiver_arrival_separation_ns=result.receiver_arrival_separation_ns,
            source_delay='UNKNOWN',sources=[dict(engine=v.engine,reason=v.reason.value,
                identity=asdict(v.identity),age_ns=v.age_ns) for v in result.sources])

    def rebind(self,engine,binding):
        """API only: explicit reviewed transition, never automatic UDP-selected matching."""
        old=self.alignment.bindings[engine]
        self.alignment.rebind(engine,binding)
        stats=self.sources[engine]
        stats['last_arrival_ns']=None
        if binding.session!=old.session: stats['last_sequence']=0

    def summary(self):
        return dict(attempts=self.attempts,sources={str(e):dict(s) for e,s in self.sources.items()},
            rejection_counts=dict(self.rejections),physical_status='BLOCKED',calibration_ready=False,
            sequence_holes_meaning='Unaccepted emitted sequences; loss and rejection not distinguishable',
            source_delay='UNKNOWN',live_gameplay_verified=False)


def receive(receiver,observer,output,*,seconds,max_packets,clock=time.monotonic_ns):
    """Single-thread receipt timestamp immediately after recvfrom, before parsing/logging."""
    if type(seconds) is not int or not 1<=seconds<=300 or type(max_packets) is not int or not 1<=max_packets<=MAX_ATTEMPTS:
        raise ValueError('Bound receiver to 1..300 seconds / 1..10000 datagrams')
    if receiver.getsockname()[0]!='127.0.0.1': raise ValueError('Bind only IPv4 loopback')
    receiver.settimeout(.05)
    start=clock()
    deadline=start+seconds*1_000_000_000
    next_status=start
    def write(row): output.write(json.dumps(row,allow_nan=False)+'\n')
    write(observer.status(start))
    while observer.attempts<max_packets:
        now=clock()
        if now>=deadline: break
        try:
            packet,peer=receiver.recvfrom(256)
        except socket.timeout:
            packet=None
        except OSError as exc:
            if getattr(exc,'winerror',None)!=10040: raise
            packet,peer=b'',('127.0.0.1',0) # oversized Windows UDP packet rejection
        now=clock()
        if now>=deadline: break # no late processing beyond the finite observation window
        if packet is not None: write(observer.accept(packet,now,peer=peer[0]))
        if now>=next_status:
            write(observer.status(now))
            next_status=now+100_000_000 # bounded 10 Hz status log; no pose history in memory
    write(observer.status(clock()))
    return observer.summary()


def private_folder():
    if os.name!='nt': raise ValueError('Operator capture requires native Windows; tests use loopback API only')
    root=(Path(os.environ['LOCALAPPDATA'])/'CrashMarioFusion/telemetry').resolve()
    repo=Path(__file__).resolve().parents[1]
    if root==repo or repo in root.parents: raise ValueError('Keep private capture outside Git')
    folder=root/('paired-'+uuid.uuid4().hex)
    folder.mkdir(parents=True,exist_ok=False)
    return folder


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True,type=Path)
    parser.add_argument('--port',required=True,type=int)
    parser.add_argument('--seconds',default=60,type=int)
    parser.add_argument('--max-packets',default=6000,type=int)
    parser.add_argument('--allow-native-epoch-rebind',action='store_true',
                        help='Explicit local operator-only whitelist for observed native epochs')
    args=parser.parse_args()
    try:
        if not 1024<=args.port<=65535: raise ValueError('Explicit localhost port 1024..65535 required')
        if not 1<=args.seconds<=300 or not 1<=args.max_packets<=MAX_ATTEMPTS: raise ValueError('Capture budget exceeded')
        bindings,age,gap=read_config(args.config)
        if args.allow_native_epoch_rebind:
            from tools.native_epoch_observer import NativeEpochObserver
            # Explicitly approved locations from the independent original-game gates.
            # Never allow UDP to choose arbitrary scene identities or mark calibration valid.
            observer=NativeEpochObserver(bindings,{CRASH:{9},MARIO:{(6,1),(16,1)}},
                clock_id='receiver-'+uuid.uuid4().hex,max_age_ns=age,max_gap_ns=gap)
        else:
            observer=PairedObserver(bindings,clock_id='receiver-'+uuid.uuid4().hex,max_age_ns=age,max_gap_ns=gap)
        folder=private_folder()
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as receiver, (folder/'observations.jsonl').open('x',encoding='utf-8') as output:
            receiver.bind(('127.0.0.1',args.port))
            print(f'READY loopback port={args.port}; private capture={folder}; start emitters separately; Ctrl+C stops receiver.',flush=True)
            try: summary=receive(receiver,observer,output,seconds=args.seconds,max_packets=args.max_packets)
            except KeyboardInterrupt: summary=observer.summary()
        (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        print('Capture complete; physical synchronization BLOCKED; source delay UNKNOWN.',flush=True)
    except (ValueError,TypeError,KeyError,OSError) as exc:
        parser.exit(1,f'Paired observation rejected: {exc}\n')

if __name__=='__main__': main()
