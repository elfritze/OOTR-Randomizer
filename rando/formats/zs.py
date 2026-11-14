"""The game's zstd files (.zs): plain, or compressed with one of the dictionaries in Pack/ZsDic.pack.zs."""
import os
import zstandard

from . import sarc

# (which dictionary a file was compressed with goes by its name, as in the game's own loader)
_DICT_FOR_SUFFIX = ((".bcett.byml.zs", "bcett.byml.zsdic"), (".pack.zs", "pack.zsdic"))
_DEFAULT_DICT = "zs.zsdic"


class Codec:
    def __init__(self, romfs):
        raw = open(os.path.join(romfs, "Pack", "ZsDic.pack.zs"), "rb").read()
        self.dicts = {name: zstandard.ZstdCompressionDict(blob) for name, blob in
                      sarc.read(zstandard.ZstdDecompressor().decompress(raw, max_output_size=1 << 26)).items()}

    def _dict_name(self, name):
        for suffix, d in _DICT_FOR_SUFFIX:
            if name.endswith(suffix):
                return d
        return _DEFAULT_DICT

    def decompress(self, data, name=""):
        # (the frame names its dictionary: try that first, then each, then none)
        for d in [self.dicts.get(self._dict_name(name))] + list(self.dicts.values()) + [None]:
            try:
                dec = zstandard.ZstdDecompressor(dict_data=d) if d is not None else zstandard.ZstdDecompressor()
                return dec.decompress(data, max_output_size=1 << 30)
            except zstandard.ZstdError:
                continue
        raise ValueError("could not decompress %s" % name)

    def compress(self, data, name):
        d = self.dicts.get(self._dict_name(name))
        c = zstandard.ZstdCompressor(level=16, dict_data=d) if d is not None else zstandard.ZstdCompressor(level=16)
        return c.compress(data)

    def compress_like(self, data, original):
        """data compressed with the dictionary the original file's frame names (none when it names none). The frame records
        its decompressed size, as the game's own do (Longshot reads the size table's size from it)."""
        want = zstandard.get_frame_parameters(original).dict_id
        d = None
        if want:
            d = next((x for x in self.dicts.values() if x.dict_id() == want), None)
            if d is None:
                raise ValueError("no dictionary with id %d" % want)
        c = zstandard.ZstdCompressor(level=16, dict_data=d, write_content_size=True) if d is not None else \
            zstandard.ZstdCompressor(level=16, write_content_size=True)
        out = c.compress(data)
        if zstandard.get_frame_parameters(out).content_size != len(data):
            raise ValueError("frame does not record its size")
        return out

    def read(self, path):
        return self.decompress(open(path, "rb").read(), os.path.basename(path))
