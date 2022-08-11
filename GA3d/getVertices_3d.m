function message = getVertices_3d(gaInfo,conn)
    getPaths;
    folderName = [gaInfo.currentExptPrefix '_r-' num2str(gaInfo.gaRun)];
    fullFolderPath = [folderName '_g-' num2str(gaInfo.genNum)];
    vertFolderPath = [stimPath '/' fullFolderPath '/vert'];
    if ~exist(vertFolderPath,'dir'); mkdir(vertFolderPath); end
    
%     screenDist = str2double(fetch(conn,'select val from systemvar where name=''xper_monkey_screen_distance'''));
%     doProjectionCorrection = false;
    
    for l=1:2
        message = ['Fetching vertex data from DB and saving in MAT for lineage ' num2str(l) '.'];
        logger(mfilename,folderName,message,conn); disp(message);
        for s=1:gaInfo.stimAndTrial.nStim
            descId = [fullFolderPath '_l-' num2str(l) '_s-' num2str(s)];
            vert = getVertices_perStim(descId,conn);
            eval(['vert = [' char(vert{1})' '];']);
            
            uniquePoints = unique(vert,'rows');
            px = uniquePoints(:,1); py = uniquePoints(:,2); pz = uniquePoints(:,3);
            % scatter3(px,py,pz,'k.'); axis image; axis off; view(0,90)

%             if doProjectionCorrection
%                 d = 1+(vert(:,3)/screenDist);
%                 px = px./d;
%                 py = py./d;
%             end

            boundaryIdx = boundary(px,py,1);
            boundarpyts = [px(boundaryIdx) py(boundaryIdx)];
            boundarpyts = interparc(100,boundarpyts(:,1),boundarpyts(:,2),'spline');
            dPts = getDensePoints(boundarpyts,[],100); %#ok<NASGU>
            
            occluderZpos = max(pz); %#ok<NASGU>
            
            save([vertFolderPath '/' descId '_vert.mat'],'vert','dPts','occluderZpos');
            
            if ~mod(s,10)
                message = [num2str(s) ' stimuli fetched and saved.'];
                logger(mfilename,folderName,message,conn); disp(message);
            end
        end
    end
    message = ['All stimuli dense points fetched from DB and saved for ' fullFolderPath '.'];
    logger(mfilename,folderName,message,conn);
end

function vert = getVertices_perStim(descId,conn)
    setdbprefs('DataReturnFormat','cellarray');
    vert = fetch(conn,['select vertspec from StimObjData_vert where descId = ''' descId '''' ]);
end

function vert = getFaces_perStim(descId,conn)
    setdbprefs('DataReturnFormat','cellarray');
    vert = fetch(conn,['select faceSpec from StimObjData_vert where descId = ''' descId '''' ]);
end

function vert = getNormals_perStim(descId,conn)
    setdbprefs('DataReturnFormat','cellarray');
    vert = fetch(conn,['select normSpec from StimObjData_vert where descId = ''' descId '''' ]);
end