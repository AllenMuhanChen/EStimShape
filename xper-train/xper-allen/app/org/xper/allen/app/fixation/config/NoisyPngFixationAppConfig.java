package org.xper.allen.app.fixation.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.support.ConfigurationSupport;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.allen.app.fixation.NoisyPngScene;
import org.xper.allen.config.MStickPngConfig;
import org.xper.allen.config.RewardButtonConfig;
import org.xper.allen.fixation.blockgen.NoisyPngFixationBlockGen;
import org.xper.allen.util.AllenDbUtil;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.object.BlankScreen;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import({ClassicConfig.class, MStickPngConfig.class, RewardButtonConfig.class})
public class NoisyPngFixationAppConfig extends ConfigurationSupport {
    @Autowired ClassicConfig classicConfig;
    @Autowired BaseConfig baseConfig;
    @Autowired MStickPngConfig mStickConfig;

    @Bean
    public NoisyPngFixationBlockGen noisyPngFixationBlockGen(){
        NoisyPngFixationBlockGen generator = new NoisyPngFixationBlockGen();
        generator.setDbUtil(allenDbUtil());
        generator.setPngMaker(mStickConfig.pngMaker());
        generator.setGeneratorPngPath(mStickConfig.generatorPngPath);
        generator.setGeneratorSpecPath(mStickConfig.generatorSpecPath);
        generator.setExperimentPngPath(mStickConfig.experimentPngPath);
        generator.setGlobalTimeUtil(baseConfig.localTimeUtil());
        generator.setMaxImageDimensionDegrees(mStickConfig.xperMaxImageDimensionDegrees());
        return generator;
    }

    @Bean
    public NoisyPngScene taskScene(){
        NoisyPngScene scene = new NoisyPngScene();
        scene.setRenderer(classicConfig.experimentGLRenderer());
        scene.setFixation(classicConfig.experimentFixationPoint());
        scene.setMarker(classicConfig.screenMarker());
        scene.setBlankScreen(new BlankScreen());
        scene.setBackgroundColor(mStickConfig.xperPngBackgroundColor());
        scene.setFrameRate(xperNoiseRate());
        scene.setSlideLength(classicConfig.xperSlideLength());
        return scene;
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public Integer xperNoiseRate() {
        return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_noise_rate", 0));
    }

    @Bean
    public AllenDbUtil allenDbUtil() {
        AllenDbUtil dbUtil = new AllenDbUtil();
        dbUtil.setDataSource(baseConfig.dataSource());
        return dbUtil;
    }

}