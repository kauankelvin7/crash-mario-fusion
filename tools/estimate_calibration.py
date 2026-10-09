"""Offline, explicit-landmark fit. This tool never calibrates a running game."""
import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import struct

from tools.world_coordinates import (FrameMap,decode_crash,encode_crash,vector,
                                     sm64_floor_query_safe)

SYNTHETIC='SYNTHETIC'
OPERATOR='OPERATOR_SUPPLIED_NOT_RUNTIME_VERIFIED'
MAX_PAIRS=128
MAX_INPUT_BYTES=131072


@dataclass(frozen=True)
class LandmarkPair:
    label: str
    crash_raw: tuple
    mario_position: tuple
    crash_level: int
    crash_epoch: int
    mario_level: int
    mario_area: int
    mario_epoch: int
    provenance: str
    correspondence_declared: bool

    def __post_init__(self):
        if not isinstance(self.label,str) or not self.label.strip() or len(self.label)>128:
            raise ValueError('Each explicit pair requires a bounded label')
        object.__setattr__(self,'crash_raw',tuple(self.crash_raw))
        object.__setattr__(self,'mario_position',vector(self.mario_position))
        decode_crash(self.crash_raw)
        limits=((self.crash_level,0,65535),(self.crash_epoch,1,2**32-1),
                (self.mario_level,1,32767),(self.mario_area,1,32767),(self.mario_epoch,1,2**32-1))
        if any(type(n) is not int or not lo<=n<=hi for n,lo,hi in limits):
            raise ValueError('Explicit valid native level/area and observer epochs required')
        if self.provenance not in (SYNTHETIC,OPERATOR) or self.correspondence_declared is not True:
            raise ValueError('Pair correspondence and provenance must be explicitly declared')

    @property
    def scope(self):
        return (self.crash_level,self.crash_epoch,self.mario_level,self.mario_area,
                self.mario_epoch,self.provenance)


@dataclass(frozen=True)
class FitPolicy:
    # All bounds are mandatory; none is a guessed real-world tolerance.
    max_error: float
    rms_error: float
    min_crash_xz_baseline: float
    min_mario_xz_baseline: float
    min_condition_ratio: float
    max_target_quantization_error: float
    require_holdout: bool

    def __post_init__(self):
        for name in ('max_error','rms_error','min_crash_xz_baseline',
                     'min_mario_xz_baseline','min_condition_ratio','max_target_quantization_error'):
            v=getattr(self,name)
            if type(v) not in (int,float) or not math.isfinite(v) or v<=0:
                raise ValueError('All fit thresholds must be explicit, positive and finite')
        if self.min_condition_ratio>1 or type(self.require_holdout) is not bool:
            raise ValueError('Invalid condition threshold or holdout policy')


@dataclass(frozen=True)
class Residuals:
    count: int
    maximum: float
    rms: float


@dataclass(frozen=True)
class Estimate:
    frame_map: FrameMap
    scope: tuple
    policy: FitPolicy
    fit: Residuals
    holdout: Residuals | None
    crash_condition_ratio: float
    mario_condition_ratio: float
    crash_xz_baseline: float
    mario_xz_baseline: float
    maximum_float32_error: float
    maximum_inverse_error: float
    interpretation: str
    calibration_ready: bool = False
    physical_status: str = 'BLOCKED'
    gates: tuple = ('Crash postphysics unverified','Native frame identity unverified',
                    'Correspondence not runtime verified','No shared collision or gameplay validation')


def _center(points):
    origin=tuple(math.fsum(p[i] for p in points)/len(points) for i in range(3))
    return origin,[tuple(p[i]-origin[i] for i in range(3)) for p in points]


def _condition(points,centered,minimum,ratio_min):
    xx=math.fsum(p[0]**2 for p in centered)
    zz=math.fsum(p[2]**2 for p in centered)
    xz=math.fsum(p[0]*p[2] for p in centered)
    largest=(xx+zz+math.hypot(xx-zz,2*xz))/2
    determinant=xx*zz-xz*xz
    ratio=determinant/largest**2 if largest>0 else 0
    baseline=max(math.hypot(a[0]-b[0],a[2]-b[2]) for a in points for b in points)
    if not math.isfinite(ratio) or ratio<ratio_min or baseline<minimum:
        raise ValueError('Insufficient XZ baseline or collinear/ill-conditioned landmarks')
    return ratio,baseline


def _float32(position,policy):
    try: target=vector(struct.unpack('<3f',struct.pack('<3f',*vector(position))))
    except (OverflowError,struct.error) as exc: raise ValueError('Mario float32 overflow') from exc
    error=max(abs(a-b) for a,b in zip(position,target))
    if error>policy.max_target_quantization_error:
        raise ValueError('Mario float32 quantization exceeds explicit threshold')
    if not sm64_floor_query_safe(target):
        raise ValueError('Position outside conservative Mario XZ/s16 query bounds')
    return target,error


