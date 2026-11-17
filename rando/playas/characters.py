"""Who adult Link is dressed as: what differs from one character to the other (build.py does the rest the same way).

  mod       the mod's folder name, and the name its own files take (Model/<mod>.<model>.bfres.zs, Phive/Cloth/<mod>...)
  who       the character's name, in messages
  model     the model: Model/<model>.<model>.bfres.zs, its cloth file Phive/Cloth/<model>.Nin_Ounce_NVN2.bphcl
  k         the size of the refitted mesh, as a fraction of the model's own: where the character's joints, posed like
            Link, fall nearest Link's (retarget.py)
  moved     rigid bones Link also has -> (a spare bone of the character's own to carry their mesh, its new parent). A
            spare bone: not Link's, no skin, no children, not in the cloth file, after its new parent in the skeleton
  held      (optional) bones -> the bone that carries their skin in their place (retarget.py): a bone Link's cloth swings
            (his belt's), or a rigid mesh on a bone Link sets in a model with no spare bone to move it to; the carrier of
            a rigid mesh is a bone Link sets (the bone itself: its mesh stays, shifted to where the character's sits)
  shift     (optional) where the scaled mesh is moved as a whole, in metres (a model standing off its own root)
  pack      the actor whose pack holds the character's cloth settings and reactions; set: its physics there (no set: a
            character without cloth); cloth (optional): its cloth file's name when not the model's
  unanchored  (optional) cloth meshes whose reference skin is left reading bones Link's cloth sets too (build.py)
  leash     cloth meshes -> how far their particles may stray from where they sit on the body, as a multiple of the
            cloth file's own distance. The game's settings leave hair and skirts all but free (20 to 65): Link rolls and
            flips, and what goes over the head stays there (seen on Ganondorf's hair)
  voices    the sound archives with the character's voice: (archive, what its clips' names start with, a prefix for
            their kinds here), the first the character's own
  rules     Link's kinds of voice (how the asset's name goes on after Vo_PlAdult_; a string: how it ends, numbers
            aside; the first rule that fits) -> the kinds of clips to pick from; other: for the rest (jumps, climbing...)
  label     the character's name in the window's list; group: its heading there (GROUPS); seen: looked at in game and
            approved (the others are built the same way, not yet judged); rough (optional): its joints are far from
            Link's (over 7 cm on average: limbs can look pulled where they bend)
"""


class Character:
    def __init__(self, **kw):
        self.__dict__.update(kw)


GANONDORF = Character(
    mod="PlayAsGanondorf",
    who="Ganondorf",
    label="Ganondorf", group="Legends", seen=True,
    model="Npc_Gerudo_GEU_Ganondorf_Adult",
    k=0.60,   # (3 cm from Link's joints on average, 6 cm at worst; his own size is 1.65 times Link's)
    moved={
        "Eyeball_L": ("Ph_Sideburns_2_L", "Head"),
        "Eyeball_R": ("Ph_Sideburns_2_R", "Head"),
        "Finger_C_1_L": ("Ph_Collar_A_2_L", "Finger_C_1_L"),
        "Finger_E_1_L": ("Ph_Collar_A_2_R", "Finger_E_1_L"),
        "Finger_B_1_R": ("Ph_Collar_C_2_L", "Finger_B_1_R"),
        "Finger_D_1_R": ("Ph_Collar_C_2_R", "Finger_D_1_R"),
        "Spine_2": ("Ph_Cloak_B_3", "Spine_2"),   # (the collar's jewels: 600 vertices of each stone shape)
    },
    pack="Enemy_DungeonBoss_Ganondorf",
    set="Phive/ControllerSetParam/Enemy_DungeonBoss_Ganondorf.phive__ControllerSetParam.bgyml",
    leash={"SimulationMesh_BackHair": 1.0, "SimulationMesh_BackHair_Out": 1.0},   # (8 to 25 cm at this size)
    voices=[("NV_USen_Custom_Ganondorf", "NV_USen_Custom_Ganondorf_Ganondorf_", "")],   # (his cries in the final battle)
    rules=[
        (("Death", "WaterDeath"), ["Die"]),   # (his one death cry, whatever Link's lasts)
        (("FallingScream", "WallMasterReturn_Scream"), ["LightArrowSecondDamage", "Die"]),   # (cries, not groans)
        (("Damage_B", "LandingDamage", "FireDamage_L", "ElectricDamage_L", "LavaDamage", "AntlionDamage"),
         ["LightArrowSecondDamage", "LightArrowDamage", "MagicBallDamage", "Down"]),
        (("Damage_", "RollAttackDamage", "IceDamage", "DrinkDamage", "PoisonDamage", "FireDamage", "ElectricDamage",
          "FallSuddenly", "GrabFall"), ["SwordDamage", "MagicBallDamage", "LightArrowDamage"]),
        (("DyingStandup", "StandDesperately", "HeavyBbreathing", "Stretching", "Emerge", "WakeUp", "BottleDrink",
          "DrinkBreath"), ["Recovery", "Down", "Restrained"]),
        (("Push", "liftingImpossible", "SilverGlove_LiftUp"),
         ["Restrained", "ReflectMagicBallCharge", "ChargeMagicBall", "AttackSCarge"]),
        ("_Charge", ["ChargeMagicBall", "ReflectMagicBallCharge", "AttackLCharge", "AttackSCarge"]),   # (the three spells)
        ("_Shoot", ["ThrowMagicBallL", "ThrowMagicBall", "AttackL"]),
        (("SwordAttack_B", "BigSwordAttack_B", "JumpAttack", "BS_JumpAttack", "H_JumpAttack", "Hammer", "RotaryCut",
          "Sword_O"), ["ReflectMagicBallL", "ThrowMagicBallL", "AttackL", "ThrowMagicBall", "ReflectMagicBall"]),
        (("SwordAttack", "BigSwordAttack", "Swing", "RollAttack", "HookShot", "Throwing", "SilverGlove_Throw"),
         ["ReflectMagicBall", "ThrowMagicBall"]),
        (("NormalBlock", "Shield_"), ["ActiveBarrier", "ActiveBarrierB", "ActiveBarrierC"]),
        (("TreasureBox_B2",), ["Laungh", "ProvokeLaungh"]),
        (("TreasureBox",), ["ProvokeLaungh", "Laungh"]),
        (("Wait",), ["Laungh", "ProvokeLaungh", "Recovery", "ActiveBarrierB", "ActiveBarrierC", "ChargeMagicBall"]),
    ],
    other=["ActiveBarrier", "ActiveBarrierB", "ActiveBarrierC", "ReflectMagicBall", "Recovery"],
)

