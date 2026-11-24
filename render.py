"""Build and render a shot with Blender's embedded Python."""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from episode import read_episode


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


def actor(name, pos, shirt, hair, skin, yaw=0, adult=False):
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


def clock(name, pos, scale, frames=0):
    prop = group(name, pos)
    piece(prop, "Clock rim", (0, 0, 0), (.58, .13, .58), ink, .07)
    piece(prop, "Clock face", (0, -.074, 0), (.45, .036, .45), cream)
    piece(prop, "Hour hand", (.066, -.10, .015), (.146, .025, .032), ink, .008)
    hand = group("Clock hand pivot", (0, -.10, 0))
    hand.parent = prop
    piece(hand, "Minute hand", (0, 0, .082), (.027, .025, .19), red, .008)
    if frames:
        keys(hand, "rotation_euler", [(1, (0, 0, 0)), (frames, (0, math.tau, 0))])
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


def town(frames):
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
    for limbs, amplitude in ((arms, .29), (legs, -.23)):
        for index, limb in enumerate(limbs):
            swing = (-1)**index * amplitude
            values = [(frame, (angle, 0, 0)) for frame, angle in
                      ((1, swing), (frames//4, -swing), (frames//2, swing),
                       (3*frames//4, -swing), (frames, swing))]
            keys(limb, "rotation_euler", values)
    light("SUN", (4, -5, 8), 2.0, (1, .88, .68), (0, 0, 0), 0)
    camera((2.6, -6.3, 2.65), (1.9, -5.6, 2.5), (0, .15, 1.45), 33, frames)


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
    _, kid_head, kid_arms, _ = actor("Narrator", (-1.13, .15, 0), teal, brown, peach, .36)
    mom, mom_head, mom_arms, _ = actor("Mom", (1.1, .78, 0), coral, ink, peach, -.38, adult=True)
    mom.scale = (1.1,)*3
    keys(kid_head, "rotation_euler", [(1, (0, 0, -.10)), (frames, (.11, 0, .37))])
    keys(mom_head, "rotation_euler", [(1, (.04, 0, 0)), (frames, (-.12, 0, -.28))])
    if action in {"lie", "appear"}:
        if action == "appear":
            keys(mom_arms[0], "rotation_euler", [(1, (0, 0, 0)), (frames//3, (-.6, -.12, .65)),
                                              (frames, (-.48, -.15, .56))])
    if action == "lie":
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
        if action in {"open", "twist"}:
            angle = -1.9
            if action == "open":
                keys(hinge, "rotation_euler", [(1, (0, 0, 0)), (frames//3, (0, 0, angle)), (frames, (0, 0, angle))])
            else:
                hinge.rotation_euler.z = angle
            double, _, double_arms, _ = actor("Double", (.18, 3.03, .06), teal, brown, peach, -.13)
            prop = group("Hidden hammer", (.205, -.465, 1.39))
            prop.parent = double
            prop.rotation_euler.y = -.35
            piece(prop, "Handle", (0, 0, 0), (.073, .085, .50), brown, .013)
            piece(prop, "Steel head", (0, 0, .228), (.36, .132, .155), ink, .025)
            piece(prop, "Striking face", (.174, 0, .227), (.06, .153, .16), denim, .014)
            keys(double, "location", [(1, (.18, 3.03, .06)), (frames, (.18, 1.91, .06))])
            for arm in double_arms:
                arm.rotation_euler.x = -.8
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
        "twist": ((.56, -2.95, 2.05), (.32, -5.14, 2.41), (0, 1.91, 1.62), 32),
    }
    camera(*shots[action], frames)


episode_path, index, duration, width, fps, engine, target = sys.argv[sys.argv.index("--")+1:]
shot = read_episode(episode_path)["shots"][int(index)]
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
if shot["action"] == "town":
    town(frames)
else:
    hallway(shot["action"], frames)
scene.render.image_settings.media_type = "VIDEO"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "HIGH"
scene.render.filepath = target
bpy.ops.render.render(animation=True)
