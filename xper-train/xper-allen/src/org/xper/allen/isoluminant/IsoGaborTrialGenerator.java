package org.xper.allen.isoluminant;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractTrialGenerator;
import org.xper.rfplot.RFInfo;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;
import org.xper.util.FileUtil;
import org.w3c.dom.Document;
import org.xml.sax.InputSource;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.StringReader;
import java.util.*;

public class IsoGaborTrialGenerator extends AbstractTrialGenerator<Stim> {
    private final int numRepeats = 5;
    private GaborSpec gaborSpec;
    public static final List<Double> frequencies = Arrays.asList(0.5, 1.0, 2.0, 4.0);
    public static final List<Double> mixedPhases = Arrays.asList(0.0, 0.25, 0.5, 0.75);

    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"),
                IsoGaborConfig.class
        );
        IsoGaborTrialGenerator gen = context.getBean(IsoGaborTrialGenerator.class);
        gen.generate();
    }


    @Override
    protected void writeTrials() {
        List<Long> allStimIds = new ArrayList<>();

        for (Stim stim : getStims()) {
            stim.writeStim();
            Long stimId = stim.getStimId();
            for (int i = 0; i < numRepeats; i++) {
                allStimIds.add(stimId);
            }
        }

        Collections.shuffle(allStimIds);

        long lastTaskId = -1L;
        for (Long stimId : allStimIds) {
            long taskId = getGlobalTimeUtil().currentTimeMicros();
            while (taskId == lastTaskId) {
                taskId = getGlobalTimeUtil().currentTimeMicros();
            }
            lastTaskId = taskId;

            getDbUtil().writeTaskToDo(taskId, stimId, -1, genId);
        }
    }

    @Override
    protected void addTrials() {
        // Get database values
        JdbcTemplate jdbcTemplate = new JdbcTemplate(dbUtil.getDataSource());

        // Get RF Info
        RFInfo rfInfo = getRFInfo(jdbcTemplate);

        // Get StimSpec
        GaborSpec stimSpec = getStimSpec(jdbcTemplate);

        // Set up GaborSpec with database values
        gaborSpec = new GaborSpec();
        gaborSpec.setXCenter(rfInfo.getCenter().getX());
        gaborSpec.setYCenter(rfInfo.getCenter().getY());
        gaborSpec.setSize(rfInfo.getRadius()*1.5);
        gaborSpec.setOrientation(stimSpec.getOrientation());
        gaborSpec.setPhase(0);
        gaborSpec.setAnimation(false);

        // Pure Gabors
        for (Double frequency : frequencies) {
            gaborSpec.setFrequency(frequency);
            addIsochromaticTrials();
            addIsoluminantTrials();
        }

        // Mixed Gabors - frequencies
        for (Double frequencyChromatic : frequencies) {
            GaborSpec chromaticSpec = new GaborSpec(gaborSpec);
            chromaticSpec.setFrequency(frequencyChromatic);
            for (Double frequencyLuminance : frequencies) {
                GaborSpec luminanceSpec = new GaborSpec(gaborSpec);
                luminanceSpec.setFrequency(frequencyLuminance);

                IsoGaborSpec rgMixedIsoSpec = new IsoGaborSpec(chromaticSpec, "RedGreen");
                MixedGaborStim rgMixedIsoStim = new MixedGaborStim(this, rgMixedIsoSpec, luminanceSpec);
                getStims().add(rgMixedIsoStim);

                IsoGaborSpec cyMixedIsoSpec = new IsoGaborSpec(chromaticSpec, "CyanYellow");
                MixedGaborStim cyMixedIsoStim = new MixedGaborStim(this, cyMixedIsoSpec, luminanceSpec);
                getStims().add(cyMixedIsoStim);
            }
        }

        // Mixed Gabors - Phases
        for (double frequency : frequencies) {
            GaborSpec chromaticSpec = new GaborSpec(gaborSpec);
            chromaticSpec.setFrequency(frequency);
            for (double phase : mixedPhases) {
                double phaseLuminance = phase * frequency;

                GaborSpec luminanceSpec = new GaborSpec(gaborSpec);
                luminanceSpec.setFrequency(frequency);
                luminanceSpec.setPhase(phaseLuminance);

                IsoGaborSpec rgMixedIsoSpec = new IsoGaborSpec(gaborSpec, "RedGreen");
                MixedGaborStim rgMixedIsoStim = new MixedGaborStim(this, rgMixedIsoSpec, luminanceSpec);
                getStims().add(rgMixedIsoStim);

                IsoGaborSpec cyMixedIsoSpec = new IsoGaborSpec(gaborSpec, "CyanYellow");
                MixedGaborStim cyMixedIsoStim = new MixedGaborStim(this, cyMixedIsoSpec, luminanceSpec);
                getStims().add(cyMixedIsoStim);
            }
        }
    }

    private void addIsochromaticTrials() {
        IsoGaborSpec spec = new IsoGaborSpec(gaborSpec, "Gray");
        IsoGaborStim stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "Red");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "Green");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "Cyan");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "Yellow");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);
    }

    private void addIsoluminantTrials() {
        IsoGaborSpec spec = new IsoGaborSpec(gaborSpec, "CyanYellow");
        IsoGaborStim stim = new IsoGaborStim(this, spec);
        getStims().add(stim);

        spec = new IsoGaborSpec(gaborSpec, "RedGreen");
        stim = new IsoGaborStim(this, spec);
        getStims().add(stim);
    }


    private long getLatestTimestamp(JdbcTemplate jdbcTemplate, String table) {
        return (long) jdbcTemplate.queryForObject(
                "SELECT MAX(tstamp) FROM " + table + " WHERE channel = 'SUPRA-000'",
                Long.class
        );
    }

    private RFInfo getRFInfo(JdbcTemplate jdbcTemplate) {
        long latestTimestamp = getLatestTimestamp(jdbcTemplate, "RFInfo");
        String rfInfoXml = (String) jdbcTemplate.queryForObject(
                "SELECT info FROM RFInfo WHERE tstamp = ? AND channel = 'SUPRA-000'",
                new Object[]{latestTimestamp},
                String.class
        );
        return RFInfo.fromXml(rfInfoXml);
    }

    private GaborSpec getStimSpec(JdbcTemplate jdbcTemplate) {
        long latestTimestamp = getLatestTimestamp(jdbcTemplate, "RFObjectData");
        String stimSpecXml = (String) jdbcTemplate.queryForObject(
                "SELECT data FROM RFObjectData WHERE tstamp = ? AND channel = 'SUPRA-000' AND object = 'org.xper.rfplot.drawing.gabor.Gabor'",
                new Object[]{latestTimestamp},
                String.class
        );
        return GaborSpec.fromXml(stimSpecXml);
    }




}