# Zelda as an adult. Her own voice in the game is six clips (two gasps of each size, two of pain): Sheik's, who is Zelda,
# gives the rest (two weapon swings, pain, surprise, anger, thought...). Kinds: hers as they are, Sheik's "Sheik_<kind>"
ZELDA = Character(
    mod="PlayAsZelda",
    who="Zelda",
    label="Zelda", group="Legends", seen=True,
    model="Npc_Hylia_WU_Zelda_Adult",
    k=0.93,   # (5 cm from Link's joints on average, 8 cm at worst, the hand; she is a little taller than Link)
    moved={
        "Eyeball_L": ("Ph_Hip_L", "Head"),
        "Eyeball_R": ("Ph_Hip_R", "Head"),
    },
    pack="Npc_Hylia_Zelda_Adult",
    set="Phive/ControllerSetParam/Npc_Hylia_WU_Zelda_Adult.phive__ControllerSetParam.bgyml",
    leash={   # (the game's: 20 to 60 for her hair, 30 and 45 for her skirt)
        "SimulationMesh_HairSide": 1.0, "SimulationMesh_HairBack": 1.0, "SimulationMesh_HairBack_In": 1.0,
        "SimulationMesh_HairBack_Out": 1.0, "SimulationMesh_HairBack_A": 1.0,   # (5 to 56 cm at this size)
        "SimulationMesh_Skirt": 2.0, "SimulationMesh_Skirt_Run": 2.0,           # (3 to 56 cm)
    },
    voices=[("NV_USen_Custom_Zelda_Adult", "NV_USen_Custom_Zelda_Adult_", ""),
            ("NV_USen_Custom_Sheik", "NV_USen_Custom_Sheik_", "Sheik_")],
    rules=[
        (("Death", "WaterDeath"), ["Sheik_Stunned", "Sheik_Sad"]),
        (("FallingScream", "WallMasterReturn_Scream"), ["SurpriseL", "Sheik_SurpriseL", "Sheik_Stunned"]),
        (("Damage_B", "LandingDamage", "FireDamage_L", "ElectricDamage_L", "LavaDamage", "AntlionDamage"),
         ["Painful", "Sheik_Painful", "Sheik_Stunned"]),
        (("Damage_", "RollAttackDamage", "IceDamage", "DrinkDamage", "PoisonDamage", "FireDamage", "ElectricDamage",
          "FallSuddenly", "GrabFall"), ["Painful", "Sheik_Painful", "SurpriseM"]),
        (("DyingStandup", "StandDesperately", "HeavyBbreathing", "Stretching", "Emerge", "WakeUp", "BottleDrink",
          "DrinkBreath"), ["Sheik_Sad", "Sheik_Ease", "Sheik_Stunned"]),
        (("Push", "liftingImpossible", "SilverGlove_LiftUp"), ["Sheik_Angry", "Sheik_Prompt"]),
        ("_Charge", ["Sheik_Think", "Sheik_Angry"]),
        ("_Shoot", ["Sheik_Angry", "Sheik_WeaponSwingS"]),
        (("SwordAttack_B", "BigSwordAttack_B", "JumpAttack", "BS_JumpAttack", "H_JumpAttack", "Hammer", "RotaryCut",
          "Sword_O"), ["Sheik_Angry", "Sheik_WeaponSwingS", "Sheik_Prompt"]),
        (("SwordAttack", "BigSwordAttack", "Swing", "RollAttack", "HookShot", "Throwing", "SilverGlove_Throw"),
         ["Sheik_WeaponSwingS", "Sheik_Prompt", "Sheik_Angry"]),
        (("NormalBlock", "Shield_"), ["Sheik_Notice", "Sheik_Prompt", "SurpriseM"]),
        (("TreasureBox",), ["Sheik_Happy", "Sheik_TalkPositive"]),
        (("Surprised",), ["SurpriseM", "SurpriseL", "Sheik_SurpriseS"]),
        (("Wait",), ["Sheik_Think", "Sheik_Ease", "Sheik_QuestionNormal", "Sheik_Notice", "Sheik_Happy"]),
    ],
    other=["Sheik_WeaponSwingS", "Sheik_Prompt", "Sheik_Notice"],
)

# Sheik: Zelda's skeleton (the same size against Link's), her own model. No spare bone for her rigid meshes (the eyes; the
# knife on her back, rigid on the waist): Link's head carries the eyes, the waist keeps the knife. Link's cloth swings
# his belt's bones (Ph_Belt_1, Ph_Belt_2), which her waist piece has by name, 20 cm from his: the waist carries them.
# Her cloth is her hair (the side locks, the braid). Her voice: her own forty clips.
SHEIK = Character(
    mod="PlayAsSheik",
    who="Sheik",
    label="Sheik", group="Legends", seen=True,
    model="Npc_Hylia_WU_Sheik",
    k=0.93,
    moved={},
    held={
        "Eyeball_L": "Head", "Eyeball_R": "Head",
        "Waist": "Waist",
        "Ph_Belt_1": "Waist", "Ph_Belt_2": "Waist", "Ph_Belt_3": "Waist",
    },
    pack="Npc_Hylia_Sheik_Adult",
    set="Phive/ControllerSetParam/Npc_Hylia_WU_Sheik.phive__ControllerSetParam.bgyml",
    leash={   # (the game's: 5 to 11)
        "SimulationMesh_Hair_1_L_Shape": 1.0, "SimulationMesh_Hair_1_T_L_Shape": 1.0, "SimulationMesh_Hair_2_L_Shape": 1.0,
        "SimulationMesh_Hair_3_L_Shape": 1.0, "SimulationMesh_Hair_1_R_Shape": 1.0, "SimulationMesh_Hair_2_R_Shape": 1.0,
        "SimulationMesh_BackHair_Shape": 2.0,   # (the braid)
    },
    voices=[("NV_USen_Custom_Sheik", "NV_USen_Custom_Sheik_", "")],
    rules=[
        (("Death", "WaterDeath"), ["Stunned", "Sad"]),
        (("FallingScream", "WallMasterReturn_Scream"), ["SurpriseL", "Stunned"]),
        (("Damage_B", "LandingDamage", "FireDamage_L", "ElectricDamage_L", "LavaDamage", "AntlionDamage"),
         ["Painful", "Stunned"]),
        (("Damage_", "RollAttackDamage", "IceDamage", "DrinkDamage", "PoisonDamage", "FireDamage", "ElectricDamage",
          "FallSuddenly", "GrabFall"), ["Painful", "SurpriseM"]),
        (("DyingStandup", "StandDesperately", "HeavyBbreathing", "Stretching", "Emerge", "WakeUp", "BottleDrink",
          "DrinkBreath"), ["Sad", "Ease", "Stunned"]),
        (("Push", "liftingImpossible", "SilverGlove_LiftUp"), ["Angry", "Prompt"]),
        ("_Charge", ["Think", "Angry"]),
        ("_Shoot", ["Angry", "WeaponSwingS"]),
        (("SwordAttack_B", "BigSwordAttack_B", "JumpAttack", "BS_JumpAttack", "H_JumpAttack", "Hammer", "RotaryCut",
          "Sword_O"), ["Angry", "WeaponSwingS", "Prompt"]),
        (("SwordAttack", "BigSwordAttack", "Swing", "RollAttack", "HookShot", "Throwing", "SilverGlove_Throw"),
         ["WeaponSwingS", "Prompt", "Angry"]),
        (("NormalBlock", "Shield_"), ["Notice", "Prompt", "SurpriseS"]),
        (("TreasureBox",), ["Happy", "TalkPositive"]),
        (("Surprised",), ["SurpriseM", "SurpriseL", "SurpriseS"]),
        (("Wait",), ["Think", "Ease", "QuestionNormal", "Notice", "Happy"]),
    ],
    other=["WeaponSwingS", "Prompt", "Notice"],
)

# Impa (the game has one model of her, for both ages): taller than Link (her joints nearest his at 0.80 of her size). As
# Sheik, no spare bone: Link's head carries her eyes, the waist keeps her knife. Her cloth: her hair (the game's own
# settings keep it near: left as they are), the two ribbons and the waist belt (free in the game's, as Zelda's skirt).
# Her back hair's bones have the names of Link's (as Ganondorf's: the build keeps them hers).
IMPA = Character(
    mod="PlayAsImpa",
    who="Impa",
    label="Impa", group="Legends", seen=True,
    model="Npc_Hylia_WU_Impa",
    k=0.80,
    moved={},
    held={"Eyeball_L": "Head", "Eyeball_R": "Head", "Waist": "Waist"},
    pack="Npc_Hylia_Impa_Child",
    set="Phive/ControllerSetParam/Npc_Hylia_WU_Impa.phive__ControllerSetParam.bgyml",
    leash={"SimulationMesh_Ribbon_01": 2.0, "SimulationMesh_Ribbon_02": 2.0, "SimulationMesh_WaistBelt": 2.0},   # (50)
    voices=[("NV_USen_Custom_Impa", "NV_USen_Custom_Impa_", "")],
    rules=[
        (("Death", "WaterDeath"), ["Sad", "Painful"]),
        (("FallingScream", "WallMasterReturn_Scream"), ["SurpriseL"]),
        (("Damage_B", "LandingDamage", "FireDamage_L", "ElectricDamage_L", "LavaDamage", "AntlionDamage"),
         ["Painful", "SurpriseL"]),
        (("Damage_", "RollAttackDamage", "IceDamage", "DrinkDamage", "PoisonDamage", "FireDamage", "ElectricDamage",
          "FallSuddenly", "GrabFall"), ["Painful", "SurpriseM"]),
        (("DyingStandup", "StandDesperately", "HeavyBbreathing", "Stretching", "Emerge", "WakeUp", "BottleDrink",
          "DrinkBreath"), ["Sad", "Think"]),
        (("Push", "liftingImpossible", "SilverGlove_LiftUp"), ["Angry", "CallFar"]),
        ("_Charge", ["Think", "Angry"]),
        ("_Shoot", ["Angry", "WeaponSwingS"]),
        (("SwordAttack_B", "BigSwordAttack_B", "JumpAttack", "BS_JumpAttack", "H_JumpAttack", "Hammer", "RotaryCut",
          "Sword_O"), ["Angry", "CallFar", "WeaponSwingS"]),
        (("SwordAttack", "BigSwordAttack", "Swing", "RollAttack", "HookShot", "Throwing", "SilverGlove_Throw"),
         ["WeaponSwingS", "Angry"]),
        (("NormalBlock", "Shield_"), ["Notice", "SurpriseS"]),
        (("TreasureBox",), ["TalkPositive", "Greeting"]),
        (("Surprised",), ["SurpriseM", "SurpriseL", "SurpriseS"]),
        (("Wait",), ["Think", "QuestionNormal", "Notice", "Greeting"]),
    ],
    other=["WeaponSwingS", "Notice"],
)

