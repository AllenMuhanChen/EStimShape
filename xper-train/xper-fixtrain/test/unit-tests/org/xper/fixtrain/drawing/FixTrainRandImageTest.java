package org.xper.fixtrain.drawing;

import org.junit.Before;
import org.junit.Test;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.util.ThreadUtil;

import static org.xper.fixtrain.drawing.RandImageFetcherTest.getResource;

public class FixTrainRandImageTest {

    private TestDrawingWindow window;
    private String imageDirectoryPath;

    @Before
    public void setUp() throws Exception {
        window = TestDrawingWindow.createDrawerWindow();

        imageDirectoryPath = getResource("image-dir");
    }

    @Test
    public void draws_from_img_dir_properly(){
        FixTrainRandImage img = new FixTrainRandImage();
        img.setSpec(imageDirectoryPath);

        for (int i = 0 ; i < 10 ; i++) {
            window.draw(new Drawable() {
                @Override
                public void draw(Context context) {
                    img.draw(context);
                }
            });
            ThreadUtil.sleep(500);
        }
    }




}