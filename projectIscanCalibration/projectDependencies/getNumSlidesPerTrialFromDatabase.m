function slidesPerTrial = getNumSlidesPerTrialFromDatabase(conn)
    setdbprefs('DataReturnFormat','numeric');
    slidesPerTrial = fetch(conn,'select val from SystemVar where name = ''xper_slides_per_trial''');
end