package org.xper.allen.pga.alexnet;

public enum StimType {
    SEEDING("SEEDING"),
    RF_LOCATE("RF_LOCATE"),
    GROWING("GROWING");


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