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
import org.xper.allen.nafc.NAFCMStickScene;
import org.xper.allen.nafc.NAFCPngScene;
import org.xper.allen.nafc.blockgen.MStickBlockGenOne;
import org.xper.allen.nafc.blockgen.PngBlockGenFour;
import org.xper.allen.nafc.blockgen.PngBlockGenTwo;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.object.BlankScreen;


@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

//@Import annotation avoids @ComponentScanning?
@Import(NAFCConfig.class)
/**
 * methods written here will OVERRIDE methods with identical name in config. 
 * By default, when one spring configuration file imports another one, the later definitions (imported) are overidden by earlier ones (importing)
 *
 *https://stackoverflow.com/questions/10993181/defining-the-same-spring-bean-twice-with-same-name
 *https://www.marcobehler.com/guides/spring-framework
 * @author r2_allen
 *
 */
/**
 * Deprecated
 * @author r2_allen
 *
 */
public class NAFCMStickAppConfig {
	@Autowired NAFCConfig config;
	@Autowired ClassicConfig classicConfig;
	@Autowired BaseConfig baseConfig;
	@Autowired AcqConfig acqConfig;
	
	@ExternalValue("generator.png_path")
	public String generatorPngPath;
	
	@ExternalValue("experiment.png_path")
	public String experimentPngPath;
	
	
	
	@Bean
	public NAFCMStickScene taskScene() {
		NAFCMStickScene scene = new NAFCMStickScene();
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
	public MStickBlockGenOne generator() {
		MStickBlockGenOne gen = new MStickBlockGenOne();
		gen.setDbUtil(config.allenDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setXmlUtil(config.allenXMLUtil());
		gen.setGeneratorPngPath(generatorPngPath);
		gen.setExperimentPngPath(experimentPngPath);
		return gen;
	}
	

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public double[] xperBackgroundColor() {
		return new double[]{Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 0)),
							Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 1)),
							Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 2))};
	}
}