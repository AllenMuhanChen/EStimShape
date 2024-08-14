package org.xper.allen.drawing.composition.noisy;

import org.junit.Before;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.AllenDrawingManager;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.ga.CircleReceptiveField;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.util.FileUtil;
import org.xper.util.ResourceUtil;
import org.xper.util.ThreadUtil;

import javax.imageio.ImageIO;
import javax.swing.*;
import javax.vecmath.Point3d;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class GaussianNoiseMapperTest {

    private String testBin;
    private TestMatchStickDrawer testMatchStickDrawer;
    private GaussianNoiseMapper gaussianNoiseMapper;
    private ProceduralMatchStick baseMStick;
    private AllenPNGMaker pngMaker;
    private AllenDrawingManager drawingManager;
    private JavaConfigApplicationContext context;

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));

        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup(500, 500);

        gaussianNoiseMapper = new GaussianNoiseMapper();
        gaussianNoiseMapper.setWidth(500);
        gaussianNoiseMapper.setHeight(500);
        gaussianNoiseMapper.setBackground(0); // Set background to black

        baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(4, "SHADE");
        baseMStick.setStimColor(new Color(255,255,255));
        baseMStick.genMatchStickRand();
        baseMStick.setMaxAttempts(100);

//        pngMaker = context.getBean(AllenPNGMaker.class);
////        pngMaker.createDrawerWindow();
//        drawingManager = pngMaker.window;
    }

    @Test
    public void testGaussianNoiseWithDifferentSpecialCompIds() throws IOException {
        ReceptiveField receptiveField = new CircleReceptiveField(new Coordinates2D(5,5), 10);

        EStimShapeTwoByTwoMatchStick mStick = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE, receptiveField);

        int nComp = 2;

        mStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, AbstractRenderer.mm2deg(receptiveField.getRadius(), 500)), "SHADE");
        while (true) {
            try {
                mStick.genMatchStickFromComponentInNoise(baseMStick, 1, nComp, true, mStick.maxAttempts);
            } catch (Exception e) {
                continue;
            }
            break;
        }


        // Test different combinations of special components
        List<List<Integer>> specialCompCombinations;
        if (nComp == 3) {
            specialCompCombinations = new LinkedList<>();
            specialCompCombinations.add(Collections.singletonList(1));
            specialCompCombinations.add(Arrays.asList(2, 3));
        } else if (nComp == 2){
            specialCompCombinations = new LinkedList<>();
            specialCompCombinations.add(Collections.singletonList(1));
            specialCompCombinations.add(Collections.singletonList(2));

        } else {
            throw new IllegalArgumentException("Invalid number of components: " + nComp);
        }

        for (List<Integer> specialComps : specialCompCombinations) {
            testGaussianNoiseForSpecialComps(mStick, specialComps);
        }
    }



    private void testGaussianNoiseForSpecialComps(ProceduralMatchStick mStick, List<Integer> specialComps) throws IOException {
        String suffix = "_specialComps_" + specialComps.toString().replaceAll("[\\[\\] ]", "");

        // Draw the original match stick
        testMatchStickDrawer.clear();
        testMatchStickDrawer.draw(new Drawable() {
            @Override
            public void draw() {
                mStick.drawCompMap();

                // Now, draw the circle
                GL11.glColor3f(1.0f, 0.0f, 0.0f);
                Point3d circle = mStick.calculateNoiseOrigin(specialComps); // Replace with the circle's center X-coordinate
                System.out.println("NOISE ORIGIN: " + circle);

                double radius = mStick.noiseRadiusMm;
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
        ThreadUtil.sleep(2000);


        String imagePath = testMatchStickDrawer.saveImage(testBin + "/original_matchstick" + suffix);

        // Generate Gaussian noise map
        String noiseMapPath = gaussianNoiseMapper.mapNoise(mStick, 0.5, specialComps, testMatchStickDrawer.window.renderer, testBin + "/gaussian_noise_map" + suffix + ".png");

        // Load original image and noise map
        BufferedImage originalImage = ImageIO.read(new File(imagePath));
        BufferedImage noiseMap = ImageIO.read(new File(noiseMapPath));

        // Apply noise manually
        BufferedImage noisyImage = applyNoise(originalImage, noiseMap);

        // Save noisy image
        ImageIO.write(noisyImage, "PNG", new File(testBin + "/noisy_matchstick" + suffix + ".png"));

        // Display noisy image
        displayImage(noisyImage, "Noisy MatchStick - Special Comps: " + specialComps);

    }


    private BufferedImage applyNoise(BufferedImage original, BufferedImage noise) {
        int width = original.getWidth();
        int height = original.getHeight();
        BufferedImage result = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int origColor = original.getRGB(x, y);
                int noiseColor = noise.getRGB(x, y);

                int alpha = (origColor >> 24) & 0xff;
                int red = Math.min(255, ((origColor >> 16) & 0xff) + ((noiseColor >> 16) & 0xff));
                int green = Math.min(255, ((origColor >> 8) & 0xff) + ((noiseColor >> 8) & 0xff));
                int blue = Math.min(255, (origColor & 0xff) + (noiseColor & 0xff));

                int newColor = (alpha << 24) | (red << 16) | (green << 8) | blue;
                result.setRGB(x, y, newColor);
            }
        }

        return result;
    }

    private void displayImage(BufferedImage image, String title) {
        JFrame frame = new JFrame(title);
        JLabel label = new JLabel(new ImageIcon(image));
        frame.getContentPane().add(label, BorderLayout.CENTER);
        frame.pack();
        frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
        frame.setVisible(true);

        // Wait for the user to close the window
        try {
            Thread.sleep(10000);  // Display for 5 seconds
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        frame.dispose();
    }
}