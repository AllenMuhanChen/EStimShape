package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.config.FixCalConfig;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;

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
@Import(FixCalConfig.class)
public class AllenFixCalConfig {
	@Autowired FixCalConfig config;
	@Autowired ClassicConfig classicConfig;
	@Autowired AcqConfig acqConfig;
	@Autowired BaseConfig baseConfig;
	@Bean
	public AbstractRenderer consoleGLRenderer () {
		PerspectiveRenderer renderer = new PerspectiveRenderer();
		renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
		renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
		renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
		renderer.setWidth(xperMonkeyScreenWidth());
		renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
		return renderer;
	}
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperMonkeyScreenWidth() {
		//DIVIDE by two account for doubled monkey screen width. 
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_monkey_screen_width", 0))/2;
	}
}
