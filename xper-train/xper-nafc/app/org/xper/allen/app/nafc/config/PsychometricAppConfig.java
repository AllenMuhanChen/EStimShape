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
import org.xper.allen.config.NAFCConfig;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.qualitativemorphs.PsychometricQualitativeMorphParameterGenerator;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.allen.noisy.nafc.NoisyNAFCPngScene;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.utils.RGBColor;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({NAFCMStickPngAppConfig.class})
public class PsychometricAppConfig {
	@Autowired NAFCMStickPngAppConfig appConfig;
	@Autowired NAFCConfig config;
	@Autowired ClassicConfig classicConfig;
	@Autowired BaseConfig baseConfig;
	@Autowired AcqConfig acqConfig;
	
	@Bean
	public NoisyNAFCPngScene taskScene() {
		NoisyNAFCPngScene scene = new NoisyNAFCPngScene();
		scene.setRenderer(config.experimentGLRenderer());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setScreenHeight(classicConfig.xperMonkeyScreenHeight());
		scene.setScreenWidth(classicConfig.xperMonkeyScreenWidth());
		scene.setDistance(classicConfig.xperMonkeyScreenDistance());
		scene.setBackgroundColor(appConfig.xperBackgroundColor());
		scene.setFrameRate(xperNoiseRate());
		return scene;
	}
	
	/**
	 * When switching to Perspective Renderer we need to make sure the xper-monkey-screen-length is precisely
	 * the same width as the actual screen. 
	 * @return
	 */
	@Bean
	public AbstractRenderer experimentGLRenderer () {
		PerspectiveRenderer renderer = new PerspectiveRenderer();
		renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
		renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
		renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
		renderer.setWidth(classicConfig.xperMonkeyScreenWidth());
		renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
		return renderer;
	}
	
	/**
	 * NoisyMStickPngBlockGen has been upgraded to have generateSet
	 * @return
	 */
	@Bean
	public PsychometricBlockGen psychometricPngGenerator() {
		PsychometricBlockGen gen = new PsychometricBlockGen();
		gen.setDbUtil(config.allenDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setGeneratorPngPath(appConfig.generatorPngPath);
		gen.setExperimentPngPath(appConfig.experimentPngPath);
		gen.setGeneratorSpecPath(appConfig.generatorSpecPath);
		gen.setGeneratorPsychometricPngPath(generatorPsychometricPngPath);
		gen.setExperimentPsychometricPngPath(experimentPsychometricPngPath);
		gen.setGeneratorPsychometricNoiseMapPath(generatorPsychometricNoiseMapPath);
		gen.setExperimentPsychometricNoiseMapPath(experimentPsychometricNoiseMapPath);
		gen.setGeneratorPsychometricSpecPath(generatorPsychometricSpecPath);
		gen.setPngMaker(psychometricPngMaker());
		gen.setMaxImageDimensionDegrees(appConfig.xperMaxImageDimensionDegrees());
		return gen;
	}
	
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public AllenPNGMaker psychometricPngMaker(){
		AllenPNGMaker pngMaker = new AllenPNGMaker();
		pngMaker.setWidth(appConfig.dpiUtil().calculateMinResolution());
		pngMaker.setHeight(appConfig.dpiUtil().calculateMinResolution());
		pngMaker.setDpiUtil(appConfig.dpiUtil());
		RGBColor backColor = new RGBColor(0,0,0);
		pngMaker.setBackColor(backColor);
		pngMaker.setDepth(6000);
		pngMaker.setDistance(500);
		pngMaker.setPupilDistance(50);
		return pngMaker;
	}
	
	@ExternalValue("generator.psychometric.noisemap_path")
	public String generatorPsychometricNoiseMapPath;

	@ExternalValue("generator.psychometric.png_path")
	public String generatorPsychometricPngPath;

	@ExternalValue("experiment.psychometric.noisemap_path")
	public String experimentPsychometricNoiseMapPath;
	
	@ExternalValue("experiment.psychometric.png_path")
	public String experimentPsychometricPngPath;
	
	@ExternalValue("generator.psychometric.spec_path")
	public String generatorPsychometricSpecPath;



	/**
	 * NoisyMStickPngBlockGen has been upgraded to have generateSet
	 * @return
	 */
	@Bean
	public AbstractMStickPngTrialGenerator randBlockGenerator() {
		PsychometricBlockGen gen = new PsychometricBlockGen();
		gen.setDbUtil(config.allenDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setGeneratorPngPath(appConfig.generatorPngPath);
		gen.setExperimentPngPath(appConfig.experimentPngPath);
		gen.setGeneratorSpecPath(appConfig.generatorSpecPath);
		gen.setPngMaker(appConfig.pngMaker());
		gen.setMaxImageDimensionDegrees(appConfig.xperMaxImageDimensionDegrees());
		return gen;
	}
	
	@Bean
	public PsychometricQualitativeMorphParameterGenerator psychometricQmpGenerator() {
		PsychometricQualitativeMorphParameterGenerator qmpGenerator = new PsychometricQualitativeMorphParameterGenerator(appConfig.xperMaxImageDimensionDegrees());
		return qmpGenerator;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperNoiseRate() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_noise_rate", 0));
	}
}
