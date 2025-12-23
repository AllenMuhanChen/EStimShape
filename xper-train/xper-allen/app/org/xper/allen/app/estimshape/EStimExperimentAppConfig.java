package org.xper.allen.app.estimshape;

import com.mchange.v2.c3p0.ComboPooledDataSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.app.nafc.config.NAFCMStickPngAppConfig;
import org.xper.allen.app.procedural.EStimShapeExperimentSetGenerator;
import org.xper.allen.app.procedural.NAFCTrialGeneratorGUI;
import org.xper.allen.app.procedural.ProceduralAppConfig;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.composition.noisy.NAFCNoiseMapper;
import org.xper.allen.nafc.blockgen.EStimShapeProceduralBehavioralGenType;
import org.xper.allen.nafc.blockgen.procedural.EStimExperimentGenType;
import org.xper.allen.nafc.blockgen.procedural.EStimExperimentVariantsGenType;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.allen.util.DPIUtil;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.exception.DbException;
import org.xper.utils.RGBColor;

import javax.sql.DataSource;
import java.beans.PropertyVetoException;
import java.util.Arrays;
import java.util.List;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ProceduralAppConfig.class)
public class EStimExperimentAppConfig {
    @Autowired
    public ProceduralAppConfig proceduralAppConfig;

    @Autowired
    public NAFCMStickPngAppConfig pngConfig;

    @Autowired
    ClassicConfig classicConfig;

    @Autowired
    BaseConfig baseConfig;

    @ExternalValue("generator.set_path")
    String generatorSetPath;

    @ExternalValue("ga.jdbc.url")
    public String ga_jdbcUrl;


    @Bean
    public List<Double> xperNoiseRewardFunctionNoises() {

        return Arrays.asList(0.0, 0.3, 0.5);
    }


    @Bean
    public List<Double> xperNoiseRewardFunctionRewards() {

        return Arrays.asList(3.0, 3.0, 3.0);
    }

    @Bean
    public EStimShapeExperimentTrialGenerator generator(){
        EStimShapeExperimentTrialGenerator generator = new EStimShapeExperimentTrialGenerator();
        generator.setDbUtil(pngConfig.config.allenDbUtil());
        generator.setGlobalTimeUtil(pngConfig.acqConfig.timeClient());
        generator.setGeneratorPngPath(pngConfig.mStickPngConfig.generatorPngPath);
        generator.setExperimentPngPath(pngConfig.mStickPngConfig.experimentPngPath);
        generator.setGeneratorSpecPath(pngConfig.mStickPngConfig.generatorSpecPath);
        generator.setPngMaker(pngConfig.mStickPngConfig.pngMaker());
        generator.setImageDimensionDegrees(pngConfig.mStickPngConfig.xperMaxImageDimensionDegrees());
        generator.setNoiseMapper(pngConfig.mStickPngConfig.noiseMapper());
        //Dependencies of ProceduuralExperimentgenerator
        generator.setGeneratorNoiseMapPath(proceduralAppConfig.generatorNoiseMapPath);
        generator.setExperimentNoiseMapPath(proceduralAppConfig.experimentNoiseMapPath);
        generator.setNafcTrialDbUtil(proceduralAppConfig.nafcTrialDbUtil());
        generator.setGaSpecPath(proceduralAppConfig.gaSpecPath);
        generator.setRfSource(rfSource());
        generator.setGeneratorSetPath(generatorSetPath);
        generator.setSamplePngMaker(samplePngMaker());
        generator.setGaDataSource(gaDataSource());
        generator.setMaxSampleDimensionDegrees(maxSampleSizeDegrees());
        generator.setMaxChoiceDimensionDegrees(pngConfig.mStickPngConfig.xperMaxImageDimensionDegrees());
        return generator;
    }

    @Bean
    public DataSource gaDataSource() {
        ComboPooledDataSource source = new ComboPooledDataSource();
        try {
            source.setDriverClass(baseConfig.jdbcDriver);
        } catch (PropertyVetoException e) {
            throw new DbException(e);
        }
        source.setJdbcUrl(ga_jdbcUrl);
        source.setUser(baseConfig.jdbcUserName);
        source.setPassword(baseConfig.jdbcPassword);
        return source;
    }

