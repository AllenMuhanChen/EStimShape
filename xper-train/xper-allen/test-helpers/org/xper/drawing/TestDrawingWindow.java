package org.xper.drawing;

import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.PixelFormat;
import org.xper.alden.drawing.drawables.BaseWindow;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.alden.drawing.renderer.PerspectiveRenderer;
import org.xper.allen.drawing.composition.AllenDrawingManager;

public class TestDrawingWindow {
    BaseWindow window;
    private PerspectiveRenderer renderer;

    public void draw(Drawable drawable){
        renderer.draw(drawable);
        window.swapBuffers();
    }

    public static TestDrawingWindow createDrawerWindow() {
        TestDrawingWindow drawingWindow = new TestDrawingWindow();
        if(drawingWindow.window == null || !drawingWindow.window.isOpen()) {
            drawingWindow.init();
        }
        return drawingWindow;

    }

    private void init(){
        window = new BaseWindow(500,500);
        PixelFormat pixelFormat = new PixelFormat(0, 8, 1, 4);
        window.setPixelFormat(pixelFormat);
        window.create();

        renderer = new PerspectiveRenderer();
        //renderer = new OrthographicRenderer();
        renderer.setDepth(6000);
        renderer.setDistance(500); //TODO: stitch this into generator so it is a dependency
        renderer.setPupilDistance(50);
        renderer.setHeight(10);
        renderer.setWidth(10);
        renderer.init(window.getWidth(), window.getHeight());
        GL11.glShadeModel(GL11.GL_SMOOTH);
        GL11.glDisable(GL11.GL_DEPTH_TEST);

        GL11.glClearColor(0,0,0,1);
    }

    public void close() {
        window.destroy();
    }
}
