package org.xper.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.ExternalValue;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.mockxper.GenerationManager;
import org.xper.mockxper.MockDataChannel;
import org.xper.mockxper.MockMarkerChannel;
import org.xper.mockxper.MockSpikeGenerator;
import org.xper.mockxper.MockXper;
import org.xper.mockxper.TaskAcqDataBuilder;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(AcqConfig.class)
public class MockConfig {
	@Autowired AcqConfig acqConfig;
	@Autowired BaseConfig baseConfig;
	
	@Autowired MockSpikeGenerator spikeGenerator;
	
	@ExternalValue("mock.tasks_per_trial")
	public int tasksPerTrial;
	
	@Bean
	public MockXper mockXper () {
		MockXper xper = new MockXper ();
		xper.setBatchSize(tasksPerTrial);
		xper.setSpikeGen(spikeGenerator);
		xper.setDbUtil(baseConfig.dbUtil());
		xper.setAcqDataBuilder(acqDataBuilder());
		xper.setGlobalTimeUtil(acqConfig.timeClient());
		xper.setGenerationManager(generationManager());
		return xper;
	}

	@Bean
	public MockDataChannel mockDataChannel () {
		return new MockDataChannel();
	}
	
	@Bean
	public MockMarkerChannel mockMarkerChannel () {
		return new MockMarkerChannel();
	}
	
	@Bean
	public TaskAcqDataBuilder acqDataBuilder () {
		TaskAcqDataBuilder builder = new TaskAcqDataBuilder ();
		builder.setDbUtil(baseConfig.dbUtil());
		builder.setDataChan(mockDataChannel());
		builder.setMarkerChan(mockMarkerChannel());
		return builder;
	}
	
	@Bean
	public GenerationManager generationManager () {
		return new GenerationManager(baseConfig.dbUtil());
	}
}
