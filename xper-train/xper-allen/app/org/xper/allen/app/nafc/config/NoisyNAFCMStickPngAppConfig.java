package org.xper.allen.app.nafc.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.allen.config.NAFCConfig;
import org.xper.allen.nafc.blockgen.NoisyMStickPngBlockGen;
import org.xper.allen.noisy.nafc.NoisyNAFCPngScene;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import(NAFCMStickPngAppConfig.class)
public class NoisyNAFCMStickPngAppConfig {
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
	
	@Bean
	public NoisyMStickPngBlockGen generator() {
		NoisyMStickPngBlockGen gen = new NoisyMStickPngBlockGen();
		gen.setDbUtil(config.allenDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setXmlUtil(config.allenXMLUtil());
		gen.setGeneratorPngPath(appConfig.generatorPngPath);
		gen.setExperimentPngPath(appConfig.experimentPngPath);
		gen.setGeneratorSpecPath(appConfig.generatorSpecPath);
		gen.setPngMaker(appConfig.pngMaker());
		gen.setMaxImageDimensionDegrees(appConfig.xperMaxImageDimensionDegrees());
		gen.setMmpGenerator(appConfig.mmpGenerator());
		gen.setQmpGenerator(appConfig.qmpGenerator());
		return gen;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperNoiseRate() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_noise_rate", 0));
	}
}
