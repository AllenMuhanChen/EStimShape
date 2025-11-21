SELECT spi.session_id, spi.unit_name, spi.solid_preference_index, spi.p_value, ici.frequency, ici.isochromatic_preference_index
FROM SolidPreferenceIndices spi
    JOIN GoodChannels g ON spi.session_id=g.session_id AND spi.unit_name=g.channel
    JOIN ChannelFiltering c ON spi.session_id = c.session_id AND spi.unit_name = c.channel
    JOIN IsochromaticPreferenceIndices ici ON spi.session_id = ici.session_id AND spi.unit_name = ici.unit_name
WHERE spi.p_value <0.05 AND spi.unit_name NOT LIKE '%Unit%'
