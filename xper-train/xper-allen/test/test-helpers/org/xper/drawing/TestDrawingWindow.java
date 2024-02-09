package org.xper.drawing;

import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.PixelFormat;
import org.xper.XperConfig;
import org.xper.alden.drawing.drawables.BaseWindow;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.alden.drawing.renderer.PerspectiveRenderer;
import org.xper.util.ThreadUtil;

import java.util.ArrayList;
import java.util.List;

public class TestDrawingWindow {
    BaseWindow window;
    public PerspectiveRenderer renderer;

    public void draw(Drawable drawable){
        renderer.draw(drawable);
        window.swapBuffers();
    }

    public void animateRotation(List<Drawable> drawables, float angle, double numFrames){
        for (int frameNum = 0; frameNum< numFrames; frameNum++) {
            int finalFrameNum = frameNum;
            renderer.draw(new Drawable() {
                @Override
                public void draw() {
                    GL11.glPushMatrix();
                    GL11.glMatrixMode(GL11.GL_MODELVIEW);
                    GL11.glRotatef(finalFrameNum*angle, 1f, 1f, 1f);
                    for (Drawable drawable:drawables)
                        drawable.draw();
                }
            });
            GL11.glPopMatrix();
            window.swapBuffers();
            GL11.glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
            GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
            GL11.glFlush();
            ThreadUtil.sleep(Math.round((1/60.0)*1000));
        }

    }


    public static TestDrawingWindow createDrawerWindow(int height, int width) {
        initXperLibs();

        TestDrawingWindow drawingWindow = new TestDrawingWindow();
        if(drawingWindow.window == null || !drawingWindow.window.isOpen()) {
            drawingWindow.init(height, width);
        }
        return drawingWindow;

    }

    public static void initXperLibs() {
        List<String> libs = new ArrayList<String>();
        libs.add("xper");
        new XperConfig("", libs);
    }

    private void init(int height, int width){
        window = new BaseWindow(height, width);
        PixelFormat pixelFormat = new PixelFormat(0, 8, 1, 4);
        window.setPixelFormat(pixelFormat);
        window.create();

        renderer = new PerspectiveRenderer();
        //renderer = new OrthographicRenderer();
        renderer.setDepth(6000);
        renderer.setDistance(500); //TODO: stitch this into generator so it is a dependency
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