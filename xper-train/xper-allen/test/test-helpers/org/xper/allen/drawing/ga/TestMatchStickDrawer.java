package org.xper.allen.drawing.ga;

import org.lwjgl.opengl.GL11;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapCalculation;
import org.xper.drawing.TestDrawingWindow;
import org.xper.drawing.stick.MatchStick;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;

import static org.xper.allen.drawing.composition.AllenPNGMaker.screenShotBinary;

public class TestMatchStickDrawer {
    public TestDrawingWindow window;
    private int height;
    private int width;

    public void setup(int height, int width){
        this.height = height;
        this.width = width;
        window = TestDrawingWindow.createDrawerWindow(height, width);
    }

    public void drawMStick(MatchStick mStick){
        window.draw(new Drawable() {
            @Override
            public void draw() {mStick.draw();
            }
        });
    }


    public void drawGhost(AllenMatchStick mStick){
        window.draw(new Drawable() {
            @Override
            public void draw() {mStick.drawGhost();
            }
        });
    }

    public void stop(){
        window.close();
    }


    public void draw(Drawable drawable){
        window.draw(drawable);
    }

    public void clear(){
        GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT);
    }

    public String saveImage(String filepath){
        byte[] data = screenShotBinary(width,height);

        String path = filepath;
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

    public String saveNoiseMap(String filepath, ProceduralMatchStick obj, double amplitude, int specialCompIndx) {
        BufferedImage img = GaussianNoiseMapCalculation.generateGaussianNoiseMapFor(obj,
                width, height,
                3.0/3,
                amplitude,  0, window.renderer, specialCompIndx);

        filepath=filepath+".png";
        File ouptutFile = new File(filepath);
        try {
            ImageIO.write(img, "png", ouptutFile);
        } catch (IOException e) {
            e.printStackTrace();
        }
        return ouptutFile.getAbsolutePath();
    }

    public AllenMStickSpec saveSpec(AllenMatchStick mStick, String filepath) {
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(mStick, true);
        spec.writeInfo2File(filepath, true);
        return spec;
    }

    public void drawCompMap(GAMatchStick complete) {
        window.draw(new Drawable() {
            @Override
            public void draw() {
                complete.drawCompMap();
            }
        });
    }
}