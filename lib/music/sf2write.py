"""A minimal SoundFont (SF2) writer: presets of key-ranged, looped stereo or mono
recordings - for building an instrument from recordings (orchestra.fetch_choir) - and a
minimal SFZ reader, for the libraries that describe their recordings in one."""
import re
import struct
import numpy as np

_NOTE = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}


def sfz_key(v) -> int:
    """An SFZ key: a MIDI number or a name ("c#4", "eb3"; C4 = 60)."""
    v = str(v).strip().lower()
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    m = re.fullmatch(r"([a-g])(#|b)?(-?\d+)", v)
    if not m:
        raise ValueError(f"not an SFZ key: {v!r}")
    return 12 * (int(m.group(3)) + 1) + _NOTE[m.group(1)] + {"#": 1, "b": -1, None: 0}[m.group(2)]


def parse_sfz(text: str):
    """An SFZ file's regions, each a dict of its opcodes with what it inherits from its
    <global>, <master> and <group> merged in, and "_default_path" (the <control>'s). Only
    the text is read - nothing it names is opened (the caller resolves the samples)."""
    text = re.sub(r"//[^\n]*", "", text)
    text = "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))
    out, scopes = [], {"control": {}, "global": {}, "master": {}, "group": {}}
    cur, region = None, None
    for tok in re.split(r"(<\w+>)", text):
        tok = tok.strip()
        if not tok:
            continue
        m = re.fullmatch(r"<(\w+)>", tok)
        if m:
            if region is not None:
                out.append(region)
                region = None
            cur = m.group(1)
            if cur == "global":
                scopes["global"], scopes["master"], scopes["group"] = {}, {}, {}
            elif cur == "master":
                scopes["master"], scopes["group"] = {}, {}
            elif cur == "group":
                scopes["group"] = {}
            elif cur == "region":
                region = {**scopes["global"], **scopes["master"], **scopes["group"]}
                region["_default_path"] = scopes["control"].get("default_path", "")
            continue
        ops = {om.group(1): om.group(2).strip()
               for om in re.finditer(r"(\w+)=(.*?)(?=\s+\w+=|$)", tok, re.S)}
        if cur == "region" and region is not None:
            region.update(ops)
        elif cur in scopes:
            scopes[cur].update(ops)
    if region is not None:
        out.append(region)
    return [r for r in out if r.get("sample")]


def _chunk(tag, body):
    return tag + struct.pack("<I", len(body)) + body + (b"\0" if len(body) % 2 else b"")


def _name(s):
    return s.encode()[:19].ljust(20, b"\0")


def crossfade_loop(x, rate, start_s, fade_s=0.5, tail_s=0.15):
    """Bake a long crossfaded loop into int16 audio x (n, ch): returns (audio, ls, le)."""
    x = x.astype("float64")
    le = len(x) - int(tail_s * rate)
    ls = int(start_s * rate)
    f = int(fade_s * rate)
    f = min(f, ls, le - ls - 1)
    ramp = np.linspace(0, 1, f)[:, None]
    # the last f frames before le blend into the f frames before ls: le wraps to ls seamlessly
    x[le - f:le] = x[le - f:le] * (1 - ramp) + x[ls - f:ls] * ramp
    return np.clip(x, -32768, 32767).astype("int16"), ls, le


def to_int16(audio):
    """Any recording (float or integer, as read) as 16-bit samples, scaled - never truncated
    (a float file read straight as int16 comes out as 0 and +-1: silence that a loudness
    match then blows up into harsh noise)."""
    a = np.asarray(audio)
    if a.dtype.kind == "f":
        a = np.clip(a, -1.0, 1.0) * 32767
    return a.astype("int16")


