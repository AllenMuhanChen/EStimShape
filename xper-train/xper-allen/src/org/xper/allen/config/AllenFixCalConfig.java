package org.xper.allen.config;

import java.util.ArrayList;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.fixcal.FixCalExperimentConsoleRenderer;
import org.xper.classic.TrialExperimentConsoleRenderer;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.object.Circle;
import org.xper.drawing.object.Square;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.eye.strategy.AnyEyeInStategy;
import org.xper.eye.strategy.EyeInStrategy;
/**
 * Uses base fixcal config but:
 * 1.  	tweaks the monkey screen width for the CONSOLE renderer only in order to correct 
 * 		for the xper_monkey_screen_width being set to 2x the actual screen width in SystemVar. 
 * @author r2_allen
 *
 */
@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(RewardButtonFixCalConfig.class)
public class AllenFixCalConfig {
	@Autowired RewardButtonFixCalConfig config;
	@Autowired ClassicConfig classicConfig;
	@Autowired AcqConfig acqConfig;
	@Autowired BaseConfig baseConfig;

	@Bean
	public AbstractRenderer consoleGLRenderer () {
		PerspectiveRenderer renderer = new PerspectiveRenderer();
		renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
		renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
		renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
		renderer.setWidth(classicConfig.xperMonkeyScreenWidth());
		renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
		return renderer;
	}
	
	
	@Bean
	public EyeInStrategy eyeInStrategy () {
		AnyEyeInStategy strategy = new AnyEyeInStategy();
		ArrayList<String> eyeDevices = new ArrayList<String>();
		eyeDevices.add(classicConfig.xperLeftIscanId());
		eyeDevices.add(classicConfig.xperRightIscanId());
		strategy.setEyeDevices(eyeDevices);
		return strategy;
	}
	
	@Bean
	public FixCalExperimentConsoleRenderer consoleRenderer () {
		FixCalExperimentConsoleRenderer renderer = new FixCalExperimentConsoleRenderer();
		renderer.setMessageHandler(classicConfig.messageHandler());
		renderer.setFixation(classicConfig.consoleFixationPoint());
		renderer.setRenderer(consoleGLRenderer());
		renderer.setBlankScreen(new BlankScreen());
		renderer.setCircle(new Circle());
		renderer.setSquare(new Square());
		return renderer;
	}
	
}
