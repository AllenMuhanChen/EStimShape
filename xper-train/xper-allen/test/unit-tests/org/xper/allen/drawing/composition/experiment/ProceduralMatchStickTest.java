package org.xper.allen.drawing.composition.experiment;

import org.junit.Before;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.AllenDrawingManager;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.noisy.ConcaveHull;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
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

import javax.imageio.ImageIO;
import javax.vecmath.Point3d;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.awt.image.DataBufferByte;
import java.io.*;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.xper.allen.drawing.composition.AllenPNGMaker.allocBytes;
import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class ProceduralMatchStickTest {
    private final GaussianNoiseMapper noiseMapper = new GaussianNoiseMapper();
    private String testBin;
    private ProceduralMatchStick baseMStick;
    private AllenPNGMaker pngMaker;
    private TestDrawingWindow window;
    private AllenDrawingManager drawingManager;
    private int numNoiseFrames;
    private ProceduralMatchStick testMStick;

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));

        pngMaker = context.getBean(AllenPNGMaker.class);
        pngMaker.createDrawerWindow();
        drawingManager = pngMaker.window;

        baseMStick = new ProceduralMatchStick(noiseMapper);
        baseMStick.setProperties(4, "SHADE", 1.0);
        baseMStick.setStimColor(new Color(255,255,255));
        baseMStick.genMatchStickRand();
        baseMStick.setMaxAttempts(-1);

    }

    @Test
    public void test_procedural_distractors(){
        pngMaker.createDrawerWindow();
        for (int i = 0; i < 2; i++) {
            generateStimAndProceduralDistractors(i);
        }
    }

    @Test
    /**
     * For testing the behavior of noise circle location relative to the stimulus (visualized as a hull)
     */
    public void drawHullAndNoiseCircle(){
        testMStick = new ProceduralMatchStick(noiseMapper);
        testMStick.PARAM_nCompDist = new double[]{0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0};
        testMStick.genMatchStickFromLeaf(1, baseMStick);

        List<List<ConcaveHull.Point>> hulls = new ArrayList<>();
        List<Boolean> isSpecial = new ArrayList<>();
        for (int compId: testMStick.getCompIds()){
            if (compId != 0) {
                hulls.add(calcHull(testMStick, compId));
                if (testMStick.getSpecialEndComp().contains(compId)) {
                    isSpecial.add(true);
                } else {
                    isSpecial.add(false);
                }
            }

        }

//        ArrayList<ConcaveHull.Point> drivingCompHull = calcHull(testMStick, baseMStick.getSpecialEndComp().get(0));
//        ArrayList<ConcaveHull.Point> baseCompHull = calcHull(testMStick, 2);
        window = TestDrawingWindow.createDrawerWindow(500, 500);
        window.draw(new Drawable() {
            @Override
            public void draw() {
                //Zoom in
                GL11.glScalef(10, 10, 1);
                int indx = 0;
                for (List<ConcaveHull.Point> hull: hulls){
                    if (isSpecial.get(indx)){
                        //Color red
                        GL11.glColor3f(1, 0, 0);
                    } else{
                        GL11.glColor3f(1, 1, 1);
                    }
                    GL11.glBegin(GL11.GL_LINE_LOOP); // Use GL_LINE_LOOP for the outline, GL_POLYGON to fill

                    for (ConcaveHull.Point point : hull) {
                        GL11.glVertex2d(point.getX(), point.getY());
                    }

                    GL11.glEnd();
                    indx++;
                }


                // Now, draw the circle
                System.out.println(testMStick.getSpecialEndComp().get(0));
                Point3d circle = testMStick.calculateGaussNoiseOrigin(testMStick.getSpecialEndComp().get(0)); // Replace with the circle's center X-coordinate

                double radius = 10;
                int numSegments = 100; // Increase for a smoother circle

                GL11.glBegin(GL11.GL_LINE_LOOP);
                for (int i = 0; i < numSegments; i++) {
                    double theta = 2.0 * Math.PI * i / numSegments; // Current angle
                    double x = radius * Math.cos(theta); // Calculate the x component
                    double y = radius * Math.sin(theta); // Calculate the y component
                    GL11.glVertex2d(x + circle.getX(), y + circle.getY()); // Output vertex
                }
                GL11.glEnd();



            }
        });
        Point3d x = testMStick.calculateGaussNoiseOrigin(testMStick.getSpecialEndComp().get(0));
        System.out.println(x);
        ThreadUtil.sleep(100000);
        window.close();

    }

    private ArrayList<ConcaveHull.Point> calcHull(ProceduralMatchStick testMStick, int compIndx) {
        Point3d[] compVect_info = testMStick.getComp()[compIndx].getVect_info();
        ArrayList<ConcaveHull.Point> concaveHullPoints = new ArrayList<>();
        int index=0;
        for (Point3d point3d: compVect_info){
            if (point3d != null){
                if (index % 3 == 0)
                    concaveHullPoints.add(new ConcaveHull.Point(point3d.getX(), point3d.getY()));
                index++;
            }
        }
        ConcaveHull concaveHull = new ConcaveHull();

        ArrayList<ConcaveHull.Point> hullVertices = concaveHull.calculateConcaveHull(concaveHullPoints, 5);
        return hullVertices;
    }

    @Test
    public void drawNoisy() throws IOException {

//        System.out.println(baseMStick.getSpecialEndComp());
//        System.out.println(baseMStick.getBaseComp());
//        drawingManager.init();
        boolean drawNewStim = true;
        boolean drawNewNoise = true;
        Color color = new Color(255/2, 255/2, 255/2);
        double noiseAmplitude = 1;



        baseMStick = new ProceduralMatchStick(noiseMapper);
        int size = 5;
        baseMStick.setProperties(size, "SHADE", 1.0);
        baseMStick.setStimColor(new Color(255,255,255));
        baseMStick.genMatchStickRand();
        baseMStick.setMaxAttempts(-1);

        drawingManager.setImageFolderName("/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin");
        drawingManager.drawStimulus(baseMStick, -1L, Collections.singletonList("Base"));
        ProceduralMatchStick sampleMStick;
        if (drawNewStim) {
            sampleMStick = new ProceduralMatchStick(noiseMapper);
//            sampleMStick.showDebug = true;
            sampleMStick.PARAM_nCompDist = new double[]{0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            sampleMStick.setProperties(size, "SHADE", 1.0);
            sampleMStick.setStimColor(color);
            sampleMStick.genMatchStickFromComponent(baseMStick, 1, 0, sampleMStick.maxAttempts);
            System.out.println("special end comp:" + sampleMStick.getSpecialEndComp());

            drawingManager.setBackgroundColor(0.f, 0.f, 0.f);
//            drawingManager.setBackgroundColor(0.5f, 0.5f, 0.5f);
            drawingManager.drawStimulus(sampleMStick, 0L, Collections.singletonList("Stim"));
            AllenMStickSpec spec = new AllenMStickSpec();
            spec.setMStickInfo(sampleMStick, true);
            spec.writeInfo2File(testBin + "/" + 0 + "_" + "Stim", true);
            ThreadUtil.sleep(100);
        } else {
            sampleMStick = new ProceduralMatchStick(noiseMapper);
            sampleMStick.genMatchStickFromFile("/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin/0_Stim_spec.xml");

        }
        if (drawNewNoise) {
            drawingManager.setBackgroundColor(0f,0,0);
            drawingManager.drawGaussNoiseMap(sampleMStick, 0L, Collections.singletonList("Noise"), noiseAmplitude, sampleMStick.getSpecialEndComp().get(0));
        }

//        drawingManager.close();
        drawingManager.setBackgroundColor(0.f, 0.f, 0.f);
//        drawingManager.init();


        numNoiseFrames = 60;
        NoisyTranslatableResizableImages image = new NoisyTranslatableResizableImages(numNoiseFrames, 1, 1);
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

        image.loadNoise("/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin/0_noisemap_Noise.png",
                color);

        // Add buffer to store the frames
        List<BufferedImage> frames = new ArrayList<>();
        drawingManager.renderer.init();
        for (int i = 0; i < numNoiseFrames; i++) {
//            int finalI = i;
            drawingManager.renderer.draw(new Drawable() {
                @Override
                public void draw() {

                    blankScreen.draw(null);
                    image.draw(true, context, 0, new Coordinates2D(0.0, 0.0), new ImageDimensions(5, 5));
//                    String filename = "frame_" + finalI;



                    // Capture the frame
//                    byte[] imageData = screenShotBinary((int) drawingManager.window.getWidth(), (int) drawingManager.window.getHeight());
//                    BufferedImage frame = null;
//                    try{
//                        frame = convertToBufferedImage(imageData);
//                    } catch (IOException e){
//                        System.out.println("Error converting to buffered image");
//                    }
//                    frames.add(frame);

//                    if (finalI < numNoiseFrames) { // change this number to save more or fewer frames
////                        try {
////                            File outputfile = new File("/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin/test_mjpeg/frame_" + finalI + ".jpg");
////                            ImageIO.write(frame, "jpg", outputfile);
////                        } catch (Exception e) {
////                            e.printStackTrace();
////                        }
//                    }



                }
            });
            drawingManager.window.swapBuffers();
        }
    }

    private void generateStimAndProceduralDistractors(long setId) {
        drawPng(baseMStick, setId, 0L);
        ProceduralMatchStick sampleMStick = new ProceduralMatchStick(noiseMapper);
        int size = 2;
        sampleMStick.setProperties(size, "SHADE", 1.0);
        sampleMStick.genMatchStickFromComponent(baseMStick, 1, 0, sampleMStick.maxAttempts);
        drawPng(sampleMStick, setId, 1L);

        ProceduralMatchStick distractor1 = new ProceduralMatchStick(noiseMapper);
        distractor1.setProperties(size, "SHADE", 1.0);
        distractor1.genMorphedDrivingComponentMatchStick(sampleMStick, 0.5, 0.5, true, true, sampleMStick.maxAttempts);
        drawPng(distractor1, setId, 2L);

        ProceduralMatchStick distractor2 = new ProceduralMatchStick(noiseMapper);
        distractor2.setProperties(size, "SHADE", 1.0);
        distractor2.genMorphedDrivingComponentMatchStick(sampleMStick, 0.5, 0.5, true, true, sampleMStick.maxAttempts);
        drawPng(distractor2, setId, 3L);
    }

    protected BufferedImage convertToBufferedImage(byte[] imageData) throws IOException {
        InputStream in = new ByteArrayInputStream(imageData);
        return ImageIO.read(in);
    }

    protected byte[] screenShotBinary(int width, int height) {
        ByteBuffer framebytes = allocBytes(width * height * 3);

        // grab a copy of the current frame contents as RGB
        GL11.glReadPixels(0, 0, width, height, GL11.GL_RGB, GL11.GL_UNSIGNED_BYTE, framebytes);

        // Convert to BufferedImage of type TYPE_3BYTE_BGR, which is the type compatible with JPEG
        BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_3BYTE_BGR);
        byte[] buffer = new byte[width * height * 3];
        framebytes.get(buffer);
        swapRedBlue(buffer);
        byte[] imagePixels = ((DataBufferByte) image.getRaster().getDataBuffer()).getData();
        System.arraycopy(buffer, 0, imagePixels, 0, buffer.length);

        // Flip the image vertically
        flipImage(image);

        try {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            ImageIO.write(image, "jpg", out); // Write as JPEG
            return out.toByteArray();
        } catch (IOException e) {
            System.out.println("screenShot(): exception " + e);
            return null;
        }
    }

    protected void swapRedBlue(byte[] buffer) {
        for (int i = 0; i < buffer.length; i += 3) {
            byte red = buffer[i];
            buffer[i] = buffer[i + 2];
            buffer[i + 2] = red;
        }
    }

    public static void flipImage(BufferedImage image) {
        for (int i = 0; i < image.getHeight() / 2; i++) {
            int[] topRow = image.getRGB(0, i, image.getWidth(), 1, null, 0, image.getWidth());
            int[] bottomRow = image.getRGB(0, image.getHeight() - i - 1, image.getWidth(), 1, null, 0, image.getWidth());
            image.setRGB(0, i, image.getWidth(), 1, bottomRow, 0, image.getWidth());
            image.setRGB(0, image.getHeight() - i - 1, image.getWidth(), 1, topRow, 0, image.getWidth());
        }
    }



    public void drawPng(ProceduralMatchStick matchStick, long setId, long id) {
//        pngMaker = new AllenPNGMaker(500, 500);
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(matchStick, true);
        spec.writeInfo2File(testBin + "/" + setId + "_" + id, true);
        pngMaker.createAndSavePNG(matchStick, setId, Collections.singletonList(Long.toString(id)), testBin);
    }

    private TestDrawingWindow getTestDrawingWindow() {
        window = TestDrawingWindow.createDrawerWindow(500, 500);
        return window;
    }
}