package org.xper.allen.nafc.blockgen.procedural;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStickTest;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.procedural.ProceduralStim.ProceduralStimParameters;
import org.xper.allen.noisy.NoisyTranslatableResizableImages;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.util.FileUtil;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class ProceduralStimTest extends ProceduralMatchStickTest {

    private NAFCBlockGen generator;
    private ProceduralMatchStick baseMStick;

    @Before
    public void setUp() throws Exception {
        FileUtil.loadTestSystemProperties("/xper.properties.procedural");

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("experiment.config_class"));

        generator = context.getBean(NAFCBlockGen.class);
        baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(generator.getMaxImageDimensionDegrees());
        baseMStick.setStimColor(new Color(255,255,255));
        baseMStick.genMatchStickRand();
    }

    @Test
    public void writeStim() {

        Color color = new Color(255, 255, 255);
        ProceduralStimParameters parameters = new ProceduralStimParameters(
                new Lims(0, 0),
                new Lims(0, 0),
                8,
                10,
                0.5,
                4,
                1,
                0.5,
                0.5,
                color
                );

        ProceduralStim stim = new ProceduralStim(generator, parameters, baseMStick, 1, 1);
        stim.writeStim();

        AllenPNGMaker pngMaker = generator.getPngMaker();
        pngMaker.createDrawerWindow();

        // Add buffer to store the frames
        List<BufferedImage> frames = new ArrayList<>();
        int numNoiseFrames = 60;
        AbstractRenderer pngRenderer = pngMaker.window.renderer;
        org.xper.drawing.renderer.AbstractRenderer xperRenderer = new org.xper.drawing.renderer.PerspectiveRenderer();
        xperRenderer.setDistance(pngRenderer.getDistance());
        xperRenderer.setPupilDistance(pngRenderer.getPupilDistance());
        xperRenderer.setHeight(pngRenderer.getHeight());
        xperRenderer.setWidth(pngRenderer.getWidth());
        xperRenderer.setDepth(pngRenderer.getDepth());

        Context context = new Context();
        context.setRenderer(xperRenderer);
        NoisyTranslatableResizableImages image = new NoisyTranslatableResizableImages(numNoiseFrames, 1, 1);
        image.initTextures();
        image.loadTexture(stim.experimentPngPaths.getSample(), 0);
        image.loadNoise(stim.experimentNoiseMapPath, color);

        for (int i = 0; i < numNoiseFrames; i++) {
            int finalI = i;
            pngRenderer.draw(new Drawable() {
                @Override
                public void draw() {
                    pngRenderer.init();
                    image.draw(true, context, 0, new Coordinates2D(0.0, 0.0), new ImageDimensions(5, 5));

                    String filename = "frame_" + finalI;



                    // Capture the frame
                    byte[] imageData = screenShotBinary((int) xperRenderer.getWidth(), (int) xperRenderer.getHeight());
                    BufferedImage frame = null;
                    try{
                        frame = convertToBufferedImage(imageData);
                    } catch (IOException e){
                        System.out.println("Error converting to buffered image");
                    }
                    frames.add(frame);

                    if (finalI < numNoiseFrames) { // change this number to save more or fewer frames
                        try {
                            File outputfile = new File("/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin/test_mjpeg/frame_" + finalI + ".jpg");
                            ImageIO.write(frame, "jpg", outputfile);
                        } catch (IOException e) {
                            e.printStackTrace();
                        }
                    }

                    pngMaker.window.window.swapBuffers();

                }
            });
        }
    }
}