# Nabooru: a little taller than Link (0.88). Link's head carries her eyes and keeps what she wears rigid on her head (the
# circlet's stones, the hair ring, the head chain); her earrings and her blade are on bones of her own. Her cloth is much
# of her: the ponytail, the hair, the earrings, the top, the belt, the trousers, the blade on her back, all free in the
# game's settings (10 to 50): kept nearer here, as the others' hair and Zelda's skirt. Her back hair's bones have the
# names of Link's (as Ganondorf's). Her voice has no fighting cries: her angry ones, and her short calls.
NABOORU = Character(
    mod="PlayAsNabooru",
    who="Nabooru",
    label="Nabooru", group="Legends", seen=True,
    model="Npc_Gerudo_GEU_Nabooru",
    k=0.88,
    moved={},
    held={"Eyeball_L": "Head", "Eyeball_R": "Head", "Head": "Head"},
    pack="Npc_Gerudo_Nabooru_Adult",
    set="Phive/ControllerSetParam/Npc_Gerudo_GEU_Nabooru.phive__ControllerSetParam.bgyml",
    leash={
        "SimulationMesh_Ponytail": 1.0, "SimulationMesh_Ponytail_Back": 1.0, "SimulationMesh_SideHair": 1.0,   # (50, 43, 9)
        "SimulationMesh_Hair_Acce": 2.0, "SimulationMesh_Earings": 2.0,                                        # (10, 20)
        "SimulationMesh_Pants": 2.0, "SimulationMesh_BareTop": 2.0, "SimulationMesh_Belt": 2.0,                # (15, 12, 10)
        "SimulationMesh_Blade": 2.0,                                                                           # (10)
    },
    voices=[("NV_USen_Custom_Nabooru", "NV_USen_Custom_Nabooru_", "")],
    rules=[
        (("Death", "WaterDeath"), ["Sad", "Painful"]),
        (("FallingScream", "WallMasterReturn_Scream"), ["SurpriseL"]),
        (("Damage_B", "LandingDamage", "FireDamage_L", "ElectricDamage_L", "LavaDamage", "AntlionDamage"),
         ["Painful", "SurpriseL"]),
        (("Damage_", "RollAttackDamage", "IceDamage", "DrinkDamage", "PoisonDamage", "FireDamage", "ElectricDamage",
          "FallSuddenly", "GrabFall"), ["Painful", "SurpriseM"]),
        (("DyingStandup", "StandDesperately", "HeavyBbreathing", "Stretching", "Emerge", "WakeUp", "BottleDrink",
          "DrinkBreath"), ["Sad", "Think"]),
        (("Push", "liftingImpossible", "SilverGlove_LiftUp"), ["Angry"]),
        ("_Charge", ["Think", "Angry"]),
        ("_Shoot", ["Angry", "Notice"]),
        (("SwordAttack_B", "BigSwordAttack_B", "JumpAttack", "BS_JumpAttack", "H_JumpAttack", "Hammer", "RotaryCut",
          "Sword_O"), ["Angry", "SurpriseS"]),
        (("SwordAttack", "BigSwordAttack", "Swing", "RollAttack", "HookShot", "Throwing", "SilverGlove_Throw"),
         ["Angry", "Greeting", "Notice"]),
        (("NormalBlock", "Shield_"), ["Notice", "SurpriseS"]),
        (("TreasureBox_B2",), ["LaughS", "Happy"]),
        (("TreasureBox",), ["Happy", "TalkPositive"]),
        (("Surprised",), ["SurpriseM", "SurpriseL", "SurpriseS"]),
        (("Wait",), ["Think", "QuestionNormal", "LaughS", "Notice"]),
    ],
    other=["Notice", "Greeting"],
)

# Ruto as an adult: a little taller than Link (0.89), the nearest to him of all (2.4 cm on average). Over 255 matrices: her
# rigid vertices name theirs in 16 bits. Link's head carries her eyes and keeps what is rigid on it (the eyes' sides); her
# teeth stay on their bones (Link's, 2 cm from hers), shifted. Her cloth: the skirt, the head's tail, the fins, the
# earrings, the necklace. Her own voice in the game is thirteen lines of the Water Temple's scene, three seconds each:
# no cries. So Zelda's and Sheik's, as Zelda's mod.
RUTO = Character(
    mod="PlayAsRuto",
    who="Ruto",
    label="Ruto", group="Legends", seen=True,
    model="Npc_Zora_ZU_Ruto_Adult",
    k=0.89,
    moved={},
    held={"Eyeball_L": "Head", "Eyeball_R": "Head", "Head": "Head", "Teeth_Down": "Teeth_Down", "Teeth_Up": "Teeth_Up"},
    pack="Npc_Zora_Ruto_Adult_001",
    set="Phive/ControllerSetParam/Npc_Zora_ZU_Ruto_Adult.phive__ControllerSetParam.bgyml",
    leash={
        "SimulationMesh_Tail": 1.0,                                                                     # (6)
        "SimulationMesh_Skirt": 2.0, "SimulationMesh_Necklace": 2.0, "SimulationMesh_Earring": 2.0,     # (16, 12, 4)
        "SimulationMesh_Fin_L": 2.0, "SimulationMesh_Fin_R": 2.0,                                       # (9)
    },
    voices=ZELDA.voices,
    rules=ZELDA.rules,
    other=ZELDA.other,
)

# Phantom Ganon: Ganondorf's size (0.60) and build, his own face, armour and hair; no cape (a scarf). What is rigid on
# bones Link sets stays on them, shifted: the collar's stones (the chest), the four rings (their fingers), the forehead
# piece (the head, which carries the eyes too). His spear is rigid on the right hand's weapon bone, where Link holds his
# shield: not worn. No voice of his own in the game: Ganondorf's.
PHANTOM_GANON = Character(
    mod="PlayAsPhantomGanon",
    who="Phantom Ganon",
    label="Phantom Ganon", group="Legends", seen=False,
    model="Npc_DungeonBoss_PhantomGanon",
    k=0.60,
    moved={},
    held={
        "Eyeball_L": "Head", "Eyeball_R": "Head", "Head": "Head",
        "Spine_2": "Spine_2",
        "Finger_C_1_L": "Finger_C_1_L", "Finger_E_1_L": "Finger_E_1_L",
        "Finger_B_1_R": "Finger_B_1_R", "Finger_D_1_R": "Finger_D_1_R",
        "Weapon_R": None,
    },
    pack="Enemy_DungeonBoss_PhantomGanon",
    set="Phive/ControllerSetParam/Enemy_DungeonBoss_PhantomGanon.phive__ControllerSetParam.bgyml",
    leash={"SimulationMesh_HairCenter_1": 1.0, "SimulationMesh_HairCenter_2": 1.0, "SimulationMesh_HairSide_1": 1.0},  # (5)
    voices=GANONDORF.voices,
    rules=GANONDORF.rules,
    other=GANONDORF.other,
)

