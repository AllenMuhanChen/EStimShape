package org.xper.fixtrain.drawing;

import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.PixelFormat;
import org.xper.XperConfig;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.util.ThreadUtil;

import java.util.ArrayList;
import java.util.List;

public class TestDrawingWindow {
    BaseWindow window;
    public PerspectiveRenderer renderer;

    public void draw(Drawable drawable){
        renderer.draw(drawable, new Context());
        window.swapBuffers();
    }



    public static TestDrawingWindow createDrawerWindow() {
        initXperLibs();

        TestDrawingWindow drawingWindow = new TestDrawingWindow();
        if(drawingWindow.window == null || !drawingWindow.window.isOpen()) {
            drawingWindow.init();
        }
        return drawingWindow;

    }

    public static void initXperLibs() {
        List<String> libs = new ArrayList<String>();
        libs.add("xper");
        new XperConfig("", libs);
    }

    private void init(){
        window = new BaseWindow(500,500);
        PixelFormat pixelFormat = new PixelFormat(0, 8, 1, 4);
        window.setPixelFormat(pixelFormat);
        window.create();

        renderer = new PerspectiveRenderer();
        renderer.setDepth(6000);
        renderer.setDistance(500);
        renderer.setPupilDistance(50);
        renderer.setHeight(100);
        renderer.setWidth(100);
        renderer.init(window.getWidth(), window.getHeight());
        GL11.glShadeModel(GL11.GL_SMOOTH);
        GL11.glDisable(GL11.GL_DEPTH_TEST);

        GL11.glClearColor(0,0,0,1);
    }

    public void close() {
        window.destroy();
    }
}