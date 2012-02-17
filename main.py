from direct.directbase.DirectStart import *
from direct.showbase.DirectObject import DirectObject
from direct.gui.DirectGui import *
from panda3d.core import CollisionTraverser, CollisionNode
from panda3d.core import CollisionHandlerQueue,CollisionRay, CollisionSphere
from panda3d.core import Filename,AmbientLight,DirectionalLight
from panda3d.core import PandaNode,NodePath,Camera,TextNode
from panda3d.core import Vec3,Vec4,BitMask32
from direct.gui.OnscreenText import OnscreenText
from direct.actor.Actor import Actor
from panda3d.ai import *
from direct.task import Task
import random, sys, os, math

class World(DirectObject):
    
    def __init__(self):
        DirectObject.__init__(self)
        base.setBackgroundColor(0,0,0,1)

        self.gameStarted = 0
        self.gamePaused = 0
        self.timeLeft = 100
        self.speed = 2
        self.obstacle_count = 10

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
        
        # Songs
        self.loadSongs()
        self.showIntroPage()

    def loadSongs(self):
        self.start_song = base.loader.loadSfx("./songs/start.mp3")
        self.play_song = base.loader.loadSfx("./songs/playing.mp3")
        self.win_song = base.loader.loadSfx("./songs/win.mp3")
        self.gameover_song = base.loader.loadSfx("./songs/gameover.mp3")

    def changeSongMode(self, sound):
        if sound.status() == sound.PLAYING:
            sound.stop()
        else:
            sound.play()
            sound.setLoop(True)

    def showIntroPage(self):
        control_direction_texts = ["Controls", "~~~~~~~~~~~~~~~~~~",
                        "[ESC] : Quit",
                        "[Left/Right Arrow] : Rotate Camera",
                        "[Mouse] : Rotate Camera",
                        "[W,S] : Run Foward & Backward",
                        "[A,D] : Rotate Player",]
        self.title_txt = OnscreenText(text = "Timed-obstacle Course Game\nAssignment - 2 (P14)\nMichelle 91148", pos = (0.,0.5), scale = 0.07,fg=(1,0.5,0.5,1),align=TextNode.ACenter,mayChange=1)
        
        # self.control_direction = OnscreenText( intro_text, scale = 0.05, fg = (1,1,1,1), shadow=(.1,.1,.1,1))
        self.control_direction = []
        pos = 0
        for direction in control_direction_texts:
            self.control_direction.append(OnscreenText(direction, scale = 0.05, fg=(1,1,1,1), shadow=(.1,.1,.1,.1), pos=(0,pos)))
            pos -= .07
        self.btn_play = DirectButton(text = ("PLAY","PLAY","PLAY","disabled"), scale=.1,command=self.startGame, pos=(0.,0.,-0.7))
        if not self.start_song.status() == self.start_song.PLAYING:
            self.start_song.play()
            self.start_song.setLoop(True)

    def hideIntroPage(self):
        self.title_txt.destroy()
        for control in self.control_direction:
            control.destroy()
        self.btn_play.destroy()
        if self.start_song.status() == self.start_song.PLAYING:
            self.start_song.stop()
        
    def showHUD(self):
        self.timeleft_txt = OnscreenText(text = "Time Left: %s"%self.time_left,pos = (0.9, 0.9), scale = 0.05, fg=(1,1,1,1), align=TextNode.ACenter,mayChange=1)
        self.health_txt = OnscreenText(text = "Health : %s"%self.health, pos=(-0.95, 0.9), scale = 0.05, fg=(1,1,1,1), align=TextNode.ACenter, mayChange=1)
        if not self.play_song.status() == self.play_song.PLAYING:
            self.play_song.play()
            self.play_song.setLoop(True)

    def hideHUD(self):
        self.timeleft_txt.destroy()
        self.health_txt.destroy()
        if self.play_song.status() == self.play_song.PLAYING:
            self.play_song.stop()

    def showRestartPage(self):
        self.game_status_txt = OnscreenText(text = "Erh...", pos = (0.,0.5), scale = 0.07,fg=(1,1,1,1),align=TextNode.ACenter,mayChange=1)
        self.restart_btn = DirectButton(text = ("RESTART","RESTART","RESTART","disabled"), scale=.1, command=self.restartGame, pos=(0,0,-0.7))

    def pauseGame(self):
        if self.gamePaused:
            self.gamePaused = 0
        else:
            self.gamePaused = 1
        return

    def startGame(self):
        self.gameStarted = 1
        self.hideIntroPage()
        self.play_song.play()
        self.play_song.setLoop(True)
        self.AIworld = AIWorld(render)
        
        # Load Environment and Players
        self.loadEnv()

        self.floater = NodePath(PandaNode("floater"))
        self.floater.reparentTo(render)
        self.isMoving = False

        self.loadMainCharacter()
        self.loadStartPoint()
        self.loadEndPoint()
        self.loadEffects()

        base.disableMouse()
        base.camera.setPos(self.mainChar.getX(), self.mainChar.getY()+10,2)

        #  Collision
        self.cTrav = CollisionTraverser()
        self.addCollisionOnMainChar()
        self.addCollisionOnCam()
        self.loadObstacles()

        # Create Actors

        # Add Lighting
        self.createLighting()

        # Counters - Time Limit
        self.total_time = 120 # 2 mins in seconds
        self.time_left = 120 # 2 mins in seconds
        # self.total_time = 5 # 2 mins in seconds
        # self.time_left = 5 # 2 mins in seconds
        self.health = 100
        self.showHUD()

        # Task Manager to control the game
        taskMgr.add(self.updateGame, "updateGameTask")
        taskMgr.add(self.updateHUD, "updateHUDTask")
        # taskMgr.add(self.updateEffects, "updateEffectsTask")
        taskMgr.add(self.updateSpeedPill, "updateSpeedPillTask")
        taskMgr.add(self.updateHealthPill, "updateHealthPillTask")
        taskMgr.add(self.updateShieldPill, "updateShieldPillTask")
        taskMgr.add(self.checkGameStage, "checkGameStageTask")
        taskMgr.add(self.AIUpdate, "AIUpdate")

    def restartGame(self):
        self.game_status_txt.destroy()
        self.restart_btn.destroy()
        self.removeNodes()

        # need to stop the winning or losing songs
        if self.win_song.status() == self.win_song.PLAYING:
            self.win_song.stop()
        if self.gameover_song.status() == self.gameover_song.PLAYING:
            self.gameover_song.stop()

        self.startGame()

    def removeNodes(self):
        self.mainChar.removeNode()
        self.panda.removeNode()
        for i in range(self.obstacle_count):
            self.flockers[i].removeNode()
        self.start_point.removeNode()
        self.end_point.removeNode()

    def setKey(self, key, value):
        self.keyMap[key] = value

    def loadEnv(self):
        self.environment = loader.loadModel("models/world")
        self.environment.reparentTo(render)
        self.environment.setPos(0,0,0)

    def loadMainCharacter(self):
        mainCharStartPos = self.environment.find("**/start_point").getPos()
        self.mainChar = Actor("models/eve/eve",
                            {"run" : "models/eve/eve-run",
                             "walk": "models/eve/eve-walk"})
        self.mainChar.reparentTo(render)
        self.mainChar.setScale(.2)
        self.mainChar.setPos(mainCharStartPos)

    def loadStartPoint(self):
        self.start_point = Actor("models/frowney")
        self.start_point.reparentTo(render)
        self.start_point.setScale(.5)
        self.start_point.setPos(self.mainChar.getPos())
        self.start_point.setX(self.mainChar.getX() - .7)

    def loadEndPoint(self):
        """
            chosen end position = point3(30.9069, 4.36755, 2.91223)
        """
        self.end_point = Actor("models/smiley")
        self.end_point.reparentTo(render)
        self.end_point.setScale(.5)
        self.end_point.setPos(30.9069, 4.36755, 3.4)

    def loadEffects(self):
        self.speed_dog = Actor("models/dog/evilaibodog")
        self.speed_dog.reparentTo(render)
        self.speed_dog.setScale(.5)
        self.speed_dog.setPos(-71.5866, 43.2459, 2.17505)

        self.health_milk = Actor("models/milk/milkbottle")
        self.health_milk.reparentTo(render)
        self.health_milk.setScale(3)
        self.health_milk.setPos(-81.977, -31.9481, 0.155029)

        self.time_plant = Actor("models/plant/shrubbery2")
        self.time_plant.reparentTo(render)
        self.time_plant.setScale(.003)
        self.time_plant.setPos(-75.8541, 3.21947, 6.19539)

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

    def loadObstacles(self):
        startPos = self.start_point.getPos()
        
        #Load the panda actor for static obstacle
        self.panda = Actor("models/panda-model",{"walk":"models/panda-walk4"})
        self.panda.setScale(0.0009,0.0009,0.0009)
        self.panda.reparentTo(render)
        self.panda.setPos(startPos[0],startPos[1]-5,startPos[2])
        self.panda.setH(self.panda.getH() + 3)
        # self.panda.setPos(startPos)
        # self.panda.setPos(startPos[0], startPos[1], startPos[2])
        
        self.pandaGroundRay = CollisionRay()
        self.pandaGroundRay.setOrigin(0,0,1000)
        self.pandaGroundRay.setDirection(0,0,-1)
        self.pandaGroundCol = CollisionNode('pandaRay')
        self.pandaGroundCol.addSolid(self.pandaGroundRay)
        self.pandaGroundCol.setFromCollideMask(BitMask32.bit(0))
        self.pandaGroundCol.setIntoCollideMask(BitMask32.allOff())
        self.pandaGroundColNp = self.panda.attachNewNode(self.pandaGroundCol)
        self.pandaGroundHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.pandaGroundColNp, self.pandaGroundHandler)

        ##### Flockers
        self.flockers = []
        self.flockersGroundRay = []
        self.flockersGroundCol = []
        self.flockersGroundColNp = []
        self.flockersGroundHandler = []
        self.AIchar = []
        self.AIbehaviors = []

        #Flock AI functions
        self.MyFlock = Flock(1, 270, 10, 2, 4, 0.8)
        self.AIworld.addFlock(self.MyFlock)
        self.AIworld.flockOn(1);
        for i in range(self.obstacle_count):
            self.flockers.append(Actor("models/panda-model",
                                     {"walk":"models/panda-walk4"}))
            self.flockers[i].reparentTo(render)
            self.flockers[i].setScale(0.001)
            self.flockers[i].setPos(startPos[0],startPos[1]-10,startPos[2])
            self.flockers[i].loop("walk")

            # Ground Ray
            self.flockersGroundRay.append(CollisionRay())
            self.flockersGroundRay[i].setOrigin(0,0,1000)
            self.flockersGroundRay[i].setDirection(0,0,-1)
            self.flockersGroundCol.append(CollisionNode('flockerRay%s'%i))
            self.flockersGroundCol[i].addSolid(self.flockersGroundRay[i])
            self.flockersGroundCol[i].setFromCollideMask(BitMask32.bit(0))
            self.flockersGroundCol[i].setIntoCollideMask(BitMask32.allOff())
            self.flockersGroundColNp.append(self.flockers[i].attachNewNode(self.flockersGroundCol[i]))
            self.flockersGroundHandler.append(CollisionHandlerQueue())
            self.cTrav.addCollider(self.flockersGroundColNp[i], self.flockersGroundHandler[i])

            self.AIchar.append(AICharacter("flockersAI%s"%i,self.flockers[i], 100, 0.05, 5))
            self.AIworld.addAiChar(self.AIchar[i])
            self.AIbehaviors.append(self.AIchar[i].getAiBehaviors())
            self.MyFlock.addAiChar(self.AIchar[i])
            self.AIbehaviors[i].flock(1)
            self.AIbehaviors[i].pursue(self.mainChar, 0.4)

            taskMgr.add(self.moveFlockers, "moveFlockersTask")
 
    def createLighting(self):
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor(Vec4(.3, .3, .3, 1))
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection(Vec3(-5, -5, -5))
        directionalLight.setColor(Vec4(1, 1, 1, 1))
        directionalLight.setSpecularColor(Vec4(1, 1, 1, 1))
        render.setLight(render.attachNewNode(ambientLight))
        render.setLight(render.attachNewNode(directionalLight))

    def AIUpdate(self, task):
        self.AIworld.update()
        return Task.cont

    def checkGameStage(self, task):
        """
            GUI with time taken and restart button when player reaches end point or reaches zero health.
        """
        # player reach end point
        player_endpoint_distance = self.mainChar.getDistance(self.end_point)
        if player_endpoint_distance < 4:
            taskMgr.remove('updateHUDTask')
            taskMgr.remove('updateGameTask')
            taskMgr.remove('updateSpeedPill')
            taskMgr.remove('updateHealthPill')
            taskMgr.remove('updateShieldPill')
            self.hideHUD()
            self.showRestartPage()
            self.changeSongMode(self.win_song)
            if self.play_song.status() == self.play_song.PLAYING:
                self.play_song.stop()
            self.game_status_txt.setText("You WIN!")
            return task.done

        if (self.time_left <= 0 or self.health <= 0):
            taskMgr.remove('updateHUDTask')
            taskMgr.remove('updateGameTask')
            taskMgr.remove('updateSpeedPill')
            taskMgr.remove('updateHealthPill')
            taskMgr.remove('updateShieldPill')
            self.hideHUD()
            self.showRestartPage()
            self.changeSongMode(self.gameover_song)
            if self.play_song.status() == self.play_song.PLAYING:
                self.play_song.stop()
            self.game_status_txt.setText("Game Over")
            return task.done
        return task.cont

    def updateHUD(self, task):

        # update time
        self.time_left = self.total_time - int(task.time)
        self.timeleft_txt.setText("Time Left: %s"%self.time_left)

        # update health
        for i in range(self.obstacle_count):
            dis = self.mainChar.getDistance(self.flockers[i])
            if dis < 500:
                self.health -= 1
        dis = self.mainChar.getDistance(self.panda)
        if dis < 500:
            self.health -= 1
        self.health_txt.setText("Health : %s"%self.health)
        return task.cont

    def updateSpeedPill(self, task):

        dis = self.mainChar.getDistance(self.speed_dog)
        if dis < 2:
            self.speed_dog.removeNode()
            self.speed = 4
            return task.done
        return task.cont

    def updateHealthPill(self, task):

        dis = self.mainChar.getDistance(self.health_milk)
        if dis < 2:
            self.health = 100
            self.health_milk.removeNode()
            return task.done
        return task.cont

    def updateShieldPill(self, task):
        dis = self.mainChar.getDistance(self.time_plant)
        if dis < 200:
            self.time_plant.removeNode()
            self.total_time += 20
            return task.done
        return task.cont

    def updateGame(self, task):

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
            self.mainChar.setY(self.mainChar, -25 * globalClock.getDt() * self.speed)
        if (self.keyMap["backward"]!=0):
            self.mainChar.setY(self.mainChar, 25 * globalClock.getDt() * self.speed)

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

    def moveFlockers(self, task):
        
        for i in range(self.obstacle_count):
            startpos = self.flockers[i].getPos()

            entries = []
            for j in range(self.flockersGroundHandler[i].getNumEntries()):
                entry = self.flockersGroundHandler[i].getEntry(j)
                entries.append(entry)
            entries.sort(lambda x,y: cmp(y.getSurfacePoint(render).getZ(),
                                         x.getSurfacePoint(render).getZ()))
            if (len(entries)>0) and (entries[0].getIntoNode().getName() == "terrain"):
                self.flockers[i].setZ(entries[0].getSurfacePoint(render).getZ())
            else:
                self.flockers[i].setPos(startpos)
            
        return task.cont


base.w = World()
run()
