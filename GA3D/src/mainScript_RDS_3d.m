function mainScript_RDS_3d
    getPaths;

    load([rootPath '/currState.mat']);
    conn = getDBconn(folderName);
    
    genNum = input('Enter generation number of the sizePos posthoc: ');
    fullFolderPath = [gaInfo.currentExptPrefix '_r-' num2str(gaInfo.gaRun) '_g-' num2str(genNum)];
        
    disp(generateAndSaveRDS(fullFolderPath,screen,conn));

    close(conn); clearvars conn ans;
end

function message = generateAndSaveRDS(fullFolderPath,screen,conn)
    getPaths;
    
    nVariantConds = 10;
    nPostHocStim = 4;
    
    % get the size to run
    disp('Select best size: ');
    fprintf('\t1. x 1\n');
    fprintf('\t2. x 2\n');
    sizeId = validatedInput('Select best size: ',1:2);
    
    % change 1-2 to 1,6 <= these are the ids of the size conditions in
    % the sizepos posthoc
    if sizeId > 1; sizeId = sizeId + 4; end
    
    % ids based on sizePos posthoc
    % 1-10 are the same stim
    idsToFetch = (0:nVariantConds:39) + sizeId;
    
    load([stimPath '/' fullFolderPath '/stimParams.mat']);
    makeImages = true; % RDS
    
    % save rds params for each stimulus
    for l=1:2
        for s=1:nPostHocStim
            stim = stimuli{l,idsToFetch(s)};
            parentId = stim.id.parentId;
            
            % get vert
            descId = [fullFolderPath '_l-' num2str(l) '_s-' num2str(idsToFetch(s))];
            vert = getVertices_perStim(descId,conn);
            eval(['vert = [' char(vert{1})' '];']);
            face = getFaces_perStim(descId,conn);
            eval(['face = [' char(face{1})' '];']);
            visVert = getVisibleVertices_perStim(descId,conn);
            eval(['visVert = [' char(visVert{1})' '];']);
            
            visVertRDS = getVisibleForAngle(visVert,0);
            visVertRDK = fixVisible(visVert);
            
            % make RDS
            for doSilh=0:1
                parfor depthId=1:4
                    disp(['Saving RDS images for stimulus ' descId ' at ' num2str(depthId) ' silhouette = ' num2str(doSilh)]);
                    makeRDS(vert,face,visVertRDS,parentId,screen,depthId,doSilh,makeImages);
                end
                disp(['Saving RDK images for stimulus ' descId ' silhouette = ' num2str(doSilh)]);
                makeRDK(vert,face,visVertRDK,parentId,screen,doSilh);
            end
        end
    end
    message = ['RDS stimuli saved for posthoc stimuli from ' fullFolderPath '.'];
end

function vert = getVertices_perStim(descId,conn)
    setdbprefs('DataReturnFormat','cellarray');
    vert = fetch(conn,['select vertspec from StimObjData_vert where descId = ''' descId '''' ]);
end

function vert = getFaces_perStim(descId,conn)
    setdbprefs('DataReturnFormat','cellarray');
    vert = fetch(conn,['select facespec from StimObjData_vert where descId = ''' descId '''' ]);
end

function visVert = getVisibleVertices_perStim(descId,conn)
    setdbprefs('DataReturnFormat','cellarray');
    visVert = fetch(conn,['select vertspec_vis from StimObjData_vert where descId = ''' descId '''' ]);
end

function [R,L,R_image,L_image] = makeRDS(vert,face,visVert,parentId,screen,depthId,doSilh,makeImages)
    getPaths;

    % change screen props
    % t = max([(max(vert(:,1))-min(vert(:,1))) (max(vert(:,2))-min(vert(:,2)))]);
    % screen.width = 4*t;
    % screen.height = 3*t;
    screen.width = 160;
    screen.height = 120;
    screen.xRes = 640;
    screen.yRes = 480;
    
    % image props
    sparseness = 0.97;
    nDepths = 5;
        
    center = (max(vert)+min(vert)) / 2;
    vert = vert - repmat(center,size(vert,1),1);
    vert(:,3) = vert(:,3) - max(vert(:,3));
    dPts = getDpts(vert);
    shapeDepthRange = [min(vert(:,3)) max(vert(:,3))];
    backgroundDepth = 1.5*shapeDepthRange(1);
    
    [X,Y] = getPixelDistanceMap(screen);
    
    % draw the background
    count = 1;
    for x=1:screen.yRes
        for y=1:screen.xRes
            if rand > sparseness
                pointsToProject(count,:) = [X(x,y) Y(x,y) backgroundDepth]; %#ok<AGROW>
                count = count + 1;
            end
        end
    end
    
    % project background
    R = projectToScreen(pointsToProject,screen,'right');
    L = projectToScreen(pointsToProject,screen,'left');
    
    silhDepths = linspace(mean(shapeDepthRange),-mean(shapeDepthRange),nDepths);
    threeDdepths = linspace(0,shapeDepthRange(1),nDepths);
    
    silhDepth = silhDepths(depthId);
    vert(:,3) = vert(:,3) - threeDdepths(depthId);
    
    % project silhouette or vert; this is for removing the background
    % points that will be filled with the shape eventually
    if doSilh
        dPtsR = projectToScreen([dPts(:,1) dPts(:,2) silhDepth*ones(size(dPts,1),1)],screen,'right');
        dPtsL = projectToScreen([dPts(:,1) dPts(:,2) silhDepth*ones(size(dPts,1),1)],screen,'left');
    else
        vertR = projectToScreen(vert,screen,'right');
        vertL = projectToScreen(vert,screen,'left');
        
        dPtsR = getDpts(vertR);
        dPtsL = getDpts(vertL);
    end
    
    % remove background points
    R(inpolygon(R(:,1),R(:,2),dPtsR(:,1),dPtsR(:,2)),:) = [];
    L(inpolygon(L(:,1),L(:,2),dPtsL(:,1),dPtsL(:,2)),:) = [];
    
    % draw shape
    pointsToProject = []; count = 1;
    for x=1:screen.yRes
        for y=1:screen.xRes
            if rand > sparseness
                if inpolygon(X(x,y),Y(x,y),dPts(:,1),dPts(:,2))
                    screenPt = [X(x,y) Y(x,y) 0];
                    if doSilh
                        z = silhDepth;
                    else
                        z = findNearestPt_z(vert,visVert,face,screenPt);
                    end
                    
                    pointsToProject(count,:) = [X(x,y) Y(x,y) z]; %#ok<AGROW>
                    count = count + 1;
                end
            end
        end
    end
    
    % project shape
    R = [R;projectToScreen(pointsToProject,screen,'right')];
    L = [L;projectToScreen(pointsToProject,screen,'left')];
    
    if makeImages
        filePath = [plotPath '/temp_RDS/' parentId '_depth-' num2str(depthId) '_silh-' num2str(doSilh)];
        [L_image,R_image] = saveImages(L,R,filePath);
    end
end

function makeRDK(vert,face,visVert,parentId,screen,doSilh)
    getPaths;
    
    screen.width = 160;
    screen.height = 120;
    screen.xRes = 640;
    screen.yRes = 480;

    % image props
    sparseness = 0.97;
    dotSize = 6;
        
    center = (max(vert)+min(vert)) / 2;
    vert = vert - repmat(center,size(vert,1),1);
    vert_orig = vert;
    
    [X,Y] = getPixelDistanceMap(screen);
    
    temp_idx = sort(randi(numel(X),round(numel(X)*(1-sparseness)),1));
    pointsToDraw_orig = [X(temp_idx) Y(temp_idx)];
    % this pointsToDraw is background points; common across rotations 
    
    dPts = getDpts(vert);
    temp_idx = sort(randi(numel(X),round(numel(X)*(1-sparseness)),1));
    pointsToDraw_in = [X(temp_idx) Y(temp_idx)];
    inPointsIdx = inpolygon(pointsToDraw_in(:,1),pointsToDraw_in(:,2),dPts(:,1),dPts(:,2));
    inPoints = pointsToDraw_in(inPointsIdx,:);
    
    if doSilh
        % get hole, put points in it. simple. inPoints are onPoints.
        % also change vert_orig to the onPoints
        silhDepth = 3; % max(vert_orig(:,3));
        onPoints_orig = [inPoints silhDepth*ones(size(inPoints,1),1)];
        vert_orig = [dPts silhDepth*ones(size(dPts,1),1)];
        onPtsVis = []; % for parallel processing; even though not used for 2D
    else
        % take a union of every point visible at all the angles and use
        % that as the visible set.
        
        visible_temp = sum(visVert,2) > 0;
        [onPoints_orig,onPointsVertId] = getOnPointsFromInPoints(inPoints,vert_orig,face,visible_temp);
        onPtsVis = visVert(onPointsVertId,:);
        onPtsVis = hmmThis(onPtsVis);
    end
    % this onPoints is common across rotations
    
    filePath = [plotPath '/temp_RDK/img/' parentId '_silh-' num2str(doSilh)];
    [~,angles,~,angleIdx] = getAngles(doSilh);
    
    if doSilh
        parfor frameNum=1:length(angles)        
            hF = figure('position',[668,281,1350,959]);
            ha = tight_subplot(1,1,0,0,0); 
            hold(ha(1),'on');

            disp(['RDK frame ' num2str(frameNum)])

            angle = angles(frameNum);
            onPoints = rotateVert(onPoints_orig,angle); 

            vert = rotateVert(vert_orig,angle); % to get the silh -> and remove background points
            pointsToDraw = pointsToDraw_orig;
            dPts = vert;
            inPointsIdx = inpolygon(pointsToDraw_orig(:,1),pointsToDraw_orig(:,2),dPts(:,1),dPts(:,2));
            pointsToDraw(inPointsIdx,:) = [];
            pointsToDraw = [pointsToDraw; onPoints(:,1:2)];

            cla(ha(1))
            plot(ha(1),pointsToDraw(:,1),pointsToDraw(:,2),'ws','MarkerSize',dotSize,'MarkerFaceColor','w','MarkerEdgeColor','none')
            axis(ha(1),[-screen.width/2 screen.width/2 -screen.height/2 screen.height/2]) %#ok<PFBNS>
            set(ha(1),'xtick',[],'ytick',[],'box','on','color',[0.3 0.3 0.3],'xcolor',[0.3 0.3 0.3],'ycolor',[0.3 0.3 0.3])

            img_rdk = export_fig([filePath '_f-' num2str(frameNum) '.png'],ha(1));

%             img_rdk(960,:) = 0.3; img_rdk(:,1281:end) = [];
%             img_rdk = padarray(img_rdk,[32 768/2]);
%             imwrite(repmat(img_rdk,1,1,3),[filePath '_f-' num2str(frameNum) '.png']);

            close(hF);
        end
    else
        parfor frameNum=1:length(angles)        
            hF = figure('position',[668,281,1350,959]);
            ha = tight_subplot(1,1,0,0,0); 
            hold(ha(1),'on');

            disp(['RDK frame ' num2str(frameNum)])

            angle = angles(frameNum);
            onPoints = rotateVert(onPoints_orig(onPtsVis(:,frameNum)==1,:),angle); %#ok<PFBNS>

            vert = rotateVert(vert_orig,angle); % to get the silh -> and remove background points
            pointsToDraw = pointsToDraw_orig;
            dPts = getDpts(vert);
            inPointsIdx = inpolygon(pointsToDraw_orig(:,1),pointsToDraw_orig(:,2),dPts(:,1),dPts(:,2));
            pointsToDraw(inPointsIdx,:) = [];
            pointsToDraw = [pointsToDraw; onPoints(:,1:2)];

            cla(ha(1))
            plot(ha(1),pointsToDraw(:,1),pointsToDraw(:,2),'ws','MarkerSize',dotSize,'MarkerFaceColor','w','MarkerEdgeColor','none')
            axis(ha(1),[-screen.width/2 screen.width/2 -screen.height/2 screen.height/2]) %#ok<PFBNS>
            set(ha(1),'xtick',[],'ytick',[],'box','on','color',[0.3 0.3 0.3],'xcolor',[0.3 0.3 0.3],'ycolor',[0.3 0.3 0.3])

            img_rdk = export_fig([filePath '_f-' num2str(frameNum) '.png'],ha(1));
            
%             img_rdk(960,:) = 0.3; img_rdk(:,1281:end) = [];
%             img_rdk = padarray(img_rdk,[32 768/2]);
%             imwrite(repmat(img_rdk,1,1,3),[filePath '_f-' num2str(frameNum) '.png']);

            close(hF);
        end
    end
    
%     videoFile = VideoWriter([plotPath '/temp_RDK/mov/' parentId '_silh-' num2str(doSilh)]);
%     videoFile.Quality = 100; 
%     videoFile.FrameRate = 60;
%     open(videoFile);
% 
%     for frameNum=1:length(angleIdx)
%         fr = im2frame(imread([filePath '_f-' num2str(angleIdx(frameNum)) '_pad.png']));
%         writeVideo(videoFile,fr);
%     end
%     close(videoFile);
end

function onPtsVis = hmmThis(onPtsVis)
    trans = [0.95 0.05; 0.05 0.95];
    emis = [0.8 0.2; 0.2 0.8];
    
%     trans = [0.9 0.1; 0.1 0.9];
%     emis = [0.9 0.1; 0.1 0.9];
    for ii=1:size(onPtsVis,1)
        adjOn = onPtsVis(ii,:) + 1;
        adjOn = hmmviterbi(adjOn,trans,emis);
        onPtsVis(ii,:) = adjOn - 1;
    end
end

function [onPoints,onPointsVertId] = getOnPointsFromInPoints(inPoints,vert,face,visible)
    onPoints = nan(size(inPoints,1),3);
    onPointsVertId = nan(size(inPoints,1),1);
    for ii=1:size(inPoints,1)
        [z,vertId] = findNearestPt_z(vert,visible,face,inPoints(ii,:));
        onPoints(ii,:) = [inPoints(ii,:) z];
        onPointsVertId(ii) = vertId;
    end
end

function vert = rotateVert(vert,angle)
    angle = deg2rad(angle);
    
    Ry = [  cos(angle)  0   sin(angle);...
            0           1   0;...
            -sin(angle) 0   cos(angle)];
        
    vert = vert*Ry; 
end

function [L_image,R_image] = saveImages(L,R,filePath)
    getPaths;
    dotSize = 6;
    
    hF = figure('position',[668,281,1350,959]);
    ha = tight_subplot(1,1,0,0,0); 
    hold(ha(1),'on');
    plot(ha(1),L(:,1),L(:,2),'ws','MarkerSize',dotSize,'MarkerFaceColor','w','MarkerEdgeColor','none')
    axis(ha(1),'image')
    set(ha(1),'xtick',[],'ytick',[],'box','on','color',[0.3 0.3 0.3],'xcolor',[0.3 0.3 0.3],'ycolor',[0.3 0.3 0.3])
    L_image = export_fig([filePath '_L.png'],ha(1));
    
%     L_image(960,:) = 0.3; L_image(:,1281:end) = [];
%     L_image = padarray(L_image,[32 768/2]);
%     imwrite(repmat(L_image,1,1,3),[filePath '_L.png']);

    clf(hF);
    ha = tight_subplot(1,1,0,0,0); 
    hold(ha(1),'on');
    plot(ha(1),R(:,1),R(:,2),'ws','MarkerSize',dotSize,'MarkerFaceColor','w','MarkerEdgeColor','none')
    axis(ha(1),'image')
    set(ha(1),'xtick',[],'ytick',[],'box','on','color',[0.3 0.3 0.3],'xcolor',[0.3 0.3 0.3],'ycolor',[0.3 0.3 0.3])
    R_image = export_fig([filePath '_R.png'],ha(1));
    close(hF);
    
%     R_image(960,:) = 0.3; R_image(:,1281:end) = [];
%     R_image = padarray(R_image,[32 768/2]);
%     imwrite(repmat(R_image,1,1,3),[filePath '_R.png']);
end

function pts_project = projectToScreen(pts,screen,screenStr)
    t1 = screen.dist*pts(:,1);
    t2 = screen.eyeDist*pts(:,3)/2;
    t3 = pts(:,3) + screen.dist;
    t4 = (screen.dist * pts(:,2))./(pts(:,3) + screen.dist);

    if strcmp(screenStr,'right')
        pts_project(:,1) = (t1-t2) ./ t3;
        pts_project(:,2) = t4;
    else
        pts_project(:,1) = (t1+t2) ./ t3;
        pts_project(:,2) = t4;
    end
end

function [X,Y] = getPixelDistanceMap(screen)
    x = linspace(-screen.width/2,0,1+screen.xRes/2);
    x = [x(1:end-1) linspace(0,screen.width/2,screen.xRes/2)];
    y = linspace(-screen.height/2,0,1+screen.yRes/2);
    y = [y(1:end-1) linspace(0,screen.height/2,screen.yRes/2)];
    [X,Y] = meshgrid(x,y);
end

function dPts = getDpts(vert)
    uniquePoints = unique(vert,'rows');
    px = uniquePoints(:,1); py = uniquePoints(:,2);

    boundaryIdx = boundary(px,py,1);
    boundarpyts = [px(boundaryIdx) py(boundaryIdx)];
    boundarpyts = interparc(100,boundarpyts(:,1),boundarpyts(:,2),'spline');
    dPts = getDensePoints(boundarpyts,[],300);
end

function [z,nearestVert] = findNearestPt_z(vert,visible,face,screenPt)    
    visVert = vert(visible==1,:);
    screenPtDist = repmat(screenPt(1:2),size(visVert,1),1);
    dist = sqrt(sum((visVert(:,1:2)-screenPtDist).^2,2));
    [~,nearestVert] = min(dist);
    visibleIdx = find(visible);
    nearestVert = visibleIdx(nearestVert);
    z = vert(nearestVert,3);
    
%     nearestFace = find(sum(face == nearestVert,2));
%     for correctTri=1:length(nearestFace)
%         tri = vert(face(nearestFace(correctTri),:),:);
%         if inpolygon(screenPt(1),screenPt(2),tri(:,1),tri(:,2))
%             break;
%         end
%     end
%     
%     % try pos z
%     pt = findPtOnTri(tri,screenPt,[0 0 1]);
%    
%     % default to nearestVert z
%     if isempty(pt)
%         z = vert(nearestVert,3);
%         disp('def');
%     else
%         z = pt(3);
%     end
    
end

function pt = findPtOnTri(tri,screenPt,unitVec)
    P1 = tri(1,:); P2 = tri(2,:); P3 = tri(3,:);
    normal = cross(P1-P2, P1-P3);
    syms x y z;
    P = [x,y,z];
    planefunction = dot(normal, P-P1);
    
    dist = 5000;
    P4 = screenPt; P5 = findPtAlongVect(screenPt,unitVec,dist);
    syms t;
    line = P4 + t*(P5-P4);
    newfunction = subs(planefunction, P, line);
    t0 = solve(newfunction);
    pt = double(subs(line, t, t0));
%     subs(planefunction, P, pt);
end

function P5 = findPtAlongVect(screenPt,unitVec,dist)
    % find a point along a vector (vec) from origin (pt0) at a distance
    % (dist)
    unitVec = unitVec./norm(unitVec);   % normalize vector
    P5 = screenPt + unitVec.*dist;
end

function visible = getVisibleForAngle(visible,angle)
    [~,~,angles,~] = getAngles(true);
    zeroIdx = find(round(cumsum(angles),1) == angle);
    if ~isempty(zeroIdx)
        visible = visible(zeroIdx,:);
    else
        disp(['Angle ' num2str(angle) ' not found in visible matrix.']);
    end
end

function [angles,uniqueAngles,diffAngles,angleIdx] = getAngles(doSilh)
    if ~exist('doSilh','var'); doSilh = false; end
    if doSilh
        angleRange = [-20 20];
    else
        angleRange = [-7 7];
    end

    stimTime = 1750/1000;
    refreshRate = 85;
    
    nRot = 2;
    
    nStaticFrames = 1;
    nDynamicFrames = floor(((stimTime * refreshRate) - nStaticFrames)/(4*nRot));

    s0 = linspace(0,0,nStaticFrames);
    s1 = linspace(0,angleRange(1),nDynamicFrames+1); s1(1) = [];
    s2 = linspace(angleRange(1),0,nDynamicFrames+1); s2(1) = [];
    s3 = linspace(0,angleRange(2),nDynamicFrames+1); s3(1) = [];
    s4 = linspace(angleRange(2),0,nDynamicFrames+1); s4(1) = [];
    s4(end) = [];
    
    angles = [s0 s1 s2 s3 s4];
    angles = repmat(angles,1,nRot);
    
    [uniqueAngles,~,angleIdx] = unique(round(angles,2));
    diffAngles = [min(angles) abs(angles(2)-angles(1))*ones(1,(length(unique(round(angles,3)))-1))];
end

function visible = fixVisible(visible)
    [~,~,~,angleIdx] = getAngles(false);
    visible = visible(angleIdx,:); 
    visible = visible'; % visible is length(vert) x nFrames
end
