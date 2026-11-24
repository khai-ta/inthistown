"""Build and render a shot with Blender's embedded Python."""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from episode import MARKET_ACTIONS, read_episode
from fetch_avatar import TARGET as AVATAR_FILE


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = mat.diffuse_color
    shader.inputs["Roughness"].default_value = .68
    return mat


def box(name, pos, size, mat, bevel=0.04):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new("Rounded edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        obj.modifiers.new("Flat faces", "WEIGHTED_NORMAL")
    return obj


def group(name, pos):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = pos
    return obj


def piece(parent, name, pos, size, mat, bevel=0.04):
    obj = box(name, pos, size, mat, bevel)
    obj.parent = parent
    obj.location = pos
    return obj


def keys(obj, prop, values):
    for frame, value in values:
        setattr(obj, prop, value)
        obj.keyframe_insert(data_path=prop, frame=frame)


def face_stroke(parent, name, points, radius, mat):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = radius
    data.bevel_resolution = 3
    path = data.splines.new("POLY")
    path.points.add(len(points)-1)
    for control, (x, z) in zip(path.points, points):
        control.co = (x, -.268, z, 1)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    data.materials.append(mat)
    return obj


def expressive_face(face, costume):
    eyes = [obj for obj in face.children if obj.name.startswith("Eye")]
    brows = [obj for obj in face.children if obj.name.startswith("Brow")]
    for obj in face.children:
        if obj.name.startswith(("Mouth", "Smile", "Mustache")) and costume != "mayor":
            obj.hide_render = True
    for eye in eyes:
        eye.scale.z = 1.25
    smile = face_stroke(face, "Happy smile", [(-.112,1.945),(-.064,1.902),(0,1.886),
                                           (.064,1.902),(.112,1.945)], .012, ink)
    frown = face_stroke(face, "Worried mouth", [(-.103,1.885),(-.053,1.912),(0,1.925),
                                             (.053,1.912),(.103,1.885)], .012, ink)
    open_mouth = piece(face, "Surprised mouth", (0,-.264,1.907), (.119,.025,.124), ink, .044)
    tooth = piece(face, "Top teeth", (0,-.279,1.944), (.071,.010,.019), cream, .006)
    lead_moods = {
        "market_street": ("smile","smile"),
        "market_win": ("smile","open"),
        "market_ticket": ("smile","open"),
        "market_friend": ("worried","worried"),
        "market_mayor": ("smile","worried") if costume == "mayor" else ("worried","open"),
        "market_count": ("smile","worried"),
        "market_trade": ("worried","open"),
        "market_blackout": ("worried","open") if costume != "jules" else ("worried","worried"),
        "market_hook": ("worried","smile"),
        "market_end": ("smile","worried"),
    }
    first, last = lead_moods[shot["action"]]
    if costume and costume.startswith("crowd"):
        first = "smile"
        last = "open" if shot["action"] in {"market_win","market_hook"} else "smile"
    reaction = max(3, int(frames * .46))
    for label, objects in (("smile",(smile,)),("worried",(frown,)),("open",(open_mouth,tooth))):
        for obj in objects:
            for f, mood in ((1,first),(reaction-1,first),(reaction,last),(frames,last)):
                obj.hide_render = label != mood
                obj.keyframe_insert(data_path="hide_render", frame=f)
    for brow in brows:
        side = -1 if brow.location.x < 0 else 1
        keys(brow, "rotation_euler", [(1,(0,side*(.24 if first=="worried" else .07),0)),
             (reaction-1,(0,side*(.24 if first=="worried" else .07),0)),
             (reaction,(0,side*(.31 if last=="worried" else -.13),0)),
             (frames,(0,side*(.31 if last=="worried" else -.13),0))])
        z = brow.location.z
        keys(brow, "location", [(1,(brow.location.x,brow.location.y,z)),
                               (reaction,(brow.location.x,brow.location.y,z+(.033 if last=="open" else .008)))])
    blink = max(3, int(frames*.25))
    for eye in eyes:
        end_height = 1.46 if last == "open" else 1.16
        keys(eye, "scale", [(1,(1,1,1.16)),(blink-2,(1,1,1.16)),(blink,(1,1,.12)),
                          (blink+2,(1,1,1.16)),(reaction,(1,1,end_height)),(frames,(1,1,end_height))])


def roblox_actor(name, pos, shirt, hair, yaw, adult, costume=None):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(AVATAR_FILE), use_anim=False)
    imported = set(bpy.data.objects) - before
    armature = next(obj for obj in imported if obj.type == "ARMATURE")
    meshes = [obj for obj in imported if obj.type == "MESH" and obj.name.split(".")[0].endswith("_Geo")]
    bpy.context.view_layer.update()
    foot = min((obj.matrix_world @ Vector(corner)).z for obj in meshes for corner in obj.bound_box)
    top = max((obj.matrix_world @ Vector(corner)).z for obj in meshes for corner in obj.bound_box)
    size = 2.2 / (top - foot)
    for obj in imported - set(meshes) - {armature}:
        bpy.data.objects.remove(obj, do_unlink=True)
    skin = peach
    pants = denim
    shoe = ink
    if costume and costume.startswith("crowd"):
        skin = material(name + " skin", (.48,.24,.11) if costume=="crowd_bun" else (.77,.47,.28))
    if costume == "jules":
        skin = material("Jules skin", (.51, .255, .14))
        pants = material("Jules overalls", (.035, .22, .20))
        shoe = cream
    elif costume == "mayor":
        skin = material("Mayor skin", (.68, .39, .24))
        pants = shirt
    for mesh in meshes:
        body = mesh.name.split(".")[0]
        color = skin if body == "Head_Geo" else shirt
        if "Leg" in body:
            color = pants
        elif "Foot" in body:
            color = shoe
        elif "Hand" in body:
            color = skin
        mesh.data.materials.clear()
        mesh.data.materials.append(color)
    rig = group(name, pos)
    rig.rotation_euler.z = yaw
    armature.parent = rig
    armature.scale *= size
    armature.location.z = -foot * size
    head = armature.pose.bones["Head"]
    arms = [armature.pose.bones[side + "UpperArm"] for side in ("Right", "Left")]
    legs = [armature.pose.bones[side + "UpperLeg"] for side in ("Right", "Left")]
    for bone in [head, *arms, *legs]:
        bone.rotation_mode = "XYZ"
    face = group("Face details", (0, 0, 0))
    face.parent = rig
    for x in (-.089, .089):
        eye = (.047, .018, .078) if costume == "jules" else (.038, .018, .054)
        piece(face, "Eye", (x, -.260, 2.011), eye, ink, .008)
        brow = piece(face, "Brow", (x, -.251, 2.073), (.082, .018, .019), hair, .006)
        if costume == "mayor":
            brow.rotation_euler.y = .21 if x > 0 else -.21
    if costume == "jules":
        piece(face, "Smile", (0, -.252, 1.906), (.14, .024, .042), ink, .018)
        piece(face, "Smile highlight", (0, -.267, 1.917), (.091, .008, .010), cream, .004)
        for side in (-1, 1):
            piece(face, "Round curls", (side*.26, -.012, 2.025), (.18, .46, .28), hair, .071)
            piece(face, "Puff", (side*.19, .03, 2.19), (.29, .42, .18), hair, .064)
            piece(face, "Star earring", (side*.252, -.095, 1.929), (.052, .072, .077), yellow, .015)
    elif costume == "mayor":
        piece(face, "Mustache", (0, -.269, 1.943), (.188, .03, .038), hair, .010)
        brim = piece(face, "Fedora brim", (0, .01, 2.17), (.69, .56, .055), ink, .022)
        brim.rotation_euler.y = -.08
        piece(face, "Fedora crown", (0, .02, 2.26), (.46, .39, .16), ink, .045)
        piece(face, "Fedora band", (0, .02, 2.214), (.47, .40, .051), yellow, .026)
    else:
        piece(face, "Mouth", (0, -.253, 1.904), (.105, .025, .027), ink, .008)
        cap = piece(face, "Hair", (0, .035, 2.15), (.51, .48, .125), hair)
        if adult:
            piece(face, "Bob", (0, .19, 1.97), (.53, .20, .40), hair, .06)
        else:
            cap.rotation_euler.y = -.13
            piece(face, "Fringe", (-.13, -.177, 2.105), (.25, .11, .145), hair)
    if costume == "milo":
        accent = material("Milo saffron", (.96, .38, .054))
        piece(face, "Knit beanie", (0, .006, 2.24), (.55, .50, .18), accent, .073)
        piece(face, "Beanie cuff", (0, -.01, 2.16), (.56, .49, .07), denim, .026)
        piece(face, "Pom", (.012, .018, 2.37), (.13, .13, .13), accent, .061)
        chest = piece(rig, "Varsity flash", (0, -.222, 1.325), (.095, .022, .245), accent, .014)
        chest.rotation_euler.y = -.48
    elif costume == "jules":
        teal_strap = material("Jules straps", (.03, .35, .27))
        for side in (-1, 1):
            piece(rig, "Overalls strap", (side*.15, -.215, 1.35), (.09, .035, .44), teal_strap, .010)
            piece(rig, "Strap clasp", (side*.15, -.237, 1.235), (.079, .025, .054), yellow, .008)
        piece(rig, "Overalls bib", (0, -.216, 1.11), (.48, .04, .23), teal_strap, .021)
    elif costume == "mayor":
        piece(rig, "White shirtfront", (0, -.221, 1.35), (.24, .025, .44), cream, .007)
        piece(rig, "Mayor tie", (0, -.238, 1.335), (.074, .022, .29), coral, .009)
        for side in (-1, 1):
            lapel = piece(rig, "Lapel", (side*.134, -.239, 1.43), (.088, .026, .27), shirt, .007)
            lapel.rotation_euler.y = side*.24
    if costume and costume.startswith("crowd"):
        accent = material(name + " accessory", (.35,.64,.74) if costume=="crowd_cap" else (.79,.34,.18))
        if costume == "crowd_cap":
            piece(face,"Cap dome",(0,.01,2.19),(.50,.49,.15),accent,.065)
            piece(face,"Cap bill",(0,-.28,2.153),(.39,.25,.055),accent,.023)
        elif costume == "crowd_glasses":
            for side in (-1,1):
                frame_obj=piece(face,"Glasses frame",(side*.105,-.278,2.014),(.174,.025,.092),ink,.017)
                frame_obj.display_type="WIRE"
                piece(face,"Glasses lens",(side*.105,-.294,2.014),(.127,.013,.057),accent,.012)
        else:
            piece(face,"High bun",(0,.17,2.28),(.25,.24,.22),hair,.083)
            piece(rig,"Crossbody strap",(0,-.224,1.32),(.08,.031,.61),accent,.012).rotation_euler.y = -.44
    if shot["action"] in MARKET_ACTIONS:
        expressive_face(face, costume)
    bpy.context.view_layer.update()
    world = face.matrix_world.copy()
    face.parent = armature
    face.parent_type = "BONE"
    face.parent_bone = head.name
    face.matrix_world = world
    if costume == "jules":
        rig.scale = (.84, .88, .91)
    elif costume == "mayor":
        rig.scale = (1.13, 1.0, 1.10)
    return rig, head, arms, legs