# Malon as an adult: all but Link's size (0.97). Link's head carries her eyes; her belt's metal parts stay rigid on the
# lower spine, shifted; her necklace is on a bone of her own. Her cloth: the long hair at the back (free in the game's
# settings, 90: kept near, as the others'), the front and side hair, the skirt (as Zelda's), the shirt and the ribbon (as
# the game has them). Her voice is not among the story characters' (NV_<language>_Custom_*): one archive for every
# language, NV_Malon_Adult, 56 clips, humming among them (for when she waits).
MALON = Character(
    mod="PlayAsMalon",
    who="Malon",
    label="Malon", group="Hyrule's people", seen=True,
    model="Npc_Hylia_WN_Malon_Adult",
    k=0.97,
    moved={},
    held={"Eyeball_L": "Head", "Eyeball_R": "Head", "Spine_1": "Spine_1"},
    pack="Npc_Hylia_Malon_Adult",
    set="Phive/ControllerSetParam/Npc_Hylia_WN_Malon_Adult.phive__ControllerSetParam.bgyml",
    # (her back hair's own distances in the cloth file are long, 32 to 90 cm, where Ganondorf's are 13 to 41: at 1.0 it
    #  came over her shoulder and hung in front like a beard (seen in game, 2026-11-17). At 0.25: 8 to 22 cm)
    leash={
        "SimulationMesh_HairBack": 0.25, "SimulationMesh_HairFront": 1.0, "SimulationMesh_HairSide": 1.0,   # (90, 14, 8)
        "SimulationMesh_Skirt": 2.0,                                                                        # (15)
    },
    voices=[("NV_Malon_Adult", "NV_Malon_Adult_", "")],
    rules=[
        (("Death", "WaterDeath"), ["Sad", "Scare"]),
        (("FallingScream", "WallMasterReturn_Scream"), ["Scare", "SurpriseL"]),
        (("Damage_B", "LandingDamage", "FireDamage_L", "ElectricDamage_L", "LavaDamage", "AntlionDamage"),
         ["Painful", "Scare"]),
        (("Damage_", "RollAttackDamage", "IceDamage", "DrinkDamage", "PoisonDamage", "FireDamage", "ElectricDamage",
          "FallSuddenly", "GrabFall"), ["Painful", "SurpriseM"]),
        (("DyingStandup", "StandDesperately", "HeavyBbreathing", "Stretching", "Emerge", "WakeUp", "BottleDrink",
          "DrinkBreath"), ["Sigh", "Wakep", "Sad"]),
        (("Push", "liftingImpossible", "SilverGlove_LiftUp"), ["Angry", "CallFar"]),
        ("_Charge", ["Think", "Angry"]),
        ("_Shoot", ["Angry", "Start"]),
        (("SwordAttack_B", "BigSwordAttack_B", "JumpAttack", "BS_JumpAttack", "H_JumpAttack", "Hammer", "RotaryCut",
          "Sword_O"), ["Angry", "CallFar", "Start"]),
        (("SwordAttack", "BigSwordAttack", "Swing", "RollAttack", "HookShot", "Throwing", "SilverGlove_Throw"),
         ["Start", "Angry", "Greeting"]),
        (("NormalBlock", "Shield_"), ["Notice", "SurpriseS"]),
        (("TreasureBox_B2",), ["LaughL", "Happy"]),
        (("TreasureBox",), ["Happy", "TalkPositiveFine"]),
        (("Surprised",), ["SurpriseM", "SurpriseL", "SurpriseS"]),
        (("Wait",), ["Humming", "Think", "Ease", "QuestionNormal"]),
    ],
    other=["Start", "Notice"],
)

# A Lizalfos: not a person's skeleton (70 bones, 38 of them Link's: the spine, the arms and three fingers, the legs, the
# head and jaw), but the same rig, standing 18 cm behind its own root: the mesh is shifted forward over Link's (shift), and
# then its joints are 5 cm from his on average at 0.77. Its neck (three bones), its tail and its eyes are its own: still.
# The eyes' model is rigid on the head. Its cloth: the sword on its hip, the apron, the waist chain, the chest string.
# Its voice: its cries as an enemy (its archive holds its steps and chain too: only the clips named ...Voice are used).
LIZALFOS = Character(
    mod="PlayAsLizalfos",
    who="Lizalfos",
    label="Lizalfos", group="Monsters", seen=False, rough=True,
    model="Enemy_Lizalfos",
    k=0.77,
    shift=(0.0, 0.0, 0.14),
    moved={},
    held={"Head": "Head"},
    pack="Enemy_Lizalfos",
    set="Phive/ControllerSetParam/Enemy_Lizalfos.phive__ControllerSetParam.bgyml",
    leash={"Havok_Sword": 2.0, "Havok_Apron": 2.0, "Havol_Waist_Chain": 2.0, "Havok_Chest_String": 2.0},   # (40, 20, 40, 40)
    voices=[("Enemy_Lizalfos", "SE_Enemy_Lizalfos_", "")],
    rules=[
        (("Death", "WaterDeath"), ["DeadVoice"]),
        (("FallingScream", "WallMasterReturn_Scream"), ["UproarVoice", "DeadVoice"]),
        (("Damage_B", "LandingDamage", "FireDamage_L", "ElectricDamage_L", "LavaDamage", "AntlionDamage"),
         ["BigDamageVoice"]),
        (("Damage_", "RollAttackDamage", "IceDamage", "DrinkDamage", "PoisonDamage", "FireDamage", "ElectricDamage",
          "FallSuddenly", "GrabFall"), ["DamageVoice", "RepelledVoice"]),
        (("DyingStandup", "StandDesperately", "HeavyBbreathing", "Stretching", "Emerge", "WakeUp", "BottleDrink",
          "DrinkBreath"), ["FaintEndVoice"]),
        (("Push", "liftingImpossible", "SilverGlove_LiftUp"), ["PreAttackVoice", "RepelledLongVoice"]),
        ("_Charge", ["PreAttackVoice", "ProvokeVoice"]),
        ("_Shoot", ["AttackVoice"]),
        (("JumpAttack", "BS_JumpAttack", "H_JumpAttack"), ["JumpVoice", "AttackVoice"]),
        (("SwordAttack_B", "BigSwordAttack_B", "Hammer", "RotaryCut", "Sword_O"), ["AttackVoice", "UproarVoice"]),
        (("SwordAttack", "BigSwordAttack", "Swing", "RollAttack", "HookShot", "Throwing", "SilverGlove_Throw"),
         ["AttackVoice", "PreAttackVoice"]),
        (("NormalBlock", "Shield_"), ["RepelledVoice", "RepelledLongVoice"]),
        (("TreasureBox",), ["ProvokeVoice", "AppearVoice"]),
        (("Surprised",), ["AppearVoice"]),
        (("Wait",), ["ProvokeVoice", "AppearVoice", "FaintEndVoice"]),
    ],
    other=["JumpVoice", "PreAttackVoice"],
)

# The Bombchu Bowling lady (the actor Npc_Hylia_067_Shop_Child, behind the counter of the Market's bowling alley): one of
# the townswomen's models, Malon's size and rig (0.97). Link's head carries her eyes; her shoes' metal parts stay rigid on
# the ankles, shifted. Her cloth: the front, side and back hair (short: 5, 11 and 8 cm at most in the cloth file), the two
# ribbons, the necklace, the skirt (up to 42 cm in the file: left at that). Her voice is the spry townswoman's, the
# archive every such woman shares, with her own lines in it (a round cleared, her panic) and the Cucco lady's (not used).
BOMBCHU_LADY = Character(
    mod="PlayAsBombchuLady",
    who="the Bombchu Bowling lady",
    label="Bombchu Bowling lady", group="Hyrule's people", seen=True,
    model="Npc_Hylia_WN_008",
    k=0.97,
    moved={},
    held={"Eyeball_L": "Head", "Eyeball_R": "Head", "Ankle_L": "Ankle_L", "Ankle_R": "Ankle_R"},
    pack="Npc_Hylia_067_Shop_Child",
    set="Phive/ControllerSetParam/Npc_Hylia_WN_008_ThroughGround.phive__ControllerSetParam.bgyml",
    leash={
        "SimulationMesh_FrontHair": 1.0, "SimulationMesh_SideHair": 1.0, "SimulationMesh_BackHair": 1.0,   # (5, 11, 8)
        "SimulationMesh_Ribbon_Small": 2.0, "SimulationMesh_Ribbon_Big": 2.0,                              # (5, 5)
        "SimulationMesh_Necklace": 2.0, "SimulationMesh_Skirt": 1.0,                                       # (5, 42)
    },
    voices=[("NV_Hylia_Woman_Spry", "NV_Hylia_Woman_Spry_", "")],
    rules=[
        (("Death", "WaterDeath"), ["Sad", "BombchuBowlingClerk_Panic"]),
        (("FallingScream", "WallMasterReturn_Scream"), ["BombchuBowlingClerk_Panic", "SurpriseL"]),
        (("Damage_B", "LandingDamage", "FireDamage_L", "ElectricDamage_L", "LavaDamage", "AntlionDamage"),
         ["Painful", "SurpriseL"]),
        (("Damage_", "RollAttackDamage", "IceDamage", "DrinkDamage", "PoisonDamage", "FireDamage", "ElectricDamage",
          "FallSuddenly", "GrabFall"), ["Painful", "SurpriseM"]),
        (("DyingStandup", "StandDesperately", "HeavyBbreathing", "Stretching", "Emerge", "WakeUp", "BottleDrink",
          "DrinkBreath"), ["Stretch", "Wakep", "Sad"]),
        (("Push", "liftingImpossible", "SilverGlove_LiftUp"), ["Angry", "CallFar"]),
        ("_Charge", ["Think", "Angry"]),
        ("_Shoot", ["Angry", "CallOut"]),
        (("SwordAttack_B", "BigSwordAttack_B", "JumpAttack", "BS_JumpAttack", "H_JumpAttack", "Hammer", "RotaryCut",
          "Sword_O"), ["Angry", "CallFar", "CallOut"]),
        (("SwordAttack", "BigSwordAttack", "Swing", "RollAttack", "HookShot", "Throwing", "SilverGlove_Throw"),
         ["CallOut", "Angry", "Greeting"]),
        (("NormalBlock", "Shield_"), ["Notice", "SurpriseS"]),
        (("TreasureBox_B2",), ["BombchuBowlingClerk_GameClear", "LaughL"]),
        (("TreasureBox",), ["Happy", "TalkPositive"]),
        (("Surprised",), ["SurpriseM", "SurpriseL", "SurpriseS"]),
        (("Wait",), ["Humming", "Think", "Ease", "QuestionNormal"]),
    ],
    other=["CallOut", "Notice"],
)


