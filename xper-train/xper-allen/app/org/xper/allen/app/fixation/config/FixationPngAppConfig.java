package org.xper.allen.app.fixation.config;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.ExternalValue;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.acq.mock.SocketSamplingDeviceServer;
import org.xper.allen.app.fixation.FixationPngBlockGen;
import org.xper.allen.app.fixation.PngScene;
import org.xper.allen.config.HeadFreeConfig;
import org.xper.allen.config.RewardButtonConfig;
import org.xper.allen.eye.headfree.HeadFreeEyeMonitorController;
import org.xper.allen.eye.headfree.HeadFreeEyeZeroAdjustable;
import org.xper.allen.eye.headfree.HeadFreeEyeZeroAlgorithm;
import org.xper.allen.eye.headfree.HeadFreeIscanDevice;
import org.xper.allen.fixcal.RewardButtonExperimentConsole;
import org.xper.allen.fixcal.RewardButtonExperimentConsoleModel;
import org.xper.allen.nafc.experiment.RewardButtonExperimentRunner;
import org.xper.allen.nafc.experiment.RewardButtonExperimentRunnerClient;
import org.xper.allen.nafc.eye.FreeHeadNAFCEyeMonitorController;
import org.xper.allen.nafc.eye.LaggingMovingAverageEyeZeroAlgorithm;
import org.xper.allen.util.AllenDbUtil;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.drawing.renderer.PerspectiveStereoRenderer;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.eye.zero.MovingAverageEyeZeroAlgorithm;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import({ClassicConfig.class, RewardButtonConfig.class})
public class FixationPngAppConfig {
	@Autowired ClassicConfig classicConfig;
	@Autowired RewardButtonConfig rewardButtonConfig;
	@Autowired HeadFreeConfig headFreeConfig;
	@Autowired BaseConfig baseConfig;
	@Autowired AcqConfig acqConfig;
	
	@ExternalValue("generator.png_path")
	public String generatorPngPath;

	@ExternalValue("experiment.png_path")
	public String experimentPngPath;
	
	@Bean
	public PngScene taskScene() {
		PngScene scene = new PngScene();
		scene.setRenderer(experimentGLRenderer());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setScreenHeight(classicConfig.xperMonkeyScreenHeight());
		scene.setScreenWidth(classicConfig.xperMonkeyScreenWidth());
		scene.setDistance(classicConfig.xperMonkeyScreenDistance());
		scene.setBackgroundColor(xperBackgroundColor());
		return scene;
	}
	
	/**
	 * Use PerspectiveStereoRenderer for mono and stereo, only changing the xper screen width accordingly. 
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
	public FixationPngBlockGen generator() {
		FixationPngBlockGen gen = new FixationPngBlockGen();
		gen.setDbUtil(allenDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setGeneratorPngPath(generatorPngPath);
		gen.setExperimentPngPath(experimentPngPath);
		return gen;
	}

	
	@Bean
	public AllenDbUtil allenDbUtil() {
		AllenDbUtil dbUtil = new AllenDbUtil();
		dbUtil.setDataSource(baseConfig.dataSource());
		return dbUtil;
	}
	
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public double[] xperBackgroundColor() {
		return new double[]{Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 0)),
				Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 1)),
				Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 2))};
	}

}
