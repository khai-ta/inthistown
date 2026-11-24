"""Street, room and prop blocking for the recruiting-season short."""

import math

from party_scene import PartySet


SCREEN = {
    "desk": ("FRIDAY", "9:03 PM", "One more application"),
    "profile": ("LinkedIn", "JOBS FOR YOU", "Search software internships"),
    "resume": ("APPLICATION", "UPLOAD RESUME", "Now enter your work history"),
    "submit": ("APPLICATION", "SUBMITTED", "Application count: 47"),
    "reject": ("INBOX", "UPDATE", "We chose other applicants"),
    "next": ("JOBS", "NEXT APPLICATION", "Application count: 48"),
    "grind": ("LeetCode", "REVERSE LINKED LIST", "1 -> 2 -> 3 -> NULL"),
    "failed": ("TEST CASE", "WRONG ANSWER", "Expected 3. Received 1."),
    "accepted": ("LeetCode", "ACCEPTED", "All test cases passed"),
    "calendar": ("CALENDAR", "INTERVIEW INVITE", "Tuesday 10:00 AM"),
    "prep": ("MOCK INTERVIEW", "CONNECTING", "Tell me about yourself"),
    "waiting": ("INTERVIEW", "CALL ENDED", "Back to waiting"),
    "night": ("INBOX", "NO NEW MAIL", "12:48 AM"),
    "uncertain": ("INBOX", "REFRESHING", "Still no new messages"),
    "montage": ("PRACTICE", "KEEP GOING", "Apply. Solve. Prepare."),
    "morning": ("SATURDAY", "8:12 AM", "A fresh start"),
    "ending": ("LeetCode", "IN PROGRESS", "One test case left"),
}


