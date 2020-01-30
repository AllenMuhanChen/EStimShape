package org.xper.app.mock;

import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.ExternalValue;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.support.ConfigurationSupport;
import org.xper.config.MockConfig;
import org.xper.mockxper.MockSpikeGenerator;
import org.xper.mockxper.plugin.ManualInputSpikeGenerator;
import org.xper.mockxper.plugin.MatlabSpikeGenerator;
import org.xper.mockxper.plugin.RandomSpikeGenerator;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(MockConfig.class)
public class MockAppConfig extends ConfigurationSupport {
	
	@ExternalValue("mock.matlab_spike_function_name")
	public String matlabSpikeFunctionName;

	@ExternalValue("mock.spike_generator_plugin")
	public String spikeGeneratorPlugin;
	
	@Bean
	public MockSpikeGenerator spikeGenerator() {
		return (MockSpikeGenerator)getBean(spikeGeneratorPlugin);
	}
	
	@Bean
	public RandomSpikeGenerator randomSpikeGenerator () {
		RandomSpikeGenerator gen = new RandomSpikeGenerator ();
		gen.setMax(100);
		gen.setMin(50);
		return gen;
	}
	
	@Bean
	public ManualInputSpikeGenerator manualInputSpikeGenerator() {
		return new ManualInputSpikeGenerator();
	}
	
	@Bean
	public MatlabSpikeGenerator matlabSpikeGenerator () {
		MatlabSpikeGenerator gen = new MatlabSpikeGenerator ();
		gen.setMatlabFunctionName(matlabSpikeFunctionName);
		return gen;
	}
}