# The voice rules of the characters below, by what Link is doing (the names Link's clips start or end with are the same
# for every character: only the kinds of clips to pick from differ)
MOMENTS = [
    ("death", ("Death", "WaterDeath")),
    ("scream", ("FallingScream", "WallMasterReturn_Scream")),
    ("hurt_big", ("Damage_B", "LandingDamage", "FireDamage_L", "ElectricDamage_L", "LavaDamage", "AntlionDamage")),
    ("hurt", ("Damage_", "RollAttackDamage", "IceDamage", "DrinkDamage", "PoisonDamage", "FireDamage", "ElectricDamage",
              "FallSuddenly", "GrabFall")),
    ("tired", ("DyingStandup", "StandDesperately", "HeavyBbreathing", "Stretching", "Emerge", "WakeUp", "BottleDrink",
               "DrinkBreath")),
    ("push", ("Push", "liftingImpossible", "SilverGlove_LiftUp")),
    ("charge", "_Charge"),
    ("shoot", "_Shoot"),
    ("jump_attack", ("JumpAttack", "BS_JumpAttack", "H_JumpAttack")),
    ("big_swing", ("SwordAttack_B", "BigSwordAttack_B", "Hammer", "RotaryCut", "Sword_O")),
    ("swing", ("SwordAttack", "BigSwordAttack", "Swing", "RollAttack", "HookShot", "Throwing", "SilverGlove_Throw")),
    ("block", ("NormalBlock", "Shield_")),
    ("big_chest", ("TreasureBox_B2",)),
    ("chest", ("TreasureBox",)),
    ("surprised", ("Surprised",)),
    ("wait", ("Wait",)),
]
# the townsfolk's archives hold the same kinds of clips (Angry, Painful, SurpriseL...: not every archive every kind, and a
# kind an archive has not is passed over), and each its character's own lines
TOWN = dict(
    death=["Sad", "Scare"], scream=["Scare", "SurpriseL"], hurt_big=["Painful", "SurpriseL"], hurt=["Painful", "SurpriseM"],
    tired=["Stretch", "Wakep", "Sad"], push=["Angry", "CallFar"], charge=["Think", "Angry"], shoot=["Angry", "CallOut"],
    jump_attack=["Angry", "CallFar", "CallOut"], big_swing=["Angry", "CallFar", "CallOut"],
    swing=["CallOut", "Angry", "Greeting"], block=["Notice", "SurpriseS"], big_chest=["LaughL", "Happy"],
    chest=["Happy", "TalkPositive"], surprised=["SurpriseM", "SurpriseL", "SurpriseS"],
    wait=["Humming", "Think", "Ease", "QuestionNormal"],
)


def cries(base=None, **kinds):
    """the rules for a character: base's kinds of clips for each moment (MOMENTS), with these put first or in their place
    (a list: with the base's after it; a tuple: instead of them)"""
    rules = []
    for moment, match in MOMENTS:
        mine = kinds.pop(moment, [])
        pick = list(mine) if isinstance(mine, tuple) else list(mine) + list((base or {}).get(moment, []))
        if pick:
            rules.append((match, pick))
    if kinds:
        raise ValueError("no such moments: %s" % ", ".join(kinds))
    return rules


# A Wolfos: a wolf on two legs, 44 of its 92 bones Link's. Hunched, long arms: its joints are 11 cm from Link's on average
# at 0.70 (the wrists 19): rough. Link's head carries its eyes. Its cloth: the mane (100 cm in the file: kept to a third),
# the beard, cheeks and moustache, the tail's fur, the sleeves, the tongue. Its voice: its cries as an enemy.
WOLFOS = Character(
    mod="PlayAsWolfos",
    who="Wolfos",
    label="Wolfos", group="Monsters", seen=False, rough=True,
    model="Enemy_Wolfos",
    k=0.70,
    shift=(0.0, 0.0, 0.03),
    moved={},
    held={"Eyeball_L": "Head", "Eyeball_R": "Head"},
    pack="Enemy_Wolfos",
    set="Phive/ControllerSetParam/Enemy_Wolfos.phive__ControllerSetParam.bgyml",
    leash={
        "SimulationMesh_Hair": 0.35, "SimulationMesh_Moustache": 0.89, "SimulationMesh_Beard": 1.0,   # (100, 40, 30)
        "SimulationMesh_Cheek": 1.0, "SimulationMesh_Fur": 1.0, "SimulationMesh_Tongue": 1.0,         # (25, 15, 30)
        "SimulationMesh_Sleeve_L": 1.0, "SimulationMesh_Sleeve_R": 1.0,                               # (30)
    },
    voices=[("Enemy_Wolfos", "SE_Enemy_Wolfos_Voice_", "")],
    rules=cries(
        death=["Dead"], scream=["Dead", "Intimidate"], hurt_big=["Damage", "AfterDamage"], hurt=["Damage", "AfterDamage"],
        tired=["Sniff", "Growl"], push=["Growl", "AttackPre"], charge=["Growl", "AttackPre"], shoot=["Attack"],
        jump_attack=["Jump", "Attack"], big_swing=["Attack", "Intimidate"], swing=["Attack", "AttackPre"],
        block=["Guard"], big_chest=["Appear", "Intimidate"], chest=["Appear", "Sniff"], surprised=["Turn", "Sniff"],
        wait=["Sniff", "Growl", "Intimidate"]),
    other=["Jump", "Turn"],
)

# A Stalfos: a skeleton knight, 70 of its 152 bones Link's, 6 cm from his joints on average at 0.63. What is rigid on
# bones Link sets stays on them, shifted (the skull, which carries the eyes too; the hip plate; the knee plates); its sword
# and its shield, rigid on the two weapon bones where Link holds his own, are not worn. Its cloth: the helmet's hair, the
# skirt, the boots' and gloves' flaps. Its voice: its cries as an enemy, and its laughs.
STALFOS = Character(
    mod="PlayAsStalfos",
    who="Stalfos",
    label="Stalfos", group="Monsters", seen=False,
    model="Enemy_Stalfos",
    k=0.63,
    shift=(0.0, 0.0, -0.03),
    moved={},
    held={
        "Head": "Head", "Eyeball_L": "Head", "Eyeball_R": "Head", "Waist": "Waist",
        "Leg_2_L": "Leg_2_L", "Leg_2_R": "Leg_2_R", "Weapon_L": None, "Weapon_R": None,
    },
    pack="Enemy_Stalfos",
    set="Phive/ControllerSetParam/Enemy_Stalfos.phive__ControllerSetParam.bgyml",
    leash={
        "SimulationMesh_Hair": 0.74, "SimulationMesh_Skirt": 1.0,                                     # (54, 40)
        "SimulationMesh_Boots_L": 2.0, "SimulationMesh_Boots_R": 2.0,                                 # (17)
        "SimulationMesh_Glove_L": 2.0, "SimulationMesh_Glove_R": 2.0,                                 # (10)
    },
    voices=[("Enemy_Stalfos", "SE_Enemy_Stalfos_", "")],
    rules=cries(
        death=["DeadVoice"], scream=["DeadVoice", "StunVoice"], hurt_big=["DamageVoice", "StunVoice"],
        hurt=["DamageVoice", "RepelledVoice"], tired=["StunVoice", "SearchVoice"], push=["GuardVoice", "RepelledVoice"],
        charge=["IntimidationVoice", "SearchVoice"], shoot=["AttackVoice"], jump_attack=["JumpAttackVoice", "AttackVoice"],
        big_swing=["JumpAttackVoice", "AttackVoice"], swing=["AttackVoice"], block=["GuardVoice", "RepelledVoice"],
        big_chest=["AppearLaugh", "Laugh"], chest=["Laugh", "AppearLaugh"], surprised=["SearchVoice"],
        wait=["Laugh", "SearchVoice", "IntimidationVoice"]),
    other=["AttackVoice", "GuardVoice"],
)

