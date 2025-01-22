package org.xper.allen.rfplot;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Lazy;

import org.xper.rfplot.RFPlotConfig;
import org.xper.rfplot.XMLizable;
import org.xper.rfplot.drawing.RFPlotBlankObject;
import org.xper.rfplot.drawing.RFPlotDrawable;
import org.xper.rfplot.drawing.RFPlotImgObject;
import org.xper.rfplot.drawing.bar.*;
import org.xper.rfplot.drawing.gabor.Gabor;
import org.xper.rfplot.gui.RFPlotStimModulator;
import org.xper.rfplot.gui.scroller.HueScroller;
import org.xper.rfplot.gui.scroller.LightnessScroller;
import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.SaturationScroller;

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
//        refObjMap.put(RFPlotImgObject.class.getName(), new RFPlotImgObject(imgPathScroller().getFirstPath()));
        refObjMap.put(Gabor.class.getName(), new Gabor());
        refObjMap.put(RFPlotBar.class.getName(), new RFPlotBar());
        return refObjMap;
    }

    @Bean
    public Map<String, RFPlotStimModulator> modulatorsForDrawables(){
        LinkedHashMap<String, RFPlotStimModulator> refModulatorMap = new LinkedHashMap<>();
//        refModulatorMap.put(RFPlotImgObject.class.getName(), imgModulator());
        refModulatorMap.put(Gabor.class.getName(), rfPlotConfig.gaborModulator());
        refModulatorMap.put(RFPlotBar.class.getName(), barModulator());
        return refModulatorMap;
    }

    @Bean
    public RFPlotStimModulator barModulator() {
        RFPlotStimModulator barModulator = new RFPlotStimModulator(barScrollers());
        return barModulator;
    }

    @Bean
    public LinkedHashMap<String, RFPlotScroller<? extends XMLizable>> barScrollers() {
        LinkedHashMap<String, RFPlotScroller<? extends XMLizable>> map = new LinkedHashMap<>();
        map.put("Orientation", new BarOrientationScroller<>(RFPlotBar.RFPlotBarSpec.class));
        map.put("Length", new BarLengthScroller<>(RFPlotBar.RFPlotBarSpec.class));
        map.put("Width", new BarWidthScroller<>(RFPlotBar.RFPlotBarSpec.class));
        map.put("Size", new BarSizeScroller<>(RFPlotBar.RFPlotBarSpec.class));
        map.put("Hue", new HueScroller());
        map.put("Saturation", new SaturationScroller());
        map.put("Lightness", new LightnessScroller());
        return map;
    }


    @Bean
    public RFPlotStimModulator mStickModulator() {
        RFPlotStimModulator mStickModulator = new RFPlotStimModulator(mStickScrollers());
        return mStickModulator;
    }

    private LinkedHashMap<String, RFPlotScroller<? extends XMLizable>> mStickScrollers() {
        LinkedHashMap<String, RFPlotScroller<? extends XMLizable>> scrollers = new LinkedHashMap<String, RFPlotScroller<? extends XMLizable>>();
        scrollers.put("RandMStick", new RandMStickScroller<>(RFPlotMatchStick.RFPlotMatchStickSpec.class));
        scrollers.put("Size", new MStickSizeScroller<>(RFPlotMatchStick.RFPlotMatchStickSpec.class));
        scrollers.put("Rotation X", new MStickRotationScroller<>(RFPlotMatchStick.RFPlotMatchStickSpec.class, 0));
        scrollers.put("Rotation Y", new MStickRotationScroller<>(RFPlotMatchStick.RFPlotMatchStickSpec.class, 1));
        scrollers.put("Rotation Z", new MStickRotationScroller<>(RFPlotMatchStick.RFPlotMatchStickSpec.class, 2));
        scrollers.put("Hue", new MStickHueScroller<>(RFPlotMatchStick.RFPlotMatchStickSpec.class));
        scrollers.put("Saturation", new MStickSaturationScroller<>(RFPlotMatchStick.RFPlotMatchStickSpec.class));
        scrollers.put("Lightness", new MStickLightnessScroller<>(RFPlotMatchStick.RFPlotMatchStickSpec.class));
        scrollers.put("Texture", new MStickTextureScroller<>(RFPlotMatchStick.RFPlotMatchStickSpec.class));
        return scrollers;
    }

}