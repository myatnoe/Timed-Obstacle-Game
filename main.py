from direct.directbase.DirectStart import *
from direct.showbase.DirectObject import DirectObject
from panda3d.core import CollisionTraverser,CollisionNode
from panda3d.core import CollisionHandlerQueue,CollisionRay
from panda3d.core import Filename,AmbientLight,DirectionalLight
from panda3d.core import PandaNode,NodePath,Camera,TextNode
from panda3d.core import Vec3,Vec4,BitMask32
from direct.gui.OnscreenText import OnscreenText
from direct.actor.Actor import Actor
from panda3d.ai import *
from direct.task import Task
import random, sys, os, math


def addInstructions(pos, msg):
    return OnscreenText(text=msg, style=1, fg=(1,1,1,1),
                        pos=(-1.3, pos), align=TextNode.ALeft, scale = .05)


class World(DirectObject):
    
    def __init__(self):
        DirectObject.__init__(self)
        
        base.setBackgroundColor(0,0,0,1)

        self.gameStarted = 0
        self.gamePaused = 0
        self.timeLeft = 100
        self.showIntroPage()

        self.keyMap = {"left":0, "right":0, "forward":0, "backward":0, "cam-left":0, "cam-right":0}
        self.musicDir = {"intro":"", "playing_game":"", "game_over":""}
        self.acceptOnce('f1', self.startGame)
        self.accept("escape", sys.exit)
        self.accept("arrow_left", self.setKey, ["cam-left",1])
        self.accept("arrow_right", self.setKey, ["cam-right",1])
        self.accept("w", self.setKey, ["forward",1])
        self.accept("a", self.setKey, ["left",1])
        self.accept("s", self.setKey, ["backward", 1])
        self.accept("d", self.setKey, ["right",1])
        self.accept("arrow_left-up", self.setKey, ["cam-left",0])
        self.accept("arrow_right-up", self.setKey, ["cam-right",0])
        self.accept("w-up", self.setKey, ["forward",0])
        self.accept("a-up", self.setKey, ["left",0])
        self.accept("s-up", self.setKey, ["backward", 0])
        self.accept("d-up", self.setKey, ["right",0])

    def showIntroPage(self):

        intro_text = """Controls\n
                        [ESC] : Quit\n
                        [Left/Right Arrow] : Rotate Camera\n
                        [Mouse] : Rotate Camera\n
                        [W,S] : Run Foward & Backward\n
                        [A,D] : Rotate Player
                        """
        self.titleText = OnscreenText(text = "Timed-obstacle Course Game", pos = (0.,0.5), 
        scale = 0.07,fg=(1,0.5,0.5,1),align=TextNode.ACenter,mayChange=1)
        
        self.waitingText = OnscreenText( intro_text, scale = 0.05, fg = (1,1,1,1), shadow=(.1,.1,.1,1))

    def hideIntroPage(self):
        self.titleText.destroy()
        self.waitingText.destroy()

    def pauseGames(self):
        if self.gamePaused:
            self.gamePaused = 0
        else:
            self.gamePaused = 1
        return

    def startGame(self):
        self.gameStarted = 1
        self.hideIntroPage()
        
        # Load Environment and Players
        self.loadEnv()

        self.floater = NodePath(PandaNode("floater"))
        self.floater.reparentTo(render)
        self.isMoving = False

        self.loadMainCharacter()

        taskMgr.add(self.move, "moveTask")
        base.disableMouse()
        base.camera.setPos(self.mainChar.getX(), self.mainChar.getY()+10,2)

        #  Collision
        self.cTrav = CollisionTraverser()
        self.addCollisionOnMainChar()
        self.addCollisionOnCam()

        # Create Actors


        # Add Lighting
        self.createLighting()


    def setKey(self, key, value):
        self.keyMap[key] = value

    def loadEnv(self):
        self.environment = loader.loadModel("models/world")
        self.environment.reparentTo(render)
        self.environment.setPos(0,0,0)

    def loadMainCharacter(self):
        mainCharStartPos = self.environment.find("**/start_point").getPos()
        self.mainChar = Actor("models/ralph",
                            {"run" : "models/ralph-run",
                             "walk": "models/ralph-walk"})
        self.mainChar.reparentTo(render)
        self.mainChar.setScale(.2)
        self.mainChar.setPos(mainCharStartPos)

    def addCollisionOnMainChar(self):
        self.mainCharGroundRay = CollisionRay()
        self.mainCharGroundRay.setOrigin(0,0,1000)
        self.mainCharGroundRay.setDirection(0,0,-1)
        self.mainCharGroundCol = CollisionNode('mainChar')
        self.mainCharGroundCol.addSolid(self.mainCharGroundRay)
        self.mainCharGroundCol.setFromCollideMask(BitMask32.bit(0))
        self.mainCharGroundCol.setIntoCollideMask(BitMask32.allOff())
        self.mainCharGroundColNp = self.mainChar.attachNewNode(self.mainCharGroundCol)
        self.mainCharGroundHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.mainCharGroundColNp, self.mainCharGroundHandler)

    def addCollisionOnCam(self):
        self.camGroundRay = CollisionRay()
        self.camGroundRay.setOrigin(0,0,1000)
        self.camGroundRay.setDirection(0,0,-1)
        self.camGroundCol = CollisionNode('camRay')
        self.camGroundCol.addSolid(self.camGroundRay)
        self.camGroundCol.setFromCollideMask(BitMask32.bit(0))
        self.camGroundCol.setIntoCollideMask(BitMask32.allOff())
        self.camGroundColNp = base.camera.attachNewNode(self.camGroundCol)
        self.camGroundHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.camGroundColNp, self.camGroundHandler)

    def createLighting(self):
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor(Vec4(.3, .3, .3, 1))
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection(Vec3(-5, -5, -5))
        directionalLight.setColor(Vec4(1, 1, 1, 1))
        directionalLight.setSpecularColor(Vec4(1, 1, 1, 1))
        render.setLight(render.attachNewNode(ambientLight))
        render.setLight(render.attachNewNode(directionalLight))

    def move(self, task):

        # If the camera-left key is pressed, move camera left.
        # If the camera-right key is pressed, move camera right.

        base.camera.lookAt(self.mainChar)
        if (self.keyMap["cam-left"]!=0):
            base.camera.setX(base.camera, -20 * globalClock.getDt())
        if (self.keyMap["cam-right"]!=0):
            base.camera.setX(base.camera, +20 * globalClock.getDt())

        # Track mouse movement and set the camera
        md = base.win.getPointer(0)
        x = md.getX()
        y = md.getY()
        if base.win.movePointer(0, base.win.getXSize()/2, base.win.getYSize()/2):
            base.camera.setX(base.camera, (x - base.win.getXSize()/2)* globalClock.getDt())

        startpos = self.mainChar.getPos()

        if (self.keyMap["left"]!=0):
            self.mainChar.setH(self.mainChar.getH() + 300 * globalClock.getDt())
        if (self.keyMap["right"]!=0):
            self.mainChar.setH(self.mainChar.getH() - 300 * globalClock.getDt())
        if (self.keyMap["forward"]!=0):
            self.mainChar.setY(self.mainChar, -25 * globalClock.getDt())
        if (self.keyMap["backward"]!=0):
            self.mainChar.setY(self.mainChar, 25 * globalClock.getDt())

        # If mainChar is moving, loop the run animation.
        # If he is standing still, stop the animation.

        if (self.keyMap["forward"]!=0) or (self.keyMap["backward"]!=0) or (self.keyMap["left"]!=0) or (self.keyMap["right"]!=0):
            if self.isMoving is False:
                self.mainChar.loop("run")
                self.isMoving = True
        else:
            if self.isMoving:
                self.mainChar.stop()
                self.mainChar.pose("walk",5)
                self.isMoving = False

        # If the camera is too far from mainChar, move it closer.
        # If the camera is too close to mainChar, move it farther.

        camvec = self.mainChar.getPos() - base.camera.getPos()
        camvec.setZ(0)
        camdist = camvec.length()
        camvec.normalize()
        if (camdist > 10.0):
            base.camera.setPos(base.camera.getPos() + camvec*(camdist-10))
            camdist = 10.0
        if (camdist < 5.0):
            base.camera.setPos(base.camera.getPos() - camvec*(5-camdist))
            camdist = 5.0

        # Now check for collisions.

        self.cTrav.traverse(render)

        # Adjust mainChar's Z coordinate.  If mainChar's ray hit terrain,
        # update his Z. If it hit anything else, or didn't hit anything, put
        # him back where he was last frame.

        entries = []
        for i in range(self.mainCharGroundHandler.getNumEntries()):
            entry = self.mainCharGroundHandler.getEntry(i)
            entries.append(entry)
        entries.sort(lambda x,y: cmp(y.getSurfacePoint(render).getZ(),
                                     x.getSurfacePoint(render).getZ()))
        if (len(entries)>0) and (entries[0].getIntoNode().getName() == "terrain"):
            self.mainChar.setZ(entries[0].getSurfacePoint(render).getZ())
        else:
            self.mainChar.setPos(startpos)

        # Keep the camera at one foot above the terrain,
        # or two feet above mainChar, whichever is greater.
        
        entries = []
        for i in range(self.camGroundHandler.getNumEntries()):
            entry = self.camGroundHandler.getEntry(i)
            entries.append(entry)
        entries.sort(lambda x,y: cmp(y.getSurfacePoint(render).getZ(),
                                     x.getSurfacePoint(render).getZ()))
        if (len(entries)>0) and (entries[0].getIntoNode().getName() == "terrain"):
            base.camera.setZ(entries[0].getSurfacePoint(render).getZ()+1.0)
        if (base.camera.getZ() < self.mainChar.getZ() + 2.0):
            base.camera.setZ(self.mainChar.getZ() + 2.0)
            
        # The camera should look in mainChar's direction,
        # but it should also try to stay horizontal, so look at
        # a floater which hovers above mainChar's head.
        
        self.floater.setPos(self.mainChar.getPos())
        self.floater.setZ(self.mainChar.getZ() + 2.0)
        base.camera.lookAt(self.floater)

        return task.cont

base.w = World()
run()
