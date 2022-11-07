package org.xper.allen.app.fixation.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.allen.app.fixation.NoisyPngScene;
import org.xper.allen.app.nafc.config.NAFCMStickPngAppConfig;
import org.xper.allen.config.HeadFreeConfig;
import org.xper.allen.noisy.nafc.NoisyNAFCPngScene;
import org.xper.allen.util.AllenDbUtil;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.object.BlankScreen;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import({ClassicConfig.class})
public class NoisyPngFixationAppConfig {
    @Autowired ClassicConfig classicConfig;
    @Autowired BaseConfig baseConfig;
    @Autowired AcqConfig acqConfig;

    @Bean
    NoisyPngScene taskScene(){
        NoisyPngScene scene = new NoisyPngScene();
        scene.setRenderer(classicConfig.experimentGLRenderer());
        scene.setFixation(classicConfig.experimentFixationPoint());
        scene.setMarker(classicConfig.screenMarker());
        scene.setBlankScreen(new BlankScreen());
        scene.setBackgroundColor(xperBackgroundColor());
        scene.setFrameRate(xperNoiseRate());
        return scene;
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public double[] xperBackgroundColor() {
        return new double[]{Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 0)),
                Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 1)),
                Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 2))};
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
