package org.xper.intan;

import org.xper.Dependency;

/**
 * @author Allen Chen
 *
 * To make your own NamingStrategy, make a new class that extends this one
 * and implement rename(). The new class should declare
 * the data type that you want to pass to the strategy
 * with NewFileNamingStrategy extends IntanFileNamingStrategy<Type>
 */
public abstract class IntanFileNamingStrategy<T> {
    @Dependency
    IntanRHD intanRHD;

    public void rename(T parameter){
        String baseFilename = nameBaseFile(parameter);
        if (baseFilename != null){
            intanRHD.setBaseFilename(baseFilename);
        }
        String savePath = nameSavePath(parameter);
        if (savePath != null) {
            intanRHD.setSavePath(savePath);
        }
    }

    protected abstract String nameBaseFile(T parameter);

    protected abstract String nameSavePath(T parameter);

    public IntanRHD getIntan() {
        return intanRHD;
    }

    public void setIntan(IntanRHD intanRHD) {
        this.intanRHD = intanRHD;
    }
}