package org.xper.allen.config;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.config.BeanDefinition;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.ga.*;
import org.xper.allen.ga.regimescore.*;
import org.xper.allen.ga.regimescore.ParentChildBinThresholdsScoreSource.NormalizedResponseBin;
import org.xper.allen.ga.regimescore.RegimeScoreSource.RegimeTransition;
import org.xper.allen.ga3d.blockgen.LinearSpline;
import org.xper.allen.ga3d.blockgen.NaturalSpline;
import org.xper.allen.ga3d.blockgen.Sigmoid;
import org.xper.allen.newga.blockgen.SlotGABlockGenerator;
import org.xper.allen.pga.FromDbGABlockGenerator;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.config.BaseConfig;
import org.xper.drawing.Coordinates2D;
import org.xper.experiment.DatabaseTaskDataSource;

import javax.vecmath.Point2d;
import java.util.*;

import static org.xper.allen.newga.blockgen.SlotGABlockGenerator.STIM_TYPE_FOR_REGIME;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({MStickPngConfig.class})
public class PGAConfig {
    @Autowired MStickPngConfig mStickPngConfig;
    @Autowired BaseConfig baseConfig;

    @ExternalValue("number_of_repetitions_per_stimulus")
    public Integer numberOfRepetitionsPerStimulus;

    @Bean
    public FromDbGABlockGenerator generator(){
        FromDbGABlockGenerator generator = new FromDbGABlockGenerator();
        generator.setGeneratorPngPath(mStickPngConfig.generatorPngPath);
        generator.setExperimentPngPath(mStickPngConfig.experimentPngPath);
        generator.setGeneratorSpecPath(mStickPngConfig.generatorSpecPath);
        generator.setMaxImageDimensionDegrees(mStickPngConfig.xperMaxImageDimensionDegrees());
        generator.setPngMaker(mStickPngConfig.pngMaker());
        generator.setGlobalTimeUtil(baseConfig.localTimeUtil());
        generator.setDbUtil(dbUtil());
        generator.setNumTrialsPerStimulus(numberOfRepetitionsPerStimulus);
        generator.setInitialSize(8);
        generator.setIntialCoords(new Coordinates2D(0,0));
        generator.setGaName("New3D");
        generator.setRfSource(rfSource());
        return generator;
    }

    @Bean
    public ReceptiveFieldSource rfSource(){
        ReceptiveFieldSource rfSource = new ReceptiveFieldSource();
        rfSource.setDataSource(baseConfig.dataSource());
        return rfSource;
    }

    @Bean
    public MultiGATaskDataSource taskDataSource(){
        return databaseTaskDataSource();
    }

    @Bean
    public MultiGATaskDataSource databaseTaskDataSource() {
        MultiGATaskDataSource source = new MultiGATaskDataSource();
        source.setDbUtil(dbUtil());
        source.setQueryInterval(1000);
        source.setUngetPolicy(DatabaseTaskDataSource.UngetPolicy.TAIL);
        source.setGaNames(Collections.singletonList(generator().getGaName()));
        return source;
    }

    @Bean
    public MultiGaDbUtil dbUtil(){
        MultiGaDbUtil dbUtil = new MultiGaDbUtil();
        dbUtil.setDataSource(baseConfig.dataSource());
        return dbUtil;
    }
}