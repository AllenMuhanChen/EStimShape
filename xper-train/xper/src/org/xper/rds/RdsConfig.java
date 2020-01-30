package org.xper.rds;

import java.util.ArrayList;
import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.classic.SlideTrialExperiment;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.console.ExperimentConsole;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.RGBColor;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.object.FixationPoint;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveStereoRenderer;
import org.xper.experiment.Experiment;
import org.xper.experiment.mock.NullTaskDataSource;
import org.xper.experiment.mock.NullTaskDoneCache;
import org.xper.eye.strategy.EyeInStrategy;
import org.xper.eye.strategy.StereoEyeInStrategy;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class RdsConfig {
	@Autowired ClassicConfig classicConfig;
	@Autowired AcqConfig acqConfig;
	@Autowired BaseConfig baseConfig;
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperDoEmptyTask() {
		return true;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperRdsFixationPointSize() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_rds_fixation_point_size", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public RGBColor xperRdsFixationPointColor() {
		RGBColor color = new RGBColor();
		color.setRed(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_rds_fixation_point_color", 0)));
		color.setGreen(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_rds_fixation_point_color", 1)));
		color.setBlue(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_rds_fixation_point_color", 2)));
		return color;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public RGBColor xperRdsBackgroundColor() {
		RGBColor color = new RGBColor();
		color.setRed(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_rds_background_color", 0)));
		color.setGreen(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_rds_background_color", 1)));
		color.setBlue(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_rds_background_color", 2)));
		return color;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperRdsBackgroundSize() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_rds_background_size", 0));
	}
	
	@Bean
	public RdsControlClient rdsControlClient() {
		RdsControlClient c = new RdsControlClient(classicConfig.consoleHost);
		return c;
	}
	
	@Bean
	public RdsConsolePlugin rdsPlugin () {
		RdsConsolePlugin p = new RdsConsolePlugin();
		p.setMinFixationSize(xperRdsFixationPointSize().floatValue());
		p.setRdsControlClient(rdsControlClient());
		p.setBackgroundColor(xperRdsBackgroundColor());
		p.setFixationColor(xperRdsFixationPointColor());
		p.setConsoleFixationPoint(consoleFixationPoint());
		return p;
	}
	
	@Bean
	public List<IConsolePlugin> consolePlugins () {
		List<IConsolePlugin> plugins = new ArrayList<IConsolePlugin>();
		plugins.add(rdsPlugin());
		return plugins;
	}
	
	@Bean
	public AbstractRenderer experimentGLRenderer () {
		PerspectiveStereoRenderer renderer = new PerspectiveStereoRenderer();
		renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
		renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
		renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
		renderer.setWidth(classicConfig.xperMonkeyScreenWidth());
		renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
		renderer.setInverted(classicConfig.xperMonkeyScreenInverted());
		return renderer;
	}
	
	@Bean
	public ExperimentConsole experimentConsole () {
		ExperimentConsole console = new ExperimentConsole();
		
		console.setPaused(classicConfig.xperExperimentInitialPause());
		console.setConsoleRenderer(classicConfig.consoleRenderer());
		console.setMonkeyScreenDimension(classicConfig.monkeyWindow().getScreenDimension());
		console.setModel(classicConfig.experimentConsoleModel());
		
		console.setConsolePlugins(consolePlugins());
		
		ExperimentMessageReceiver receiver = classicConfig.messageReceiver();
		// register itself to avoid circular reference
		receiver.addMessageReceiverEventListener(console);
		
		return console;
	}
	
	@Bean
	public FixationPoint consoleFixationPoint() {
		FixationPoint fixation = new FixationPoint();
		fixation.setColor(xperRdsFixationPointColor());
		fixation.setSize(xperRdsFixationPointSize());
		fixation.setFixationPosition(classicConfig.xperFixationPosition());
		fixation.setSolid(false);
		return fixation;
	}
	
	@Bean
	public EyeInStrategy eyeInStrategy () {
		StereoEyeInStrategy strategy = new StereoEyeInStrategy();
		strategy.setLeftDeviceId(classicConfig.xperLeftIscanId());
		strategy.setRightDeviceId(classicConfig.xperRightIscanId());
		return strategy;
	}
	
	@Bean
	public RdsFixationPoint rdsFixationPoint() {
		RdsFixationPoint f = new RdsFixationPoint ();
		f.setBackgroundColor(xperRdsBackgroundColor());
		f.setFixationColor(xperRdsFixationPointColor());
		f.setRdsBackground(rdsBackground());
		f.setRdsFixation(rdsFixation());
		return f;
	}
	
	@Bean
	public RdsSquare rdsFixation () {
		RdsSquare s = new RdsSquare();
		s.setSize(xperRdsFixationPointSize().floatValue());
		s.init();
		return s;
	}
	
	@Bean
	public RdsSquare rdsBackground () {
		RdsSquare s = new RdsSquare();
		s.setSize(xperRdsBackgroundSize().floatValue());
		s.init();
		return s;
	}
	
	@Bean
	public RdsTaskScene taskScene() {
		RdsTaskScene scene = new RdsTaskScene();
		scene.setFixation(rdsFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setRenderer(experimentGLRenderer());
		return scene;
	}
	
	@Bean
	public RdsControlServer rdsControlServer() {
		RdsControlServer s = new RdsControlServer();
		s.setHost(classicConfig.experimentHost);
		s.setRdsFixationPoint(rdsFixationPoint());
		s.setEyeMonitor(classicConfig.eyeMonitor());
		return s;
	}
	
	@Bean
	public Experiment experiment () {
		SlideTrialExperiment xper = new SlideTrialExperiment();
		xper.setStateObject(classicConfig.experimentState());
		
		RdsControlServer rdsServer = rdsControlServer();
		rdsServer.start();
		return xper;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperRightIscanEyeZeroUpdateEnabled () {
		return false;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperLeftIscanEyeZeroUpdateEnabled () {
		return false;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperFixationOnWithStimuli() {
		return true;
	}
	
	@Bean
	public NullTaskDoneCache taskDoneCache() {
		return new NullTaskDoneCache();
	}
	
	@Bean
	public NullTaskDataSource taskDataSource() {
		return new NullTaskDataSource();
	}
}
