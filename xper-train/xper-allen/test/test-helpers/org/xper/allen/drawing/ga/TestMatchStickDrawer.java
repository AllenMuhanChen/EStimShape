package org.xper.allen.drawing.ga;

import org.xper.alden.drawing.drawables.Drawable;
import org.xper.drawing.TestDrawingWindow;
import org.xper.drawing.stick.MatchStick;

public class TestMatchStickDrawer {
    public TestDrawingWindow window;

    public void setup(int height, int width){
        window = TestDrawingWindow.createDrawerWindow(height, width);
    }

    public void drawMStick(MatchStick mStick){
        window.draw(new Drawable() {
            @Override
            public void draw() {mStick.draw();
            }
        });
    }

    public void draw(Drawable drawable){
        window.draw(drawable);
    }

}