# A Stalchild: the small skeleton of the field at night, made a little larger than itself (1.08) to stand on Link's
# skeleton, 10 cm from his joints on average (short legs, long arms): rough. Its skull and its jaw are rigid on the head
# and the chin: they stay there, shifted (the jaw moves as Link's). Its cloth: the two rags at its waist.
STALCHILD = Character(
    mod="PlayAsStalchild",
    who="Stalchild",
    label="Stalchild", group="Monsters", seen=False, rough=True,
    model="Enemy_Stalchild",
    k=1.08,
    shift=(0.0, 0.0, -0.04),
    moved={},
    held={"Head": "Head", "Chin": "Chin"},
    pack="Enemy_Stalchild",
    set="Phive/ControllerSetParam/Enemy_Stalchild.phive__ControllerSetParam.bgyml",
    leash={"SimulationMesh_Skirt_A": 0.74, "SimulationMesh_Skirt_B": 0.91},                           # (50, 41)
    voices=[("Enemy_Stalchild", "SE_Enemy_Stulchild_Voice_", "")],
    rules=cries(
        death=["Dead"], scream=["Dead"], hurt_big=["Damage"], hurt=["Damage"], tired=["Appear"], push=["Attack"],
        charge=["Appear"], shoot=["Attack"], jump_attack=["Attack"], big_swing=["Attack"], swing=["Attack"],
        block=["Damage"], big_chest=["Appear"], chest=["Appear"], surprised=["Appear"], wait=["Appear"]),
    other=["Attack", "Appear"],
)

# A Dinolfos: the Lizalfos's larger kin, the same rig (39 of its 80 bones Link's, no neck bone of his), standing 9 cm
# behind its root: shifted forward, 8 cm from Link's joints on average at 0.79: rough. Its sword, rigid on the weapon bone
# where Link holds his shield, is not worn; the one on its hip is cloth, with the waist chain. Its voice: its cries.
DINOLFOS = Character(
    mod="PlayAsDinolfos",
    who="Dinolfos",
    label="Dinolfos", group="Monsters", seen=False, rough=True,
    model="Enemy_Dinolfos",
    k=0.79,
    shift=(0.0, 0.0, 0.09),
    moved={},
    held={"Weapon_R": None},
    pack="Enemy_Dinolfos",
    set="Phive/ControllerSetParam/Enemy_Dinolfos.phive__ControllerSetParam.bgyml",
    leash={"SimulationMesh_Sword": 1.0, "SimulationMesh_Waist_Chain": 1.0},                           # (40)
    voices=[("Enemy_Dinolfos", "SE_Enemy_Dinolfos_", "")],
    rules=cries(
        death=["DeadVoice"], scream=["UproarVoice", "DeadVoice"], hurt_big=["RepelledVoice", "StunEndVoice"],
        hurt=["RepelledVoice", "StunEndVoice"], tired=["StunEndVoice", "SearchVoice_Last"],
        push=["PreAttackVoice", "RushVoice"], charge=["PreAttackVoice", "SearchVoiceFirst"], shoot=["AttackVoice"],
        jump_attack=["JumpAttackVoice", "JumpVoice"], big_swing=["BigAttackVoice", "UproarVoice"],
        swing=["AttackVoice", "PreAttackVoice"], block=["RepelledVoice"], big_chest=["UproarVoice", "AppearVoice"],
        chest=["AppearVoice", "SearchVoiceFirst"], surprised=["SearchVoiceFirst", "AppearVoice"],
        wait=["SearchVoice", "SearchVoice_Last", "AppearVoice"]),
    other=["JumpVoice", "PreAttackVoice"],
)

# A ReDead: a tall thin corpse (0.73), 5 cm from Link's joints on average. Its mask is rigid on the head: it stays there,
# shifted. Its cloth (the loincloth's rags) has a cloth file and no settings in the game: simulated as the file has it.
# Its voice: its moans and its scream (the 22 seconds of its waiting moan are too long for any of Link's clips).
REDEAD = Character(
    mod="PlayAsReDead",
    who="ReDead",
    label="ReDead", group="Monsters", seen=False,
    model="Enemy_ReDead",
    k=0.73,
    moved={},
    held={"Head": "Head"},
    pack="Enemy_ReDead",
    set="Phive/ControllerSetParam/Enemy_ReDead.phive__ControllerSetParam.bgyml",
    leash={},
    voices=[("Enemy_ReDead", "SE_Enemy_ReDead_", ""), ("Enemy_ReDead", "SE_ReDead_Voice_", "")],
    rules=cries(
        death=["DeadtVoice"], scream=["Shout", "DeadtVoice"], hurt_big=["AttackStVoice", "AttackVoice"],
        hurt=["AttackVoice"], tired=["Cry", "AttackStVoice"], push=["AttackStVoice"], charge=["AttackStVoice"],
        shoot=["AttackVoice"], jump_attack=["AttackVoice", "Shout"], big_swing=["AttackVoice", "AttackStVoice"],
        swing=["AttackVoice"], block=["AttackVoice"], big_chest=["Shout", "Cry"], chest=["Cry", "AttackStVoice"],
        surprised=["AttackStVoice"], wait=["Cry", "AttackStVoice"]),
    other=["AttackVoice"],
)

# The Great Fairy: over five times Link's size in her own model, worn at 0.176 of it, 5 cm from his joints on average.
# Link's head carries her eyes. Her cloth: the ivy in her hair (its file is named Npc_U_GreantFairy, not as the model). Her
# voice has no cries: her laughs, for most of what Link does.
GREAT_FAIRY = Character(
    mod="PlayAsGreatFairy",
    who="the Great Fairy",
    label="Great Fairy", group="Legends", seen=False,
    model="Npc_U_GreatFairy",
    cloth="Npc_U_GreantFairy",
    k=0.176,
    moved={},
    held={"Eyeball_L": "Head", "Eyeball_R": "Head"},
    pack="Npc_GreatFairy_DefaultActor",
    set="Phive/ControllerSetParam/Dm_Npc_GreatFairy.phive__ControllerSetParam.bgyml",
    leash={"SimulationMesh_HairPlant": 2.0},                                                          # (the file's, small)
    voices=[("NV_GreatFairy", "NV_GreatFairy_", "")],
    rules=cries(
        death=["Sad"], scream=["SurpriseS", "Sad"], hurt_big=["SurpriseS", "Sad"], hurt=["SurpriseS"],
        tired=["Sad", "Think"], push=["Think", "Notice"], charge=["Think", "QuestionNormal"], shoot=["Notice", "LaughS"],
        jump_attack=["LaughL", "LaughS"], big_swing=["LaughS", "Notice"], swing=["Notice", "Greeting"],
        block=["SurpriseS", "Notice"], big_chest=["LaughL"], chest=["Happy", "TalkPositive", "LaughS"],
        surprised=["SurpriseS"], wait=["LaughS", "Think", "QuestionNormal", "Greeting"]),
    other=["Notice", "LaughS"],
)

