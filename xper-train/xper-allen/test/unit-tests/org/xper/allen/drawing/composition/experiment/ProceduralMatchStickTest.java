package org.xper.allen.drawing.composition.experiment;

import org.junit.Before;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.AllenDrawingManager;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.noisy.NoisePositions;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.vo.NoiseForm;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.allen.noisy.NoisyTranslatableResizableImages;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.TestDrawingWindow;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.util.FileUtil;
import org.xper.util.ResourceUtil;

import java.util.Collection;
import java.util.Collections;
import java.util.List;

import static org.junit.Assert.*;
import static org.lwjgl.opengl.GL11.*;
import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class ProceduralMatchStickTest {
    private String testBin;
    private TwobyTwoExperimentMatchStick baseMStick;
    private AllenPNGMaker pngMaker;
    private TestDrawingWindow window;
    private AllenDrawingManager drawingManager;

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));

        pngMaker = context.getBean(AllenPNGMaker.class);



        drawingManager = new AllenDrawingManager(1000, 1000);
        drawingManager.setPngMaker(pngMaker);

        baseMStick = new TwobyTwoExperimentMatchStick();
        baseMStick.setProperties(8);
        baseMStick.genMatchStickRand();
    }

    @Test
    public void test_msticks(){
        for (int i = 0; i < 2; i++) {
            generateSet(i);
        }
    }

    @Test
    public void drawNoisy(){
        drawingManager.init();
        NoiseForm noiseForm = new NoiseForm(NoiseType.PRE_JUNC, new NoisePositions(0.0, 1.0));
        baseMStick.setNoiseParameters(new NoiseParameters(noiseForm, new Lims(0, 1)));
        drawingManager.setImageFolderName("/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin");
        drawingManager.drawStimulus(baseMStick, 0L, Collections.singletonList("Stim"));
        drawingManager.drawNoiseMap(baseMStick, 0L, Collections.singletonList("Noise"));


        NoisyTranslatableResizableImages image = new NoisyTranslatableResizableImages(60, 1);
        image.initTextures();

        Context context = new Context();
        AbstractRenderer perspectiveRenderer = new PerspectiveRenderer();
        perspectiveRenderer.setDepth(6000);
        perspectiveRenderer.setDistance(500);
        perspectiveRenderer.setHeight(190);
        perspectiveRenderer.setWidth(190);
        perspectiveRenderer.setPupilDistance(50);
        context.setRenderer(perspectiveRenderer);

        BlankScreen blankScreen = new BlankScreen();
        drawingManager.renderer.init(190, 190);
        image.loadTexture("/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin/0_Stim.png", 0);
        image.loadNoise("/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin/0_noisemap_Noise.png");
        for (int i=0; i<100; i++){
            drawingManager.renderer.draw(new Drawable() {
                @Override
                public void draw() {
                    blankScreen.draw(null);
                    image.draw(true, context, 0, new Coordinates2D(0.0,0.0), new ImageDimensions(50, 50));
                    drawingManager.window.swapBuffers();
                }
            });

            System.out.println("Frame " + i);
        }

    }

    private void generateSet(long setId) {
        drawPng(baseMStick, setId, 0L);
        ProceduralMatchStick sampleMStick = new ProceduralMatchStick();
        sampleMStick.setProperties(8);
        sampleMStick.genMatchStickFromDrivingComponent(baseMStick, 1);
        drawPng(sampleMStick, setId, 1L);

        ProceduralMatchStick distractor1 = new ProceduralMatchStick();
        distractor1.setProperties(8);
        distractor1.genNewDrivingComponentMatchStick(sampleMStick, 1, 0.5);
        drawPng(distractor1, setId, 2L);

        ProceduralMatchStick distractor2 = new ProceduralMatchStick();
        distractor2.setProperties(8);
        distractor2.genNewDrivingComponentMatchStick(sampleMStick, 1, 0.5);
        drawPng(distractor2, setId, 3L);
    }

    private void drawPng(ExperimentMatchStick matchStick, long setId, long id) {
//        pngMaker = new AllenPNGMaker(500, 500);
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(matchStick);
        spec.writeInfo2File(testBin + "/" + setId + "_" + id, true);
        pngMaker.createAndSavePNG(matchStick, setId, Collections.singletonList(Long.toString(id)), testBin);
    }

    private TestDrawingWindow getTestDrawingWindow() {
        window = TestDrawingWindow.createDrawerWindow();
        return window;
    }
}