"""Build and render a shot with Blender's embedded Python."""

from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from episode import read_episode
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


def roblox_actor(name, pos, shirt, hair, yaw, adult):
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
    for mesh in meshes:
        body = mesh.name.split(".")[0]
        color = peach if body == "Head_Geo" else shirt
        if "Leg" in body:
            color = denim
        elif "Foot" in body:
            color = ink
        elif "Hand" in body:
            color = peach
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
        piece(face, "Eye", (x, -.256, 2.008), (.038, .018, .054), ink, .008)
        piece(face, "Brow", (x, -.249, 2.074), (.075, .018, .018), hair, .006)
    piece(face, "Mouth", (0, -.253, 1.904), (.105, .025, .027), ink, .008)
    cap = piece(rig, "Side-part hair" if adult else "Swept hair", (0, .035, 2.15), (.51, .48, .125), hair)
    if adult:
        piece(rig, "Bob", (0, .19, 1.97), (.53, .20, .40), hair, .06)
    else:
        cap.rotation_euler.y = -.13
        piece(rig, "Fringe", (-.13, -.177, 2.105), (.25, .11, .145), hair)
    bpy.context.view_layer.update()
    for accessory in list(rig.children):
        if accessory == armature:
            continue
        world = accessory.matrix_world.copy()
        accessory.parent = armature
        accessory.parent_type = "BONE"
        accessory.parent_bone = head.name
        accessory.matrix_world = world
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
        if action in {"open", "twist", "twin", "key", "escape"}:
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
                brass_key((.47, 2.29, 1.42), 1.1)
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
        "key": ((.83, .46, 1.58), (.70, .85, 1.50), (.47, 2.28, 1.43), 48),
        "escape": ((1.61, -3.33, 2.24), (1.04, -4.48, 2.46), (0, -.09, 1.50), 33),
        "twist": ((.56, -2.95, 2.05), (.32, -5.14, 2.41), (0, 1.91, 1.62), 32),
    }
    camera(*shots[action], frames)


episode_path, index, duration, width, fps, engine, target = sys.argv[sys.argv.index("--")+1:]
episode = read_episode(episode_path)
avatar = episode.get("avatar")
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
scene.eevee.taa_render_samples = 16
scene.render.use_persistent_data = True
scene.cycles.samples = 8
scene.cycles.use_denoising = True
scene.view_settings.view_transform = "AgX"
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
if shot["action"] in {"town", "dusk", "streetdoor"}:
    town(frames, shot["action"])
else:
    hallway(shot["action"], frames)
scene.render.image_settings.media_type = "VIDEO"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "HIGH"
scene.render.filepath = target
bpy.ops.render.render(animation=True)