# Rauru: a broad old man in a robe (0.85), 6 cm from Link's joints on average (the wrists 12). Link's head carries his
# eyes. His cloth: sixteen meshes, the robe, the long cloth of the back (100 cm in the file: kept to half), the sleeves,
# the hood, the apron, the beard and the hair. His own voice in the game is seven spoken sounds of the Chamber of Sages'
# scene: those for chests and waiting, an old townsman's for the rest.
RAURU = Character(
    mod="PlayAsRauru",
    who="Rauru",
    label="Rauru", group="Legends", seen=False,
    model="Npc_Hylia_MU_Rauru",
    k=0.85,
    moved={},
    held={"Eyeball_L": "Head", "Eyeball_R": "Head"},
    pack="Dm_Npc_Hylia_Rauru",
    set="Phive/ControllerSetParam/Dm_Npc_Hylia_Rauru.phive__ControllerSetParam.bgyml",
    leash={
        "SimulationMesh_SpineCloth": 0.47, "SimulationMesh_Robe": 0.94,                               # (100, 50)
        "SimulationMesh_ArmCloth_L": 0.94, "SimulationMesh_ArmCloth_R": 0.94,                         # (50)
        "SimulationMesh_Hood_Back": 1.0, "SimulationMesh_Apron": 1.0, "SimulationMesh_Necklace": 1.0,   # (40, 40, 19)
        "SimulationMesh_Sleeve_L": 1.0, "SimulationMesh_Sleeve_R": 1.0, "SimulationMesh_Hood_Up": 2.0,  # (20, 20, 10)
        "SimulationMesh_Hair_Up": 1.0, "SimulationMesh_Hair_Down": 1.0,                               # (6, 5)
        "SimulationMesh_Beard_L": 1.0, "SimulationMesh_Beard_R": 1.0,                                 # (3)
        "SimulationMesh_Hem_L": 2.0, "SimulationMesh_Hem_R": 2.0,                                     # (5)
    },
    voices=[("NV_USen_Custom_Rauru", "NV_USen_Custom_Rauru_Dm_SageRoom_0005_", "Rauru_"),
            ("NV_Hylia_Elderly_Man_1", "NV_Hylia_Elderly_Man_1_", "")],
    rules=cries(
        TOWN,
        big_chest=("Rauru_0017_Sp", "Rauru_0020_Sp"),
        chest=("Rauru_0001_Sp", "Rauru_0008_Sp", "Rauru_0015_Sp", "Rauru_0022_Sp", "Rauru_0030_Sp"),
        wait=("Rauru_0001_Sp", "Rauru_0008_Sp", "Rauru_0015_Sp", "Rauru_0022_Sp", "Rauru_0030_Sp", "Think")),
    other=["CallOut", "Notice"],
)

# The Running Man: a townsman of Link's size and rig (0.98, 3 cm from his joints). Nothing rigid. His cloth: the side
# hair, the trousers' legs. His voice is a townsman's archive with his own lines in it: his wheezing, his triumph.
RUNNING_MAN = Character(
    mod="PlayAsRunningMan",
    who="the Running Man",
    label="Running Man", group="Hyrule's people", seen=False,
    model="Npc_Hylia_MN_103",
    k=0.98,
    moved={},
    pack="Npc_Hylia_RunningMan_Adult",
    set="Phive/ControllerSetParam/Npc_Hylia_MN_103.phive__ControllerSetParam.bgyml",
    leash={"SimulationMesh_SideHair": 1.0, "SimulationMesh_Pants_L": 2.0, "SimulationMesh_Pants_R": 2.0},   # (24, 3, 3)
    voices=[("NV_Hylia_Man_4", "NV_Hylia_Man_4_", "")],
    rules=cries(
        TOWN, tired=["RunningMan_Wheeze"], big_chest=["RunningMan_Exultation"], scream=["RunningMan_BeggingLL"],
        surprised=["RunningMan_NoticeL"], wait=["RunningMan_Thinkback"]),
    other=["Run", "CallOut", "Notice"],
)

# The Happy Mask salesman: a townsman's rig (0.93, 3 cm from Link's joints). Link's head carries his eyes and keeps what
# is rigid on it; his collar's two bones are bones Link's own cloth swings (his collar's): the neck carries their skin.
# His cloth: the necklace's chains and parts, the dress, the sleeve. His voice is his own (his three angers among it).
MASK_SALESMAN = Character(
    mod="PlayAsMaskSalesman",
    who="the Happy Mask salesman",
    label="Happy Mask salesman", group="Hyrule's people", seen=False,
    model="Npc_Hylia_MN_005",
    k=0.93,
    moved={},
    held={"Head": "Head", "Eyeball_L": "Head", "Eyeball_R": "Head", "Ph_Collar_1_L": "Neck", "Ph_Collar_1_R": "Neck"},
    pack="Npc_Hylia_023_Shop_Child",
    set="Phive/ControllerSetParam/Npc_Hylia_MN_005.phive__ControllerSetParam.bgyml",
    leash={
        "SimulationMesh_Chains": 1.0, "SimulationMesh_Dress": 2.0,                                    # (20, 10)
        "SimulationMesh_Necklace_Parts": 2.0, "SimulationMesh_Sleeve": 2.0,                           # (4)
    },
    voices=[("NV_Happy_Mask_Shop", "NV_Happy_Mask_Shop_", "")],
    rules=cries(
        TOWN, push=["AngryM"], big_swing=["AngryL", "AngryM"], jump_attack=["AngryL"], chest=["LaughM"],
        wait=["LaughS", "LaughM"]),
    other=["Notice", "Greeting"],
)

# Shiro, the fourth of the carpenters: a young man broader than Link in the shoulders, long in the arm (1.00, but 10 cm
# from Link's joints on average, the elbows 19): rough. Nothing rigid. His cloth: the coat, the trousers, the hair.
SHIRO = Character(
    mod="PlayAsShiro",
    who="Shiro",
    label="Shiro (carpenter)", group="Hyrule's people", seen=False, rough=True,
    model="Npc_Hylia_MF_004",
    k=1.0,
    moved={},
    pack="Npc_Hylia_016_Adult",
    set="Phive/ControllerSetParam/Npc_Hylia_MF_004.phive__ControllerSetParam.bgyml",
    leash={
        "SimulationMesh_Coat": 1.0, "SimulationMesh_Pants": 2.0,                                      # (25, 10)
        "SimulationMesh_Hair_Front": 0.83, "SimulationMesh_Hair_Back": 0.83,                          # (30)
    },
    voices=[("NV_Hylia_Androgynous_Youth_2", "NV_Hylia_Androgynous_Youth_2_", "")],
    rules=cries(TOWN, big_swing=["Determination"], jump_attack=["Determination"], chest=["Praise"]),
    other=["Run", "Notice", "Greeting"],
)

# The lady whose dog is Richard: a stout townswoman (1.00, 8 cm from Link's joints on average, the hips 13): rough.
# Link's head carries her eyes; her sleeves' four bones are bones Link's own cloth swings: the shoulders' helper bones
# carry their skin. Her cloth: the tall hair (100 cm in the file: kept to a quarter), the skirt, the sleeves, the earrings,
# the necklace. Her voice is a townswoman's archive with her own lines (her anger, her cheers, her sorrow for the dog).
POOCH_LADY = Character(
    mod="PlayAsPoochLady",
    who="Richard's lady",
    label="Richard's lady", group="Hyrule's people", seen=False, rough=True,
    model="Npc_Hylia_WX_002",
    k=1.0,
    moved={},
    held={
        "Eyeball_L": "Head", "Eyeball_R": "Head",
        "Ph_Sleeve_Back_1_L": "Ph_Clavicle_Assist_L", "Ph_Sleeve_Front_1_L": "Ph_Clavicle_Assist_L",
        "Ph_Sleeve_Back_1_R": "Ph_Clavicle_Assist_R", "Ph_Sleeve_Front_1_R": "Ph_Clavicle_Assist_R",
    },
    pack="Npc_Hylia_052_Adult",
    set="Phive/ControllerSetParam/Npc_Hylia_WX_002.phive__ControllerSetParam.bgyml",
    # (her sleeves' cloth sets two bones Link's own sleeves' cloth sets too, and reads them back through a bone-space
    #  skin, which cloth_scale does not move to the parent bone: left as it is, kept within its 4 cm)
    unanchored=("SimulationMesh_Sleeve",),
    leash={
        "SimulationMesh_Hair_A": 0.25, "SimulationMesh_Hair_B": 2.0, "SimulationMesh_Skirt": 1.0,     # (100, 2, 25)
        "SimulationMesh_Sleeve": 1.0, "SimulationMesh_EarRing": 2.0, "SimulationMesh_Neckless": 2.0,  # (4, 5, 3)
    },
    voices=[("NV_Hylia_MA_Woman_2", "NV_Hylia_MA_Woman_2_", "")],
    rules=cries(
        TOWN, death=["DogMadam_Sad"], push=["DogMadam_Angry"], big_swing=["DogMadam_Angry"],
        big_chest=["DogMadam_Cheers"], tired=["DogMadam_Impatience"]),
    other=["CallOut", "Notice"],
)

