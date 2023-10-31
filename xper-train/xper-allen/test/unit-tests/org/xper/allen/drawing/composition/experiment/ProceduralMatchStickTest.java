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
import org.xper.allen.nafc.blockgen.NoiseFormer;
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
import org.xper.util.ThreadUtil;

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
    private int numNoiseFrames;

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
        NoiseForm noiseForm = NoiseFormer.getNoiseForm(NoiseType.POST_JUNC);
        baseMStick.setNoiseParameters(new NoiseParameters(noiseForm, new Lims(0.5, 1.0)));
        drawingManager.setImageFolderName("/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin");
        drawingManager.setBackgroundColor(0.0f,0.f, 0.f);
        drawingManager.drawStimulus(baseMStick, 0L, Collections.singletonList("Stim"));
        drawingManager.setBackgroundColor(1.0f,0.f, 0.f);
        drawingManager.drawNoiseMap(baseMStick, 0L, Collections.singletonList("Noise"));

        drawingManager.close();
        ThreadUtil.sleep(100);
        drawingManager.init();
        drawingManager.setBackgroundColor(0.0f,0.f, 0.f);

        numNoiseFrames = 240;
        NoisyTranslatableResizableImages image = new NoisyTranslatableResizableImages(numNoiseFrames, 1);
        image.initTextures();

        Context context = new Context();
        AbstractRenderer perspectiveRenderer = new PerspectiveRenderer();
        perspectiveRenderer.setDepth(drawingManager.renderer.getDepth());
        perspectiveRenderer.setDistance(drawingManager.renderer.getDistance());
        perspectiveRenderer.setHeight(drawingManager.renderer.getHeight());
        perspectiveRenderer.setWidth(drawingManager.renderer.getWidth());
        perspectiveRenderer.setPupilDistance(drawingManager.renderer.getPupilDistance());

        context.setRenderer(perspectiveRenderer);

        BlankScreen blankScreen = new BlankScreen();
        image.loadTexture("/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin/0_Stim.png", 0);
        image.loadNoise("/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin/0_noisemap_Noise.png");


        for (int i = 0; i< numNoiseFrames; i++){
            drawingManager.renderer.draw(new Drawable() {
                @Override
                public void draw() {
                    blankScreen.draw(null);
                    drawingManager.renderer.init();
                    image.draw(true, context, 0, new Coordinates2D(0.0,0.0), new ImageDimensions(5, 5));
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