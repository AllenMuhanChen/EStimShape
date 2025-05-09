package org.xper.allen.drawing.gabor;

import com.mchange.v2.c3p0.ComboPooledDataSource;
import org.junit.Before;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.alden.drawing.renderer.PerspectiveRenderer;
import org.xper.allen.isoluminant.CombinedGabor;
import org.xper.allen.monitorlinearization.ColorLookupTable;
import org.xper.allen.monitorlinearization.GainLookupTable;
import org.xper.allen.monitorlinearization.LookUpTableCorrector;
import org.xper.allen.monitorlinearization.SinusoidGainCorrector;
import org.xper.drawing.Context;
import org.xper.drawing.RGBColor;
import org.xper.drawing.TestDrawingWindow;
import org.xper.exception.DbException;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.allen.rfplot.IsochromaticGabor;
import org.xper.allen.isoluminant.IsoluminantGabor;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;
import org.xper.util.ThreadUtil;

import javax.sql.DataSource;
import java.beans.PropertyVetoException;

public class IsoGaborTest {

    private TestDrawingWindow window;
    private int height;
    private int width;
    private org.xper.drawing.renderer.PerspectiveRenderer perspectiveRenderer;
    private Context context;
    private LookUpTableCorrector lutCorrector = new LookUpTableCorrector();
    private SinusoidGainCorrector sinusoidGainCorrector = new SinusoidGainCorrector();

    @Before
    public void setUp() throws Exception {

        height = 1000;
        width = 1500;
        window = TestDrawingWindow.createDrawerWindow(height, width);
        PerspectiveRenderer renderer = window.renderer;
        perspectiveRenderer = new org.xper.drawing.renderer.PerspectiveRenderer();
        perspectiveRenderer.setDepth(renderer.getDepth());
        perspectiveRenderer.setHeight(renderer.getHeight());
        perspectiveRenderer.setWidth(renderer.getWidth());
        perspectiveRenderer.setPupilDistance(renderer.getPupilDistance());
        perspectiveRenderer.setDistance(renderer.getDistance());
        perspectiveRenderer.init(width, height);


        context = new Context();
        System.out.println(perspectiveRenderer.mm2deg(perspectiveRenderer.getVpWidthmm()));
        context.setRenderer(perspectiveRenderer);

        DataSource dataSource = dataSource();

        ColorLookupTable clt = new ColorLookupTable();
        clt.setDataSource(dataSource);
        clt.init();

        lutCorrector.setLookupTable(clt);

        GainLookupTable glt = new GainLookupTable();
        glt.setDataSource(dataSource);
        glt.init();
        sinusoidGainCorrector.setGainLookupTable(glt);
    }

    @Test
    public void testIsochromatic() {
        IsoGaborSpec spec = new IsoGaborSpec();
        spec.setOrientation(45);
        spec.setPhase(0);
        spec.setFrequency(0.5);
        spec.setXCenter(0);
        spec.setYCenter(0);
        spec.setSize(10);
        spec.setAnimation(false);
        spec.setType("Orange");


        IsochromaticGabor gabor = new IsochromaticGabor(spec, 400, lutCorrector);
        gabor.setSpec(spec.toXml());

        window.draw(new Drawable() {
            @Override
            public void draw() {
                RGBColor gray = lutCorrector.correctSingleColor(400, "gray");
                GL11.glClearColor(gray.getRed(), gray.getGreen(), gray.getBlue(), 1.0f);
                GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
                IsochromaticGabor.initGL(width, height);
                gabor.draw(context);
            }
        });

        ThreadUtil.sleep(10000);
    }

    @Test
    public void testRedGreenIsoluminant() {
        int size = 5;
        GaborSpec spec = new GaborSpec();
        spec.setOrientation(45);
        spec.setPhase(0);
        spec.setFrequency(1);
        spec.setXCenter(0);
        spec.setYCenter(0);
        spec.setSize(size);
        spec.setAnimation(false);

        IsoGaborSpec isoGaborSpec = new IsoGaborSpec(
               spec, "RedGreen");
        IsoluminantGabor gabor = new IsoluminantGabor(isoGaborSpec, 400, lutCorrector, sinusoidGainCorrector);
        gabor.setGaborSpec(isoGaborSpec);
        gabor.setSpec(isoGaborSpec.toXml());

        window.draw(new Drawable() {
            @Override
            public void draw() {
                RGBColor gray = lutCorrector.correctSingleColor(150, "gray");
                GL11.glClearColor(gray.getRed(), gray.getGreen(), gray.getBlue(), 1.0f);
                GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
                gabor.draw(context);
            }
        });

        double diskSize = perspectiveRenderer.deg2mm(size);
        double fadeSize = perspectiveRenderer.deg2mm(2 * 0.5 * size);
        double ratio = (diskSize + fadeSize) / perspectiveRenderer.getVpWidthmm();
        System.out.println("The Gabor should span approx: " + ratio + " of the screen width.");

        ThreadUtil.sleep(100000);

    }