def actor(name, pos, shirt, hair, skin, yaw=0, adult=False):
    if avatar == "roblox-r15":
        return roblox_actor(name, pos, shirt, hair, yaw, adult)
    rig = group(name, pos)
    rig.rotation_euler.z = yaw
    piece(rig, "Sweatshirt", (0, 0, 1.27), (.69, .43, .68), shirt, .07)
    piece(rig, "Ribbed hem", (0, -.018, .967), (.63, .438, .10), shirt, .025)
    piece(rig, "Collar", (0, -.035, 1.58), (.39, .39, .09), cream, .035)
    if adult:
        for height in (1.20, 1.34, 1.47):
            piece(rig, "Cardigan button", (0, -.229, height), (.047, .025, .043), cream, .009)
    else:
        piece(rig, "Kangaroo pocket", (0, -.216, 1.13), (.42, .058, .18), shirt, .04)
        for side in (-1, 1):
            piece(rig, "Drawstring", (side * .085, -.226, 1.454), (.017, .023, .15), cream, .005)
        piece(rig, "Folded hood", (0, .199, 1.52), (.51, .20, .28), shirt, .068)
    head = group("Head", (0, 0, 1.91))
    head.parent = rig
    piece(head, "Head", (0, 0, 0), (.61, .55, .58), skin, .09)
    piece(head, "Hair", (0, .01, .255), (.65, .57, .18), hair, .06)
    fringe = piece(head, "Fringe", (-.14, -.27, .17), (.34, .087, .132), hair)
    fringe.rotation_euler.y = -.15
    if adult:
        piece(head, "Bob", (0, .16, .01), (.64, .36, .50), hair, .085)
        for side in (-1, 1):
            piece(head, "Hair side", (side*.268, .035, -.045), (.12, .37, .38), hair, .042)
            piece(head, "Earring", (side*.275, -.106, -.147), (.057, .045, .070), amber, .022)
    else:
        for x, height in ((-.14, .305), (.012, .316), (.15, .299)):
            piece(head, "Swept hair", (x, -.053, height), (.20, .39, .10), hair, .041)
    legs = []
    for side in (-1, 1):
        piece(head, "Eye", (side*.124, -.276, .015), (.054, .033, .078), ink)
        piece(head, "Eyebrow", (side*.124, -.278, .112), (.096, .028, .027), hair, .008)
        piece(head, "Cheek", (side*.193, -.274, -.08), (.075, .028, .034), blush, .012)
        leg = group("Hip", (side*.185, 0, .93))
        leg.parent = rig
        piece(leg, "Jeans", (0, 0, -.39), (.32, .36, .65), denim)
        piece(leg, "Sneaker", (0, -.066, -.797), (.34, .48, .24), cream)
        piece(leg, "Sole", (0, -.072, -.887), (.351, .493, .061), ink, .024)
        piece(leg, "Laces", (0, -.181, -.675), (.18, .15, .028), cream, .01)
        legs.append(leg)
    piece(head, "Nose", (0, -.274, -.045), (.083, .059, .070), skin, .023)
    piece(head, "Mouth", (0, -.277, -.12), (.13, .03, .035), ink, .01)
    arms = []
    for side in (-1, 1):
        arm = group("Shoulder", (side*.454, 0, 1.51))
        arm.parent = rig
        piece(arm, "Sleeve", (0, 0, -.183), (.22, .37, .44), shirt)
        piece(arm, "Hand", (0, 0, -.447), (.207, .31, .16), skin)
        arms.append(arm)
    return rig, head, arms, legs


