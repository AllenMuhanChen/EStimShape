package org.xper.fixtrain.drawing;

import org.junit.Before;
import org.junit.Test;

import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;

import static org.junit.Assert.*;

public class RandImageFetcherTest {

    private File imageDirectory;

    @Before
    public void setUp() throws Exception {
        String imageDirectoryPath = getResource("image-dir");
        imageDirectory = new File(imageDirectoryPath);
    }

    @Test
    public void fetches_random_image_from_directory() {
        File randFile = RandImageFetcher.fetchRandImage(imageDirectory);
        String name = randFile.getName();
        assertTrue(name.equals("test1.png") || name.equals("test2.jpeg"));
    }

    public static String getResource(String resourceFileName) {
        Path libraryResource = Paths.get("test", "test-resources", resourceFileName);
        return libraryResource.toAbsolutePath().toString();
    }
}