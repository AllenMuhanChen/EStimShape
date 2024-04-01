package org.xper.allen.rfplot;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Lazy;

import org.xper.rfplot.RFPlotConfig;
import org.xper.rfplot.drawing.RFPlotBlankObject;
import org.xper.rfplot.drawing.RFPlotDrawable;
import org.xper.rfplot.drawing.RFPlotImgObject;
import org.xper.rfplot.drawing.gabor.Gabor;

import java.util.LinkedHashMap;
import java.util.Map;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(RFPlotConfig.class)
public class AllenRFPlotConfig {
    @Autowired RFPlotConfig rfPlotConfig;

    @Bean
    public Map<String, RFPlotDrawable> namesForDrawables() {
        LinkedHashMap<String, RFPlotDrawable> refObjMap = new LinkedHashMap<String, RFPlotDrawable>();
        refObjMap.put(RFPlotBlankObject.class.getName(), new RFPlotBlankObject());
        refObjMap.put(RFPlotMatchStick.class.getName(), new RFPlotMatchStick());
        refObjMap.put(RFPlotImgObject.class.getName(), new RFPlotImgObject(rfPlotConfig.imgPathScroller().getFirstPath()));
        refObjMap.put(Gabor.class.getName(), new Gabor());
        return refObjMap;
    }

}