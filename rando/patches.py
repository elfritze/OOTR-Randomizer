"""Changes to the game's data outside the chests, each one a setting."""
import copy
import os

from .events import EVENT_SETTING
from .formats import byml, sarc

# The new game's opening (OpeningEvent: Opening_LoadingKokiriForest, then Opening_Introduction) plays two movies by
# EventTransition: Dm_Kokiri_0000 (the story's opening) and Dm_Kokiri_0030 (Navi waking Link). Nothing else plays them. Their
# RSDB/EventSetting rows are made DefaultParentEvent's, the engine's own empty event (a 30-frame wait), so the opening goes on
# with what it does around them: the time set to 6:00, the Meet_DekuTree quest step, Navi placed and talked to, an autosave.
# The opening asks whether the last event was skipped and handles both answers, as a player's own skip of the movies does.
OPENING_MOVIES = ("Dm_Kokiri_0000", "Dm_Kokiri_0030")
EMPTY_EVENT = "DefaultParentEvent"


def skip_intro(romfs, codec, mod):
    raw = mod.read(EVENT_SETTING)
    rows, version = byml.read(raw)
    by_id = {r["__RowId"]: i for i, r in enumerate(rows)}
    empty = rows[by_id[EMPTY_EVENT]]
    for name in OPENING_MOVIES:
        row = copy.deepcopy(empty)
        row["__RowId"] = name
        rows[by_id[name]] = row
    mod.write(EVENT_SETTING, byml.write(rows, version, byml.endian(raw)))


# A song's item (Item_Melody_*, as a chest gives it) has a rupee for its model: the game never shows one. Every song shows
# Sheik's harp instead: (model project, model) as a ModelInfo names them, Model/<project>.<model>.bfres.zs. (Not tinted by the
# song: the engine recolors a model only by a material animation in its own files, as the rupee's Obj_Rupee_Color, and the
# harp has none; its color is its textures'.)
SONG_MODEL = ("Item_Harp_Sheik", "Item_Harp_Sheik")
SONGS = ("Item_Melody_ZeldaLullaby", "Item_Melody_EponaSong", "Item_Melody_SariaSong", "Item_Melody_SunSong",
         "Item_Melody_TimeSong", "Item_Melody_StormSong", "Item_Melody_ForestMinuet", "Item_Melody_FireBolero",
         "Item_Melody_WaterSerenade", "Item_Melody_ShadowNocturne", "Item_Melody_SpiritRequiem", "Item_Melody_LightPrelude")


def song_models(romfs, codec, mod, songs=SONGS):
    """each song's item shows SONG_MODEL"""
    project, model = SONG_MODEL
    for actor in songs:
        if not os.path.exists(os.path.join(romfs, "Model", "%s.%s.bfres.zs" % (project, model))):
            raise ValueError("no model %s.%s" % (project, model))
        rel = "Pack/Actor/%s.pack.zs" % actor
        files = sarc.read(mod.read(rel))
        key = "Component/ModelInfo/%s.engine__component__ModelInfo.bgyml" % actor
        info, version = byml.read(files[key])
        if info != {"FmdbName": "Obj_Rupee", "ModelProjectName": "Obj_Rupee"}:
            raise ValueError("%s: its model is not the rupee any more: %r" % (actor, info))
        info["FmdbName"], info["ModelProjectName"] = model, project
        files[key] = byml.write(info, version, byml.endian(files[key]))
        mod.write(rel, sarc.write(files))
