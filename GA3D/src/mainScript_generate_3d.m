function mainScript_generate_3d
    getPaths;
    secondaryPath
    gaInfo = getGaInfo(rootPath);
    screen = getScreenStruct;

    disp(['Current GA run: ' num2str(gaInfo.gaRun)]);
    gaInfo.currentExptPrefix = datestr(now,'yymmdd');
    folderName = [gaInfo.currentExptPrefix '_r-' num2str(gaInfo.gaRun)];
    fullFolderPath = [folderName '_g-' num2str(gaInfo.genNum)];
    
    save([rootPath '/currentGAInfo.mat'],'gaInfo','screen','-append');

    conn = getDBconn(folderName);
    updateDescriptiveInfo(gaInfo,conn);

    copyEyeCoordinates(conn);

    randStim = getRandStim(gaInfo,screen,folderName,conn);
    xperChangeStimColor([1 1 1],randStim.bColor,conn);

    nTask = modifyTrialStructure(gaInfo,folderName,conn);

    exec(conn,'TRUNCATE TABLE TaskToDo');
    logger(mfilename,folderName,'TaskToDo table truncated.',conn);

    updateInternalState(nTask,gaInfo,conn);

    logger(mfilename,folderName,['Experiment started. Id = ' fullFolderPath '.'],conn);

    disp(runRandGen_3d(folderName,gaInfo,randStim,conn));

    close(conn); clearvars conn ans;
    save([rootPath '/currState.mat']);
    
    system('java -jar /Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectXper/3dma/xper_sach7/dist/sach/ga_sachrandgen.jar');
    mkdir(['/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectXper/3dma/xper_sach7/xper-sach/images/' fullFolderPath]);
    copyfile(['images/' fullFolderPath '/*'],['/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectXper/3dma/xper_sach7/xper-sach/images/' fullFolderPath '/.']);
    
    mainScript_proliferate_3d
end

function gaInfo = getGaInfo(rootPath)
    if exist([rootPath '/currentGAInfo.mat'],'file')
        load([rootPath '/currentGAInfo.mat']);
        gaInfo.gaRun = gaInfo.gaRun + 1; %#ok<NODEF>
    else
        gaInfo.gaRun = 1;
        save([rootPath '/currentGAInfo.mat'],'gaInfo');
    end

    gaInfo.exptType = 'GA3D';
    gaInfo.genNum = 1;

    gaInfo.stimAndTrial.nStim = 40;
    gaInfo.stimAndTrial.nReps = 5;
    gaInfo.stimAndTrial.nStimPerTrial = 4;
    gaInfo.stimAndTrial.nStimPerChunk = 500;
    
    gaInfo.posthocId = 0;
    gaInfo.doStereo = false;
end

function screen = getScreenStruct
    screen.dist = 500; % mm
    screen.height = 302; % mm
    screen.width = 408; % mm
    screen.xRes = 1600;
    screen.yRes = 1200;
    screen.perfectPixelDensity = [screen.xRes/screen.width screen.yRes/screen.height];
    screen.pixelDensity = 4; % pix/mm
    screen.eyeDist = 36;
end

function updateDescriptiveInfo(gaInfo,conn)
    insertIntoSqlTable({getPosixTimeNow,str2double(gaInfo.currentExptPrefix),gaInfo.gaRun,1,1,0,0,0},...
                       {'tstamp','currentExptPrefix','gaRun','genNum','isRealExpt','firstTrial','lastTrial','containsAnimation'},...
                       'DescriptiveInfo',conn);
end

function randStim = getRandStim(gaInfo,screen,folderName,conn)
    r = abs(input('r: '));
    th = abs(input('th (deg, from horiz): '));
    [x,y] = pol2cart(deg2rad(th),r);

    randStim.xPos = deg2mm(-x,screen);
    randStim.yPos = deg2mm(-y,screen);
    randStim.siz = input('size (deg): '); % specified in degrees
    randStim.occluderColor = [0 0 0];
    randStim.bColor = [0.3 0.3 0.3];

    randStim.fColor.options = validatedInput('Select 2d color (1-7): ',1:7);
    randStim.fColor.prob = 1;

    messageToLog = ['Real mode; nStim = ' num2str(gaInfo.stimAndTrial.nStim)...
        '; xPos = ' num2str(randStim.xPos) 'mm; yPos = ' num2str(randStim.yPos) 'mm; siz = ' num2str(randStim.siz) ...
        'mm; screen.dist = ' num2str(screen.dist) '; occluderColor = ' num2str(randStim.occluderColor) ...
        '; bColor = ' num2str(randStim.bColor) ''];
    disp(messageToLog);
    logger(mfilename,folderName,messageToLog,conn);
end

function mm = deg2mm(deg,screen)
    mm = tan(deg2rad(deg)) * screen.dist;
end

function copyEyeCoordinates(conn3d)
    databaseName = 'allen_estimshape_ga_dev_220812';
    serverAddress = '172.30.6.80';
    conn2d = database(databaseName,'xper_rw','up2nite','Vendor','MySQL','Server',serverAddress);

    eyeData = fetch(conn2d,'SELECT a.name,arr_ind,a.tstamp,val FROM SystemVar a INNER JOIN (SELECT name, MAX(tstamp) tstamp FROM SystemVar GROUP BY name) b ON a.tstamp = b.tstamp AND a.name = b.name WHERE b.name=''xper_right_iscan_mapping_algorithm_parameter'' OR b.name=''xper_left_iscan_mapping_algorithm_parameter'' OR b.name=''xper_right_iscan_eye_zero'' OR b.name=''xper_left_iscan_eye_zero''');
    eyeData = table2cell(eyeData);
    try
        insertIntoSqlTable(eyeData,{'name','arr_ind','tstamp','val'},'SystemVar',conn3d);
    catch
        disp('Eye coordinates already exist.');
    end
end