    @Test
    public void testCyanOrangeIsoluminant(){
        int size = 10;
        GaborSpec spec = new GaborSpec();
        spec.setOrientation(45);
        spec.setPhase(0);
        spec.setFrequency(0.5);
        spec.setXCenter(0);
        spec.setYCenter(0);
        spec.setSize(size);
        spec.setAnimation(false);

        IsoGaborSpec isoGaborSpec = new IsoGaborSpec(
                spec, "CyanOrange");
        IsoluminantGabor gabor = new IsoluminantGabor(isoGaborSpec, 400, lutCorrector, sinusoidGainCorrector);
        gabor.setGaborSpec(isoGaborSpec);
        gabor.setSpec(isoGaborSpec.toXml());

        window.draw(new Drawable() {
            @Override
            public void draw() {
                RGBColor gray = lutCorrector.correctSingleColor(150, "gray");
                GL11.glClearColor(gray.getRed(), gray.getGreen(), gray.getBlue(), 1.0f);
                GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
                gabor.draw(context);
            }
        });

        double diskSize = perspectiveRenderer.deg2mm(size);
        double fadeSize = perspectiveRenderer.deg2mm(2 * 0.5 * size);
        double ratio = (diskSize + fadeSize) / perspectiveRenderer.getVpWidthmm();
        System.out.println("The Gabor should span approx: " + ratio + " of the screen width.");

        ThreadUtil.sleep(100000);
    }

    @Test
    public void testMixedAligned() {
        int size = 5;

        // Create base specs with different frequencies
        GaborSpec baseSpec = new GaborSpec();
        baseSpec.setOrientation(45);
        baseSpec.setPhase(0);
        baseSpec.setXCenter(0);
        baseSpec.setYCenter(0);
        baseSpec.setSize(size);
        baseSpec.setAnimation(false);

        // Chromatic component with frequency 1.0
        IsoGaborSpec chromaticSpec = new IsoGaborSpec(baseSpec, "CyanOrange");
        chromaticSpec.setFrequency(1.0);
        chromaticSpec.setPhase(0);

        // Luminance component with frequency 1.0
        GaborSpec luminanceSpec = new GaborSpec(baseSpec);
        luminanceSpec.setFrequency(1.0);
        luminanceSpec.setPhase(0.5);

        // Create combined gabor with different frequencies
        CombinedGabor gabor = new CombinedGabor(
                chromaticSpec,
                luminanceSpec,
                150,
                lutCorrector,
                sinusoidGainCorrector
        );

        window.draw(new Drawable() {
            @Override
            public void draw() {
                RGBColor gray = lutCorrector.correctSingleColor(150, "gray");
                GL11.glClearColor(gray.getRed(), gray.getGreen(), gray.getBlue(), 1.0f);
                GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
                gabor.draw(context);
            }
        });

        ThreadUtil.sleep(10000);
    }

    @Test
    public void testMixedUnaligned() {
        int size = 5;

        // Create base specs with different frequencies
        GaborSpec baseSpec = new GaborSpec();
        baseSpec.setOrientation(45);
        baseSpec.setPhase(0);
        baseSpec.setXCenter(0);
        baseSpec.setYCenter(0);
        baseSpec.setSize(size);
        baseSpec.setAnimation(false);

        // Chromatic component with frequency 1.0
        IsoGaborSpec chromaticSpec = new IsoGaborSpec(baseSpec, "CyanOrange");
        chromaticSpec.setFrequency(1.0);
        chromaticSpec.setPhase(0);

        // Luminance component with frequency 2.0
        GaborSpec luminanceSpec = new GaborSpec(baseSpec);
        luminanceSpec.setFrequency(0.5);
        luminanceSpec.setPhase(0.25);

        // Create combined gabor with different frequencies
        CombinedGabor gabor = new CombinedGabor(
                chromaticSpec,
                luminanceSpec,
                150,
                lutCorrector,
                sinusoidGainCorrector
        );

        window.draw(new Drawable() {
            @Override
            public void draw() {
                RGBColor gray = lutCorrector.correctSingleColor(150, "gray");
                GL11.glClearColor(gray.getRed(), gray.getGreen(), gray.getBlue(), 1.0f);
                GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
                gabor.draw(context);
            }
        });

        ThreadUtil.sleep(100000);
    }

    public DataSource dataSource() {
        ComboPooledDataSource source = new ComboPooledDataSource();
        try {
            source.setDriverClass("com.mysql.jdbc.Driver");
        } catch (PropertyVetoException e) {
            throw new DbException(e);
        }
        source.setJdbcUrl("jdbc:mysql://172.30.6.80/allen_monitorlinearization_250128?rewriteBatchedStatements=true");
        source.setUser("xper_rw");
        source.setPassword("up2nite");
        return source;
    }
}