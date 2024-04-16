package org.xper.allen.pga;

public enum StimType {
    REGIME_ZERO("REGIME_ZERO"),
    REGIME_ONE("REGIME_ONE"),
    REGIME_TWO("REGIME_TWO"),
    REGIME_THREE("REGIME_THREE"),
    REGIME_ZERO_2D("REGIME_ZERO_2D"),
    REGIME_ONE_2D("REGIME_ONE_2D"),
    REGIME_TWO_2D("REGIME_TWO_2D"),
    REGIME_THREE_2D("REGIME_THREE_2D"),
    CATCH("CATCH");


    private final String value;

    StimType(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static StimType fromString(String value) {
        for (StimType stimType : StimType.values()) {
            if (stimType.value.equalsIgnoreCase(value)) {
                return stimType;
            }
        }
        throw new IllegalArgumentException("No enum constant found for value: " + value);
    }
}