# The Poe collector: a cloaked figure of Link's size (1.04, 3 cm from his joints), with a simple face of his own (79 of
# his 182 bones are Link's). What he holds is rigid on the weapon bone where Link holds his shield: not worn. His cloth:
# the cloak (back, top, front, arms) and the skirt. His voice is his own.
POE_COLLECTOR = Character(
    mod="PlayAsPoeCollector",
    who="the Poe collector",
    label="Poe collector", group="Hyrule's people", seen=False,
    model="Npc_Hylia_MU_005",
    k=1.04,
    moved={},
    held={"Weapon_R": None},
    pack="Npc_Hylia_048_BottleShop",
    set="Phive/ControllerSetParam/Npc_Hylia_MU_005_ThroughGround.phive__ControllerSetParam.bgyml",
    leash={
        "SimulationMesh_ClothBack": 0.64, "SimulationMesh_Skirt": 1.0, "SimulationMesh_ClothTop": 1.0,   # (60, 30, 30)
        "SimulationMesh_ClothFront": 1.0, "SimulationMesh_ClothArm_R": 1.0, "SimulationMesh_ClothArm_L": 1.0,   # (20)
    },
    voices=[("NV_PoeBuyer", "NV_PoeBuyer_", "")],
    rules=cries(TOWN, big_chest=["PoeBuyer_ClearDM", "PoeBuyer_LaughDM"], wait=["LaughS"]),
    other=["Notice", "Greeting"],
)

# A soldier of Hyrule: taller than Link in his armour (0.80, 3 cm from Link's joints). His shoulder plates are rigid on
# bones of his own. His cloth: the helmet's feather, the plates of the belly. His voice: the townsman's archive that holds
# the soldiers' lines (their orders, their alarm).
SOLDIER = Character(
    mod="PlayAsSoldier",
    who="the soldier",
    label="Hyrule soldier", group="Hyrule's people", seen=False,
    model="Npc_Hylia_MS_001",
    k=0.80,
    moved={},
    pack="Npc_Hylia_Soldier_001",
    set="Phive/ControllerSetParam/Npc_Hylia_MS_001.phive__ControllerSetParam.bgyml",
    leash={
        "SimulationMesh_Head_Feather": 1.0, "SimulationMesh_Stomach_Armor_01": 2.0,                   # (20, 5)
        "SimulationMesh_Stomach_Armor_02": 2.0, "SimulationMesh_Stomach_Armor_03": 2.0,               # (5)
    },
    voices=[("NV_Hylia_Man_4", "NV_Hylia_Man_4_", "")],
    rules=cries(
        TOWN, shoot=["Soldier_Coercion"], big_swing=["Soldier_Coercion"], swing=["Soldier_Disarming"],
        block=["Soldier_DetectionAlert"], surprised=["Soldier_Discovery"]),
    other=["CallOut", "Notice"],
)

# Talon: short and round, made larger than himself (1.12) to stand on Link's skeleton, and still 11 cm from his joints on
# average (the wrists 28: short arms): rough, the roughest of the townsfolk. Link's head carries his eyes. His cloth: the
# necklace, the sleeves, the trousers, the hair's tail. His voice is his own: he hums and snores when Link waits.
TALON = Character(
    mod="PlayAsTalon",
    who="Talon",
    label="Talon", group="Hyrule's people", seen=False, rough=True,
    model="Npc_Hylia_MU_Talon",
    k=1.12,
    moved={},
    held={"Eyeball_L": "Head", "Eyeball_R": "Head"},
    pack="Npc_Hylia_Talon_Adult",
    set="Phive/ControllerSetParam/Npc_Hylia_MU_Talon.phive__ControllerSetParam.bgyml",
    leash={
        "SimulMesh_Neckles": 1.0, "SimulMesh_Hair_Tail": 1.0,                                         # (30, 10)
        "SimulMesh_Sleeve": 2.0, "SimulMesh_Pants": 2.0,                                              # (3, 4)
    },
    voices=[("NV_Talon", "NV_Talon_", "")],
    rules=cries(
        TOWN, death=["Cry"], tired=["Tired", "BeWokenUp"], big_chest=["CorrectAnswer"], wait=["Sleep", "SadSleepTalk"]),
    other=["CallFar", "Notice", "Greeting"],
)

# Ingo as the ranch's master (the adult's model, in his finery): Link's size and rig (1.00, 4 cm from his joints). Link's
# head carries his eyes. His cloth: the ruff, the coat's tail and flap, the cuffs, the trousers, the hair and moustache.
# His voice is his own: his screams, his panic, his guffaw.
INGO = Character(
    mod="PlayAsIngo",
    who="Ingo",
    label="Ingo", group="Hyrule's people", seen=False,
    model="Npc_Hylia_MU_Ingo_Adult",
    k=1.0,
    moved={},
    held={"Eyeball_L": "Head", "Eyeball_R": "Head"},
    pack="Npc_Hylia_Ingo_002_Adult",
    set="Phive/ControllerSetParam/Npc_Hylia_MU_Ingo_Adult.phive__ControllerSetParam.bgyml",
    leash={
        "SimulMesh_Ruff": 1.0, "SimulMesh_Flap": 1.0, "SimulMesh_Tail": 1.0,                          # (24, 13, 10)
        "SimulMesh_Ruff_Arm": 2.0, "SimulMesh_Pants": 2.0,                                            # (3, 8)
        "SimulMesh_Hair_Su": 1.0, "SimulMesh_Hair_F": 1.0, "SimulMesh_Hair_Ff": 1.0, "SimulMesh_Hair_Beard": 1.0,   # (5)
    },
    voices=[("NV_Ingo", "NV_Ingo_", "")],
    rules=cries(
        TOWN, death=["Cry", "IngoPainfulD"], scream=["IngoScream", "IngoPanic"], hurt_big=["IngoPainfulD"],
        push=["IngoMortifying"], big_swing=["IngoRace"], jump_attack=["IngoRaceStart"], big_chest=["IngoGuffaw", "LaughA"],
        block=["IngoClickingTongue"]),
    other=["Notice", "GreetingA"],
)

# The Cucco Lady of Kakariko: a townswoman of the Bombchu Bowling lady's size and rig (0.97, 4 cm from Link's joints), and
# of her voice (the archive holds the Cucco Lady's own lines: her calls, her sighs). Link's head carries her eyes; her
# shoes' metal parts stay rigid on the ankles, shifted. Her cloth: the hair (back, side, front), the skirt.
CUCCO_LADY = Character(
    mod="PlayAsCuccoLady",
    who="the Cucco Lady",
    label="Cucco Lady", group="Hyrule's people", seen=False,
    model="Npc_Hylia_WN_001",
    k=0.97,
    moved={},
    held={"Eyeball_L": "Head", "Eyeball_R": "Head", "Ankle_L": "Ankle_L", "Ankle_R": "Ankle_R"},
    pack="Npc_Hylia_049_Adult",
    set="Phive/ControllerSetParam/Npc_Hylia_WN_001.phive__ControllerSetParam.bgyml",
    leash={
        "SimulationMesh_BackHair": 1.0, "SimulationMesh_SidetHair": 1.0, "SimulationMesh_FrontHair": 1.0,   # (9, 8, 5)
        "SimulationMesh_Hair_RS": 1.0, "SimulationMesh_Skirt": 1.0,                                   # (6, 17)
    },
    voices=[("NV_Hylia_Woman_Spry", "NV_Hylia_Woman_Spry_", "")],
    rules=cries(
        TOWN, tired=["CuccoWoman_Sigh"], big_chest=["CuccoWoman_Clear"], swing=["CuccoWoman_CallOut"],
        shoot=["CuccoWoman_CallOut"]),
    other=["CallOut", "Notice"],
)

# the window's headings, in its order, and what each says of its characters
GROUPS = [
    ("Legends", "The story's own: sages, royalty, villains."),
    ("Hyrule's people", "Townsfolk, ranchers, shopkeepers."),
    ("Monsters", "Not people's skeletons: the fit is rougher, and they have no faces to move."),
]

CHARACTERS = {
    "ganondorf": GANONDORF, "phantom": PHANTOM_GANON, "zelda": ZELDA, "sheik": SHEIK, "impa": IMPA, "nabooru": NABOORU,
    "ruto": RUTO, "rauru": RAURU, "greatfairy": GREAT_FAIRY,
    "malon": MALON, "talon": TALON, "ingo": INGO, "bombchu": BOMBCHU_LADY, "cucco": CUCCO_LADY, "pooch": POOCH_LADY,
    "mask": MASK_SALESMAN, "runningman": RUNNING_MAN, "shiro": SHIRO, "poe": POE_COLLECTOR, "soldier": SOLDIER,
    "lizalfos": LIZALFOS, "dinolfos": DINOLFOS, "wolfos": WOLFOS, "stalfos": STALFOS, "stalchild": STALCHILD,
    "redead": REDEAD,
}
