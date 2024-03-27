package org.xper.allen.monitorlinearization;

import java.util.Objects;

public class Cyan {
    private int green;
    private int blue;

    public Cyan(int green, int blue) {
        this.green = green;
        this.blue = blue;
    }

    public int getGreen() {
        return green;
    }

    public int getBlue() {
        return blue;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Cyan)) return false;
        Cyan cyan = (Cyan) o;
        return green == cyan.green && blue == cyan.blue;
    }

    @Override
    public int hashCode() {
        return Objects.hash(green, blue);
    }

    @Override
    public String toString() {
        return String.format("Cyan(green=%d, blue=%d)", green, blue);
    }

    public void setGreen(int green) {
        this.green = green;
    }

    public void setBlue(int blue) {
        this.blue = blue;
    }
}