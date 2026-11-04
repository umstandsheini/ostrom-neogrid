"""Dump the string table of a Hermes bytecode bundle (read-only, local)."""
import struct
import sys

path, out = sys.argv[1], sys.argv[2]
d = open(path, "rb").read()
magic, version = struct.unpack_from("<QI", d, 0)
assert magic == 0x1F1903C103BC1FC6, hex(magic)
# header: magic8 version4 hash20 fileLen4 globalCode4 funcCount4 stringKindCount4
#         identCount4 stringCount4 overflowCount4 stringStorageSize4
func_count, kind_cnt, ident_cnt, str_cnt, ovf_cnt, storage = struct.unpack_from("<6I", d, 40)
print("version", version, "funcs", func_count, "strings", str_cnt, "overflow", ovf_cnt, "storage", storage)

# header is 128 bytes (v>=94), tables are 4-byte aligned after it
pos = 128
pos += func_count * 16
pos = (pos + 3) & ~3
pos += kind_cnt * 4
pos += ident_cnt * 4
pos = (pos + 3) & ~3
small = pos
pos += str_cnt * 4
ovf = pos
pos += ovf_cnt * 8
pos = (pos + 3) & ~3
base = pos

strings = []
for i in range(str_cnt):
    (e,) = struct.unpack_from("<I", d, small + i * 4)
    utf16, off, ln = e & 1, (e >> 1) & 0x7FFFFF, e >> 24
    if ln == 0xFF:
        off, ln = struct.unpack_from("<II", d, ovf + off * 8)
    raw = d[base + off: base + off + (ln * 2 if utf16 else ln)]
    strings.append(raw.decode("utf-16le" if utf16 else "latin1", "replace"))

with open(out, "w", encoding="utf-8") as f:
    for i, s in enumerate(strings):
        f.write(f"{i}\t{s!r}\n")
print("wrote", len(strings))
