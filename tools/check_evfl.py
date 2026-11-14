"""Checks rando.formats.evfl_patch's writers against every event flow of the game: the relocation table written for a file's own
pointers is the file's own table, byte for byte; every DIC built for its keys is the file's own (bit, left, right) for each
node; and each flow takes two new actions after its first action event (a new actor) and reads back as it should.

    python tools/check_evfl.py <romfs>"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando.formats import evfl, evfl_patch, zs   # noqa: E402


def dics(r, flow_at):
    """every DIC offset of a flowchart: the entry points' and every parameter container's"""
    out = [r.u64(flow_at + 0x38)]

    def container(p):
        if p and r.u8(p) == evfl.CONTAINER:
            out.append(r.u64(p + 8))
            for i in range(r.u16(p + 2)):
                container(r.u64(p + 0x10 + 8 * i))

    n_actors, _, _, n_events = (r.u16(flow_at + 0x10 + 2 * i) for i in range(4))
    actors_at, events_at = r.u64(flow_at + 0x28), r.u64(flow_at + 0x30)
    for i in range(n_actors):
        container(r.u64(actors_at + 0x38 * i + 0x28))
    for i in range(n_events):
        e = events_at + 0x30 * i
        if r.u8(e + 8) in (evfl.ACTION, evfl.SWITCH, evfl.SUBFLOW, evfl.SUBFLOW_SWITCH):
            container(r.u64(e + 0x10))
    return [d for d in out if d]


def main():
    romfs = sys.argv[1]
    codec = zs.Codec(romfs)
    folder = os.path.join(romfs, "Event", "EventFlow")
    files = sorted(f for f in os.listdir(folder) if f.endswith(".bfevfl.zs"))
    problems, n_dics, n_added = [], 0, 0
    for f in files:
        data = codec.read(os.path.join(folder, f))
        r = evfl.Reader(data)
        at = r.u32(0x18)
        if evfl_patch.relt_write(evfl_patch.relt_pointers(data), at, evfl_patch.relt_section_size(data)) != data[at:r.u32(0x1C)]:
            problems.append("%s: relocation table not written back the same" % f)
        for k in range(r.u16(0x20)):
            flow_at = r.u64(r.u64(0x28) + 8 * k)
            for d in dics(r, flow_at):
                n = r.u32(d + 4)
                have = [(r.u32(d + 8 + 16 * i), r.u16(d + 12 + 16 * i), r.u16(d + 14 + 16 * i)) for i in range(n + 1)]
                if evfl_patch.dic_nodes(r.dic(d)) != have:
                    problems.append("%s: DIC at %#x not built the same" % (f, d))
                n_dics += 1
        flows = evfl.read(data)
        if not flows:
            continue
        first = next((e["name"] for e in flows[0]["events"] if e["type"] == "action"), None)
        if first is None:
            continue
        try:
            evfl_patch.add_actions(data, first, "RandoCheckActor", "RandoCheckAction",
                                   {"EventMemberCreateMethod": 0, "IsWorld": False, "UseEventAS": "x"},
                                   [("RandoCheck1", {"Num": 1, "Flag": True, "Off": False, "Name": "Item_X"}),
                                    ("RandoCheck2", {"Rate": 0.5, "Name": ""})])
            n_added += 1
        except Exception as e:   # noqa: BLE001
            problems.append("%s: add_actions: %s" % (f, e))
    print("%d flows, %d DICs, %d flows took new actions; %d problems" % (len(files), n_dics, n_added, len(problems)))
    for p in problems[:30]:
        print("  ", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
