package org.xper.rfplot.gui.scroller;

import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.rfplot.gui.CyclicIterator;

import java.io.File;
import java.io.FileFilter;
import java.util.Arrays;
import java.util.Objects;

public class ImgPathScroller extends RFPlotScroller {

    private String libraryPath_generator;
    private String libraryPath_experiment;
    CyclicIterator<File> pngs;

    public ImgPathScroller(String libraryPath_generator, String libraryPath_experiment) {
        this.setLibraryPath_generator(libraryPath_generator);
        this.setLibraryPath_experiment(libraryPath_experiment);

        setPngsFromLibrary(libraryPath_generator);
    }
    public void init(){
        System.err.println(libraryPath_generator);
        try {
            setPngsFromLibrary(libraryPath_experiment);
        } catch (Exception e){
            setPngsFromLibrary(libraryPath_generator);
        }
    }

    public ImgPathScroller() {
    }

    public String getLibraryPath_generator() {
        return libraryPath_generator;
    }

    public String getLibraryPath_experiment() {
        return libraryPath_experiment;
    }

    private void setPngsFromLibrary(String libraryPath) {
        File path = new File(libraryPath);
        pngs = new CyclicIterator<>(Arrays.asList(Objects.requireNonNull(path.listFiles(new FileFilter() {
            @Override
            public boolean accept(File pathname) {
                String lowerCaseName = pathname.getName().toLowerCase();
                return lowerCaseName.endsWith(".png")
                        || lowerCaseName.endsWith(".jpg")
                        || lowerCaseName.endsWith(".jpeg")
                        || lowerCaseName.endsWith(".bmp")
                        || lowerCaseName.endsWith(".gif")
                        || lowerCaseName.endsWith(".webp");
            }
        }))));
    }

    public String getFirstPath(){
        return convertGeneratorToExperiment(pngs.first().getAbsolutePath());
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        String nextPath = pngs.next().getAbsolutePath();
        nextPath = convertGeneratorToExperiment(nextPath);
        PngSpec pngSpec = PngSpec.fromXml(scrollerParams.getRfPlotDrawable().getSpec());
        pngSpec.setPath(nextPath);
        scrollerParams.getRfPlotDrawable().setSpec(pngSpec.toXml());
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        String nextPath = pngs.previous().getAbsolutePath();
        nextPath = convertGeneratorToExperiment(nextPath);
        PngSpec pngSpec = PngSpec.fromXml(scrollerParams.getRfPlotDrawable().getSpec());
        pngSpec.setPath(nextPath);
        scrollerParams.getRfPlotDrawable().setSpec(pngSpec.toXml());
        return scrollerParams;
    }

    private String convertGeneratorToExperiment(String imagePath){
        String newPath = imagePath.replace(getLibraryPath_generator(), getLibraryPath_experiment());
        return newPath;
    }

    public void setLibraryPath_generator(String libraryPath_generator) {
        this.libraryPath_generator = libraryPath_generator;
    }

    public void setLibraryPath_experiment(String libraryPath_experiment) {
        this.libraryPath_experiment = libraryPath_experiment;
    }
}