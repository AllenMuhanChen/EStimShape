package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.allen.eye.headfree.HeadFreeEyeMonitorController;
import org.xper.allen.eye.headfree.HeadFreeEyeZeroAdjustable;
import org.xper.allen.eye.headfree.HeadFreeEyeZeroAlgorithm;
import org.xper.allen.eye.headfree.HeadFreeIscanDevice;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;

import java.util.LinkedList;
import java.util.List;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
public class HeadFreeConfig {
    @Autowired
    ClassicConfig classicConfig;
    @Autowired
    BaseConfig baseConfig;


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

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public int xperEyeZeroAlgorithmInnerUpdateMinSample() {
        return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_eye_zero_algorithm_inner_update_min_sample", 0));
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public int xperEyeZeroAlgorithmInnerSpan() {
        return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_eye_zero_algorithm_inner_span", 0));
    }
}