    @Bean
    public EStimShapeProceduralBehavioralGenType eStimBehavioralGenType() {
        EStimShapeProceduralBehavioralGenType genType = new EStimShapeProceduralBehavioralGenType();
        genType.setGenerator(generator()); // Uses EStimShapeExperimentTrialGenerator
        return genType;
    }
    @Bean
    public NAFCTrialGeneratorGUI nafcTrialGeneratorGUI() {
        NAFCTrialGeneratorGUI gui = new NAFCTrialGeneratorGUI();
        gui.setBlockgen(generator());
        gui.setStimTypes(Arrays.asList(
                proceduralAppConfig.proceduralRandGenType(),
                eStimBehavioralGenType(),
                eStimExperimentGenType(),
                estimExperimentVariantsGenType()
        ));
        gui.setDefaultStimType(proceduralAppConfig.proceduralRandGenType());
        return gui;
    }

    @Bean
    public EStimExperimentVariantsGenType estimExperimentVariantsGenType() {
        EStimExperimentVariantsGenType genType = new EStimExperimentVariantsGenType();
        genType.setGenerator(generator());
        return genType;
    }

    @Bean
    public EStimExperimentGenType eStimExperimentGenType() {
        EStimExperimentGenType eStimExperimentGenType = new EStimExperimentGenType();
        eStimExperimentGenType.setGaSpecPath(proceduralAppConfig.gaSpecPath);
        eStimExperimentGenType.setGenerator(generator());
        return eStimExperimentGenType;
    }

    @Bean
    public EStimShapeExperimentSetGenerator setGenerator(){
        EStimShapeExperimentSetGenerator setGenerator = new EStimShapeExperimentSetGenerator();
        setGenerator.setGenerator(generator());
        setGenerator.setGeneratorSetPath(generatorSetPath);
        setGenerator.setNoiseMapper(pngConfig.mStickPngConfig.noiseMapper());
        return setGenerator;
    }

    @Bean
    public ReceptiveFieldSource rfSource(){
        ReceptiveFieldSource rfSource = new ReceptiveFieldSource();
        rfSource.setDataSource(baseConfig.dataSource());
        rfSource.setRenderer(classicConfig.experimentGLRenderer());
        return rfSource;
    }

    @Bean
    public AllenPNGMaker samplePngMaker(){
        AllenPNGMaker pngMaker = new AllenPNGMaker();
        pngMaker.setWidth(sampleDPIUtil().calculateMinResolution());
        pngMaker.setHeight(sampleDPIUtil().calculateMinResolution());
        pngMaker.setDpiUtil(sampleDPIUtil());
        RGBColor backColor = new RGBColor(0.0, 0.0, 0.0);
        pngMaker.setBackColor(backColor);
        pngMaker.setDepth(6000);
        pngMaker.setDistance(500);
        pngMaker.setPupilDistance(50);
        pngMaker.setNoiseMapper(noiseMapper());
        return pngMaker;
    }

    @Bean
    public DPIUtil sampleDPIUtil(){
        DPIUtil dpiUtil = new DPIUtil();
        dpiUtil.setRenderer(classicConfig.experimentGLRenderer());
        dpiUtil.setDpi(pngConfig.mStickPngConfig.xperMonkeyScreenDPI());
        dpiUtil.setMaxStimulusDimensionDegrees(maxSampleSizeDegrees());
        dpiUtil.setGeneratorDPI(163.2);
        return dpiUtil;
    }

    @Bean
    public int maxSampleSizeDegrees() {
        return 45;
    }

    @Bean
    public NAFCNoiseMapper noiseMapper() {
        GaussianNoiseMapper noiseMapper = new GaussianNoiseMapper();
        noiseMapper.setBackground(0);
        noiseMapper.setWidth(sampleDPIUtil().calculateMinResolution());
        noiseMapper.setHeight(sampleDPIUtil().calculateMinResolution());
        noiseMapper.setDoEnforceHiddenJunction(true);
        return noiseMapper;
    }

}