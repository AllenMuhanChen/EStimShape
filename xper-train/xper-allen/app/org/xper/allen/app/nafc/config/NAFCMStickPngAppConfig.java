package org.xper.allen.app.nafc.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.config.MStickPngConfig;
import org.xper.allen.config.NAFCConfig;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParameterGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParameterGenerator;
import org.xper.allen.nafc.NAFCPngScene;
import org.xper.allen.nafc.blockgen.MStickPngBlockGen;
import org.xper.config.AcqConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.object.BlankScreen;


@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({NAFCConfig.class, MStickPngConfig.class})
public class NAFCMStickPngAppConfig{
	@Autowired public NAFCConfig config;
	@Autowired public MStickPngConfig mStickPngConfig;
	@Autowired public ClassicConfig classicConfig;
	@Autowired public AcqConfig acqConfig;

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
		scene.setBackgroundColor(classicConfig.xperBackgroundColor());
		return scene;
	}

	@Bean
	public MStickPngBlockGen generator() {
		MStickPngBlockGen gen = new MStickPngBlockGen();
		gen.setDbUtil(config.allenDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setXmlUtil(config.allenXMLUtil());
		gen.setGeneratorPngPath(mStickPngConfig.generatorPngPath);
		gen.setExperimentPngPath(mStickPngConfig.experimentPngPath);
		gen.setGeneratorSpecPath(mStickPngConfig.generatorSpecPath);
		gen.setPngMaker(mStickPngConfig.pngMaker());
		gen.setMaxImageDimensionDegrees(mStickPngConfig.xperMaxImageDimensionDegrees());
		gen.setMmpGenerator(mmpGenerator());
		gen.setQmpGenerator(qmpGenerator());
		return gen;
	}


	@Bean
	public MetricMorphParameterGenerator mmpGenerator() {
		return new MetricMorphParameterGenerator();
	}

	@Bean
	public QualitativeMorphParameterGenerator qmpGenerator() {
		return new QualitativeMorphParameterGenerator(mStickPngConfig.xperMaxImageDimensionDegrees());
	}

}