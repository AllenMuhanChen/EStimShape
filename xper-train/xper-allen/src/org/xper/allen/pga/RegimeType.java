package org.xper.allen.pga;

public enum RegimeType {
    REGIME_ZERO("REGIME_ZERO"),
    REGIME_ONE("REGIME_ONE"),
    REGIME_TWO("REGIME_TWO"),
    REGIME_THREE("REGIME_THREE");

    private final String value;

    RegimeType(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static RegimeType fromString(String value) {
        for (RegimeType regimeType : RegimeType.values()) {
            if (regimeType.value.equalsIgnoreCase(value)) {
                return regimeType;
            }
        }
        throw new IllegalArgumentException("No enum constant found for value: " + value);
    }
}