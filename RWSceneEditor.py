from PyQt5.QtWidgets import QFileDialog
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

        if not filepath.endswith("positions.txt"):
            raise Exception("positions.txt not found")

        folderpath = filepath.rsplit("/", 1)[0]
        foldername = folderpath.rsplit("/", 1)[1]
        folderpath += "/"

        #print(filepath)
        #print(foldername)
        #print(folderpath)

        if not os.path.exists(folderpath + foldername + "_map.txt"):
            raise Exception("map.txt not found")


        doc = k.createDocument(1920, 1080, foldername, "RGBA", "U8", "", 300.0)
        activeView = k.activeWindow().activeView()
        k.activeWindow().addView(doc) # shows it in the application
        # added early so no leak on crash lmao


        background = doc.rootNode().childNodes()[0]
        doc.setActiveNode(background)
        k.action("reset_fg_bg").trigger()
        k.action("fill_selection_foreground_color").trigger()
        background.setOpacity(255);

        with open(folderpath + foldername + "_map.txt") as f:
            files = [p.strip() for p in f.readlines() if p.strip()]

        with open(filepath) as f:
            positions = [list(map(int,p.split(", "))) for p in f.readlines() if p.strip()]

        for i, f in enumerate(files):
            #print(f)
            layername = f
            layerfile = layername + ".png"
            img = doc.createFileLayer(layername, folderpath + layerfile, "None")
            dim = (img.bounds().right() + 1, (img.bounds().bottom() + 1)//2)

            pix = img.projectionPixelData(0, dim[1], dim[0], dim[1])
            depth = doc.createNode(layername + "[dpt]", "paintlayer")
            depth.setPixelData(pix, 0, 0, dim[0], dim[1])
            doc.rootNode().addChildNode(depth, None)
            depth.move((1920 - 1366)//2 + positions[i][0], 1080 - (1080 - 768)//2 -dim[1] - positions[i][1])
            depth.setVisible(False)

            pix = img.projectionPixelData(0, 0, dim[0], dim[1])
            image = doc.createNode(layername + "[img]", "paintlayer")
            image.setPixelData(pix, 0, 0, dim[0], dim[1])
            doc.rootNode().addChildNode(image, None)
            image.move((1920 - 1366)//2 + positions[i][0], 1080 - (1080 - 768)//2 -dim[1] - positions[i][1])

        doc.refreshProjection()

    def saveRWScene(self):
        k = Krita.instance()

        q = QFileDialog()
        q.setWindowTitle("The folder to save the scene, the name of the folder will ")
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

        #raise Exception(scenename)
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

        for layer in layers:
            exportlayer = doc.createNode(layer[0], "paintlayer")
            bounds = layer[1].bounds().united(layer[2].bounds())
            x,y,w,h = bounds.getRect()
            exportlayer.setPixelData(layer[1].pixelData(x,y,w,h), x,y,w,h)
            exportlayer.setPixelData(layer[2].pixelData(x,y,w,h), x,y+h,w,h)
            bounds.setHeight(2*h)
            k.setBatchmode(True)
            exportParameters = InfoObject()
            exportParameters.setProperty("alpha", True)
            exportParameters.setProperty("compression", 6)
            exportParameters.setProperty("indexed", False)
            exportlayer.save(scenepath+layer[0]+".png",1,1,exportParameters,bounds)
            k.setBatchmode(False)

            offsets.append((x-(1920 - 1366)//2, 1080 - (1080 - 768)//2 - y - h))

        with open(scenepath + scenename + "_map.txt",'w') as f:
            f.write("\n".join(l[0] for l in layers))

        with open(scenepath + "positions.txt",'w') as f:
            f.writelines((f"{o[0]}, {o[1]}\n" for o in offsets))






# And add the extension to Krita's list of extensions:
Krita.instance().addExtension(RWSceneEditor(Krita.instance()))
