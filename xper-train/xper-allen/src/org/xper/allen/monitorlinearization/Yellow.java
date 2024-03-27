package org.xper.allen.monitorlinearization;

import java.util.Objects;

public class Yellow {
    private int red;
    private int green;

    public Yellow(int red, int green) {
        this.red = red;
        this.green = green;
    }

    public int getRed() {
        return red;
    }

    public int getGreen() {
        return green;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Yellow)) return false;
        Yellow yellow = (Yellow) o;
        return red == yellow.red && green == yellow.green;
    }

    @Override
    public int hashCode() {
        return Objects.hash(red, green);
    }

    @Override
    public String toString() {
        return String.format("Yellow(red=%d, green=%d)", red, green);
    }

    public void setRed(int red) {
        this.red = red;
    }

    public void setGreen(int green) {
        this.green = green;
    }
}