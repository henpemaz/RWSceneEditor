from PyQt5 import QtCore
from PyQt5.QtWidgets import QFileDialog, QProgressDialog
import os
from krita import *

class RWSceneEditor(Extension):
    def __init__(self, parent):
        # This is initialising the parent, always important when subclassing.
        super().__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction("openRWScene", "Open RW Scene", "tools")
        action.triggered.connect(self.openRWScene)
        action = window.createAction("saveRWScene", "Save RW Scene", "tools")
        action.triggered.connect(self.saveRWScene)

    def openRWScene(self):
        k = Krita.instance()

        q = QFileDialog()
        q.setWindowTitle("select positions.txt for the scene")

        q.setNameFilter("positions.txt")
        q.setFileMode(QFileDialog.ExistingFile)

        q.exec_() # show the dialog
        filepath = q.selectedFiles()[0]
        filepath = str(filepath)

        if filepath.endswith("positions.txt") and os.path.exists(filepath):
            with open(filepath) as f:
                positions = [list(map(int,p.split(", "))) for p in f.readlines() if p.strip()]
        else:
            raise Exception("positions.txt not found")

        folderpath = filepath.rsplit("/", 1)[0]
        foldername = folderpath.rsplit("/", 1)[1]
        folderpath += "/"

        if os.path.exists(folderpath + "layers.txt"):
            with open(folderpath + "layers.txt") as f:
                files = [p.strip() for p in f.readlines() if p.strip()]
        elif foldername in known_scenes:
            files = known_scenes[foldername]
        else:
            raise Exception("layers.txt not found")

        progress = QProgressDialog("Loading scene...", None, 0, len(files) + 2)
        progress.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        progress.forceShow()

        doc = k.createDocument(1920, 1080, foldername, "RGBA", "U8", "", 300.0)
        progress.setValue(progress.value() + 1)

        for i, f in enumerate(files):
            #print(f)
            layername = f
            layerfile = layername + ".png"
            img = k.openDocument(folderpath + layerfile)
            dim = (img.width(), (img.height())//2)

            pix = img.pixelData(0, dim[1], dim[0], dim[1])
            depth = doc.createNode(layername + "[dpt]", "paintlayer")
            depth.setPixelData(pix, 0, 0, dim[0], dim[1])
            doc.rootNode().addChildNode(depth, None)
            depth.move((1920 - 1366)//2 + positions[i][0], 1080 - (1080 - 768)//2 -dim[1] - positions[i][1])
            depth.setVisible(False)
            del pix

            pix = img.pixelData(0, 0, dim[0], dim[1])
            image = doc.createNode(layername + "[img]", "paintlayer")
            image.setPixelData(pix, 0, 0, dim[0], dim[1])
            doc.rootNode().addChildNode(image, None)
            image.move((1920 - 1366)//2 + positions[i][0], 1080 - (1080 - 768)//2 -dim[1] - positions[i][1])
            del pix

            img.close()
            img.deleteLater()
            del img
            progress.setValue(progress.value() + 1)

        k.activeWindow().addView(doc) # shows it in the application, also allows actions
        background = doc.rootNode().childNodes()[0]
        doc.setActiveNode(background)
        k.action("reset_fg_bg").trigger()
        k.action("fill_selection_foreground_color").trigger()
        background.setOpacity(255);

        doc.refreshProjection()
        progress.setValue(progress.value() + 1)
        progress.reset()

    def saveRWScene(self):
        k = Krita.instance()

        q = QFileDialog()
        q.setWindowTitle("The folder to save the scene")
        q.setFileMode(QFileDialog.Directory)
        q.setOption(QFileDialog.ShowDirsOnly, True)

        q.exec_() # show the dialog
        scenepath = q.selectedFiles()[0]
        scenepath = str(scenepath)
        if not os.path.exists(scenepath) or len(scenepath) < 1:
            raise Exception("invalid path selected")
        scenepath = scenepath.rstrip("/")
        scenename = scenepath.rsplit("/", 1)[1]
        scenepath+= "/"

        doc = k.activeDocument()
        layers = []
        offsets = []

        for l in doc.topLevelNodes():
            if l.name().endswith("[img]"):
                name = l.name()[:-5]
                l2 = doc.nodeByName(name+"[dpt]")
                if l2 != None:
                    layers.append((name,l,l2))
                else:
                    raise Exception("depth missing for layer " + name)

        progress = QProgressDialog("Saving scene...", None, 0, len(layers) + 2)
        progress.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        progress.forceShow()

        for layer in layers:
            exportlayer = doc.createNode(layer[0], "paintlayer")
            bounds = layer[1].bounds().united(layer[2].bounds())
            x,y,w,h = bounds.getRect()
            exportlayer.setPixelData(layer[1].projectionPixelData(x,y,w,h), x,y,w,h)
            exportlayer.setPixelData(layer[2].projectionPixelData(x,y,w,h), x,y+h,w,h)
            bounds.setHeight(2*h)

            k.setBatchmode(True)
            exportParameters = InfoObject()
            exportParameters.setProperty("alpha", True)
            exportParameters.setProperty("compression", 6)
            exportParameters.setProperty("indexed", False)
            exportlayer.save(scenepath+layer[0]+".png",1,1,exportParameters,bounds)
            k.setBatchmode(False)

            exportlayer.deleteLater()

            offsets.append((x-(1920 - 1366)//2, 1080 - (1080 - 768)//2 - y - h))
            progress.setValue(progress.value() + 1)

        with open(scenepath + "layers.txt",'w') as f:
            f.write("\n".join(l[0] for l in layers))
        progress.setValue(progress.value() + 1)
        with open(scenepath + "positions.txt",'w') as f:
            f.writelines((f"{o[0]}, {o[1]}\n" for o in offsets))

        progress.setValue(progress.value() + 1)
        progress.reset()


known_scenes = {
    "Main Menu": [
        "MainFarBackground",
        "MainArchs",
        "MainWaterfall",
        "MainVines3",
        "MainVines2",
        "MainTerrain1",
        "MainMGLizard2",
        "MainMGLizard1",
        "MainDarken",
        "MainFog",
        "MainVignette",
        "MainFGLizard3",
        "MainFGLizard2",
        "MainFGLizard1",
        "MainVines1"
    ],
    "Sleep Screen - White": [
        "Sleep - 5",
        "Sleep - 4",
        "Sleep - 3",
        "Sleep - 2 - White",
        "Sleep - 1"
    ],
	"Sleep Screen - Yellow": [
        "Sleep - 5",
        "Sleep - 4",
        "Sleep - 3",
        "Sleep - 2 - Yellow",
        "Sleep - 1"
    ],
	"Sleep Screen - Red": [
        "Sleep - 5",
        "Sleep - 4",
        "Sleep - 3",
        "Sleep - 2 - Red",
        "Sleep - 1"
    ],
    "Death Screen": [
        "Death - 5",
        "Death - 4",
        "Death - 3",
        "Death - 2",
        "Death - 1",
        "FlowerA",
        "FlowerA2",
        "FlowerB",
        "FlowerB2",
        "FlowerC",
        "FlowerC2"
    ],
    "New Death": [
        "New Death - 6",
        "New Death - 55",
        "New Death - 5",
        "New Death - 4",
        "New Death - 3",
        "New Death - 2",
        "New Death - 1",
        "FlowerA",
        "FlowerA2",
        "FlowerB",
        "FlowerB2",
        "FlowerC",
        "FlowerC2"
    ],
    "Starve Screen": [
        "Starve - 5",
        "Starve - 4",
        "Starve - 3",
        "Starve - 2",
        "Starve - 1"
    ],
    "Intro 1 - Tree": [
        "11 - Bkg",
        "10 - TerrainC",
        "9 - TerrainB",
        "8 - TerrainA",
        "7 - FoliageB",
        "6 - Trunk",
        "5 - LightC",
        "4 - FoliageA",
        "3 - LightB",
        "2 - LightA",
        "1 - Pipes"
    ],
    "Intro 2 - Branch": [
        "6 - Bkg",
        "5 - Trunk",
        "4 - FoliageB",
        "3 - Slugcats",
        "2 - Light",
        "1 - FoliageA"
    ],
    "Intro 3 - In Tree": [
        "12 - Bkg",
        "11 - TerrainD",
        "10 - RainB",
        "9 - RainA",
        "RainEffect",
        "RainMist",
        "8 - TerrainC",
        "7 - TerrainB",
        "6 - FruitsB",
        "5 - SlugcatB",
        "4 - TerrainA",
        "3 - SlugcatsA",
        "2 - FruitsA",
        "1 - Roots"
    ],
    "Intro 4 - Walking": [
        "7 - RocksD",
        "6 - RocksC",
        "5 - RocksB",
        "4 - RocksA",
        "3 - Pipe",
        "2 - Slugcats",
        "1 - Foreground"
    ],
    "Intro 5 - Hunting": [
        "13 - Bkg",
        "12 - Light",
        "11 - Waterfall",
        "10 - Pillar",
        "9 - Terrain",
        "8 - SlugcatC",
        "7 - SlugcatD",
        "6 - SlugcatB",
        "5 - Specks",
        "4 - CeilingB",
        "3 - CeilingA",
        "2 - SlugcatA",
        "1 - Grass"
    ],
    "Intro 6 - 7 - Rain Drop": [
        "Sharp Ground",
        "Blurred Ground",
        "Sharp Slugcats",
        "Blurred Slugcats",
        "RainDrops"
    ],
    "Intro 8 - Climbing": [
        "9 - PipesB",
        "8 - PipesA",
        "7 - WaterB",
        "6 - RockFormation",
        "5 - RockBloom",
        "4 - ClimbingSlugcat",
        "3 - SlugcatsAndRock",
        "2 - WaterB",
        "1 - RainDistortion",
        "0 - RainFilter",
        "-1 - Dark",
        "-2 - Bloom"
    ],
    "Intro 9 - Rainy Climb": [
        "13 - Background",
        "12 - Flash",
        "11 - BkgAndSlugcat",
        "10 - Terrain",
        "9 - SkyOverlay",
        "8 - BkgWater",
        "7 - WaterFallB",
        "6 - WaterFoamA",
        "5 - WaterFallA",
        "4 - BlurredSlugcats",
        "3 - SlugcatsClimbing",
        "2 - ForegroundWavesB",
        "0 - RainOverlay",
        "1 - ForegroundWaves",
        "WhiteFade"
    ],
    "Intro 10 - Fall": [
        "13 - Background",
        "11 - BkgAndSlugcat",
        "10 - Terrain",
        "9 - SidePipes",
        "3 - DarkSlugcatsClimbing",
        "8.5 - Darken",
        "8 - DarkBkgWater",
        "7 - DarkWaterFallB",
        "6 - DarkWaterFoamA",
        "5 - DarkWaterFallA",
        "2 - DarkForegroundWavesB",
        "1 - DarkForegroundWaves",
        "0 - Lightning",
        "-1 - SkySoftLight",
        "-2 - SkyOverlay",
        "-3 - LightOutline",
        "-4 - FallingSlugcat",
        "0 - RainOverlay",
        "WhiteFade"
    ],
    "Intro 10p5 - Separation": [
        "6 - SlugcatPup",
        "5 - DripsD",
        "4 - DripsC",
        "3 - SlugcatMother",
        "2 - DripsB",
        "1 - DripsA"
    ],
    "Intro 11 - Drowning": [
        "11 - DrowningBkg",
        "10 - FloraC",
        "9 - FloraB",
        "8 - FloraA",
        "7 - BubblesD",
        "6 - BubblesC",
        "5 - Slugcat",
        "4 - BubblesB",
        "3 - BubblesA",
        "2 - LightB",
        "1 - LightA"
    ],
    "Intro 12 - Waking": [
        "3 - Ground",
        "2 - SlugcatWaking",
        "1 - Dust"
    ],
    "Intro 13 - Alone": [
        "12 - AloneBkg",
        "11 - BkgRain",
        "10 - Archways",
        "9 - SlugcatBloom",
        "8 - SlugcatOnRock",
        "7 - Dust",
        "6 - Bloom",
        "5 - Wires",
        "4 - ForegroundRocks",
        "2 - ChainB",
        "1 - ChainA"
    ],
    "Endgame - Survivor": [
        "Survivor - 6",
        "Survivor - 5",
        "Survivor - 4",
        "Survivor - 3",
        "Survivor - 2",
        "Survivor - 1"
    ],
    "Endgame - Hunter": [
        "Hunter - 4",
        "Hunter - 3",
        "Hunter - 2",
        "Hunter - 1"
    ],
    "Endgame - Saint": [
        "Saint - 5",
        "Saint - 4",
        "Saint - 3",
        "Saint - 2",
        "Saint - 1"
    ],
    "Endgame - Wanderer": [
        "Wanderer - 6",
        "Wanderer - 7",
        "Wanderer - 5",
        "Wanderer - 4",
        "Wanderer - 3",
        "Wanderer - 2",
        "Wanderer - 1"
    ],
    "Endgame - Chieftain": [
        "Chieftain - 3",
        "Chieftain - 2",
        "Chieftain - 1"
    ],
    "Endgame - Monk": [
        "Monk - 5",
        "Monk - 4",
        "Monk - 3",
        "Monk - 2",
        "Monk - 1"
    ],
    "Endgame - Outlaw": [
        "Outlaw - 8",
        "Outlaw - 6",
        "Outlaw - 7",
        "Outlaw - 5",
        "Outlaw - 4",
        "Outlaw - 3",
        "Outlaw - 2",
        "Outlaw - 1"
    ],
    "Endgame - DragonSlayer": [
        "DragonSlayer - 2",
        "DragonSlayer - 1"
    ],
    "Endgame - Scholar": [
        "Scholar - 8",
        "Scholar - 7",
        "Scholar - 6",
        "Scholar - 5",
        "Scholar - 4",
        "Scholar - 3",
        "Scholar - 2",
        "Scholar - 1"
    ],
    "Endgame - Friend": [
        "Friend - 4",
        "Friend - 3",
        "Friend - 2",
        "Friend - 1"
    ],
    "Landscape - CC": [
        "CC_Landscape - 4",
        "CC_Landscape - 3",
        "CC_Landscape - 2",
        "CC_Landscape - 1"
    ],
    "Landscape - DS": [
        "DS_Landscape - 6",
        "DS_Landscape - 5",
        "DS_Landscape - 4",
        "DS_Landscape - 3",
        "DS_Landscape - 2",
        "DS_Landscape - 1"
    ],
    "Landscape - GW": [
        "GW_Landscape - 4",
        "GW_Landscape - 3",
        "GW_Landscape - 2",
        "GW_Landscape - 1"
    ],
    "Landscape - HI": [
        "HI_Landscape - 4",
        "HI_Landscape - 3",
        "HI_Landscape - 2",
        "HI_Landscape - 1"
    ],
    "Landscape - LF": [
        "LF_Landscape - 4",
        "LF_Landscape - 3",
        "LF_Landscape - 2",
        "LF_Landscape - 1"
    ],
    "Landscape - SB": [
        "SB_Landscape - 5",
        "SB_Landscape - 4",
        "SB_Landscape - 3",
        "SB_Landscape - 2",
        "SB_Landscape - 1"
    ],
    "Landscape - SH": [
        "SH_Landscape - 5",
        "SH_Landscape - 4",
        "SH_Landscape - 3",
        "SH_Landscape - 2",
        "SH_Landscape - 1"
    ],
    "Landscape - SI": [
        "SI_Landscape - 5",
        "SI_Landscape - 4",
        "SI_Landscape - 3",
        "SI_Landscape - 2",
        "SI_Landscape - 1"
    ],
    "Landscape - SL": [
        "SL_Landscape - 6",
        "SL_Landscape - 5",
        "SL_Landscape - 1",
        "SL_Landscape - 4",
        "SL_Landscape - 1",
        "SL_Landscape - 3",
        "SL_Landscape - 2",
        "SL_Landscape - 1",
        "SL_Landscape - 1"
    ],
    "Landscape - SS": [
        "SS_Landscape - 6",
        "SS_Landscape - 5",
        "SS_Landscape - 4",
        "SS_Landscape - 3",
        "SS_Landscape - 2",
        "SS_Landscape - 1"
    ],
    "Landscape - SU": [
        "SU_Landscape - 3",
        "SU_Landscape - 2",
        "SU_Landscape - 1"
    ],
    "Landscape - UW": [
        "UW_Landscape - 5",
        "UW_Landscape - 4",
        "UW_Landscape - 3",
        "UW_Landscape - 2",
        "UW_Landscape - 1"
    ],
    "Outro 1 - Left Swim": [
        "10 - SlugcatsE",
        "9 - SlugcatsD",
        "8 - SlugcatsC",
        "7 - SlugcatsB",
        "6 - SlugcatsA",
        "5 - MainSlugcat",
        "4 - BlueBloom",
        "3 - CatsBloom",
        "2 - Specks",
        "1 - ForegroundBloom"
    ],
    "Outro 2 - Up Swim": [
        "7 - SwimBkg",
        "6 - BkgSwimmers",
        "5 - MainSwimmer",
        "4 - SlugcatBloomLighten",
        "3 - SlugcatBloomOverlay",
        "2 - Bubbles",
        "1 - ForegroundSlugcats"
    ],
    "Outro 3 - Face": [
        "5 - CloudsB",
        "4 - CloudsA",
        "3 - BloomLights",
        "2 - FaceCloseUp",
        "1 - FaceBloom"
    ],
    "Outro 4 - Tree": [
        "8 - Bkg",
        "7 - Trunk",
        "6 - Foliage",
        "5 - Fog",
        "4 - TreeLight",
        "3 - TreeOverlay",
        "2 - MainSlugcat",
        "1 - SlugcatBloom",
        "0 - ForeGroundSlugcats"
    ],
    "Options Menu Bkg": [
        "3 - OptnsPipe",
        "2 - OptnsSlugcats",
        "1 - OptnsWires"
    ],
    "Dream - Sleep": [
        "DreamSleep - 5",
        "DreamSleep - 4",
        "DreamSleep - LoneSlugcat",
        "DreamSleep - 3",
        "DreamSleep - 2",
        "DreamSleep - 1"
    ],
    "Dream - Acceptance": [
        "Acceptance - 6",
        "Acceptance - 5",
        "Acceptance - 4",
        "Acceptance - 3",
        "Acceptance - 2",
        "Acceptance - 1"
    ],
    "Dream - Iggy": [
        "Iggy - 5",
        "Iggy - 4",
        "Iggy - 3",
        "Iggy - 2",
        "Iggy - 1"
    ],
    "Dream - Iggy Doubt": [
        "Iggy Doubt - 7",
        "Iggy Doubt - 6",
        "Iggy Doubt - 5",
        "Iggy Doubt - 4",
        "Iggy Doubt - 3",
        "Iggy Doubt - 2",
        "Iggy Doubt - 1"
    ],
    "Dream - Iggy Image": [
        "Iggy Image - 9",
        "Iggy Image - 8",
        "Iggy Image - 7",
        "Iggy Image - 6",
        "Iggy Image - 5",
        "Iggy Image - 4",
        "Iggy Image - 3",
        "Iggy Image - 2",
        "Iggy Image - 1"
    ],
    "Dream - Moon Betrayal": [
        "Betrayal - 9",
        "Betrayal - 8",
        "Betrayal - 7",
        "Betrayal - 6",
        "Betrayal - 5",
        "Betrayal - 4",
        "Betrayal - 3",
        "Betrayal - 2",
        "Betrayal - 1"
    ],
    "Dream - Moon Friend": [
        "Friend - 12",
        "Friend - 11",
        "Friend - 10",
        "Friend - 9",
        "Friend - 8",
        "Friend - 7",
        "Friend - 6",
        "Friend - 5",
        "Friend - 4",
        "Friend - 3",
        "Friend - 2",
        "Friend - 1"
    ],
    "Dream - Pebbles": [
        "Pebbles - 10",
        "Pebbles - 9",
        "Pebbles - 9",
        "Pebbles - 8",
        "Pebbles - 7",
        "Pebbles - 6",
        "Pebbles - 5",
        "Pebbles - 4",
        "Pebbles - 3",
        "Pebbles - 2",
        "Pebbles - 1"
    ],
    "Void": [
        "Void - 4",
        "Void - 3",
        "Void - 2",
        "Void - 1",
        "Downwards Slugcat",
        "Upright Slugcat"
    ],
    "Slugcat - White": [
        "White Background - 5",
        "White Haze - 4",
        "White BkgPlants - 3",
        "White Vines - 1",
        "White Slugcat - 2",
        "White FgPlants - 0"
    ],
    "Slugcat - Yellow": [
        "Yellow Background - 5",
        "Yellow Specks - 4",
        "Yellow Vines - 3",
        "Yellow BkgPlants - 2",
        "Yellow Slugcat - 1",
        "Yellow FgPlants - 0"
    ],
    "Slugcat - Red": [
        "Red Background - 4",
        "Red Spears - 3",
        "Red BgPlants - 2",
        "Red Slugcat - 1",
        "Red FgPlants - 0"
    ],
    "White Ghost Slugcat": [
        "White Ghost Bkg",
        "White Ghost A",
        "White Ghost B"
    ],
    "Yellow Ghost Slugcat": [
        "Yellow Ghost Bkg",
        "Yellow Ghost A",
        "Yellow Ghost B"
    ],
    "Red Ghost Slugcat": [
        "Red Ghost Bkg",
        "Red Ghost A",
        "Red Ghost B"
    ],
    "Yellow Intro A": [
        "YellowA - 8",
        "YellowA - 7",
        "YellowA - 6",
        "YellowA - 5",
        "YellowA - 4",
        "YellowA - 3",
        "YellowA - 1",
        "YellowA - 2",
        "YellowA - Pixel",
        "YellowA - 0"
    ],
    "Yellow Intro B": [
        "YellowB - 5",
        "YellowB - 4",
        "YellowB - 3",
        "YellowB - 1",
        "YellowB - 2"
    ],
    "Dead Red": [
        "Red Death - 5",
        "Red Death - 4",
        "Red Death - 3",
        "Red Death - 2",
        "Red Death - 1"
    ],
    "Red Ascended Scene": [
        "Red Ascend - 3",
        "Red Ascend - 2",
        "Red Ascend - 1"
    ]
}


# And add the extension to Krita's list of extensions:
Krita.instance().addExtension(RWSceneEditor(Krita.instance()))
