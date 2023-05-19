package org.xper.allen.app.nafc;

import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.util.FileUtil;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.concurrent.TimeUnit;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class PsychometricPngGeneratorMainIntegrationTest {

    private BasicFileAttributes attributes;
    private String numSets;
    private String numPerSet;
    private String size;
    private String percentChangePosition;
    private PsychometricBlockGen gen;

    @Test
    public void classic_use_case_generates_pngs(){
        FileUtil.loadTestSystemProperties("/xper.properties.psychometric");
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));

        gen = context.getBean(PsychometricBlockGen.class);

        numSets = "1";
        numPerSet = "3";
        size = "8";
        percentChangePosition = "0.5";

        String[] args = new String[]{
                numSets,
                numPerSet,
                size,
                percentChangePosition,
                "0"
        };

        long startTime = System.currentTimeMillis();
        PsychometricPngGeneratorMain.main(args);

        creates_correct_number_of_pngs(startTime);

    }

    private void creates_correct_number_of_pngs(long startTime) {
        File folder = new File(gen.getGeneratorPsychometricPngPath());
        File[] files = folder.listFiles();

        int numCreated = 0;
        for (File file: files){
            if (getFileCreationMs(file)> startTime){
                numCreated++;
                assertTrue(file.delete());
            }
        }

        assertEquals(expectedNumFilesCreated(), numCreated);
    }

    private int expectedNumFilesCreated(){
        return Integer.parseInt(numSets) * Integer.parseInt(numPerSet);
    }

    private long getFileCreationMs(File folder) {
        Path folderPath = folder.toPath();
        try {
            attributes = Files.readAttributes(folderPath, BasicFileAttributes.class);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }

        long creationMs = attributes.creationTime().to(TimeUnit.MILLISECONDS);
        return creationMs;
    }
}