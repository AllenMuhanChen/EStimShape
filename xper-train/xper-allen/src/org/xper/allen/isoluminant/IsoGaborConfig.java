package org.xper.allen.isoluminant;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.monitorlinearization.ColorLookupTable;
import org.xper.allen.monitorlinearization.GainLookupTable;
import org.xper.allen.monitorlinearization.LookUpTableCorrector;
import org.xper.allen.monitorlinearization.SinusoidGainCorrector;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.RGBColor;
import org.xper.drawing.object.BlankScreen;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class IsoGaborConfig {
    @Autowired
    ClassicConfig classicConfig;
    @Autowired
    BaseConfig baseConfig;

    @Bean
    public IsoGaborScene taskScene() {
        IsoGaborScene scene = new IsoGaborScene();
        scene.setRenderer(classicConfig.experimentGLRenderer());
        scene.setFixation(classicConfig.experimentFixationPoint());
        scene.setMarker(classicConfig.screenMarker());
        scene.setBlankScreen(new BlankScreen());
        scene.setLutCorrector(lookUpTableCorrector());
        scene.setSinusoidGainCorrector(sinusoidCorrector());
        scene.setTargetLuminanceCandela(targetLuminanceCandela());
        scene.setBackgroundColor(targetLuminanceBackgroundColor());
        return scene;
    }

    @Bean
    public int targetLuminanceCandela() {
        return 400;
    }

    @Bean
    public RGBColor targetLuminanceBackgroundColor() {
        return lookUpTableCorrector().correctSingleColor(targetLuminanceCandela(), "gray");
    }

    @Bean
    public LookUpTableCorrector lookUpTableCorrector() {
        LookUpTableCorrector lut = new LookUpTableCorrector();
        lut.setLookupTable(colorLookupTable());
        return lut;
    }

    @Bean
    public ColorLookupTable colorLookupTable() {
        ColorLookupTable lut = new ColorLookupTable();
        lut.setDataSource(baseConfig.dataSource());
        lut.init();
        return lut;
    }

    @Bean
    public SinusoidGainCorrector sinusoidCorrector() {
        SinusoidGainCorrector sc = new SinusoidGainCorrector();
        sc.setGainLookupTable(gainLookupTable());
        return sc;
    }

    @Bean
    public GainLookupTable gainLookupTable() {
        GainLookupTable table = new GainLookupTable();
        table.setDataSource(baseConfig.dataSource());
        table.init();
        return table;
    }

    @Bean
    public IsoGaborTrialGenerator trialGenerator() {
        IsoGaborTrialGenerator gen = new IsoGaborTrialGenerator();
        gen.setGlobalTimeUtil(baseConfig.localTimeUtil());
        gen.setDbUtil(baseConfig.dbUtil());
        return gen;
    }
}