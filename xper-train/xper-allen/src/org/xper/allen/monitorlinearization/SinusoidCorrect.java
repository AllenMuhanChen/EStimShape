package org.xper.allen.monitorlinearization;

import org.xper.Dependency;
import org.xper.drawing.RGBColor;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class SinusoidCorrect {
    @Dependency
    DataSource dataSource;


    public double getGainFromRedGreen(double angle){
        // Map the angle to the range [0, 180] based on the cosine function
        double mappedAngle = Math.abs(180 - Math.abs(angle % 360 - 180));

        String query = "SELECT angle, gain FROM SinGain WHERE colors = 'RedGreen' ORDER BY ABS(angle - ?) LIMIT 2";
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement(query)) {
            statement.setDouble(1, mappedAngle);
            ResultSet resultSet = statement.executeQuery();

            double angle1 = 0, gain1 = 0, angle2 = 0, gain2 = 0;
            if (resultSet.next()) {
                angle1 = resultSet.getDouble("angle");
                gain1 = resultSet.getDouble("gain");
            }
            if (resultSet.next()) {
                angle2 = resultSet.getDouble("angle");
                gain2 = resultSet.getDouble("gain");
            }

            if (angle1 == angle2) {
                return gain1;
            } else {
                // return the closest one
                double diff1 = Math.abs(angle1 - mappedAngle);
                double diff2 = Math.abs(angle2 - mappedAngle);
                if (diff1 < diff2) {
                    return gain1;
                } else {
                    return gain2;
                }
            }
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    public void setDataSource(DataSource dataSource) {
        this.dataSource = dataSource;
    }
}