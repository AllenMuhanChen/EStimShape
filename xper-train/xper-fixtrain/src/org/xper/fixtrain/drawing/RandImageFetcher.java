package org.xper.fixtrain.drawing;

import java.io.File;
import java.util.Arrays;
import java.util.function.Predicate;

public class RandImageFetcher {

    public static File fetchRandImage(File directory) {
        File[] files = directory.listFiles();

        //filter by images (jpeg, png, or bmp)
        File[] images = Arrays.stream(files).filter(new Predicate<File>() {
            @Override
            public boolean test(File f) {
                return f.getName().endsWith(".jpeg") ||
                        f.getName().endsWith(".png") ||
                        f.getName().endsWith(".bmp");
            }
        }).toArray(File[]::new);

        //get random image
        return images[(int)(Math.random() * images.length)];
    }
}