def write(path, presets, title):
    """presets: [(name, [zone, ...])], zone = dict(audio=int16 (n, ch), rate, key, lo, hi,
    ls, le, tune=0, att_cb=0, release_s=0.6) - and, for struck sounds, vlo/vhi (the velocities
    it plays at: a velocity layer), loop=False (played once, to its end) and excl (an
    exclusive class: a new note in it stops the one ringing - a drum head struck again)."""
    import math
    data, shdr = [], []
    pos = 0
    inst, ibag, igen = [], [], []
    stored = {}                                 # a recording used by several presets: stored once
    for pname, zones in presets:
        inst.append((pname, len(ibag)))
        for z in zones:
            a = z["audio"]
            if a.dtype != np.int16:
                raise ValueError("recordings must be 16-bit samples: use to_int16")
            if np.abs(a).max() < 64:
                raise ValueError(f"recording {z['key']} is near-silent: read with the wrong format?")
            chans = a.shape[1]
            ids = stored.get(id(a), [])
            for c in range(chans if not ids else 0):
                start = pos
                data += [a[:, c], np.zeros(46, "int16")]
                ids.append(len(shdr))
                kind = 1 if chans == 1 else (4 if c == 0 else 2)
                shdr.append([f"{pname[:10]}{z['key']}{'LR'[c] if chans > 1 else ''}", start, start + len(a),
                             start + z["ls"], start + z["le"], z["rate"], z["key"], 0, 0, kind])
                pos = start + len(a) + 46
            if chans == 2 and id(a) not in stored:
                shdr[ids[0]][8], shdr[ids[1]][8] = ids[1], ids[0]
            stored[id(a)] = ids
            pans = [0] if chans == 1 else [-500, 500]
            for sid, pan in zip(ids, pans):
                ibag.append((len(igen), 0))
                igen.append((43, z["lo"] | (z["hi"] << 8)))         # (keyRange first, velRange next)
                if "vlo" in z:
                    igen.append((44, z["vlo"] | (z["vhi"] << 8)))
                igen += [(17, pan), (48, int(z.get("att_cb", 0))),
                         (52, int(z.get("tune", 0))), (38, int(1200 * math.log2(z.get("release_s", 0.6)))),
                         (54, 1 if z.get("loop", True) else 0), (58, z["key"])]
                if z.get("excl"):
                    igen.append((57, int(z["excl"])))
                igen.append((53, sid))
    phdr, pbag, pgen = [], [], []
    for i, (pname, _) in enumerate(presets):
        phdr.append((pname, i, 0, len(pbag)))
        pbag.append((len(pgen), 0))
        pgen.append((41, i))
    smpl = np.concatenate(data).tobytes()
    U = (41, 43, 44, 53, 54, 57, 58)
    info = _chunk(b"ifil", struct.pack("<HH", 2, 1)) + _chunk(b"isng", b"EMU8000\0") + _chunk(b"INAM", title.encode() + b"\0")
    pd = _chunk(b"phdr", b"".join(_name(n) + struct.pack("<HHHIII", p, b, bag, 0, 0, 0) for n, p, b, bag in phdr)
                + _name("EOP") + struct.pack("<HHHIII", 0, 0, len(pbag), 0, 0, 0))
    pd += _chunk(b"pbag", b"".join(struct.pack("<HH", g, m) for g, m in pbag) + struct.pack("<HH", len(pgen), 0))
    pd += _chunk(b"pmod", b"\0" * 10)
    pd += _chunk(b"pgen", b"".join(struct.pack("<HH", o, a) for o, a in pgen) + b"\0" * 4)
    pd += _chunk(b"inst", b"".join(_name(n) + struct.pack("<H", bag) for n, bag in inst) + _name("EOI") + struct.pack("<H", len(ibag)))
    pd += _chunk(b"ibag", b"".join(struct.pack("<HH", g, m) for g, m in ibag) + struct.pack("<HH", len(igen), 0))
    pd += _chunk(b"imod", b"\0" * 10)
    pd += _chunk(b"igen", b"".join(struct.pack("<HH" if o in U else "<Hh", o, a) for o, a in igen) + b"\0" * 4)
    pd += _chunk(b"shdr", b"".join(_name(s[0]) + struct.pack("<IIIIIBbHH", *s[1:]) for s in shdr) + _name("EOS") + b"\0" * 26)
    body = b"sfbk" + _chunk(b"LIST", b"INFO" + info) + _chunk(b"LIST", b"sdta" + _chunk(b"smpl", smpl)) + _chunk(b"LIST", b"pdta" + pd)
    open(path, "wb").write(b"RIFF" + struct.pack("<I", len(body)) + body)


def read_samples(path):
    """[(name, int16 mono array, rate, key, loopstart, loopend)] from an SF2."""
    f = open(path, "rb").read()
    def chunk(tag):
        i = f.find(tag); n = struct.unpack("<I", f[i + 4:i + 8])[0]; return f[i + 8:i + 8 + n]
    smpl = np.frombuffer(chunk(b"smpl"), dtype="<i2")
    sh = chunk(b"shdr")
    out = []
    for k in range(len(sh) // 46 - 1):
        r = sh[k * 46:(k + 1) * 46]
        name = r[:20].split(b"\0")[0].decode(errors="ignore")
        s, e, ls, le, rate, key = struct.unpack("<IIIIIB", r[20:41])
        out.append((name, smpl[s:e].copy(), rate, key, ls - s, le - s))
    return out
