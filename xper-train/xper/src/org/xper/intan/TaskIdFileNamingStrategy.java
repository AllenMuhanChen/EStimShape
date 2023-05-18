package org.xper.intan;

/**
 * @author Allen Chen
 */
public class TaskIdFileNamingStrategy extends IntanFileNamingStrategy<Long>{

    @Override
    public void rename(Long parameter) {
        intanRHD.setBaseFilename(parameter.toString());
    }
}