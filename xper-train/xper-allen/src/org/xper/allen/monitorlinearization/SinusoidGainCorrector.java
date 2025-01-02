package org.xper.allen.monitorlinearization;

import org.xper.Dependency;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
public class SinusoidGainCorrector {
    @Dependency
    private GainLookupTable gainLookup;

    public double getGain(double angle, String colors) {
        return gainLookup.getGain(angle, colors);
    }

    public void setGainLookup(GainLookupTable gainLookup) {
        this.gainLookup = gainLookup;
    }
}