package org.xper.allen.app.nafc.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.ExternalValue;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.allen.config.HeadFreeConfig;
import org.xper.allen.config.NAFCConfig;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParameterGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParameterGenerator;
import org.xper.allen.nafc.NAFCPngScene;
import org.xper.allen.nafc.blockgen.MStickPngBlockGen;
import org.xper.allen.util.DPIUtil;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.object.BlankScreen;
import org.xper.utils.RGBColor;


@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

//@Import annotation avoids @ComponentScanning?
@Import({NAFCConfig.class, HeadFreeConfig.class})
/**
 * methods written here will OVERRIDE methods with identical name in config. 
 * By default, when one spring configuration file imports another one, the later definitions (imported) are overidden by earlier ones (importing)
 *
 *https://stackoverflow.com/questions/10993181/defining-the-same-spring-bean-twice-with-same-name
 *https://www.marcobehler.com/guides/spring-framework
 * @author r2_allen
 *
 */

public class NAFCMStickPngAppConfig {
	@Autowired NAFCConfig config;
	@Autowired HeadFreeConfig headFreeConfig;
	@Autowired ClassicConfig classicConfig;
	@Autowired BaseConfig baseConfig;
	@Autowired AcqConfig acqConfig;

	@ExternalValue("generator.png_path")
	public String generatorPngPath;

	@ExternalValue("experiment.png_path")
	public String experimentPngPath;
	
	@ExternalValue("generator.spec_path")
	public String generatorSpecPath;



	@Bean
	public NAFCPngScene taskScene() {
		NAFCPngScene scene = new NAFCPngScene();
		scene.setRenderer(config.experimentGLRenderer());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setScreenHeight(classicConfig.xperMonkeyScreenHeight());
		scene.setScreenWidth(classicConfig.xperMonkeyScreenWidth());
		scene.setDistance(classicConfig.xperMonkeyScreenDistance());
		scene.setBackgroundColor(xperBackgroundColor());
		return scene;
	}

	@Bean
	public MStickPngBlockGen generator() {
		MStickPngBlockGen gen = new MStickPngBlockGen();
		gen.setDbUtil(config.allenDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setXmlUtil(config.allenXMLUtil());
		gen.setGeneratorPngPath(generatorPngPath);
		gen.setExperimentPngPath(experimentPngPath);
		gen.setGeneratorSpecPath(generatorSpecPath);
		gen.setPngMaker(pngMaker());
		gen.setMaxImageDimensionDegrees(xperMaxImageDimensionDegrees());
		gen.setMmpGenerator(mmpGenerator());
		gen.setQmpGenerator(qmpGenerator());
		return gen;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public AllenPNGMaker pngMaker(){
		AllenPNGMaker pngMaker = new AllenPNGMaker();
		pngMaker.setWidth(dpiUtil().calculateMinResolution());
		pngMaker.setHeight(dpiUtil().calculateMinResolution());
		pngMaker.setDpiUtil(dpiUtil());
		RGBColor backColor = new RGBColor(0,0,0);
		pngMaker.setBackColor(backColor);
		pngMaker.setDepth(6000);
		pngMaker.setDistance(500);
		pngMaker.setPupilDistance(50);
		return pngMaker;
	}


	@Bean
	public DPIUtil dpiUtil(){
		DPIUtil dpiUtil = new DPIUtil();
		dpiUtil.setRenderer(config.experimentGLRenderer());
		dpiUtil.setDpi(xperMonkeyScreenDPI());
		dpiUtil.setMaxStimulusDimensionDegrees(xperMaxImageDimensionDegrees());
		dpiUtil.setGeneratorDPI(91.79);
		return dpiUtil;
	}

	@Bean
	public MetricMorphParameterGenerator mmpGenerator() {
		MetricMorphParameterGenerator mmpGenerator = new MetricMorphParameterGenerator(); 
		return mmpGenerator;
	}
	
	@Bean
	public QualitativeMorphParameterGenerator qmpGenerator() {
		QualitativeMorphParameterGenerator qmpGenerator = new QualitativeMorphParameterGenerator(xperMaxImageDimensionDegrees());
		return qmpGenerator;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public double[] xperBackgroundColor() {
		return new double[]{Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 0)),
				Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 1)),
				Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 2))};
	}

	//For DPIUtil
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public double xperMonkeyScreenDPI(){
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_monkey_screen_dpi", 0));
	}

	//For DPIUtil
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public double xperMaxImageDimensionDegrees(){
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_max_image_dimension_degrees", 0));
	}
}