def estimate(fit,holdout,policy):
    """Least squares positive uniform scale + Y yaw; Y contributes to scale.

    FrameMap yaw convention: X'=cos(yaw)*X+sin(yaw)*Z,
    Z'=-sin(yaw)*X+cos(yaw)*Z. No trimming, guessed pairs or RANSAC.
    The supplied holdout is independent of fitting, NOT runtime verification.
    """
    if not isinstance(policy,FitPolicy): raise ValueError('Explicit FitPolicy required')
    if not isinstance(fit,(list,tuple)) or not isinstance(holdout,(list,tuple)):
        raise ValueError('Bounded explicit landmark lists required')
    if len(fit)<3 or len(fit)+len(holdout)>MAX_PAIRS or (policy.require_holdout and not holdout):
        raise ValueError('Need >=3 fit pairs, required holdout, and <=128 total pairs')
    pairs=tuple(fit)+tuple(holdout)
    if any(not isinstance(p,LandmarkPair) for p in pairs): raise ValueError('Explicit LandmarkPair required')
    if any(p.scope!=pairs[0].scope for p in pairs): raise ValueError('Mixed frame identity or provenance')
    if len({p.label for p in pairs})!=len(pairs): raise ValueError('Repeated pair identifier')
    if len({p.crash_raw for p in pairs})!=len(pairs) or len({p.mario_position for p in pairs})!=len(pairs):
        raise ValueError('Repeated landmark coordinate (including holdout)')
    sources=[decode_crash(p.crash_raw) for p in pairs]
    targets=[]
    quantization=0
    for p in pairs:
        target,error=_float32(p.mario_position,policy)
        targets.append(target)
        quantization=max(quantization,error)
    if len(set(targets))!=len(targets): raise ValueError('Float32 collapses distinct landmarks')
    count=len(fit)
    co,cs=_center(sources[:count])
    mo,ms=_center(targets[:count])
    cc,cb=_condition(sources[:count],cs,policy.min_crash_xz_baseline,policy.min_condition_ratio)
    mc,mb=_condition(targets[:count],ms,policy.min_mario_xz_baseline,policy.min_condition_ratio)
    a=math.fsum(c[0]*m[0]+c[2]*m[2] for c,m in zip(cs,ms))
    b=math.fsum(c[2]*m[0]-c[0]*m[2] for c,m in zip(cs,ms))
    yy=math.fsum(c[1]*m[1] for c,m in zip(cs,ms))
    denominator=math.fsum(v*v for c in cs for v in c)
    if math.hypot(a,b)<=0: raise ValueError('Yaw is not identifiable')
    scale=(math.hypot(a,b)+yy)/denominator
    mapping=FrameMap(co,mo,scale,math.degrees(math.atan2(b,a)))
    errors=[]
    inverse_error=0
    for source,target in zip(sources,targets):
        predicted=mapping.to_mario(source) # enforces half-raw-unit inverse quantization guard
        _float32(predicted,policy) # native query bounds also apply to predictions
        # Check actual fitted output rounding against the unquantized fit.
        delta=tuple(v-o for v,o in zip(source,co))
        exact=tuple(o+scale*v for o,v in zip(mo,mapping._rotate(delta)))
        qe=max(abs(a-b) for a,b in zip(predicted,exact))
        if qe>policy.max_target_quantization_error: raise ValueError('Fitted float32 error exceeds threshold')
        quantization=max(quantization,qe)
        recovered=mapping.to_crash(predicted)
        encode_crash(recovered)
        encode_crash(mapping.to_crash(target)) # observed inverse must not overflow signed fixed point
        inverse_error=max(inverse_error,max(abs(a-b) for a,b in zip(source,recovered)))
        errors.append(math.dist(predicted,target))
    def summarize(values):
        if not values: return None
        result=Residuals(len(values),max(values),math.sqrt(math.fsum(e*e for e in values)/len(values)))
        if result.maximum>policy.max_error or result.rms>policy.rms_error:
            raise ValueError('Landmark residual/outlier exceeds explicit maximum or RMS threshold')
        return result
    interpretation='SYNTHETIC_MATH_ESTIMATE_ONLY' if pairs[0].provenance==SYNTHETIC else OPERATOR
    result=Estimate(mapping,pairs[0].scope,policy,summarize(errors[:count]),summarize(errors[count:]),
                    cc,mc,cb,mb,quantization,inverse_error,interpretation)
    if not holdout:
        from dataclasses import replace
        result=replace(result,gates=result.gates+('No independent holdout supplied',))
    return result


def estimate_document(document):
    if type(document) is not dict or type(document.get('schema_version')) is not int or document['schema_version']!=1:
        raise ValueError('Explicit schema_version=1 required')
    fit,holdout=document['fit'],document['holdout']
    if not isinstance(fit,list) or not isinstance(holdout,list) or len(fit)+len(holdout)>MAX_PAIRS:
        raise ValueError('Bounded landmark lists required')
    return estimate([LandmarkPair(**p) for p in fit],[LandmarkPair(**p) for p in holdout],FitPolicy(**document['policy']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    args=parser.parse_args()
    try:
        with args.input.open('rb') as stream: data=stream.read(MAX_INPUT_BYTES+1)
        if len(data)>MAX_INPUT_BYTES: raise ValueError('Input exceeds 128 KiB')
        result=estimate_document(json.loads(data.decode('utf-8-sig')))
    except (ValueError,TypeError,KeyError,OverflowError,OSError) as exc:
        parser.exit(1,f'Calibration estimate rejected: {exc}\n')
    print(json.dumps(asdict(result),allow_nan=False,indent=2))

if __name__=='__main__': main()
