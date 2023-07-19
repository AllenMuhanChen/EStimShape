package org.xper.intan;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

import static org.junit.Assert.*;

public class TaskIdFileNamingStrategyTest {

    private TaskIdFileNamingStrategy taskIdFileNamingStrategy;
    private String expectedPath;

    @Before
    public void setUp() throws Exception {
        taskIdFileNamingStrategy = new TaskIdFileNamingStrategy();
        IntanRHD intanRHD = new IntanRHD();
        intanRHD.setDefaultSavePath("/tmp");
        taskIdFileNamingStrategy.setIntan(intanRHD);

        LocalDate date = LocalDate.now();
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd");
        expectedPath = "/tmp/" + date.format(formatter);
        delete_test_directory();

    }

    private void delete_test_directory() {
        // delete the directory if it exists
        Path path = Paths.get(expectedPath);
        if (path.toFile().exists()) {
            System.out.println("Deleting directory: " + expectedPath);
            path.toFile().delete();
        }
    }

    @Test
    public void nameSavePath() {
        String savePath = taskIdFileNamingStrategy.nameSavePath(1L);
        assertEquals(expectedPath, savePath);
        assertPathExists(savePath);
    }

    private void assertPathExists(String savePath) {
        Path path = Paths.get(savePath);
        assertTrue(path.toFile().exists());
    }

    @After
    public void tearDown() throws Exception {
        delete_test_directory();
    }
}