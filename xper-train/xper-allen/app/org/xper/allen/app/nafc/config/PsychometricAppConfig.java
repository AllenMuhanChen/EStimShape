package org.xper.allen.app.nafc.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.ExternalValue;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.config.MStickPngConfig;
import org.xper.allen.config.NAFCConfig;
import org.xper.allen.drawing.composition.qualitativemorphs.PsychometricQualitativeMorphParameterGenerator;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.allen.noisy.nafc.NoisyNAFCPngScene;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.object.BlankScreen;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({NAFCMStickPngAppConfig.class, NAFCConfig.class})
public class PsychometricAppConfig{
	@Autowired NAFCMStickPngAppConfig appConfig;
	@Autowired NAFCConfig config;
	@Autowired MStickPngConfig mStickPngConfig;
	@Autowired ClassicConfig classicConfig;
	@Autowired BaseConfig baseConfig;
	@Autowired AcqConfig acqConfig;

	@ExternalValue("generator.psychometric.noisemap_path")
	public String generatorPsychometricNoiseMapPath;

	@ExternalValue("generator.psychometric.png_path")
	public String generatorPsychometricPngPath;

	@ExternalValue("experiment.psychometric.noisemap_path")
	public String experimentPsychometricNoiseMapPath;

	@ExternalValue("experiment.psychometric.png_path")
	public String experimentPsychometricPngPath;

	@ExternalValue("generator.psychometric.spec_path")
	public String generatorPsychometricSpecPath;


	@Bean
	public NoisyNAFCPngScene taskScene() {
		NoisyNAFCPngScene scene = new NoisyNAFCPngScene();
		scene.setRenderer(config.experimentGLRenderer());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setScreenHeight(classicConfig.xperMonkeyScreenHeight());
		scene.setScreenWidth(classicConfig.xperMonkeyScreenWidth());
		scene.setDistance(classicConfig.xperMonkeyScreenDistance());
		scene.setBackgroundColor(mStickPngConfig.xperBackgroundColor());
		scene.setFrameRate(mStickPngConfig.xperNoiseRate());
		return scene;
	}

	@Bean
	public PsychometricBlockGen psychometricPngGenerator() {
		PsychometricBlockGen gen = new PsychometricBlockGen();
		gen.setDbUtil(config.allenDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setGeneratorPngPath(mStickPngConfig.generatorPngPath);
		gen.setExperimentPngPath(mStickPngConfig.experimentPngPath);
		gen.setGeneratorSpecPath(mStickPngConfig.generatorSpecPath);
		gen.setGeneratorPsychometricPngPath(generatorPsychometricPngPath);
		gen.setExperimentPsychometricPngPath(experimentPsychometricPngPath);
		gen.setGeneratorPsychometricNoiseMapPath(generatorPsychometricNoiseMapPath);
		gen.setExperimentPsychometricNoiseMapPath(experimentPsychometricNoiseMapPath);
		gen.setGeneratorPsychometricSpecPath(generatorPsychometricSpecPath);
		gen.setPngMaker(mStickPngConfig.pngMaker());
		gen.setMaxImageDimensionDegrees(mStickPngConfig.xperMaxImageDimensionDegrees());
		return gen;
	}

	@Bean
	public PsychometricQualitativeMorphParameterGenerator psychometricQmpGenerator() {
		PsychometricQualitativeMorphParameterGenerator qmpGenerator = new PsychometricQualitativeMorphParameterGenerator(mStickPngConfig.xperMaxImageDimensionDegrees());
		return qmpGenerator;
	}



}