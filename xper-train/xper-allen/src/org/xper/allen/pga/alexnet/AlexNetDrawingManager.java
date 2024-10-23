package org.xper.allen.pga.alexnet;

import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.PixelFormat;
import org.xper.alden.drawing.drawables.BaseWindow;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.alden.drawing.renderer.PerspectiveRenderer;
import org.xper.drawing.RGBColor;
import org.xper.util.ThreadUtil;

import java.io.FileOutputStream;
import java.io.IOException;
import java.util.LinkedList;
import java.util.List;

import static org.xper.allen.drawing.composition.AllenPNGMaker.screenShotBinary;

public class AlexNetDrawingManager {

    public double generatorDPI;

    public int width = 227;
    public int height = 227;
    RGBColor backgroundColor = new RGBColor(0.5,0.5,0.5);

    private BaseWindow window;
    private AbstractRenderer renderer;

    public void createDrawerWindow(){
        if (window == null || !window.isOpen()) {
            init();
        }
    }

    public String createAndSavePNG(Drawable obj, Long stimObjId, List<String> labels, String destinationFolder) {
        String imageFolderName = destinationFolder;
        return drawStimulus(obj, stimObjId, labels, imageFolderName);
    }

    private String drawStimulus(Drawable obj, Long stimObjId, List<String> labels, String folderName) {
        ThreadUtil.sleep(100);
        GL11.glClearColor(backgroundColor.getRed(),backgroundColor.getGreen(),backgroundColor.getBlue(),1);
        GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
        renderer.draw(new Drawable() {
            @Override
            public void draw() {
                obj.draw();
            }
        });

        window.swapBuffers();
        return saveImage(stimObjId, labels, height, width, folderName);
    }

    public static String saveImage(long stimObjId, List<String> labels, int height, int width,String imageFolderName) {
        byte[] data = screenShotBinary(width,height);

        String path = imageFolderName + "/" + stimObjId;
        for (String str:labels) {
            if(!str.isEmpty())
                path=path+"_"+str;
        }
        path=path+".png";

        try {
            FileOutputStream fos = new FileOutputStream(path);
            fos.write(data);
            fos.close();
            return path;
        }

        catch (IOException e) {
            e.printStackTrace();
            return "Error: No Path";
        }
    }


    private void init(){
        window = new BaseWindow(width,height);
        PixelFormat pixelFormat = new PixelFormat(0, 8, 1, 4);
        window.setPixelFormat(pixelFormat);
        window.create();

        renderer = new PerspectiveRenderer();
        renderer.setDepth(6000);
        renderer.setDistance(500);
        renderer.setPupilDistance(50);
        renderer.setHeight(calculateMmForPixels(height));
        renderer.setWidth(calculateMmForPixels(width));
        renderer.init(window.getWidth(), window.getHeight());
        GL11.glShadeModel(GL11.GL_SMOOTH);
        GL11.glDisable(GL11.GL_DEPTH_TEST);

        GL11.glClearColor(backgroundColor.getRed(),backgroundColor.getGreen(),backgroundColor.getBlue(),1);

    }


    public double calculateMmForPixels(int numPixels){
        double mmPerInch = 25.4;
        double pixelsPerInch = generatorDPI;
        double pixelsPerMm = pixelsPerInch / mmPerInch;
        double mmPerPixels = 1 / pixelsPerMm;

        return mmPerPixels * numPixels;
    }

    public double getGeneratorDPI() {
        return generatorDPI;
    }

    public void setGeneratorDPI(double generatorDPI) {
        this.generatorDPI = generatorDPI;
    }
}