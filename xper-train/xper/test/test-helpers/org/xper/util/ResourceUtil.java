package org.xper.util;

import java.nio.file.Path;
import java.nio.file.Paths;

public class ResourceUtil {
    public static String getResource(String resourceFileName) {
        Path libraryResource = Paths.get("test", "test-resources", resourceFileName);
        String resourcePath = libraryResource.toAbsolutePath().toString();
        return resourcePath;
    }
}
