package org.xper.allen.app.nafc.config;

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
import org.xper.allen.config.NAFCConfig;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParameterGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParameterGenerator;
import org.xper.allen.eye.headfree.HeadFreeEyeMonitorController;
import org.xper.allen.eye.headfree.HeadFreeEyeZeroAdjustable;
import org.xper.allen.eye.headfree.HeadFreeEyeZeroAlgorithm;
import org.xper.allen.eye.headfree.HeadFreeIscanDevice;
import org.xper.allen.nafc.NAFCPngScene;
import org.xper.allen.nafc.blockgen.MStickPngBlockGen;
import org.xper.allen.util.DPIUtil;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.object.BlankScreen;
import org.xper.utils.RGBColor;


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

public class NAFCMStickPngAppConfig {
	@Autowired NAFCConfig config;
	@Autowired ClassicConfig classicConfig;
	@Autowired BaseConfig baseConfig;
	@Autowired AcqConfig acqConfig;

	@ExternalValue("generator.png_path")
	public String generatorPngPath;

	@ExternalValue("experiment.png_path")
	public String experimentPngPath;
	
	@ExternalValue("generator.spec_path")
	public String generatorSpecPath;



	@Bean
	public NAFCPngScene taskScene() {
		NAFCPngScene scene = new NAFCPngScene();
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
	public MStickPngBlockGen generator() {
		MStickPngBlockGen gen = new MStickPngBlockGen();
		gen.setDbUtil(config.allenDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setXmlUtil(config.allenXMLUtil());
		gen.setGeneratorPngPath(generatorPngPath);
		gen.setExperimentPngPath(experimentPngPath);
		gen.setGeneratorSpecPath(generatorSpecPath);
		gen.setPngMaker(pngMaker());
		gen.setMaxImageDimensionDegrees(xperMaxImageDimensionDegrees());
		gen.setMmpGenerator(mmpGenerator());
		gen.setQmpGenerator(qmpGenerator());
		return gen;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public AllenPNGMaker pngMaker(){
		AllenPNGMaker pngMaker = new AllenPNGMaker();
		pngMaker.setWidth(dpiUtil().calculateMinResolution());
		pngMaker.setHeight(dpiUtil().calculateMinResolution());
		pngMaker.setDpiUtil(dpiUtil());
		RGBColor backColor = new RGBColor(0,0,0);
		pngMaker.setBackColor(backColor);
		pngMaker.setGeneratorImageFolderName(generatorPngPath);
		pngMaker.setDepth(6000);
		pngMaker.setDistance(500);
		pngMaker.setPupilDistance(50);
		return pngMaker;
	}


	@Bean
	public DPIUtil dpiUtil(){
		DPIUtil dpiUtil = new DPIUtil();
		dpiUtil.setRenderer(config.experimentGLRenderer());
		dpiUtil.setDpi(xperMonkeyScreenDPI());
		dpiUtil.setMaxStimulusDimensionDegrees(xperMaxImageDimensionDegrees());
		dpiUtil.setGeneratorDPI(91.79);
		return dpiUtil;
	}

	@Bean
	public MetricMorphParameterGenerator mmpGenerator() {
		MetricMorphParameterGenerator mmpGenerator = new MetricMorphParameterGenerator(); 
		return mmpGenerator;
	}
	
	@Bean
	public QualitativeMorphParameterGenerator qmpGenerator() {
		QualitativeMorphParameterGenerator qmpGenerator = new QualitativeMorphParameterGenerator(xperMaxImageDimensionDegrees());
		return qmpGenerator;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public double[] xperBackgroundColor() {
		return new double[]{Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 0)),
				Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 1)),
				Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 2))};
	}

	/**
	 * Important to change this in an NAFC task, because we don't want the eye zero updater to use 
	 * eye data from when the animal is choosing a target. And we want to 
	 * @return
	 */
	@Bean
	public HeadFreeEyeMonitorController eyeMonitorController() {
		HeadFreeEyeMonitorController controller = new HeadFreeEyeMonitorController();
		controller.setEyeSampler(classicConfig.eyeSampler());
		controller.setEyeWindowAdjustable(classicConfig.eyeWindowAdjustables());
		controller.setEyeDeviceWithAdjustableZero(classicConfig.eyeZeroAdjustables());
		controller.setEyeDeviceWithHeadFreeAdjustableZero(eyeZeroAdjustables());
		return controller;
	}
	
	@Bean (scope = DefaultScopes.PROTOTYPE)
	public List<HeadFreeEyeZeroAdjustable> eyeZeroAdjustables () {
		List<HeadFreeEyeZeroAdjustable> adjustables = new LinkedList<HeadFreeEyeZeroAdjustable>();
		adjustables.add(leftIscan());
		adjustables.add(rightIscan());
		return adjustables;
	}
	
	@Bean
	public HeadFreeIscanDevice leftIscan() {
		HeadFreeIscanDevice iscan = new HeadFreeIscanDevice();
		iscan.setEyeDeviceMessageListener(classicConfig.eyeDeviceMessageListeners());
		iscan.setEyeZeroMessageListener(classicConfig.eyeZeroMessageListeners());
		iscan.setId(classicConfig.xperLeftIscanId());
		iscan.setChannel(classicConfig.xperLeftIscanChannelSpec());
		iscan.setEyeZero(classicConfig.xperLeftIscanEyeZero());
		iscan.setEyeZeroAlgorithm(leftIscanHeadFreeEyeZeroAlgorithm());
		iscan.setEyeZeroUpdateEnabled(classicConfig.xperLeftIscanEyeZeroUpdateEnabled());
		iscan.setMappingAlgorithm(classicConfig.leftIscanMappingAlgorithm());
		iscan.setLocalTimeUtil(baseConfig.localTimeUtil());
		return iscan;
	}
	
	@Bean
	public HeadFreeIscanDevice rightIscan() {
		HeadFreeIscanDevice iscan = new HeadFreeIscanDevice();
		iscan.setEyeDeviceMessageListener(classicConfig.eyeDeviceMessageListeners());
		iscan.setEyeZeroMessageListener(classicConfig.eyeZeroMessageListeners());
		iscan.setId(classicConfig.xperRightIscanId());
		iscan.setChannel(classicConfig.xperRightIscanChannelSpec());
		iscan.setEyeZero(classicConfig.xperRightIscanEyeZero());
		iscan.setEyeZeroAlgorithm(rightIscanHeadFreeEyeZeroAlgorithm());
		iscan.setEyeZeroUpdateEnabled(classicConfig.xperRightIscanEyeZeroUpdateEnabled());
		iscan.setMappingAlgorithm(classicConfig.rightIscanMappingAlgorithm());
		iscan.setLocalTimeUtil(baseConfig.localTimeUtil());
		return iscan;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public HeadFreeEyeZeroAlgorithm leftIscanHeadFreeEyeZeroAlgorithm() {
		HeadFreeEyeZeroAlgorithm algo = new HeadFreeEyeZeroAlgorithm(classicConfig.xperLeftIscanEyeZeroAlgorithmSpan(), xperEyeZeroAlgorithmInnerSpan());
		algo.setEyeZeroUpdateEyeWinThreshold(classicConfig.xperLeftIscanEyeZeroAlgorithmEyeWindowThreshold());
		algo.setEyeZeroUpdateMinSample(classicConfig.xperLeftIscanEyeZeroAlgorithmMinSample());
		algo.setEyeZeroUpdateEyeWinCenter(classicConfig.xperEyeWindowCenter());
		algo.setEyeZeroInnerThreshold(classicConfig.xperEyeWindowAlgorithmBaseWindowSize());
		algo.setEyeZeroInnerUpdateMinSample(xperEyeZeroAlgorithmInnerUpdateMinSample());
		return algo;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public HeadFreeEyeZeroAlgorithm rightIscanHeadFreeEyeZeroAlgorithm() {
		HeadFreeEyeZeroAlgorithm algo = new HeadFreeEyeZeroAlgorithm(classicConfig.xperRightIscanEyeZeroAlgorithmSpan(), xperEyeZeroAlgorithmInnerSpan());
		algo.setEyeZeroUpdateEyeWinThreshold(classicConfig.xperRightIscanEyeZeroAlgorithmEyeWindowThreshold());
		algo.setEyeZeroUpdateMinSample(classicConfig.xperRightIscanEyeZeroAlgorithmMinSample());
		algo.setEyeZeroUpdateEyeWinCenter(classicConfig.xperEyeWindowCenter());
		algo.setEyeZeroInnerThreshold(classicConfig.xperEyeWindowAlgorithmBaseWindowSize());
		algo.setEyeZeroInnerUpdateMinSample(xperEyeZeroAlgorithmInnerUpdateMinSample());
		return algo;
	}
	
//	@Bean(scope = DefaultScopes.PROTOTYPE)
//	public LaggingMovingAverageEyeZeroAlgorithm leftIscanMovingAverageEyeZeroAlgorithm() {
//		LaggingMovingAverageEyeZeroAlgorithm algo = new LaggingMovingAverageEyeZeroAlgorithm(classicConfig.xperLeftIscanEyeZeroAlgorithmSpan());
//		algo.setEyeZeroUpdateEyeWinThreshold(classicConfig.xperLeftIscanEyeZeroAlgorithmEyeWindowThreshold());
//		algo.setEyeZeroUpdateMinSample(classicConfig.xperLeftIscanEyeZeroAlgorithmMinSample());
//		algo.setEyeZeroUpdateEyeWinCenter(classicConfig.xperEyeWindowCenter());
//		return algo;
//	}
//
//	@Bean(scope = DefaultScopes.PROTOTYPE)
//	public LaggingMovingAverageEyeZeroAlgorithm rightIscanMovingAverageEyeZeroAlgorithm() {
//		LaggingMovingAverageEyeZeroAlgorithm algo = new LaggingMovingAverageEyeZeroAlgorithm(classicConfig.xperRightIscanEyeZeroAlgorithmSpan());
//		algo.setEyeZeroUpdateEyeWinThreshold(classicConfig.xperRightIscanEyeZeroAlgorithmEyeWindowThreshold());
//		algo.setEyeZeroUpdateMinSample(classicConfig.xperRightIscanEyeZeroAlgorithmMinSample());
//		algo.setEyeZeroUpdateEyeWinCenter(classicConfig.xperEyeWindowCenter());
//		return algo;
//	}
	
//	@Bean(scope = DefaultScopes.PROTOTYPE)
//	public String xperExperimentImageFolderName(){
//		return baseConfig.systemVariableContainer().get("xper_experiment_image_folder_name", 0);
//	}
//	
//	@Bean(scope = DefaultScopes.PROTOTYPE)
//	public String xperGeneratorImageFolderName(){
//		return baseConfig.systemVariableContainer().get("xper_generator_image_folder_name", 0);
//	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public int xperEyeZeroAlgorithmInnerUpdateMinSample() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_eye_zero_algorithm_inner_update_min_sample", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public int xperEyeZeroAlgorithmInnerSpan() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_eye_zero_algorithm_inner_span", 0));
	}
	//For DPIUtil
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public double xperMonkeyScreenDPI(){
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_monkey_screen_dpi", 0));
	}

	//For DPIUtil
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public double xperMaxImageDimensionDegrees(){
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_max_image_dimension_degrees", 0));
	}
}