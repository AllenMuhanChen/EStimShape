package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.util.DPIUtil;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.utils.RGBColor;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class MStickPngConfig {
    @Autowired ClassicConfig classicConfig;
    @Autowired BaseConfig baseConfig;

    @ExternalValue("generator.png_path")
    public String generatorPngPath;

    @ExternalValue("experiment.png_path")
    public String experimentPngPath;

    @ExternalValue("generator.spec_path")
    public String generatorSpecPath;

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public AllenPNGMaker pngMaker(){
        AllenPNGMaker pngMaker = new AllenPNGMaker();
        pngMaker.setWidth(dpiUtil().calculateMinResolution());
        pngMaker.setHeight(dpiUtil().calculateMinResolution());
        pngMaker.setDpiUtil(dpiUtil());
        RGBColor backColor = new RGBColor(xperBackgroundColor());
        pngMaker.setBackColor(backColor);
        pngMaker.setDepth(6000);
        pngMaker.setDistance(500);
        pngMaker.setPupilDistance(50);
        return pngMaker;
    }

    @Bean
    public DPIUtil dpiUtil(){
        DPIUtil dpiUtil = new DPIUtil();
        dpiUtil.setRenderer(classicConfig.experimentGLRenderer());
        dpiUtil.setDpi(xperMonkeyScreenDPI());
        dpiUtil.setMaxStimulusDimensionDegrees(xperMaxImageDimensionDegrees());
        dpiUtil.setGeneratorDPI(91.79);
        return dpiUtil;
    }
    @Bean(scope = DefaultScopes.PROTOTYPE)
    public double xperMaxImageDimensionDegrees(){
        return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_max_image_dimension_degrees", 0));
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public double[] xperBackgroundColor() {
        return new double[]{Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 0)),
                Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 1)),
                Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 2))};
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public double xperMonkeyScreenDPI(){
        return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_monkey_screen_dpi", 0));
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public Integer xperNoiseRate() {
        return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_noise_rate", 0));
    }
}