
/*
package org.xper.allen.config;
import org.xper.app.experiment.test.TestGeneration;
import org.xper.example.classic.ClassicAppConfig;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
public class AllenAppConfig extends ClassicAppConfig {
	@Autowired AllenConfig allenConfig;
	//AllenConfig allenConfig = new AllenConfig();
	@Bean
	public TestGeneration testGen() {
		TestGeneration gen = new TestGeneration();
		gen.setDbUtil(allenConfig.allenDbUtil());
		gen.setGlobalTimeUtil(allenAcqConfig.timeClient());
		//gen.setTaskCount(100);
		gen.setGenerator(generator());
		return gen;
	}
}
*/
package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.app.experiment.test.TestGeneration;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;


@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import(AllenConfig.class)
public class AllenAppConfig {
	@Autowired AllenConfig allenConfig;
	@Autowired ClassicConfig classicConfig;
	@Autowired BaseConfig baseConfig;
	@Autowired AcqConfig acqConfig;
	
	/*
	@Bean
	public TestGeneration testGen() {
		TestGeneration gen = new TestGeneration();
		gen.setDbUtil(allenConfig.allenDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		//gen.setTaskCount(100);
		gen.setGenerator(generator());
		return gen;
		
	}
	*/
}