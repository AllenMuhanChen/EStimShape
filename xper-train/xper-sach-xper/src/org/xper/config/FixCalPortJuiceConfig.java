package org.xper.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.classic.JuiceController;
import org.xper.classic.TrialEventListener;
import org.xper.config.AcqConfig;
import org.xper.config.ClassicConfig;
import org.xper.config.FixCalConfig;
import org.xper.exception.ExperimentSetupException;
import org.xper.juice.DigitalPortJuice;
import org.xper.juice.mock.NullDynamicJuice;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(FixCalConfig.class)
public class FixCalPortJuiceConfig {
	@Autowired AcqConfig acqConfig;
	@Autowired ClassicConfig classicConfig;
	
	@Bean
	public TrialEventListener juiceController() {
		JuiceController controller = new JuiceController();
		if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			controller.setJuice(new NullDynamicJuice());
		} else {
			controller.setJuice(xperDynamicJuice());
			System.out.println("In juicecontroller");
		}
		return controller;
	}
	
	@Bean 
	public DigitalPortJuice xperDynamicJuice() {
		DigitalPortJuice juice = new DigitalPortJuice();
		juice.setTriggerDelay(acqConfig.digitalPortJuiceTriggerDelay);
		juice.setReward(classicConfig.xperJuiceRewardLength());
		if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NI)) {
			juice.setDevice(classicConfig.niDigitalPortJuiceDevice());
		} else if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_COMEDI)) {
			System.out.println("In comedi xperdynamic");
			juice.setDevice(classicConfig.comediDigitalPortJuiceDevice());
		} else {
			throw new ExperimentSetupException("Acq driver " + acqConfig.acqDriverName + " not supported.");
		}
		return juice;
	}
}

