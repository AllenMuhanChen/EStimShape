function nTask = modifyTrialStructure(gaInfo,folderName,conn)
    if strcmp(gaInfo.exptType,'GA')
        slideLength = 1000; isi = 100; iti = 1500; auxOn = 500; auxOff = 900;
    elseif strcmp(gaInfo.exptType,'GA3D')
        if gaInfo.posthocId == 4 % || gaInfo.posthocId == 6
            slideLength = 1750; isi = 250; iti = 1500; auxOn = 500; auxOff = 900;
        else
            slideLength = 750; isi = 250; iti = 1500; auxOn = 500; auxOff = 900;
        end
    elseif strcmp(gaInfo.exptType,'bubbles')
        slideLength = 500; isi = 500; iti = 1500;
    end
    modifyTrialStructureDatabase(conn,slideLength,isi,gaInfo.stimAndTrial.nStimPerTrial,iti,auxOn,auxOff)
    
    nStim = gaInfo.stimAndTrial.nStim * 2 * gaInfo.stimAndTrial.nReps;
    nBlank = ceil((gaInfo.stimAndTrial.nStim * 2)/gaInfo.stimAndTrial.nStimPerChunk) * gaInfo.stimAndTrial.nReps;
    if strcmp(gaInfo.exptType,'GA')
        nFinger = gaInfo.enableFingerprinting * (gaInfo.stimAndTrial.nStim * 2)/gaInfo.stimAndTrial.nStimPerChunk * gaInfo.stimAndTrial.nStimFingerprinting * gaInfo.stimAndTrial.nRepsFingerprintingPerChunk;
    else
        nFinger = 0;
    end
    
    nTask = ceil((nStim + nBlank + nFinger)/gaInfo.stimAndTrial.nStimPerTrial);
    
    logger(mfilename,folderName,['Trial structure modified: slideLength = ' num2str(slideLength) '; isi = ' num2str(isi) '; iti = ' num2str(iti) '; slidesPerTrial = ' num2str(gaInfo.stimAndTrial.nStimPerTrial) '.'],conn);
end

function modifyTrialStructureDatabase(conn,slideLength,isi,slidesPerTrial,iti,auxOn,auxOff)
%     setdbprefs('FetchInBatches','no');
    data = {num2str(slideLength);num2str(isi);num2str(slidesPerTrial);num2str(iti);num2str(auxOn);num2str(auxOff)};
    where = {'where name = ''xper_slide_length''';'where name = ''xper_inter_slide_interval''';...
        'where name = ''xper_slides_per_trial''';'where name = ''xper_inter_trial_interval''';...
        'where name = ''xper_slide_aux_on_time''';'where name = ''xper_slide_aux_off_time'''};
	updateSqlTable(data,{'val'},'SystemVar',where,conn);
end