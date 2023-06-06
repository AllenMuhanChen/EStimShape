package org.xper.fixtrain.drawing;

import org.junit.Before;
import org.junit.Test;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;
import org.xper.util.ThreadUtil;

import static org.xper.fixtrain.drawing.RandImageFetcherTest.getResource;

public class ImageTest {

    private TestDrawingWindow window;

    @Before
    public void setUp() throws Exception {
        window = TestDrawingWindow.createDrawerWindow();


    }

    @Test
    public void test(){
        String imagePath = getResource("img-0.png");

        TranslatableResizableImages images = new TranslatableResizableImages(1);
        images.initTextures();
        images.loadTexture(imagePath, 0);

        window.draw(new Drawable() {
            @Override
            public void draw(Context context) {
                images.draw(context, 0, new Coordinates2D(0,0), new Coordinates2D(200,200));
            }
        });
        ThreadUtil.sleep(10000);
    }
}