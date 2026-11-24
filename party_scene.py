"""Build the aligned neighborhood and house for A Party for Two."""

import math

import bpy
from mathutils import Vector


class PartySet:
    def __init__(self, renderer, action, frames):
        self.r = renderer
        self.action = action
        self.frames = frames
        self.blockers = []
        colors = {
            "asphalt": (.075, .096, .135), "walk": (.46, .47, .50),
            "grass": (.12, .34, .18), "leaf": (.10, .30, .14),
            "siding": (.25, .49, .62), "sage": (.32, .48, .30),
            "sand": (.70, .51, .34), "rose": (.57, .29, .30),
            "navy": (.038, .055, .107), "window": (.18, .38, .59),
            "warm": (1, .71, .33), "pink": (.98, .16, .48),
            "wall": (.60, .69, .75), "fabric": (.22, .40, .57),
        }
        self.m = {name: renderer.material(name, rgb) for name, rgb in colors.items()}
        for name in ("warm", "pink"):
            shader = self.m[name].node_tree.nodes.get("Principled BSDF")
            shader.inputs["Emission Color"].default_value = self.m[name].diffuse_color
            shader.inputs["Emission Strength"].default_value = 1.25

    def block(self, name, center, size, material, bevel=.035, solid=False):
        obj = self.r.box(name, center, size, material, bevel)
        if solid:
            self.blockers.append((name, Vector(center), Vector(size) / 2))
        return obj

    def time(self, fraction):
        return 1 + round((self.frames - 1) * fraction)

    def key(self, obj, prop, beats):
        self.r.keys(obj, prop, [(self.time(at), value) for at, value in beats])

    def camera(self, *moves, indoors=False):
        bpy.ops.object.camera_add()
        camera = bpy.context.object
        self.r.scene.camera = camera
        camera.data.sensor_fit = "HORIZONTAL"
        camera.data.clip_start = .065
        def place(frame, position, target, focal):
            camera.location = position
            camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
            camera.data.lens = focal
            camera.keyframe_insert(data_path="location", frame=frame)
            camera.keyframe_insert(data_path="rotation_euler", frame=frame)
            camera.data.keyframe_insert(data_path="lens", frame=frame)

        previous = 0
        last_move = None
        for fraction, position, target, focal in moves:
            frame = max(previous + 1, self.time(fraction))
            if last_move and fraction - last_move[0] <= .035 and frame - 1 > previous:
                place(frame - 1, *last_move[1:])
            place(frame, position, target, focal)
            previous = frame
            last_move = (fraction, position, target, focal)
        for frame in range(1, self.frames + 1):
            self.r.scene.frame_set(frame)
            x, y, z = camera.location
            if indoors and not (-3.67 < x < 3.67 and -2.43 < y < 3.40 and .25 < z < 3.02):
                raise ValueError(f"{self.action}: camera leaves room at frame {frame}")
            for label, center, half in self.blockers:
                if all(abs(v - c) < extent + .12 for v, c, extent in zip(camera.location, center, half)):
                    raise ValueError(f"{self.action}: camera intersects {label} at frame {frame}")
        self.r.scene.frame_set(1)

    def person(self, role, position, yaw):
        leo = role == "Leo"
        shirt = self.r.material(role + " outfit", (.045,.36,.57) if leo else (.91,.49,.14))
        return self.r.roblox_actor(role, position, shirt, self.r.brown if leo else self.r.ink,
                                   yaw, False, "party_leo" if leo else "party_michael")

    def motion(self, rig, poses):
        self.r.market_character_motion(rig, self.frames, poses)

    def lamp(self, x, y, z):
        self.block("Porch sconce", (x,y,z), (.20,.16,.30), self.m["navy"])
        bulb = self.block("Porch lamp glass", (x,y-.10,z), (.15,.045,.22), self.m["pink"], .018)
        return bulb

    def house(self, x, y, width, color, lead=False):
        depth = 5.0
        front = y - depth / 2
        height = 3.28
        self.block("House structure", (x,y,height/2), (width,depth,height), color, solid=True)
        for sign in (-1, 1):
            roof = self.block("Roof slope", (x,y+sign*1.17,height+.40),
                              (width+.34,2.78,.16), self.m["navy"])
            roof.rotation_euler.x = -sign*.30
        self.block("Base trim", (x,front-.025,.13), (width,.13,.26), self.m["walk"])
        self.block("Entry trim", (x,front-.061,1.29), (1.26,.15,2.58), self.r.cream)
        if not lead or self.action not in {"party_lantern","party_end"}:
            self.block("Front door", (x,front-.151,1.22), (1.02,.10,2.43), self.m["navy"])
            self.block("Door handle", (x+.34,front-.22,1.15), (.087,.08,.103), self.r.amber)
        else:
            interior = self.m["navy"] if self.action == "party_lantern" else self.m["warm"]
            self.block("Open doorway", (x,front-.145,1.22), (1.03,.016,2.43), interior)
        for sign in (-1, 1):
            wx = x + sign * width * .29
            self.block("Window trim", (wx,front-.06,1.77), (1.38,.14,1.31), self.r.cream)
            self.block("Window glass", (wx,front-.145,1.77), (1.18,.035,1.11), self.m["window"])
            self.block("Window vertical bar", (wx,front-.173,1.77), (.055,.035,1.08), self.r.cream)
            self.block("Window horizontal bar", (wx,front-.173,1.77), (1.15,.032,.055), self.r.cream)
        self.block("Porch", (x,front-.77,.11), (2.85,1.6,.22), self.m["walk"])
        self.block("Entry step", (x,front-1.54,.058), (2.31,.38,.116), self.m["walk"])
        self.block("Walk to front door", (x,(front-1.75-3.56)/2,.013),
                   (1.26,abs(front-1.75+3.56),.03), self.m["walk"])
        lamp = self.lamp(x+.82,front-.11,2.32)
        if lead:
            lamp.data.materials[0] = self.m["navy"]
        elif self.action == "party_lantern":
            lamp.data.materials[0] = self.m["navy"]
        elif self.action in {"party_street","party_end"}:
            # One switch event across the block, without moving the fixtures.
            socket = lamp.data.materials[0].copy()
            lamp.data.materials[0] = socket
            power = socket.node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"]
            power.default_value = .03
            power.keyframe_insert(data_path="default_value", frame=1)
            power.default_value = 2.7
            power.keyframe_insert(data_path="default_value", frame=self.time(.48))
        if not lead and self.action != "party_lantern":
            self.r.light("AREA",(x+.57,front-.54,2.65),42,(1,.18,.46),(x,front-.85,.18),1.35)
            glow = bpy.context.object.data
            if self.action in {"party_street","party_end"}:
                self.key(glow,"energy",[(0,0),(.43,0),(.48,42),(1,42)])

    def tree(self, x, y, size):
        self.block("Trunk", (x,y,.83*size), (.19*size,.19*size,1.66*size), self.r.brown)
        self.block("Canopy", (x,y,1.99*size), (1.07*size,.96*size,1.34*size), self.m["leaf"], .20)
        self.block("Lower foliage",(x-.34*size,y+.07,1.62*size),(.66*size,.74*size,.64*size),self.m["leaf"],.16)

    def car(self, name, position, direction, shade):
        car = self.r.group(name, position)
        car.rotation_euler.z = direction
        piece = self.r.piece
        piece(car, "Chassis", (0,0,.45), (1.68,3.58,.55), shade,.12)
        piece(car, "Glass cabin", (0,.25,.90), (1.40,1.75,.54), self.m["navy"],.11)
        piece(car, "Car roof", (0,.31,1.16), (1.44,1.59,.12), shade,.04)
        for side in (-1,1):
            for length in (-1.09,1.10):
                piece(car, "Tire", (side*.81,length,.29), (.22,.59,.58), self.r.ink,.105)
            piece(car, "Headlamp", (side*.59,-1.77,.49), (.30,.10,.14),self.m["warm"],.033)
            piece(car, "Taillamp", (side*.58,1.76,.46), (.27,.08,.13),self.r.red,.033)
        return car

    def neighborhood(self):
        b, m = self.block, self.m
        b("Ground", (0,-4,-.20),(86,64,.36),m["grass"])
        b("Main road", (0,-6.16,.002),(52,4.10,.036),m["asphalt"],.014)
        for y in (-3.64,-8.67):
            b("Sidewalk", (0,y,.065),(50,.95,.14),m["walk"],.02)
        for x in range(-23,25,2):
            b("Center stripe",(x,-6.16,.028),(.81,.077,.018),self.r.yellow,.004)
        for x, width, color in ((-17,5.4,"rose"),(-8.5,5.8,"sage"),(0,6.2,"siding"),
                                (8.5,5.8,"sand"),(17,5.4,"rose")):
            self.house(x,2.95,width,m[color],lead=x==0)
            for side in (-1,1):
                tx=x+side*(width/2+.55)
                self.tree(tx,.42,.94 if side==-1 else 1.08)
            for offset in (-1.94,-1.64,1.64,1.94):
                b("Flower stem",(x+offset,-1.44,.12),(.035,.037,.23),m["leaf"],.006)
                b("Flower head",(x+offset,-1.44,.25),(.121,.121,.088),
                  m["pink"] if offset<0 else self.r.yellow,.028)
        for x in (-13.6,-4.25,4.27,13.57):
            b("Street lamp",(x,-3.20,1.34),(.115,.118,2.68),m["navy"],.019)
            b("Lamp head",(x,-3.36,2.72),(.34,.47,.14),m["navy"],.030)
            b("Lamp diffuser",(x,-3.37,2.638),(.25,.36,.037),m["navy"] if self.action=="party_lantern" else m["warm"],.017)
        for x, y, shade in ((-5.47,-1.47,m["sand"]),(12.60,-1.44,m["rose"])):
            b("Driveway",(x,(-1.08-4.0)/2,.019),(2.02,3.00,.034),m["walk"],.018)
            self.car("Parked on driveway",(x,y,.01),0,shade)
        if self.action == "party_street":
            # Cars travel east or west on one lane each, clear of both curbs.
            east = self.car("Eastbound blue car",(-17,-7.10,.014),math.pi/2,m["siding"])
            west = self.car("Westbound red car",(15,-5.19,.014),-math.pi/2,m["rose"])
            self.key(east,"location",[(0,(-17,-7.10,.014)),(1,(20,-7.10,.014))])
            self.key(west,"location",[(0,(15,-5.19,.014)),(1,(-19,-5.19,.014))])
        for x,y,z in ((-12,18,7),(0,24,10),(13,26,9.4)):
            for offset in (-.78,0,.87):
                bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,location=(x+offset,y,z))
                cloud = bpy.context.object
                cloud.scale=(1.12,.63,.44)
                cloud.data.materials.append(m["window"])
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=10,location=(-4.2,23,9.0))
        moon=bpy.context.object
        moon.scale=(.50,)*3
        moon.data.materials.append(m["warm"])
        self.r.sky.inputs["Color"].default_value = (.065,.105,.29,1)
        self.r.light("AREA",(0,-7,5.5),620,(.59,.71,1),(0,.7,1.05),6.3)
        self.r.light("AREA",(2.6,-1,3.2),285,(1,.63,.72),(0,-.54,1.1),3.8)

    def room(self, bedroom=False):
        b, m = self.block, self.m
        b("Wood floor",(0,.47,-.14),(7.96,6.47,.28),self.r.brown)
        for index in range(24):
            b("Floorboard seam",(-3.76+index*.32,.47,.004),(.012,6.38,.012),m["navy"],.002)
        b("Ceiling",(0,.47,3.24),(7.96,6.47,.16),self.r.cream,.009)
        for x in (-3.94,3.94):
            b("Side wall",(x,.45,1.56),(.18,6.47,3.13),m["wall"])
        b("Back wall",(0,3.64,1.56),(7.96,.18,3.13),m["wall"])
        if bedroom:
            b("Front wall",(0,-2.76,1.56),(7.96,.18,3.13),m["wall"])
            b("Room baseboard",(0,-2.64,.15),(7.8,.08,.26),self.r.cream)
        else:
            for sign in (-1,1):
                b("Front wall beside doorway",(sign*2.26,-2.76,1.56),(3.46,.18,3.13),m["wall"])
                b("Room baseboard",(sign*2.25,-2.64,.15),(3.42,.08,.26),self.r.cream)
            b("Door lintel",(0,-2.76,2.79),(1.13,.18,.69),m["wall"])
            b("Outside landing",(0,-3.49,-.105),(2.88,1.61,.21),m["walk"])
            b("Dark front lawn",(0,-5.23,-.24),(14.1,5.2,.31),m["grass"])
            b("Street beyond doorway",(0,-9.34,-.048),(21.1,4.10,.038),m["asphalt"])
            self.r.light("AREA",(0,-4.46,2.45),65,(.61,.70,1),(0,-3.36,.81),2.1)
        b("Rug",(0,-.18,.016),(3.74,2.04,.034),m["fabric"],.13)
        b("Room pendant",(0,.5,2.91),(.62,.52,.17),m["navy"])
        b("Pendant diffuser",(0,.5,2.81),(.48,.42,.062),m["navy"] if self.action=="party_beat" else m["warm"],.02)
        power = .32 if self.action == "party_beat" else 1
        self.r.light("AREA",(-2,1.85,2.73),207*power,(1,.73,.47),(0,-.8,1.1),2.4)
        self.r.light("AREA",(2,-.2,2.68),142*power,(.72,.81,1),(0,-.6,1.2),2.8)
        if bedroom:
            b("Bed base",(-2.25,.70,.40),(1.63,2.35,.70),m["navy"])
            b("Bed quilt",(-2.25,.62,.83),(1.58,2.22,.18),m["fabric"])
            b("Pillow",(-2.25,1.54,.95),(1.10,.42,.12),self.r.cream,.06)
            b("Nightstand",(-2.8,-1.28,.43),(.75,.67,.85),self.r.brown)
        else:
            for x in (-.575,.575):
                b("Door jamb",(x,-2.62,1.23),(.12,.13,2.47),self.r.cream)
            b("Door head trim",(0,-2.62,2.47),(1.26,.13,.12),self.r.cream)
            door = self.r.group("Hinged front door",(-.52,-2.53,0))
            self.r.piece(door,"Door panel",(.52,0,1.21),(1.06,.109,2.41),m["navy"])
            self.r.piece(door,"Handle",(.94,.075,1.09),(.12,.10,.11),self.r.amber)
            if self.action == "party_beat":
                self.key(door,"rotation_euler",[(0,(0,0,0)),(.62,(0,0,0)),(.94,(0,0,1.14))])
            b("Sofa seat",(-2.45,1.71,.53),(2.23,.93,.48),m["fabric"])
            b("Sofa back",(-2.45,2.11,.96),(2.23,.24,1.24),m["fabric"])
            for x in (-3.42,-1.48):
                b("Sofa arm",(x,1.66,.73),(.30,.91,.53),m["fabric"])
            for x,color in ((-2.95,self.r.cream),(-2.11,m["pink"])):
                b("Throw pillow",(x,1.95,.93),(.49,.18,.49),color,.11)
            b("Coffee table",(.08,-.2,.67),(1.66,.93,.16),self.r.brown)
            for side in (-1,1):
                b("Coffee table leg",(.08+side*.58,-.2,.33),(.13,.62,.64),self.r.brown)
        for x in (-1.94,1.94):
            b("Window casing",(x,-2.624,1.77),(1.32,.13,1.29),self.r.cream)
            b("Window insert",(x,-2.542,1.77),(1.13,.043,1.08),m["window"])
            b("Window division",(x,-2.513,1.77),(.061,.03,1.06),self.r.cream)
            b("Window ledge",(x,-2.44,1.19),(1.41,.22,.12),self.r.cream)
        return door if not bedroom else None

    def speaker(self, pos):
        prop=self.r.group("Michael's old speaker",pos)
        self.r.piece(prop,"Speaker case",(0,0,0),(.54,.37,.57),self.m["navy"],.065)
        self.r.piece(prop,"Speaker grille",(0,-.195,.008),(.44,.045,.47),self.r.ink,.043)
        for x in (-.135,0,.135):
            self.r.piece(prop,"Grille rib",(x,-.227,0),(.021,.022,.42),self.m["walk"],.006)
        self.r.piece(prop,"Handle",(0,0,.329),(.28,.095,.074),self.r.cream,.017)
        return prop

    def cup(self, name, pos, material):
        bpy.ops.mesh.primitive_cone_add(vertices=24,radius1=.059,radius2=.087,depth=.17,location=pos)
        cup=bpy.context.object
        cup.name=name
        cup.data.materials.append(material)
        return cup

    def opening(self):
        self.neighborhood()
        leo=self.person("Leo",(.18,-2.25,0),.14)
        self.motion(leo,[(0,(.18,-2.25,0),(0,0),(0,0),.1),(.46,(.27,-2.22,0),(-.37,0),(.32,0),-.4),
                         (1,(.18,-2.19,0),(0,-.16),(0,.13),-.2)])
        self.camera((0,(10.1,-11.8,4.12),(0,-.86,1.44),34),
                    (.46,(7.3,-10.03,3.21),(0,-1.14,1.39),36),
                    (.48,(1.21,-4.29,1.94),(.20,-2.16,1.49),43),
                    (1,(1.01,-3.97,1.90),(.21,-2.15,1.55),46))

    def bedroom(self):
        self.room(bedroom=True)
        for side in (-1,1):
            x=-1.94+side*.74
            panel=self.block("Curtain panel",(x,-2.44,1.80),(.70,.111,1.40),self.m["rose"],.05)
            self.key(panel,"location",[(0,(x,-2.44,1.80)),(.41,(x,-2.44,1.80)),
                                      (.66,(-1.94+side*.34,-2.44,1.8)),(1,(-1.94+side*.34,-2.44,1.8))])
        leo=self.person("Leo",(-1.55,-1.66,0),-2.42)
        self.motion(leo,[(0,(-1.55,-1.66,0),(-.21,0),(.16,0),.1),
                         (.55,(-1.70,-1.75,0),(-.75,-.73),(.43,.46),-.06),
                         (1,(-1.40,-1.19,0),(0,0),(0,0),.94)])
        self.camera((0,(2.37,1.85,2.38),(-1.41,-1.74,1.36),36),
                    (.52,(1.43,1.14,2.12),(-1.45,-1.77,1.43),40),
                    (.54,(-.24,-.92,1.98),(-1.44,-1.58,1.76),43),
                    (1,(-.11,-.80,1.95),(-1.36,-1.25,1.73),46),indoors=True)

    def knock(self):
        self.neighborhood()
        michael=self.person("Michael",(-.16,-.72,.22),.12)
        self.motion(michael,[(0,(-.16,-.72,.22),(-.35,-.60),(.42,.44),-2.30),
                             (.43,(-.15,-.70,.22),(-.90,-.61),(.56,.47),-2.30),
                             (.59,(-.14,-.74,.22),(-.38,-.58),(.26,.48),-.15),
                             (1,(-.13,-.75,.22),(-.49,-.57),(.37,.46),.04)])
        speaker=self.speaker((.24,-1.08,1.39))
        self.key(speaker,"location",[(0,(.22,-.57,1.41)),(.53,(.22,-.57,1.41)),
                                      (.67,(.22,-1.08,1.39)),(1,(.21,-1.11,1.38))])
        self.cup("Red cup",(-.39,-1.07,1.40),self.m["rose"])
        self.cup("Paper cup",(-.50,-1.03,1.40),self.r.cream)
        self.camera((0,(.93,-2.61,1.72),(-.02,-.32,1.61),42),
                    (.54,(.82,-2.38,1.68),(-.06,-.38,1.61),45),
                    (.56,(-1.33,-2.61,2.02),(-.14,-.71,1.65),42),
                    (1,(-1.11,-2.39,1.99),(-.12,-.74,1.67),46))

    def living(self):
        self.room()
        action=self.action
        leo=self.person("Leo",(-1.18,-.25,0),.69)
        michael=self.person("Michael",(1.20,-.15,0),-.64)
        if action=="party_invite":
            self.motion(leo,[(0,(-1.18,-.25,0),(0,0),(0,0),0),(.49,(-1.18,-.25,0),(-.31,-.37),(.31,.27),.16),
                             (1,(-1.16,-.22,0),(0,-.13),(0,.12),.3)])
            self.motion(michael,[(0,(1.20,-.15,0),(0,0),(0,0),0),(.62,(1.19,-.18,0),(-.77,-.74),(.50,.41),-.28),
                                  (1,(1.18,-.16,0),(-.27,-.19),(.28,.16),-.16)])
        elif action=="party_power":
            self.motion(leo,[(0,(-1.18,-.25,0),(0,-.53),(0,.30),0),(.45,(-1.08,-.25,0),(0,-.95),(0,.61),.24),
                             (1,(-1.19,-.24,0),(0,-.26),(0,.32),-.05)])
            self.motion(michael,[(0,(1.20,-.15,0),(0,0),(0,0),0),(.58,(1.22,-.16,0),(-.12,-.30),(.29,.37),-.28),
                                  (1,(1.25,-.19,0),(0,-.13),(0,.20),-.28)])
            for lamp in (obj.data for obj in self.r.scene.objects if obj.type=="LIGHT"):
                initial=lamp.energy
                self.key(lamp,"energy",[(0,initial),(.54,initial),(.56,initial*.12),(1,initial*.17)])
        else:
            self.motion(leo,[(0,(-1.18,-.25,0),(0,-.55),(0,.35),0),(.33,(-1.13,-.23,0),(0,-.91),(0,.55),.22),
                             (.62,(-.90,-1.48,0),(-.29,.32),(.22,.34),-.50),(1,(-.65,-1.90,0),(0,-.83),(0,.57),-.95)])
            self.motion(michael,[(0,(1.20,-.15,0),(-.45,0),(.28,0),0),(.25,(1.20,-.16,0),(-.90,0),(.48,0),.04),
                                  (.50,(1.21,-.15,0),(-.55,0),(.29,0),-.05),(1,(.93,-.46,0),(-.63,0),(.47,0),-.60)])
        speaker=self.speaker((.05,-.06,1.036))
        red=self.cup("Michael's cup",(.49,-.32,.838),self.m["rose"])
        white=self.cup("Leo's cup",(-.44,-.29,.838),self.r.cream)
        if action=="party_power":
            plug=self.block("Speaker plug",(-.44,.16,.785),(.16,.08,.061),self.m["navy"],.012)
            self.key(plug,"location",[(0,(-.55,.17,.90)),(.43,(-.27,.16,.83)),(.53,(-.23,.16,.82)),(1,(-.23,.16,.82))])
            self.camera((0,(-1.47,-1.96,2.01),(-.07,-.08,1.30),41),
                        (.33,(-1.18,-1.64,1.89),(-.10,-.06,1.30),44),
                        (.35,(-.35,-1.07,1.41),(-.12,.04,.98),48),
                        (1,(-.21,-.97,1.37),(-.10,.04,.98),50),indoors=True)
        elif action=="party_beat":
            self.key(red,"location",[(0,(.49,-.32,.838)),(.18,(.47,-.32,.99)),(.30,(.46,-.34,.838)),(1,(.46,-.34,.838))])
            self.key(white,"location",[(0,(-.44,-.29,.838)),(.33,(-.43,-.29,1.01)),(.45,(-.42,-.31,.838)),(1,(-.42,-.31,.838))])
            self.camera((0,(.10,-1.17,1.85),(0,-.22,.99),43),
                        (.53,(.02,-1.01,1.68),(0,-.24,1.01),48),
                        (.55,(2.10,.20,2.14),(-.43,-2.14,1.46),40),
                        (1,(1.78,.06,2.02),(-.47,-2.16,1.43),46),indoors=True)
        else:
            self.camera((0,(.14,-2.12,2.05),(0,-.10,1.49),32),
                        (.48,(.08,-1.94,1.93),(0,-.12,1.49),34),
                        (.5,(-.51,-1.72,1.83),(1.16,-.15,1.77),48),
                        (1,(-.39,-1.54,1.80),(1.16,-.15,1.77),50),indoors=True)

    def dance(self):
        self.neighborhood()
        leo=self.person("Leo",(-.75,-.94,.22),.10)
        michael=self.person("Michael",(.77,-.87,.22),-.16)
        for actor, side in ((leo,-1),(michael,1)):
            x=side*.77
            poses=[]
            for i in range(9):
                phase=(-1)**i
                poses.append((i/8,(x+.13*phase,-.93+.10*(i%2),.22+.10*(i%2)),
                              (-.87 if phase>0 else .17,-.88 if phase<0 else .13),
                              (.44 if phase>0 else .18,.43 if phase<0 else .17),.30*phase))
            self.motion(actor,poses)
        lantern=self.block("Battery lantern",(0,-1.53,.24),(.25,.26,.35),self.m["pink"],.053)
        self.block("Lantern base",(0,-1.53,.082),(.32,.32,.077),self.m["navy"],.029)
        self.r.light("AREA",(0,-1.77,.58),118,(1,.20,.56),(0,-.63,1.10),.78)
        if self.action=="party_lantern":
            self.key(lantern,"location",[(0,(.39,-.95,1.12)),(.39,(.18,-1.22,.66)),(.53,(0,-1.53,.24)),(1,(0,-1.53,.24))])
            self.camera((0,(1.20,-3.18,.94),(.13,-1.42,.57),41),
                        (.48,(.77,-2.96,.88),(.09,-1.42,.59),46),
                        (.50,(-2.51,-4.38,1.55),(0,-.91,1.39),37),
                        (1,(-2.12,-4.13,1.64),(0,-.89,1.37),40))
        else:
            self.camera((0,(4.92,-8.55,3.28),(0,-.86,1.42),35),
                        (.48,(4.01,-7.35,2.78),(0,-.89,1.43),38),
                        (.50,(1.20,-4.00,1.82),(0,-.91,1.52),43),
                        (1,(.81,-3.55,1.86),(0,-.92,1.53),44))


def stage_party(renderer, action, frames):
    party = PartySet(renderer, action, frames)
    if action == "party_street":
        party.opening()
    elif action == "party_bedroom":
        party.bedroom()
    elif action == "party_knock":
        party.knock()
    elif action in {"party_invite","party_power","party_beat"}:
        party.living()
    else:
        party.dance()