def camera(start, finish, target, lens, frames):
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    scene.camera = cam
    cam.data.lens = lens
    cam.data.sensor_fit = "HORIZONTAL"
    for frame, pos in ((1, start), (frames, finish)):
        cam.location = pos
        cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.keyframe_insert(data_path="location", frame=frame)
        cam.keyframe_insert(data_path="rotation_euler", frame=frame)
    if not shorts_style:
        return
    inserts = {
        "town": ((-.24, -2.7, 2.01), (.05, -.87, 1.89), 40, .50),
        "knock": ((.99, -.91, 2.18), (1.72, .78, 2.15), 47, .67),
        "lie": ((-.02, -1.68, 2.02), (-1.13, .15, 1.77), 48, .46),
        "appear": ((-.28, -.64, 1.95), (.05, 2.43, 1.56), 53, .54),
        "twist": ((1.12, -1.86, 2.19), (1.21, .78, 2.12), 53, .68),
        "escape": ((.56, -4.15, 1.55), (-.11, -1.62, 1.31), 38, .58),
        "dusk": ((-2.10, -2.40, 2.15), (-.51, -.42, 1.86), 47, .44),
        "streetdoor": ((.04, -3.44, 2.0), (0, .6, 1.52), 41, .68),
    }
    if shot["action"] not in inserts:
        return
    close_pos, close_target, close_lens, cut = inserts[shot["action"]]
    frame = max(3, int(frames * cut))
    scene.frame_set(frame - 1)
    cam.keyframe_insert(data_path="location", frame=frame-1)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame-1)
    cam.data.keyframe_insert(data_path="lens", frame=frame-1)
    for f in (frame, frames):
        cam.location = close_pos
        cam.rotation_euler = (Vector(close_target) - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = close_lens
        cam.keyframe_insert(data_path="location", frame=f)
        cam.keyframe_insert(data_path="rotation_euler", frame=f)
        cam.data.keyframe_insert(data_path="lens", frame=f)
    scene.frame_set(1)


def light(kind, pos, power, color, target, size):
    bpy.ops.object.light_add(type=kind, location=pos)
    obj = bpy.context.object
    obj.data.energy = power
    obj.data.color = color
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    if kind == "AREA":
        obj.data.shape = "DISK"
        obj.data.size = size


def clock(name, pos, scale):
    prop = group(name, pos)
    piece(prop, "Clock rim", (0, 0, 0), (.58, .13, .58), ink, .07)
    piece(prop, "Clock face", (0, -.074, 0), (.45, .036, .45), cream)
    piece(prop, "Hour hand", (.066, -.10, .015), (.146, .025, .032), ink, .008)
    hand = group("Clock hand pivot", (0, -.10, 0))
    hand.parent = prop
    piece(hand, "Minute hand", (0, 0, .082), (.027, .025, .19), red, .008)
    prop.scale = (scale,) * 3
    return prop



def cat(pos, frames):
    rig = group("Cat", pos)
    fur = material("Ginger fur", (.61, .22, .065))
    piece(rig, "Body", (0, 0, .18), (.27, .49, .28), fur, .05)
    head = group("Cat head", (0, -.22, .31))
    head.parent = rig
    piece(head, "Face", (0, 0, 0), (.29, .24, .24), fur, .048)
    for side in (-1, 1):
        ear = piece(head, "Ear", (side * .095, 0, .132), (.082, .09, .13), fur, .022)
        ear.rotation_euler.y = side * .25
        piece(head, "Eye", (side * .064, -.119, .015), (.032, .022, .032), ink, .005)
        for y in (-.16, .16):
            piece(rig, "Paw", (side * .09, y, .043), (.09, .14, .088), cream, .018)
    piece(head, "Nose", (0, -.119, -.036), (.043, .025, .027), blush, .008)
    tail = piece(rig, "Tail", (0, .29, .26), (.08, .09, .29), fur, .025)
    tail.rotation_euler.x = -.42
    keys(head, "rotation_euler", [(1, (0, 0, -.35)), (frames // 2, (.19, 0, .35)),
                                  (frames, (0, 0, .12))])


def town(frames, action):
    grass = material("Grass", (.22, .56, .22))
    asphalt = material("Asphalt", (.087, .12, .16))
    roof = material("Terracotta", (.37, .089, .055))
    leaf = material("Leaves", (.045, .34, .17))
    glass = material("Blue windows", (.16, .47, .72))
    box("Ground", (0, 0, -.14), (75, 75, .2), grass)
    box("Street", (0, 0, -.025), (5, 59, .14), asphalt)
    for side in (-1, 1):
        box("Sidewalk", (side*3.2, 0, .04), (1.25, 59, .2), cream)
    for y in range(-16, 21, 4):
        box("Road stripe", (0, y, .052), (.14, 1.6, .013), yellow, .005)
    for index, y in enumerate(range(-2, 22, 5)):
        for side in (-1, 1):
            x = side*(5.5 + .4*(index % 2))
            walls = (coral, cream, teal)[(index + side) % 3]
            box("House", (x, y, 1.23), (3.1, 3.6, 2.46), walls)
            for tilt in (-1, 1):
                slab = box("Pitched roof", (x, y+tilt*.94, 2.79), (3.51, 2.1, .18), roof)
                slab.rotation_euler.x = -tilt*.40
            facade = x-side*1.56
            box("Front door", (facade, y, .74), (.09, .68, 1.48), ink)
            for offset in (-1.04, 1.04):
                box("Window frame", (facade, y+offset, 1.46), (.14, .78, .72), cream)
                box("Window", (facade-side*.07, y+offset, 1.46), (.08, .60, .54), glass)
            trunk_y = y+2.35
            box("Tree trunk", (side*4.1, trunk_y, .68), (.24, .24, 1.36), roof)
            box("Tree crown", (side*4.1, trunk_y, 1.62), (.9, .95, 1.08), leaf, .18)
    kid, _, arms, legs = actor("Narrator", (.05, -.3, .05), teal, brown, peach)
    keys(kid, "location", [(1, (.05, -.3, .05)), (frames, (.05, -1.1, .05))])
    casts = [(arms, legs)]
    if action in {"dusk", "streetdoor"}:
        twin, _, twin_arms, twin_legs = actor("Twin", (-.82, .21, .05), teal, brown, peach, -.18)
        casts.append((twin_arms, twin_legs))
        move_end = frames if action == "dusk" else frames // 2
        keys(twin, "location", [(1, (-.82, .21, .05)), (move_end, (-.72, -.76, .05))])
        keys(kid, "location", [(1, (.45, -.05, .05)), (move_end, (.55, -.9, .05))])
        sky.inputs["Color"].default_value = (.14, .28, .51, 1)
    if action == "streetdoor":
        street_portal = group("Door in the road", (0, .7, .045))
        for x in (-.72, .72):
            piece(street_portal, "Portal jamb", (x, 0, 1.24), (.12, .22, 2.48), amber)
        piece(street_portal, "Portal lintel", (0, 0, 2.45), (1.57, .23, .12), amber)
        door_leaf = group("Knocking door leaf", (0, -.045, 0))
        door_leaf.parent = street_portal
        piece(door_leaf, "Portal leaf", (0, 0, 1.22), (1.34, .18, 2.36), yellow)
        piece(door_leaf, "Knob", (.49, -.125, 1.21), (.13, .13, .13), ink)
        keys(street_portal, "location", [(1, (0, .7, -2.55)), (frames//4, (0, .7, -2.55)),
                                           (frames//2, (0, .7, .045)), (frames, (0, .7, .045))])
        knocks = [(1, (0, 0, 0))]
        for fraction in (.78, .86, .94):
            beat = int(frames * fraction)
            knocks.extend([(beat-1, (0, 0, 0)), (beat, (0, -.08, 0)), (beat+2, (0, 0, 0))])
        keys(door_leaf, "location", knocks)
        for character, direction in ((kid, 1), (twin, -1)):
            keys(character, "rotation_euler", [(1, (0, 0, 0)),
                 (frames//2, (0, 0, 0)), (2*frames//3, (0, 0, direction*2.46))])
    walk_end = frames if action != "streetdoor" else max(8, frames // 2)
    for cast_index, (cast_arms, cast_legs) in enumerate(casts):
        for limbs, amplitude in ((cast_arms, .29), (cast_legs, -.23)):
            for index, limb in enumerate(limbs):
                swing = (-1)**(index + cast_index) * amplitude
                values = [(frame, (angle, 0, 0)) for frame, angle in
                          ((1, swing), (walk_end//4, -swing), (walk_end//2, swing),
                           (3*walk_end//4, -swing), (walk_end, 0 if action == "streetdoor" else swing))]
                keys(limb, "rotation_euler", values)
    if shorts_style:
        sky.inputs["Color"].default_value = (.065, .13, .34, 1)
        light("SUN", (4, -5, 8), .85, (.62, .76, 1), (0, 0, 0), 0)
        glow = material("Lamp glass", (1.0, .71, .24))
        shader = glow.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Emission Color"].default_value = (1, .66, .18, 1)
        shader.inputs["Emission Strength"].default_value = 2.4
        pole = material("Street lamp pole", (.054, .069, .10))
        for x, y in ((-3.55, 1.9), (3.55, 7.4), (-3.55, 14.7)):
            box("Street lamp", (x, y, 1.75), (.105, .105, 3.5), pole)
            box("Lamp housing", (x, y, 3.46), (.43, .44, .22), pole)
            box("Lamp glass", (x, y, 3.34), (.34, .35, .06), glow)
            light("AREA", (x, y, 3.26), 110, (1, .73, .42), (x, y, 0), 1.1)
        light("AREA", (2.0, -3.4, 3.0), 160, (.77, .84, 1), (0, 0, 1.25), 3)
    else:
        light("SUN", (4, -5, 8), 2.0, (1, .88, .68), (0, 0, 0), 0)
    if action == "streetdoor":
        camera((2.4, -4.9, 2.8), (1.7, -4.1, 2.6), (0, .3, 1.22), 34, frames)
    elif action == "dusk":
        camera((-2.5, -5.7, 2.6), (-2.1, -4.6, 2.4), (0, -.2, 1.47), 37, frames)
    else:
        camera((2.6, -6.3, 2.65), (1.9, -5.6, 2.5), (0, .15, 1.45), 33, frames)


def brass_key(pos, angle):
    prop = group("Brass key", pos)
    prop.rotation_euler.z = angle
    bpy.ops.mesh.primitive_torus_add(major_segments=24, minor_segments=8,
                                     major_radius=.078, minor_radius=.018)
    ring = bpy.context.object
    ring.name = "Bow"
    ring.parent = prop
    ring.location = (0, 0, .023)
    ring.data.materials.append(yellow)
    piece(prop, "Key blade", (.135, 0, .026), (.16, .041, .038), amber, .008)
    piece(prop, "Key tooth", (.2, .026, .026), (.037, .069, .038), amber, .006)
    return prop


def hallway(action, frames):
    wood = material("Oak", (.33, .16, .078))
    wall = material("Mint plaster", (.37, .61, .55))
    opening = material("Doorway shadow", (.026, .033, .051))
    rug = material("Runner", (.36, .047, .073))
    box("Floor", (0, 0, -.11), (10, 12, .22), wood)
    box("Ceiling", (0, .45, 4.06), (6.4, 7.3, .13), cream)
    box("Pendant cable", (0, .95, 3.79), (.034, .034, .48), ink, .007)
    box("Pendant shade", (0, .95, 3.55), (.52, .49, .16), amber, .05)
    box("Pendant diffuser", (0, .95, 3.465), (.39, .35, .035), cream, .015)
    for i in range(-9, 10):
        box("Floorboard seam", (i*.52, 0, .003), (.016, 12, .009), brown, .002)
    box("Hall runner", (0, .2, .015), (2.2, 5.15, .035), rug)
    for side in (-1, 1):
        box("Side wall", (side*3.15, 1, 2), (.17, 7, 4), wall)
        box("Skirting", (side*3.03, 1, .15), (.09, 7, .22), cream)
    box("Back wall left", (-2.03, 2.65, 2), (2.06, .21, 4), wall)
    box("Back wall right", (2.03, 2.65, 2), (2.06, .21, 4), wall)
    box("Wall above door", (0, 2.65, 3.45), (2.02, .21, 1.1), wall)
    if action == "appear":
        cover = box("Wall before the door", (0, 2.65, 1.45), (2.04, .21, 2.93), wall)
        keys(cover, "scale", [(1, (1, 1, 1)), (frames//3, (.01, 1, 1))])
    box("Dark passage", (0, 3.85, 1.5), (2.9, .21, 3), opening)
    box("Console", (-2.25, 1.84, .86), (1.13, .52, .12), brown)
    for x in (-2.7, -1.8):
        box("Console leg", (x, 1.84, .4), (.11, .41, .8), brown)
    broken = clock("Broken clock", (-2.25, 1.76, .99), .65)
    broken.rotation_euler = (.9, .15, -.4)
    cat((-.48, .59, .026), frames)
    for x in (-2.1, 2.08):
        box("Picture frame", (x, 2.51, 2.76), (.57, .08, .65), cream)
        box("Picture", (x, 2.45, 2.76), (.42, .06, .49), coral if x < 0 else teal)
    kid, kid_head, kid_arms, kid_legs = actor("Narrator", (-1.13, .15, 0), teal, brown, peach, .36)
    mom, mom_head, mom_arms, _ = actor("Mom", (1.1, .78, 0), coral, ink, peach, -.38, adult=True)
    mom.scale = (1.1,)*3
    if action in {"open", "key"} and avatar == "roblox-r15":
        mom.location.x = 1.84
    if action == "knock" and shorts_style:
        mom.location.x = 1.72
    keys(kid_head, "rotation_euler", [(1, (0, 0, -.10)), (frames, (.11, 0, .37))])
    keys(mom_head, "rotation_euler", [(1, (.04, 0, 0)), (frames, (-.12, 0, -.28))])
    if action == "appear":
        keys(mom_arms[0], "rotation_euler", [(1, (0, 0, 0)), (frames//3, (-.6, -.12, .65)),
                                             (frames, (-.48, -.15, .56))])
    if action == "clock":
        brass_key((-2.10, 1.60, .946), -.3)
    if action in {"lie", "clock"}:
        box("Unbroken wall", (0, 2.65, 1.45), (2.04, .21, 2.93), wall)
        keys(kid_arms[0], "rotation_euler", [(1, (0, 0, 0)), (frames//2, (-.9, .2, -.25)), (frames, (-.15, 0, 0))])
    else:
        portal = group("Portal", (0, 2.49, .04))
        for x in (-.95, .95):
            piece(portal, "Door trim", (x, 0, 1.44), (.15, .25, 2.88), yellow)
        piece(portal, "Header", (0, 0, 2.9), (2.05, .25, .16), yellow)
        hinge = group("Door hinge", (-.9, -.06, 0))
        hinge.parent = portal
        piece(hinge, "Door", (.9, 0, 1.42), (1.81, .18, 2.83), yellow)
        for z in (.7, 1.97):
            piece(hinge, "Inset", (.9, -.104, z), (1.32, .046, .91), amber)
        piece(hinge, "Handle", (1.57, -.18, 1.35), (.18, .14, .13), ink)
        if action == "appear":
            keys(portal, "scale", [(1, (.03, .25, .03)), (max(2, frames//3), (1.07, 1, 1.07)), (max(3, frames//2), (1, 1, 1))])
        if action == "knock":
            impacts = [int(frames*f) for f in (.37, .53, .69)]
            jitter = [(1, (0, 0, 0))]
            for frame in impacts:
                jitter.extend([(frame-1, (0, 0, 0)), (frame, (0, 0, .034)), (frame+2, (0, 0, 0))])
            keys(hinge, "rotation_euler", jitter)
        if action in {"open", "twin", "key", "escape"} or (action == "twist" and avatar is None):
            angle = -1.9
            if action == "open":
                keys(hinge, "rotation_euler", [(1, (0, 0, 0)), (frames//3, (0, 0, angle)), (frames, (0, 0, angle))])
            else:
                hinge.rotation_euler.z = angle
            double, _, double_arms, double_legs = actor("Double", (.18, 3.03, .06), teal, brown, peach, -.13)
            prop = group("Hidden hammer", (.205, -.465, 1.39))
            prop.parent = double
            prop.rotation_euler.y = -.35
            piece(prop, "Handle", (0, 0, 0), (.073, .085, .50), brown, .013)
            piece(prop, "Steel head", (0, 0, .228), (.36, .132, .155), ink, .025)
            piece(prop, "Striking face", (.174, 0, .227), (.06, .153, .16), denim, .014)
            keys(double, "location", [(1, (.18, 3.03, .06)), (frames, (.18, 1.91, .06))])
            for arm in double_arms:
                arm.rotation_euler.x = -.8
            if action == "key":
                box("Lock plate", (.924, 2.331, 1.42), (.14, .042, .19), ink, .018)
                key_prop = brass_key((.758, 2.237, 1.43), .08)
                keys(key_prop, "rotation_euler", [(1, (1.05, 0, .08)),
                    (frames//2, (1.05, 0, .08)), (frames, (1.88, 0, .08))])
                keys(kid_arms[1], "rotation_euler", [(1, (0, 0, 0)), (frames//2, (-.85, 0, 0))])
            if action == "escape":
                keys(kid, "location", [(1, (-1.13, .15, 0)), (frames, (-.55, -2.4, 0))])
                keys(double, "location", [(1, (.18, 1.82, .06)), (frames, (.42, -1.94, .03))])
                for legs in (kid_legs, double_legs):
                    for side, leg in zip((-1, 1), legs):
                        keys(leg, "rotation_euler", [(1, (side*.24, 0, 0)),
                              (frames//3, (-side*.35, 0, 0)), (2*frames//3, (side*.35, 0, 0)),
                              (frames, (-side*.20, 0, 0))])
    for index, x in enumerate((-2.06, 2.06)):
        door = box("Hall closet", (x, 2.51, 1.05), (1.05, .105, 2.1), brown)
        inset = box("Closet panel", (x, 2.445, 1.33), (.79, .04, 1.35), wood)
        box("Closet knob", (x + .34, 2.397, 1.04), (.093, .09, .093), ink, .022)
        if action == "twist":
            start = int(frames * (.39 + index * .11))
            for obj, color in ((door, yellow), (inset, amber)):
                obj.data.materials[0] = obj.data.materials[0].copy()
                shader = obj.data.materials[0].node_tree.nodes.get("Principled BSDF")
                value = shader.inputs["Base Color"]
                value.keyframe_insert(data_path="default_value", frame=start)
                value.default_value = color.diffuse_color
                value.keyframe_insert(data_path="default_value", frame=start + 4)
            wobble = [(1, (0, 0, 0))]
            for fraction in (.69, .8, .87):
                beat = int(frames * fraction)
                wobble.extend([(beat-1, (0, 0, 0)), (beat, (-.027, 0, 0)), (beat+2, (0, 0, 0))])
            keys(door, "rotation_euler", wobble)
    light("AREA", (-2, -3, 3.65), 420, (1, .79, .63), (0, 1, 1), 5)
    light("AREA", (2, 1, 3.65), 265, (.63, .79, 1), (0, 1, 1), 4)
    light("AREA", (0, 3.65, 2.6), 90, (.72, .62, 1), (0, 1, 1), 1.5)
    shots = {
        "lie": ((-.05, -4, 1.94), (.19, -3.65, 1.87), (-.35, .64, 1.3), 32),
        "appear": ((2.14, -3.8, 2.16), (1.72, -3.35, 2), (.27, 1.9, 1.5), 37),
        "knock": ((.28, -.56, 1.81), (.19, .02, 1.74), (.22, 2.39, 1.53), 50),
        "open": ((.54, -.67, 1.86), (.63, -.35, 1.80), (.20, 2.31, 1.42), 44),
        "clock": ((-2.34, -.10, 2.07), (-2.17, .54, 1.75), (-2.17, 1.7, .92), 47),
        "twin": ((-.68, .03, 1.76), (-.43, .40, 1.88), (.12, 2.25, 1.67), 47),
        "key": ((1.27, .72, 1.70), (1.19, 1.00, 1.66), (.86, 2.27, 1.43), 53),
        "escape": ((1.61, -3.33, 2.24), (1.04, -4.48, 2.46), (0, -.09, 1.50), 33),
        "twist": ((.56, -2.95, 2.05), (.32, -5.14, 2.41), (0, 1.91, 1.62), 32),
    }
    camera(*shots[action], frames)


def market_lettering(label, pos, size, color, parent=None):
    bpy.ops.object.text_add()
    text = bpy.context.object
    text.name = label
    text.parent = parent
    text.location = pos
    text.rotation_euler.x = 1.5708
    text.data.body = label
    text.data.size = size
    text.data.align_x = "CENTER"
    text.data.align_y = "CENTER"
    text.data.extrude = .006
    text.data.materials.append(color)
    return text


def market_camera(frames, moves):
    """Each tuple marks a camera key. Adjacent keys at a cut skip interpolation."""
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.data.sensor_fit = "HORIZONTAL"
    scene.camera = cam
    previous = 0
    for t, pos, point, focal in moves:
        frame = max(previous + 1, round(1 + (frames - 1) * t))
        previous = frame
        cam.location = pos
        cam.rotation_euler = (Vector(point) - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = focal
        cam.data.keyframe_insert(data_path="lens", frame=frame)
        cam.keyframe_insert(data_path="location", frame=frame)
        cam.keyframe_insert(data_path="rotation_euler", frame=frame)


def market_actor(role, position, yaw=0):
    colors = {
        "milo": ((.24, .092, .42), brown, False, "milo"),
        "jules": ((.76, .14, .36), ink, False, "jules"),
        "mayor": ((.09, .36, .29), brown, True, "mayor"),
        "dad": ((.64, .20, .072), brown, True, None),
    }
    shade, hair, adult, costume = colors[role]
    return roblox_actor(role.title(), position, material(role, shade), hair, yaw, adult, costume)


def market_character_motion(character, frames, poses):
    rig, head, arms, legs = character
    # Rotations are in the official R15 joints' local space.
    for index, arm in enumerate(arms):
        elbow = next(bone for bone in arm.children if bone.name.endswith("LowerArm"))
        elbow.rotation_mode = "XYZ"
        keys(arm, "rotation_euler", [(max(1, round(n*frames)), (s[index], .07*(-1)**index, 0))
                                      for n, _, s, _, _ in poses])
        keys(elbow, "rotation_euler", [(max(1, round(n*frames)), (e[index], 0, 0))
                                        for n, _, _, e, _ in poses])
    base_yaw = rig.rotation_euler.z
    keys(rig, "location", [(max(1, round(n*frames)), pos) for n, pos, _, _, _ in poses])
    keys(rig, "rotation_euler", [(max(1, round(n*frames)), (0, 0, base_yaw + yaw))
                                  for n, _, _, _, yaw in poses])
    keys(head, "rotation_euler", [(max(1, round(n*frames)), (.12 if any(a < -.4 for a in arms_pose) else -.05, 0, .1*yaw))
                                  for n, _, arms_pose, _, yaw in poses])
    for side, hip in zip((-1, 1), legs):
        knee = next(bone for bone in hip.children if bone.name.endswith("LowerLeg"))
        knee.rotation_mode = "XYZ"
        stride = .22 if (Vector(poses[0][1])-Vector(poses[-1][1])).length > .55 else .055
        sequence = [(1, 0), (frames//5, stride), (2*frames//5, -stride),
                    (3*frames//5, stride), (4*frames//5, -stride), (frames, 0)]
        keys(hip, "rotation_euler", [(frame, (side*step, 0, 0)) for frame, step in sequence])
        keys(knee, "rotation_euler", [(frame, (max(0, -side*step*.8), 0, 0)) for frame, step in sequence])


def market_phone(pos, navy, glow, title, detail):
    prop = group("Phone", pos)
    piece(prop, "Case", (0, 0, 0), (.64, .12, .95), navy, .07)
    piece(prop, "Display", (0, -.067, 0), (.56, .02, .85), glow, .03)
    market_lettering(title, (0, -.088, .14), .105, cream, prop)
    market_lettering(detail, (0, -.088, -.13), .19, yellow, prop)
    return prop


def market_school(frames, m):
    box("Grass", (0, 1, -.16), (20, 17, .30), m["grass"])
    box("Walkway", (0, -.58, .004), (3.0, 9.4, .03), m["concrete"])
    box("School", (0, 3.2, 2.3), (9.4, 2.7, 4.6), m["brick"])
    box("Entry", (0, 1.80, 1.20), (1.8, .12, 2.39), m["navy"])
    box("Canopy", (0, 1.46, 2.57), (2.68, .91, .18), cream)
    for x in (-3.3, -2.2, 2.2, 3.3):
        for z in (1.48, 3.0):
            box("Classroom window", (x, 1.8, z), (.81, .10, .83), m["glass"])
    market_lettering("SCHOOL", (0, 1.78, 3.38), .42, cream)
    board = group("Snow day sign", (1.88, -.64, 1.07))
    piece(board, "Stake", (0, 0, -.47), (.12, .14, 1.2), brown)
    piece(board, "Sign", (0, 0, .21), (1.44, .14, .89), m["navy"])
    market_lettering("SNOW DAY?", (0,-.083,.39), .16, cream, board)
    market_lettering("12% YES", (0,-.083,.11), .21, m["mint"], board)
    milo = market_actor("milo", (-1.82, -.06, 0), .22)
    market_character_motion(milo, frames, [
        (0, (-1.82,-.06,0), (0,0), (0,0), 0),
        (.41, (-.84,-.55,0), (-.47,0), (.26,0), .23),
        (.68, (-.38,-.68,0), (0,-.59), (0,.30), .51),
        (1, (-.29,-.74,0), (0,-.24), (0,.20), .26),
    ])
    for i in range(14):
        dot = box("Snow flurry", ((i*13%37)/7-2.4, .6+(i%3)*.35, 2.4), (.034, .035, .043), cream, .006)
        keys(dot, "location", [(1, dot.location.copy()), (frames, (dot.location.x+.2, dot.location.y, .05+i*.15))])
    market_camera(frames, [(0,(-.52,-12.6,8.35),(0,-.26,1.2),33),
                            (.42,(-3.43,-6.5,3.65),(0,.7,1.26),37),
                            (.43,(3.65,-4.80,2.0),(1.18,-.28,1.20),44),
                            (1,(3.15,-3.73,1.82),(1.2,-.32,1.20),48)])


def market_fountain(frames, m):
    box("Park pavers", (0, .6, -.14), (16, 15, .27), m["concrete"])
    for x in (-4.1,-2.8,2.95,4.15):
        box("Tree trunks", (x,2.8,.88), (.25,.25,1.76), brown)
        box("Tree canopy", (x,2.8,2.07), (1.35,1.25,1.42), m["grass"], .20)
    fountain = group("Fountain", (0,.84,0))
    basin_material = material("Fountain changes to gold", (.16,.43,.58))
    color = basin_material.node_tree.nodes.get("Principled BSDF").inputs["Base Color"]
    impact = max(2, int(frames*.31))
    color.keyframe_insert(data_path="default_value", frame=impact-3)
    color.default_value = yellow.diffuse_color
    color.keyframe_insert(data_path="default_value", frame=impact+3)
    for z, radius, depth in ((.15,1.26,.27),(.48,.41,.45),(.79,.84,.16)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=radius, depth=depth)
        cylinder = bpy.context.object
        cylinder.parent = fountain
        cylinder.location = (0,0,z)
        cylinder.data.materials.append(basin_material)
    for index in range(9):
        angle = index * 2.399
        x, y = math.cos(angle), math.sin(angle)
        water = piece(fountain, "Water spray", (x*.27,y*.27,1.25),
                      (.037,.04,.32), m["glass"], .014)
        water.rotation_euler = (y*.49,-x*.49,0)
        keys(water,"scale",[(1,(.45,)*3),(impact-3,(1,)*3),(impact,(.001,)*3)])
        keys(water,"location",[(1,(x*.22,y*.22,1.03)),(impact-3,(x*.43,y*.43,1.51))])
    for i in range(22):
        angle = i*2.399
        x,y = math.cos(angle), math.sin(angle)
        coin = piece(fountain, "Gold coin", (0,0,.84), (.11,.04,.11), yellow, .033)
        launch = impact + i%5
        keys(coin,"scale",[(1,(.001,)*3),(launch-1,(.001,)*3),(launch,(1,)*3)])
        keys(coin,"location",[(launch,(0,0,.84)),(int(frames*.64),(x*1.18,y*.75,2.8+(i%6)*.08)),
                              (frames,(x*2.0,y*1.5,.19 + (i%3)*.22))])
        keys(coin,"rotation_euler",[(launch,(0,0,0)),(frames,(i*.7,5.8,i*.41))])
    jules = market_actor("jules", (-1.82,-.05,0), -.12)
    market_character_motion(jules,frames,[(0,(-1.82,-.05,0),(0,0),(0,0),.05),
        (.34,(-1.76,-.06,0),(-.62,-.76),(.26,.35),-.14),
        (.69,(-1.55,-.27,.12),(-.88,-.9),(.45,.4),.11),
        (1,(-1.62,-.32,0),(-.38,-.4),(.23,.13),0)])
    market_camera(frames,[(0,(3.9,-4.2,2.5),(-.25,.5,1.14),34),(.30,(2.77,-3.57,2.2),(-.25,.61,1.17),38),
                          (.31,(.78,-1.18,1.64),(.1,.82,.91),42),(.58,(.62,-1.5,2.13),(.22,.65,1.3),37),
                          (.59,(-3.6,-3.8,2.52),(-.71,.42,1.37),33),(1,(-3.15,-3.08,2.25),(-.84,.23,1.35),35)])


def market_room(m, floor, wall):
    box("Interior floor", (0, .34, -.14), (12, 12, .27), floor)
    box("Back wall", (0, 2.53, 2.22), (11, .20, 4.5), wall)
    box("Side wall", (-4.4, .35, 2.22), (.19, 4.5, 4.5), wall)
    box("Back trim", (0, 2.41, .12), (10.8, .11, .22), cream)


def market_bedroom(frames,m):
    market_room(m,brown,m["violet"])
    box("Rug", (-.9,-.11,.012),(3.2,3.42,.04),m["pink"])
    box("Bed frame", (-2.02,1.18,.34),(1.78,2.25,.63),m["navy"])
    box("Mattress", (-2.02,1.18,.69),(1.70,2.15,.28),cream)
    box("Quilt", (-2.02,.95,.85),(1.69,1.60,.12),m["glass"])
    box("Pillow", (-2.02,1.96,.88),(1.19,.44,.17),cream)
    box("Window", (.87,2.405,2.42),(1.66,.12,1.29),m["navy"])
    box("Window pane", (.87,2.33,2.43),(1.47,.038,1.1),m["glass"])
    box("Bedside table", (.1,.87,.44),(1.08,.76,.87),brown)
    phone = market_phone((.1,.78,1.24),m["navy"],m["violet"],"MILO: VANISH?","99% YES")
    keys(phone,"rotation_euler",[(1,(.88,0,0)),(frames//3,(.51,0,.06)),(frames,(.51,0,.04))])
    milo = market_actor("milo", (-1.03,-.11,0),.19)
    market_character_motion(milo,frames,[(0,(-1.03,-.11,0),(0,0),(0,0),0),(.55,(-.96,.13,0),(0,-.7),(0,.38),.29),
                                        (1,(-1.02,.16,0),(-.34,-.4),(.27,.2),-.12)])
    market_camera(frames,[(0,(-3.55,-4.65,2.9),(-.81,.62,1.13),33),(.42,(-2.55,-3.71,2.46),(-.55,.63,1.16),36),
                            (.43,(.82,-.93,2.32),(.1,.78,1.22),47),(1,(.69,-.50,2.12),(.1,.78,1.24),50)])


def market_diner(frames,m):
    market_room(m,m["concrete"],m["brick"])
    for x in range(-4,5):
        for y in range(-3,3):
            if (x+y)%2:
                box("Checker tile",(x,y,.006),(.98,.98,.013),m["navy"],0)
    for x in (-2.85,1.98):
        box("Booth seat",(x,1.33,.54),(1.69,.83,.34),m["pink"])
        box("Booth back",(x,1.75,1.05),(1.69,.24,1.23),m["pink"])
    box("Diner table",(0,.4,1.06),(1.70,1.02,.16),cream)
    box("Pedestal",(0,.40,.52),(.38,.44,1.0),m["concrete"])
    market_lettering("DINER", (0,2.38,2.8),.5,cream)
    phone = market_phone((.42,.13,1.45),m["navy"],m["violet"],"MILO","99%")
    keys(phone,"location",[(1,(.42,.13,1.45)),(int(frames*.42),(-.12,.14,1.55)),
                          (int(frames*.62),(-.37,.15,1.25)),(frames,(-.37,.15,1.25))])
    keys(phone,"rotation_euler",[(1,(.20,0,0)),(int(frames*.52),(1.18,0,-.24)),
                                (int(frames*.63),(-1.57,0,.21)),(frames,(-1.57,0,.21))])
    jules = market_actor("jules",(-1.36,.40,0),.25)
    milo = market_actor("milo",(1.42,.52,0),-.36)
    market_character_motion(jules,frames,[(0,(-1.36,.40,0),(0,0),(0,0),0),(.42,(-1.04,.33,0),(0,-.75),(0,.4),.18),
                                          (.65,(-.98,.27,0),(0,-.96),(0,.62),.30),(1,(-1.03,.31,0),(0,-.33),(0,.22),0)])
    market_character_motion(milo,frames,[(0,(1.42,.52,0),(-.6,0),(.3,0),0),(.49,(1.35,.50,0),(-.50,-.11),(.22,0),-.16),
                                         (1,(1.49,.50,0),(0,0),(0,0),.07)])
    market_camera(frames,[(0,(2.72,-4.75,2.66),(0,.48,1.39),37),(.39,(2.02,-3.9,2.34),(0,.35,1.35),42),
                          (.40,(-.82,-1.71,2.45),(-.16,.18,1.21),39),(.68,(-.75,-1.44,2.36),(-.19,.19,1.15),45),
                          (.69,(-2.63,-2.67,1.89),(-.95,.32,1.64),42),(1,(-2.2,-2.11,1.80),(-.95,.32,1.64),46)])


def market_office(frames,m):
    market_room(m,brown,m["grass"])
    for x in (-2.55,2.55):
        box("Office bookshelf",(x,2.12,1.60),(1.27,.51,3.13),brown)
        for i in range(4):
            for j in range(5):
                box("Ledger",(x+(j-2)*.19,1.84,.51+i*.59),(.13,.15,.44),(m["navy"],m["pink"],cream)[(j+i)%3],.008)
    market_lettering("TOWN HALL", (0,2.38,3.16),.40,cream)
    desk = group("Mayor's desk",(0,.14,0))
    piece(desk,"Desktop",(0,0,1.14),(2.66,1.05,.18),brown)
    piece(desk,"Desk front",(0,-.46,.57),(2.45,.16,1.02),brown)
    contract = group("Contract",(-.48,.51,1.28))
    piece(contract,"Paper",(0,0,0),(.79,.89,.018),cream,.006)
    for i in range(5):
        piece(contract,"Printed clause",(0,-.26+i*.12,.013),(.54-.05*(i%2),.025,.009),m["navy"],.003)
    keys(contract,"location",[(1,(-.48,.51,1.28)),(int(frames*.37),(-.32,.44,1.28)),
                              (int(frames*.56),(.46,-.29,1.28)),(frames,(.53,-.35,1.28))])
    mayor = market_actor("mayor",(-.73,1.24,0),.27)
    milo = market_actor("milo",(1.79,-.27,0),-1.02)
    market_character_motion(mayor,frames,[(0,(-.73,1.24,0),(0,0),(0,0),0),(.55,(-.55,1.14,0),(0,-.88),(0,.42),.23),
                                           (1,(-.57,1.17,0),(0,-.27),(0,.19),.15)])
    market_character_motion(milo,frames,[(0,(2.18,-.19,0),(0,0),(0,0),0),(.47,(1.57,-.36,0),(-.31,0),(.3,0),-.12),
                                         (1,(1.47,-.34,0),(-.49,0),(.32,0),-.18)])
    market_camera(frames,[(0,(3.8,-4.31,2.73),(.22,.65,1.44),38),(.46,(3.25,-3.48,2.40),(.18,.52,1.37),43),
                          (.47,(.38,-.36,3.63),(.07,-.03,1.13),42),(.73,(.40,-.29,3.12),(.28,-.12,1.19),51),
                          (.74,(2.74,-2.24,2.2),(1.47,-.32,1.83),43),(1,(2.49,-1.92,2.11),(1.49,-.32,1.86),47)])


def market_side_street(m):
    box("Street",(0,0,-.17),(17,15,.29),m["navy"])
    box("Pavement",(0,2.48,.02),(16,3.1,.12),m["concrete"])
    for x in (-4.8,-2.35,2.35,4.8):
        box("Shop wall",(x,4.41,1.72),(2.3,1.9,3.43),m["brick"] if x > 0 else m["violet"])
        box("Window",(x,3.43,1.85),(1.52,.07,.95),m["glass"])
        box("Awning",(x,3.28,2.48),(2.17,.56,.18),m["pink"])
    for x in (-3.18,3.13):
        box("Lamp pole",(x,1.18,1.51),(.12,.12,3),ink)
        box("Streetlight glass",(x,1.18,3.03),(.3,.33,.18),m["mint"])
    for x in range(-6,7):
        box("Road dash",(x*1.2,-1.76,.015),(.61,.10,.014),yellow,.004)


def market_raffle(frames,m):
    market_side_street(m)
    box("Raffle counter",(0,.79,.51),(2.33,.8,1.02),brown)
    box("Countertop",(0,.79,1.06),(2.44,.89,.14),cream)
    box("Raffle sign",(0,.34,1.43),(1.55,.11,.43),m["navy"])
    market_lettering("RAFFLE", (0,.271,1.44),.21,cream)
    for index in range(7):
        ticket=box("Ticket",(-.92+index*.29,.59,1.15),(.21,.27,.027),m["pink"],.01)
        ticket.rotation_euler.z = .29 * (-1)**index
    dad = market_actor("dad",(.41,1.46,0),-.27)
    milo = market_actor("milo",(-1.64,-.22,0),.46)
    market_character_motion(dad,frames,[(0,(.41,1.46,0),(0,0),(0,0),0),(.58,(.38,1.32,0),(-.38,-.20),(.25,.24),.35),
                                       (1,(.39,1.36,0),(-.27,0),(.12,0),-.21)])
    market_character_motion(milo,frames,[(0,(-1.64,-.22,0),(0,0),(0,0),0),(.35,(-1.39,-.14,0),(-.92,0),(.33,0),.39),
                                         (.64,(-1.31,-.17,0),(-.71,0),(.32,0),.22),(1,(-1.39,-.15,0),(0,0),(0,0),.03)])
    market_camera(frames,[(0,(-4.7,-4.16,3.15),(-.29,.78,1.23),37),(.45,(-3.8,-3.45,2.76),(-.30,.79,1.19),42),
                          (.46,(1.95,-1.68,1.91),(.35,1.38,1.70),44),(1,(1.72,-1.36,1.91),(.34,1.37,1.73),46)])


def market_booth(frames,m):
    box("Alley",(0,1,-.14),(10,12,.27),m["navy"])
    box("Alley back",(0,2.88,2.09),(9,.34,4.2),m["violet"])
    box("Left wall",(-2.5,0,1.83),(.20,6,3.66),m["brick"])
    for z in (.54,1.28,2.06,2.84):
        box("Brick course",(-2.371,0,z),(.018,6,.033),m["concrete"])
    machine = group("Betting booth",(.47,1.57,0))
    piece(machine,"Cabinet",(0,0,1.13),(1.48,.62,2.26),m["violet"],.08)
    piece(machine,"Panel",(0,-.325,1.62),(1.13,.09,.91),m["navy"])
    market_lettering("VANISH?", (0,-.379,1.87),.18,cream,machine)
    button = piece(machine,"No button",(.25,-.389,1.43),(.44,.11,.31),m["mint"],.045)
    market_lettering("NO", (.25,-.452,1.43),.18,m["navy"],machine)
    piece(machine,"Coin slot",(-.29,-.358,1.06),(.31,.062,.10),ink,.012)
    keys(button,"location",[(1,(.25,-.389,1.43)),(int(frames*.74)-1,(.25,-.389,1.43)),
                            (int(frames*.74),(.25,-.34,1.43)),(frames,(.25,-.38,1.43))])
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.125,depth=.045)
    coin=bpy.context.object
    coin.data.materials.append(yellow)
    coin.rotation_euler.x=1.57
    keys(coin,"location",[(1,(-.26,.56,1.75)),(int(frames*.47),(.16,.86,1.44)),
                          (int(frames*.67),(.18,1.23,1.065)),(frames,(.18,1.31,1.065))])
    milo=market_actor("milo",(-1.57,-1.03,0),.33)
    market_character_motion(milo,frames,[(0,(-1.57,-1.03,0),(-.47,.22),(.21,.20),0),
        (.35,(-.76,.21,0),(.25,-.54),(.25,.40),.45),(.72,(-.55,.65,0),(0,-.93),(0,.63),.65),
        (1,(-.58,.61,0),(-.12,-.36),(.12,.25),.47)])
    market_camera(frames,[(0,(-2.26,-4.2,1.53),(-.55,.62,1.21),35),(.40,(-1.67,-3.28,1.62),(-.17,.80,1.30),40),
                          (.41,(.31,-.55,1.54),(.25,1.21,1.31),49),(1,(.48,-.29,1.51),(.48,1.21,1.37),51)])


def market_crossing(action,frames,m):
    market_side_street(m)
    for x in range(-3,4):
        box("Crosswalk",(.55*x,.38,.019),(.33,2.2,.022),cream,.006)
    milo = market_actor("milo",(-.9,-.12,0),.48)
    jules = market_actor("jules",(1.0,.27,0),-.61)
    if action=="market_blackout":
        market_character_motion(jules,frames,[(0,(1.0,.27,0),(0,0),(0,0),0),(.6,(.84,.31,0),(0,0),(0,0),-.45),
                                              (1,(.60,.30,0),(0,0),(0,0),-.54)])
        market_character_motion(milo,frames,[(0,(-.9,-.12,0),(0,0),(0,0),0),(.55,(-.59,-.09,0),(0,-.52),(0,.24),.08),
                                             (1,(-.50,-.11,0),(0,-.33),(0,.21),.12)])
        market_camera(frames,[(0,(-.95,-5,3.42),(0,.29,1.17),35),(.53,(-.76,-4.21,2.72),(0,.24,1.24),37),
                              (.54,(-2.9,-1.62,1.85),(.65,.33,1.68),44),(1,(-2.57,-1.61,1.87),(.59,.32,1.66),48)])
    else:
        market_character_motion(jules,frames,[(0,(.60,.30,0),(0,0),(0,0),-.54),(.31,(.38,.14,0),(-.84,0),(.46,0),.18),
                                              (.58,(.30,.09,0),(-.62,0),(.55,0),.32),(1,(.28,.07,0),(-.25,-.3),(.19,.23),.31)])
        market_character_motion(milo,frames,[(0,(-.50,-.11,0),(0,-.33),(0,.21),.12),(.38,(-.50,-.11,0),(0,-.25),(0,.20),.56),
                                             (1,(-.52,-.13,0),(-.18,-.37),(.24,.31),.42)])
        market_camera(frames,[(0,(.25,-3.62,1.43),(-.16,.07,1.25),43),(.43,(.13,-2.75,1.45),(-.15,.05,1.36),47),
                              (.44,(1.94,-2.51,2.03),(.21,.08,1.78),45),(1,(1.49,-2.02,1.98),(.21,.08,1.77),50)])


def market_rooftop(frames,m):
    box("Roof",(0,.63,-.15),(11,8,.30),m["concrete"])
    box("Parapet",(0,2.43,.51),(11,.27,1.02),m["brick"])
    for index,x in enumerate((-6,-3.7,-1.9,.3,2.7,5.1,7.1)):
        high = (index*7%5)*.59+2.2
        box("Distant building",(x,6,-1.6+high/2),(1.9,2.04,high),m["navy"] if index%2 else m["violet"])
        for z in (.45,1.08):
            box("Lit windows",(x,4.96,z-.71),(1.14,.07,.22),m["glass"])
    phone=market_phone((.46,-.19,1.47),m["navy"],m["violet"],"WILL MILO TELL?","YES")
    keys(phone,"rotation_euler",[(1,(.42,0,-.37)),(int(frames*.46),(.12,0,.05)),
                                (int(frames*.52),(.13,0,-.05)),(frames,(.13,0,.01))])
    keys(phone,"location",[(1,(.46,.14,1.22)),(int(frames*.50),(.46,-.19,1.47)),
                            (frames,(.46,-.19,1.47))])
    bpy.ops.mesh.primitive_cylinder_add(vertices=26,radius=.10,depth=.04)
    dollar = bpy.context.object
    dollar.name = "Jules's dollar"
    dollar.data.materials.append(yellow)
    dollar.rotation_euler.x = 1.57
    keys(dollar,"location",[(1,(-1.06,.38,1.17)),(int(frames*.74),(-1.02,.37,1.19)),
                            (frames,(-.63,-.08,1.52))])
    jules=market_actor("jules",(-1.04,.65,0),.25)
    milo=market_actor("milo",(1.22,.49,0),-.42)
    market_character_motion(jules,frames,[(0,(-1.04,.92,0),(0,0),(0,0),0),(.54,(-.94,.56,0),(0,-.46),(0,.32),.34),
                                           (1,(-.82,.46,0),(0,-.73),(0,.55),.51)])
    market_character_motion(milo,frames,[(0,(1.22,.73,0),(0,0),(0,0),0),(.51,(1.18,.52,0),(-.54,0),(.28,0),.21),
                                         (1,(1.13,.51,0),(-.63,0),(.33,0),.29)])
    market_camera(frames,[(0,(-4.9,-5.6,4.35),(.0,.85,1.27),38),(.37,(-3.7,-4.4,3.47),(0,.69,1.46),39),
                          (.38,(.15,-2.31,1.91),(.46,-.04,1.39),47),(.72,(.09,-1.97,1.83),(.46,-.19,1.45),52),
                          (.73,(-2.66,-2.88,1.96),(-.55,.43,1.65),42),(1,(-2.33,-2.58,1.90),(-.52,.42,1.66),47)])


def town_house(x, y, base, width, paint, m):
    height = 2.12 + width*.09
    depth = 2.2
    box("Siding", (x,y,base+height/2), (width,depth,height), paint)
    for direction in (-1, 1):
        roof = box("Pitched roof", (x,y+direction*.53,base+height+.31),
                   (width+.26,1.34,.14), m["navy"], .027)
        roof.rotation_euler.x = direction*-.39
    front = y-depth/2
    box("Front door", (x,front-.031,base+.67), (.54,.09,1.32), m["navy"],.022)
    box("Door step", (x,front-.19,base+.07), (.82,.35,.14), m["concrete"],.018)
    for direction in (-1, 1):
        window_x = x+direction*width*.31
        box("White window trim", (window_x,front-.038,base+1.36), (.62,.10,.69), cream,.018)
        box("Window glass", (window_x,front-.096,base+1.36), (.49,.019,.55), m["glass"],.009)
        box("Window sash", (window_x,front-.111,base+1.36), (.035,.024,.54), cream,.004)
    box("Chimney", (x+width*.30,y+.22,base+height+.58), (.29,.32,.61), m["brick"],.012)


def town_tree(x,y,scale,m):
    box("Street tree trunk",(x,y,.66*scale),(.20*scale,.23*scale,1.32*scale),brown)
    box("Street tree crown",(x,y,1.66*scale),(.84*scale,.86*scale,1.14*scale),m["grass"],.14*scale)
    box("Low foliage",(x-.24*scale,y+.05,1.42*scale),(.53*scale,.71*scale,.63*scale),m["grass"],.11*scale)


def town_bench(x,y,m):
    for side in (-1,1):
        box("Bench leg",(x+side*.54,y,.20),(.12,.37,.39),m["navy"],.018)
    box("Bench seat",(x,y,.42),(1.52,.49,.10),brown,.027)
    for z in (.58,.73):
        box("Bench slat",(x,y+.20,z),(1.52,.099,.11),brown,.02)


def town_lamp(x,y,m):
    box("Lamp pole",(x,y,1.35),(.10,.10,2.70),ink,.013)
    box("Lamp head",(x,y-.12,2.75),(.32,.43,.13),m["navy"],.025)
    box("Glowing lamp",(x,y-.14,2.687),(.23,.31,.04),m["goldlight"],.016)


def town_car(x,y,heading,color,m):
    car = group("Parked car",(x,y,0))
    car.rotation_euler.z = heading
    piece(car,"Car body",(0,0,.32),(1.15,2.02,.36),color,.09)
    piece(car,"Windshield and cabin",(0,.06,.58),(.91,1.12,.38),m["navy"],.07)
    piece(car,"Roof",(0,.09,.79),(.94,1.04,.09),color,.033)
    for side in (-1,1):
        for end in (-1,1):
            piece(car,"Wheel",(side*.54,end*.64,.22),(.20,.33,.35),ink,.071)
        piece(car,"Headlight",(side*.35,-1,.36),(.26,.105,.12),cream,.025)


def market_crowd(entries, frames):
    shirts = ((.12,.50,.62),(.86,.43,.10),(.34,.20,.65),(.22,.53,.30),(.66,.16,.13),(.20,.32,.56))
    costumes = ("crowd_cap","crowd_bun","crowd_glasses")
    for index,(x,y,heading,activity) in enumerate(entries):
        pos=(x,y,0)
        person = roblox_actor(f"Townsperson {index+1}",pos,
            material(f"Townsperson {index+1} shirt",shirts[index%len(shirts)]),
            (brown,ink,brown,ink)[index%4],heading,index%3==2,costumes[index%3])
        scale=(.78,.93,.86,1.0,.82,.92)[index%6]
        person[0].scale=(scale,scale,scale)
        if activity == "walk":
            move=.63 if index%2 else -.78
            poses=[(0,pos,(0,0),(0,0),0),
                   (.52,(x+move*.52,y-.17,0),(-.35,.28),(.22,.10),.18),
                   (1,(x+move,y-.26,0),(.1,-.29),(.13,.27),.04)]
        elif activity == "react":
            poses=[(0,pos,(0,0),(0,0),0),
                   (.54,(x,y,.01),(-.21,-.36),(.1,.31),-.19),
                   (.74,(x,y,.11),(-.91,-.77),(.40,.45),.16),
                   (1,pos,(-.41,-.26),(.18,.14),.06)]
        else:
            poses=[(0,pos,(-.16,0),(.3,0),0),
                   (.6,(x+.04,y,.02),(-.38,0),(.39,.13),-.22),
                   (1,pos,(-.19,-.11),(.26,0),.09)]
        market_character_motion(person,frames,poses)


def market_neighborhood(action,frames,m):
    paints = (m["brick"],m["glass"],m["sand"],m["mint"],m["violet"])
    if action in {"market_street","market_win"}:
        box("Town ground", (0,9,-.24), (30,27,.41), m["grass"])
        if action == "market_street":
            box("Residential street",(0,-5.15,-.021),(2.83,7.5,.037),m["navy"],.012)
            for side in (-1,1):
                box("Residential sidewalk",(side*1.72,-5.27,.028),(.60,7.5,.071),m["concrete"],.019)
                for row,y in enumerate((-6.63,-3.84,-.93)):
                    town_house(side*(4.45-.23*(row%2)),y,0,2.28,
                               paints[(row+int(side>0)*2)%len(paints)],m)
                    town_tree(side*2.54,y+.46,.73,m)
                    town_lamp(side*2.08,y+.39,m)
            for y in (-7.2,-5.9,-4.6,-3.3,-2.0):
                box("Residential road stripe",(0,y,.013),(.085,.64,.023),yellow,.004)
            for side in (-1,1):
                for post in range(5):
                    box("School fence post",(side*(2.53+.38*post),-.55,.30),(.09,.11,.59),cream,.01)
                box("School fence rail",(side*3.30,-.55,.44),(1.65,.065,.091),cream,.009)
        else:
            for i,x in enumerate((-8.2,-5.75,5.55,8.02)):
                town_house(x,5.9+(i%2)*.54,0,2.23,paints[i],m)
        for x,y,s in ((-4.4,1.28,1.15),(4.2,1.92,1.12),(-5.9,3.8,1),(5.3,3.8,1.04)):
            town_tree(x,y,s,m)
        for x in (-4.3,4.33):
            town_lamp(x,.87,m)
        town_car(3.85,-.92,.44,m["brick"],m)
        town_bench(-3.29,.9,m)
        if action == "market_street":
            entries=[(-2.82,1.29,.48,"walk"),(2.95,.68,-.37,"talk"),
                     (-3.28,-.51,.39,"walk"),(3.9,1.48,-.52,"talk")]
        else:
            entries=[(-2.97,1.07,.54,"react"),(2.21,1.19,-.55,"react"),
                     (1.61,2.1,-.34,"react"),(.16,2.67,.12,"talk"),(-3.45,.25,.94,"walk")]
        market_crowd(entries,frames)
    elif action in {"market_count","market_blackout","market_hook"}:
        for i,x in enumerate((-8.3,-5.7,-3.23,-.72,1.84,4.66,7.27)):
            town_house(x,7.5+(i%2)*.52,0,2.30,paints[i%5],m)
        for x in (-4.65,4.78):
            town_tree(x,2.03,1.08,m)
        town_car(3.88,-.96,-.17,m["brick"],m)
        town_car(-4.06,1.18,.18,m["sand"],m)
        town_bench(3.09,2.48,m)
        entries=[(-2.4,2.08,.24,"talk"),(2.31,2.19,-.42,"react"),
                 (3.25,3.11,-.48,"walk"),(-3.24,2.77,.41,"walk"),
                 (.29,3.27,-.12,"react")]
        market_crowd(entries,frames)
    elif action == "market_end":
        for i,x in enumerate((-9,-6,-3,0,3,6,9)):
            town_house(x,9.4+(i%3)*.58,-2.3,2.66,paints[i%5],m)
        for i,x in enumerate((-7.55,-4.3,2.38,6.9)):
            town_house(x,12.5,-2.1,2.54,paints[(i+2)%5],m)
        town_lamp(-3.1,1.7,m)
        town_lamp(3.9,1.7,m)
    elif action == "market_friend":
        for x in (-3.6,3.02):
            box("Table placemat",(x,1.31,.93),(.54,.39,.022),m["pink"],.012)
            box("Coffee mug",(x,1.32,1.021),(.14,.13,.18),cream,.034)
        market_crowd([(-3.18,1.54,.16,"talk"),(2.57,1.6,-.28,"talk")],frames)
    elif action == "market_mayor":
        market_crowd([(-2.66,.91,.42,"talk")],frames)


def stage_market(action, frames):
    m = {
        "navy": material("Midnight blue",(.037,.046,.118)),
        "violet": material("Purple",(.27,.11,.47)),
        "pink": material("Pink vinyl",(.78,.13,.33)),
        "brick": material("Burnt brick",(.52,.18,.106)),
        "grass": material("Green",(.105,.31,.22)),
        "glass": material("Blue glass",(.23,.56,.86)),
        "concrete": material("Pavement",(.39,.42,.5)),
        "mint": material("Mint",(.1,.85,.48)),
        "sand": material("Warm siding",(.83,.55,.27)),
        "goldlight": material("Warm lamp glass",(1,.79,.35)),
    }
    glow = m["goldlight"].node_tree.nodes.get("Principled BSDF")
    glow.inputs["Emission Color"].default_value = (1,.64,.20,1)
    glow.inputs["Emission Strength"].default_value = 1.0
    shots = {
        "market_street": market_school, "market_win": market_fountain,
        "market_ticket": market_bedroom, "market_friend": market_diner,
        "market_mayor": market_office, "market_count": market_raffle,
        "market_trade": market_booth, "market_end": market_rooftop,
    }
    if action in {"market_hook", "market_blackout"}:
        market_crossing(action,frames,m)
    else:
        shots[action](frames,m)
    market_neighborhood(action,frames,m)
    outside = action in {"market_street","market_win","market_count","market_blackout","market_hook","market_end"}
    is_day = action in {"market_street","market_win"}
    sky.inputs["Color"].default_value = (.31,.54,.88,1) if is_day else (.045,.085,.28,1)
    light("AREA",(-3.1,-3.6,4.2),700 if is_day else 465,
          (1,.84,.71) if is_day else (.55,.65,1),(0,.55,1.15),4.4)
    light("AREA",(3.2,-1.55,3.7),420,(1,.73,.70) if outside else (1,.79,.56),(0,.53,1.2),3.5)
    light("AREA",(0,2.15,4.8),635,(.57,.77,1) if outside else (.59,.78,1),(0,0,1.0),3.4)
    if action=="market_blackout":
        midpoint=frames//2
        for lamp in (obj.data for obj in scene.objects if obj.type=="LIGHT"):
            full=lamp.energy
            keys(lamp,"energy",[(1,full),(midpoint-2,full),(midpoint,full*.045),(frames,full*.06)])


episode_path, index, duration, width, fps, engine, target = sys.argv[sys.argv.index("--")+1:]
episode = read_episode(episode_path)
avatar = episode.get("avatar")
shorts_style = episode.get("style") == "shorts"
shot = episode["shots"][int(index)]
frames = max(12, int(duration))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.world = bpy.data.worlds.new("Sky")
scene.world.use_nodes = True
sky = scene.world.node_tree.nodes.get("Background")
sky.inputs["Color"].default_value = (.32, .48, .76, 1)
sky.inputs["Strength"].default_value = .65
scene.render.engine = engine
scene.eevee.taa_render_samples = 8 if shorts_style else 16
scene.render.use_persistent_data = True
scene.cycles.samples = 8
scene.cycles.use_denoising = True
scene.view_settings.view_transform = "AgX"
if shorts_style:
    scene.view_settings.look = "AgX - Medium High Contrast"
scene.render.resolution_x = int(width)
scene.render.resolution_y = round(int(width)*16/9/2)*2
scene.render.resolution_percentage = 100
scene.render.fps = int(fps)
scene.frame_end = frames
ink = material("Ink", (.027, .035, .054))
cream = material("Cream", (.93, .83, .63))
teal = material("Teal sweatshirt", (.017, .46, .49))
coral = material("Coral", (.72, .145, .15))
brown = material("Brown", (.12, .055, .027))
peach = material("Peach", (.84, .46, .27))
blush = material("Blush", (.76, .25, .22))
denim = material("Denim", (.055, .113, .27))
red = material("Red", (.64, .055, .044))
yellow = material("Yellow", (.98, .62, .049))
amber = material("Amber", (.81, .36, .018))
if shot["action"] in MARKET_ACTIONS:
    stage_market(shot["action"], frames)
elif shot["action"] in {"town", "dusk", "streetdoor"}:
    town(frames, shot["action"])
else:
    hallway(shot["action"], frames)
scene.render.fps = int(fps)
scene.render.fps_base = 1
scene.render.image_settings.media_type = "VIDEO"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "HIGH"
scene.render.filepath = target
bpy.ops.render.render(animation=True)
