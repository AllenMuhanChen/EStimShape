package org.xper.allen.monitorlinearization;

import java.util.Objects;

public class Orange {
    private int red;
    private int green;

    public Orange(int red, int green) {
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
        if (!(o instanceof Cyan)) return false;
        Orange orange = (Orange) o;
        return red == orange.red && green == orange.green;
    }

    @Override
    public int hashCode() {
        return Objects.hash(red, green);
    }

    @Override
    public String toString() {
        return String.format("Orange(red=%d, green=%d)", red, green);
    }

    public void setRed(int red) {
        this.red = red;
    }

    public void setGreen(int green) {
        this.green = green;
    }
}