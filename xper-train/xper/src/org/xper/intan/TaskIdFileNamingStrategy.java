package org.xper.intan;

import org.xper.Dependency;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

/**
 * @author Allen Chen
 */
public class TaskIdFileNamingStrategy extends IntanFileNamingStrategy<Long>{

    @Dependency
    String baseNetworkPath;


    @Override
    protected String nameBaseFile(Long taskId) {
        return taskId.toString();
    }

    /**
     * name the savePath to today's date in the format yyyy-MM-dd
     */
    @Override
    protected String nameSavePath(Long parameter) {
        LocalDate date = LocalDate.now();
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd");
        Path basePath = Paths.get(intanRHD.getDefaultSavePath());
        Path fullPath = basePath.resolve(date.format(formatter));

        create_remote_directory(fullPath);

        return fullPath.toAbsolutePath().toString();
    }

    private void create_remote_directory(Path fullPath) {
        Path baseNetworkPath = Paths.get(this.baseNetworkPath);
        String networkPathString = baseNetworkPath.toAbsolutePath() + File.separator + fullPath.toAbsolutePath();
        Path networkPath = Paths.get(networkPathString);
        System.out.println("networkPath: " + networkPath);
        try {
            if (!Files.exists(networkPath)) {
                Files.createDirectories(networkPath);
                System.out.println("Directory created: " + networkPath);
            }
        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }

    public String getBaseNetworkPath() {
        return baseNetworkPath;
    }

    public void setBaseNetworkPath(String baseNetworkPath) {
        this.baseNetworkPath = baseNetworkPath;
    }
}