class RecruitingSet(PartySet):
    def __init__(self, renderer, action, frames):
        super().__init__(renderer, action, frames)
        self.beat = action.removeprefix("recruit_")

    def leo(self, position, yaw, interview=False):
        shirt = self.r.material("Interview shirt" if interview else "Campus hoodie",
                                (.75,.83,.86) if interview else (.056,.37,.55))
        return self.r.roblox_actor("Leo",position,shirt,self.r.brown,yaw,False,"party_leo")

    def text(self, label, x, y, z, size, material):
        return self.r.market_lettering(label,(x,y,z),size,material)

    def street(self):
        self.neighborhood()
        r,m,b=self.r,self.m,self.block
        # The party venue sits off the same sidewalk used in the later walk.
        b("Venue facade",(0,.37,1.48),(5.3,.29,2.96),m["navy"],.07,solid=True)
        b("Venue entry",(0,.19,1.07),(1.48,.08,2.14),m["rose"])
        self.text("FRIDAY SOCIAL",0,.174,2.51,.34,m["pink"])
        for x in (-1.69,1.69):
            b("Lit venue window",(x,.19,1.40),(1.19,.065,1.29),m["pink"],.07)
        for x in (-2.15,-1.34,-.53,.28,1.09,1.90):
            b("String light",(x,-.06,2.78),(.115,.108,.115),m["warm"],.048)
        r.light("AREA",(0,-.9,2.72),190,(1,.21,.49),(0,-2.41,.88),3.3)
        guests=[(-3.2,-2.84,.52,"walk"),(-2.19,-1.56,.33,"react"),(-.42,-1.43,.05,"talk"),
                (.94,-1.35,-.29,"react"),(2.05,-1.51,-.32,"talk"),(3.17,-2.62,-.42,"walk")]
        r.market_crowd(guests,self.frames)
        if self.beat=="city":
            self.camera((0,(6.5,-8.51,3.23),(0,-1.15,1.38),35),
                        (.44,(4.18,-6.80,2.66),(.27,-1.43,1.43),39),
                        (.46,(-2.80,-4.42,1.94),(-.18,-1.28,1.58),36),
                        (1,(-2.29,-3.91,1.83),(-.12,-1.37,1.57),42))
            return
        actor=self.leo((-.59,-3.21,0),.31)
        self.motion(actor,[(0,(-.59,-3.21,0),(0,0),(0,0),0),(.48,(.05,-3.24,0),(-.17,.21),(.11,.19),.18),
                           (1,(1.25,-3.28,0),(.21,-.14),(.19,.14),.16)])
        self.camera((0,(3.51,-6.50,2.19),(-.12,-2.64,1.46),36),
                    (.49,(2.81,-6.28,2.10),(.41,-2.78,1.49),38),
                    (.51,(-2.25,-5.28,2.10),(.05,-2.67,1.52),35),
                    (1,(-1.63,-5.02,2.04),(.72,-2.83,1.52),37))

    def screen(self, beat):
        r,m,b=self.r,self.m,self.block
        x,y,z=.58,-.02,1.52
        b("Monitor shell",(x,y,z),(1.48,.14,.93),m["navy"],.06,solid=True)
        b("Monitor screen",(x,y+.082,z),(1.34,.024,.79),m["fabric"],.027)
        b("Monitor stand neck",(x,y,.98),(.15,.15,.29),m["navy"])
        b("Monitor stand foot",(x,y-.03,.862),(.51,.37,.046),m["navy"])
        title, hero, detail=SCREEN[beat]
        status = r.teal if beat in {"accepted","submit"} else r.red if beat in {"reject","failed"} else m["navy"]
        b("Screen header",(x,y+.10,z+.305),(1.31,.018,.15),m["navy"],.012)
        self.text(title,x,y+.12,z+.303,.090,r.cream).rotation_euler.z=math.pi
        b("Status card",(x,y+.103,z+.053),(1.18,.018,.23),status,.024)
        self.text(hero,x,y+.126,z+.055,.105,r.cream).rotation_euler.z=math.pi
        self.text(detail,x,y+.121,z-.161,.065,r.cream).rotation_euler.z=math.pi
        if beat == "montage":
            for index,(label,color) in enumerate((("APPLICATION SENT",r.teal),
                                                 ("PROBLEM ACCEPTED",r.teal),
                                                 ("INTERVIEW NOTES",m["navy"]))):
                plate = r.group(label,(x,y+.143,z+.057))
                r.piece(plate,"Montage status", (0,0,0),(1.24,.024,.24),color,.023)
                text = r.market_lettering(label,(0,.019,0),.095,r.cream,plate)
                text.rotation_euler.z=math.pi
                start=max(1,self.time(index/3))
                end=self.time((index+1)/3)
                for frame,visible in ((1,False),(start,True),(end-1,True),(end,False)):
                    plate.scale=(1,)*3 if visible else (.001,)*3
                    plate.keyframe_insert(data_path="scale",frame=frame)
        if beat in {"resume","grind","prep"}:
            for index in range(3):
                b("Entry guide",(x-.21+.09*index,y+.117,z-.27),(1.06-.18*index,.02,.018),m["window"],.004)

    def bedroom(self):
        r,m,b=self.r,self.m,self.block
        self.room(bedroom=True)
        b("Shared desk",(.32,.04,.76),(2.42,1.04,.15),r.brown,.045,solid=True)
        for x in (-.67,1.30):
            b("Desk leg",(x,.05,.36),(.13,.78,.71),r.ink)
        b("Keyboard",(.27,.31,.861),(.66,.22,.046),m["navy"],.013)
        for i in range(12):
            b("Key",(-.005+.047*i,.31,.895),(.032,.11,.017),m["walk"],.004)
        b("Mouse",(.77,.32,.888),(.15,.20,.089),m["navy"],.045)
        for index in range(3 if self.beat in {"night","reflect","uncertain"} else 1):
            self.cup("Coffee cup",(-.76+.117*index,.19+.10*(index%2),.932),r.cream)
            b("Coffee lid",(-.76+.117*index,.19+.10*(index%2),1.023),(.166,.166,.031),m["navy"],.019)
        b("Desk lamp base",(1.29,.26,.865),(.25,.25,.052),m["navy"])
        b("Desk lamp stem",(1.29,.26,1.113),(.06,.06,.51),m["navy"])
        b("Desk lamp shade",(1.23,.22,1.383),(.37,.33,.15),m["warm"],.046)
        r.light("AREA",(1.21,.03,1.35),42,(1,.56,.27),(.17,-.39,.85),.37)
        if self.beat in {"grind","failed","accepted","prep"}:
            b("Whiteboard frame",(.97,3.49,1.97),(1.94,.10,1.10),r.brown,.023)
            b("Whiteboard",(.97,3.42,1.97),(1.79,.026,.97),r.cream,.021)
            self.text("1  ->  2  ->  3",.98,3.395,2.10,.14,r.ink)
            self.text("3  <-  2  <-  1",.98,3.395,1.83,.14,r.teal)
        if self.beat=="morning":
            r.light("AREA",(-1.95,-2.2,2.27),380,(1,.74,.47),(-.98,.16,1.05),1.6)
            for side in (-1,1):
                curtain=b("Morning curtain",(-1.94+side*.30,-2.435,1.78),(.64,.11,1.37),m["rose"],.046)
                self.key(curtain,"location",[(0,(-1.94+side*.30,-2.435,1.78)),
                    (.42,(-1.94+side*.30,-2.435,1.78)),(.82,(-1.94+side*.84,-2.435,1.78))])
        if self.beat in {"mirror_first","mirror_second","mirror_third"}:
            b("Mirror",(1.89,3.47,1.72),(1.24,.07,1.38),m["window"])
            for side in (-1,1):
                b("Mirror frame",(1.89+side*.63,3.42,1.72),(.065,.10,1.40),r.brown)
            self.text("INTERVIEW PRACTICE",-1.12,3.46,2.27,.14,r.cream)
        elif self.beat == "waiting":
            b("Laptop keyboard",(.41,.19,.862),(.82,.57,.076),m["navy"],.04)
            lid=r.group("Laptop hinge",(.41,-.06,.905))
            r.piece(lid,"Laptop lid",(0,0,.26),(.82,.07,.53),m["navy"],.042)
            r.piece(lid,"Laptop display",(0,.044,.26),(.73,.013,.45),m["window"],.023)
            end=r.market_lettering("CALL ENDED",(0,.056,.26),.077,r.cream,lid)
            end.rotation_euler.z=math.pi
            self.key(lid,"rotation_euler",[(0,(0,0,0)),(.53,(0,0,0)),(.82,(-1.48,0,0)),(1,(-1.48,0,0))])
        else:
            self.screen(self.beat if self.beat in SCREEN else "night")
        if self.beat=="ending":
            phone=r.group("Phone",(-.66,-.30,1.10))
            r.piece(phone,"Case",(0,0,0),(.57,.11,.41),m["navy"],.052)
            r.piece(phone,"Lit screen",(0,-.061,0),(.50,.022,.34),m["window"],.043)
            r.market_lettering("You coming out",(0,-.081,.061),.061,r.cream,phone)
            r.market_lettering("tonight?",(0,-.081,-.066),.073,r.cream,phone)
            cover=r.piece(phone,"Unlit screen",(0,-.089,0),(.50,.014,.34),m["navy"],.034)
            self.key(cover,"scale",[(0,(1,)*3),(.12,(1,)*3),(.15,(.001,)*3)])

    def work(self):
        self.bedroom()
        beat=self.beat
        if beat.startswith("mirror"):
            actor=self.leo((1.68,2.58,0),.04,True)
            self.motion(actor,[(0,(1.68,2.58,0),(-.20,-.11),(.14,.10),-.11),
                               (1,(1.69,2.58,0),(-.48,-.26),(.29,.18),.20)])
            offsets={"mirror_first":(1.34,.82,1.94),"mirror_second":(2.54,.95,2.01),
                     "mirror_third":(1.56,1.19,1.85)}
            x,y,z=offsets[beat]
            self.camera((0,(x,y,z),(1.68,2.57,1.78),45),
                        (1,(x,y+.18,z),(1.68,2.57,1.78),50),indoors=True)
            return
        actor=self.leo((-.61,.62,0),.16,beat in {"prep","waiting"})
        if beat == "morning":
            self.motion(actor,[(0,(-.61,.62,0),(0,-.24),(0,.37),.02),
                (.40,(-.86,-.31,0),(-.13,.26),(.19,.31),-.78),
                (.58,(-1.49,-1.61,0),(-.53,-.54),(.32,.34),-2.41),
                (.86,(-1.64,-1.72,0),(-.92,-.91),(.44,.46),-2.55),
                (1,(-1.60,-1.68,0),(-.24,-.39),(.18,.22),-2.40)])
        else:
            self.motion(actor,[(0,(-.61,.62,0),(0,-.24),(0,.37),.02),
                               (.34,(-.60,.57,0),(-.26,-.83),(.26,.39),.15),
                               (.70,(-.60,.53,0),(-.55,-.27),(.40,.21),-.16),
                               (1,(-.61,.62,0),(-.15,-.28),(.18,.25),.06)])
        if beat=="ending":
            self.camera((0,(-1.05,-1.55,1.48),(-.65,-.31,1.13),51),
                        (.51,(-.93,-1.42,1.45),(-.66,-.30,1.13),54),
                        (.53,(1.34,1.75,1.83),(.59,-.03,1.53),45),
                        (1,(1.17,1.60,1.78),(.59,-.03,1.54),49),indoors=True)
        elif beat == "morning":
            self.camera((0,(-2.60,-2.11,2.39),(-.58,.49,1.39),35),
                        (.41,(-2.22,-1.76,2.18),(-.61,.54,1.51),39),
                        (.43,(.12,-.78,2.06),(-1.88,-2.45,1.81),36),
                        (1,(-.10,-1.12,1.93),(-1.91,-2.42,1.80),43),indoors=True)
        elif beat in {"desk","night","reflect","waiting"}:
            self.camera((0,(-2.60,-2.11,2.39),(-.58,.49,1.39),35),
                        (1,(-2.22,-1.76,2.18),(-.61,.54,1.51),39),indoors=True)
        else:
            self.camera((0,(-2.11,-2.12,2.03),(-.19,.22,1.54),36),
                        (.37,(-1.90,-1.91,1.98),(-.11,.22,1.53),38),
                        (.39,(1.27,1.72,1.78),(.59,-.03,1.54),44),
                        (1,(1.12,1.41,1.69),(.59,-.03,1.54),53 if beat=="failed" else 47),indoors=True)


def stage_recruiting(renderer, action, frames):
    stage = RecruitingSet(renderer, action, frames)
    if stage.beat in {"city", "walk"}:
        stage.street()
    else:
        stage.work()
